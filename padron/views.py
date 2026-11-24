from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, Q, Count

from usuarios.models import Solicitud, Empresa, MUNICIPIOS_TABASCO


def lista(request):
    """Padrón público de operadores inmobiliarios vigentes.

    Permite filtrar por tipo (física/moral), municipio, empresa,
    rango de horas, búsqueda por nombre, y ordenar por horas o alfabéticamente.
    """
    hoy = timezone.now().date()

    # ============================================================
    # QUERYSET BASE
    # ============================================================
    qs = (
        Solicitud.objects
        .filter(
            estado='licencia_emitida',
            fecha_vigencia_padron__gte=hoy,
            ciudadano__folio_licencia__isnull=False,
            ciudadano__activo=True,
        )
        .exclude(ciudadano__folio_licencia='')
        .select_related(
            'ciudadano',
            'ciudadano__user',
            'ciudadano__empresa',
            'datos_personales',
            'domicilio_identificacion',
        )
        .annotate(
            horas_curso=Sum('cursos_cargados__horas'),
        )
    )

    # ============================================================
    # FILTROS
    # ============================================================
    municipio_filtro = request.GET.get('municipio', '').strip()
    empresa_filtro = request.GET.get('empresa', '').strip()
    busqueda = request.GET.get('q', '').strip()
    orden = request.GET.get('orden', 'alfabetico')
    horas_filtro = request.GET.get('horas', '').strip()
    tipo_filtro = request.GET.get('tipo', '').strip()

    if municipio_filtro:
        qs = qs.filter(
            domicilio_identificacion__municipio__iexact=municipio_filtro
        )

    if empresa_filtro:
        if empresa_filtro == '__sin_empresa__':
            qs = qs.filter(ciudadano__empresa__isnull=True)
        else:
            qs = qs.filter(ciudadano__empresa__nombre__iexact=empresa_filtro)

    if busqueda:
        qs = qs.filter(ciudadano__nombre_completo__icontains=busqueda)

    # ============================================================
    # FILTRO POR TIPO (FÍSICA / MORAL)
    # ============================================================
    if tipo_filtro == 'fisica':
        qs = qs.filter(
            Q(datos_personales__regimen_fiscal='pfae') |
            Q(datos_personales__isnull=True)
        ).filter(ciudadano__empresa__isnull=True)
    elif tipo_filtro == 'moral':
        qs = qs.filter(
            Q(datos_personales__regimen_fiscal='pm') |
            Q(ciudadano__empresa__isnull=False)
        )

    # ============================================================
    # FILTRO POR RANGO DE HORAS
    # ============================================================
    # Nota: si no tiene cursos cargados, horas_curso = None.
    #       Se considera como 30h por defecto (mínimo legal).
    if horas_filtro == 'rango_0_30':
        qs = qs.filter(Q(horas_curso__isnull=True) | Q(horas_curso__lte=30))
    elif horas_filtro == 'rango_31_50':
        qs = qs.filter(horas_curso__gte=31, horas_curso__lte=50)
    elif horas_filtro == 'rango_50_mas':
        qs = qs.filter(horas_curso__gte=51)

    # ============================================================
    # ORDENAMIENTO
    # ============================================================
    if orden == 'horas':
        qs = qs.order_by('-horas_curso', 'ciudadano__nombre_completo')
    else:
        qs = qs.order_by('ciudadano__nombre_completo')

    # ============================================================
    # AGRUPACIÓN POR EMPRESA
    # ============================================================
    grupos_dict = {}

    for s in qs:
        empresa = s.ciudadano.empresa
        if empresa:
            key = ('empresa', empresa.nombre)
            nombre_grupo = empresa.nombre
        else:
            key = ('sin_empresa', 'Personas independientes')
            nombre_grupo = 'Personas independientes'

        if key not in grupos_dict:
            grupos_dict[key] = {
                'nombre': nombre_grupo,
                'empresa': empresa,
                'agentes': [],
                'total_horas': 0,
                'total_agentes': 0,
            }

        # Regla visual: 30h mínimo si no hay cursos cargados
        horas = s.horas_curso if s.horas_curso else 30

        grupos_dict[key]['agentes'].append(s)
        grupos_dict[key]['total_horas'] += horas
        grupos_dict[key]['total_agentes'] += 1

    # Ordenar los grupos: Personas independientes primero
    grupos = list(grupos_dict.values())
    if orden == 'horas':
        grupos.sort(
            key=lambda g: (
                0 if g['nombre'] == 'Personas independientes' else 1,
                -g['total_horas']
            )
        )
    else:
        grupos.sort(
            key=lambda g: (
                0 if g['nombre'] == 'Personas independientes' else 1,
                g['nombre']
            )
        )

    # ============================================================
    # EMPRESAS DISPONIBLES PARA EL FILTRO
    # ============================================================
    empresas = (
        Empresa.objects
        .filter(
            activa=True,
            agentes__folio_licencia__isnull=False,
            agentes__activo=True,
        )
        .annotate(num_agentes=Count('agentes'))
        .filter(num_agentes__gt=0)
        .order_by('nombre')
        .values_list('nombre', flat=True)
        .distinct()
    )

    # ============================================================
    # RANGOS DE HORAS PARA EL FILTRO
    # ============================================================
    rangos_horas = [
        ('', 'Todas las horas'),
        ('rango_0_30', 'Hasta 30 horas'),
        ('rango_31_50', '31 a 50 horas'),
        ('rango_50_mas', 'Más de 50 horas'),
    ]

    # ============================================================
    # CONTADORES PARA LOS BOTONES DE TIPO
    # ============================================================
    # Base sin el filtro de tipo (pero con los demás filtros aplicados)
    qs_base = (
        Solicitud.objects
        .filter(
            estado='licencia_emitida',
            fecha_vigencia_padron__gte=hoy,
            ciudadano__folio_licencia__isnull=False,
            ciudadano__activo=True,
        )
        .exclude(ciudadano__folio_licencia='')
    )

    if municipio_filtro:
        qs_base = qs_base.filter(
            domicilio_identificacion__municipio__iexact=municipio_filtro
        )
    if empresa_filtro:
        if empresa_filtro == '__sin_empresa__':
            qs_base = qs_base.filter(ciudadano__empresa__isnull=True)
        else:
            qs_base = qs_base.filter(ciudadano__empresa__nombre__iexact=empresa_filtro)
    if busqueda:
        qs_base = qs_base.filter(ciudadano__nombre_completo__icontains=busqueda)

    # Filtro de horas también aplica al contador
    if horas_filtro == 'rango_0_30':
        qs_base = qs_base.annotate(
            horas_curso=Sum('cursos_cargados__horas')
        ).filter(Q(horas_curso__isnull=True) | Q(horas_curso__lte=30))
    elif horas_filtro == 'rango_31_50':
        qs_base = qs_base.annotate(
            horas_curso=Sum('cursos_cargados__horas')
        ).filter(horas_curso__gte=31, horas_curso__lte=50)
    elif horas_filtro == 'rango_50_mas':
        qs_base = qs_base.annotate(
            horas_curso=Sum('cursos_cargados__horas')
        ).filter(horas_curso__gte=51)

    total_todos = qs_base.count()
    total_fisicas_filtro = qs_base.filter(
        Q(datos_personales__regimen_fiscal='pfae') |
        Q(datos_personales__isnull=True)
    ).filter(ciudadano__empresa__isnull=True).count()
    total_morales_filtro = qs_base.filter(
        Q(datos_personales__regimen_fiscal='pm') |
        Q(ciudadano__empresa__isnull=False)
    ).count()

    # ============================================================
    # CONTEXTO
    # ============================================================
    contexto = {
        'grupos': grupos,
        'total': qs.count(),
        'total_todos': total_todos,
        'total_fisicas_filtro': total_fisicas_filtro,
        'total_morales_filtro': total_morales_filtro,
        'municipios': MUNICIPIOS_TABASCO,
        'empresas': empresas,
        'rangos_horas': rangos_horas,
        'municipio_filtro': municipio_filtro,
        'empresa_filtro': empresa_filtro,
        'busqueda': busqueda,
        'orden': orden,
        'horas_filtro': horas_filtro,
        'tipo_filtro': tipo_filtro,
        'fecha_actualizacion': timezone.now(),
    }
    return render(request, 'padron/lista.html', contexto)