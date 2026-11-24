# usuarios/views_admin.py

from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from .models import (
    Solicitud,
    HistorialEstado,
    Ciudadano,
    Empresa,
    DatosPersonales,
    DomicilioIdentificacion,
    DocumentosNegocio,
    CursosCapacitaciones,
    Curso,
    MUNICIPIOS_TABASCO,
    ESTADOS_SOLICITUD,
)
from .emails import (
    enviar_correo_estado_cambiado,
    enviar_correo_correcciones,
    enviar_correo_pago_aprobado,
    enviar_correo_pago_rechazado,
)
from .pase_caja import generar_pase_caja
from .pdf import generar_licencia


# ============================================================
# DASHBOARD
# ============================================================

@staff_member_required
def admin_dashboard(request):
    """Panel ejecutivo con KPIs, filtros y últimas solicitudes."""
    hoy = timezone.now()
    inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total = Solicitud.objects.exclude(
        estado='borrador',
        datos_personales__isnull=True,
    ).count()

    pendientes = Solicitud.objects.filter(estado='en_revision').count()
    requiere_accion = Solicitud.objects.filter(estado='requiere_accion').count()
    aprobadas = Solicitud.objects.filter(estado='aprobada').count()
    rechazadas = Solicitud.objects.filter(estado='rechazada').count()
    licencias_emitidas = Solicitud.objects.filter(estado='licencia_emitida').count()

    pagos_cargados = Solicitud.objects.filter(
        estado='aprobada',
        pago_estado='comprobante_cargado',
    ).count()

    este_mes = Solicitud.objects.filter(fecha_envio__gte=inicio_mes).count()

    ultimas = (
        Solicitud.objects
        .exclude(estado='borrador')
        .select_related('ciudadano', 'ciudadano__user')
        .order_by('-fecha_envio')[:10]
    )

    contexto = {
        'total': total,
        'pendientes': pendientes,
        'requiere_accion': requiere_accion,
        'aprobadas': aprobadas,
        'rechazadas': rechazadas,
        'licencias_emitidas': licencias_emitidas,
        'pagos_cargados': pagos_cargados,
        'este_mes': este_mes,
        'ultimas': ultimas,
        'estados': Solicitud.ESTADOS_SOLICITUD,
        'tipos': [
            ('nuevo', 'Nuevo agente'),
            ('revalidacion', 'Revalidación'),
        ],
    }
    return render(request, 'usuarios/admin/dashboard.html', contexto)


# ============================================================
# LISTA DE SOLICITUDES CON FILTROS + PAGINACIÓN
# ============================================================

@staff_member_required
def admin_lista_solicitudes(request):
    """Lista de solicitudes con filtros avanzados y paginación."""
    qs = (
        Solicitud.objects
        .exclude(estado='borrador')
        .select_related('ciudadano', 'ciudadano__user')
        .order_by('-fecha_envio')
    )

    estado = request.GET.get('estado', '')
    tipo = request.GET.get('tipo', '')
    folio = request.GET.get('folio', '').strip()
    fecha_desde = request.GET.get('desde', '')
    fecha_hasta = request.GET.get('hasta', '')
    orden = request.GET.get('orden', '-fecha_envio')

    if estado:
        qs = qs.filter(estado=estado)
    if tipo:
        qs = qs.filter(tipo_tramite=tipo)
    if folio:
        # Buscar por folio de licencia del agente
        qs = qs.filter(ciudadano__folio_licencia__icontains=folio)
    if fecha_desde:
        qs = qs.filter(fecha_envio__date__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha_envio__date__lte=fecha_hasta)
    if orden in ['-fecha_envio', 'fecha_envio']:
        qs = qs.order_by(orden)

    # ============================================================
    # PAGINACIÓN
    # ============================================================
    paginator = Paginator(qs, 20)  # 20 por página
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    contexto = {
        'page_obj': page_obj,
        'solicitudes': page_obj,  # compatibilidad con el template
        'total_resultados': paginator.count,
        'filtros': {
            'estado': estado,
            'tipo': tipo,
            'folio': folio,
            'desde': fecha_desde,
            'hasta': fecha_hasta,
            'orden': orden,
        },
        'estados': Solicitud.ESTADOS_SOLICITUD,
        'tipos': [
            ('nuevo', 'Nuevo agente'),
            ('revalidacion', 'Revalidación'),
        ],
    }
    return render(request, 'usuarios/admin/lista_solicitudes.html', contexto)


# ============================================================
# DETALLE DE SOLICITUD + ACCIONES
# ============================================================

@staff_member_required
def admin_detalle_solicitud(request, solicitud_id):
    """Detalle completo de una solicitud + acciones."""
    solicitud = get_object_or_404(
        Solicitud.objects.select_related('ciudadano', 'ciudadano__user'),
        id=solicitud_id,
    )

    if request.method == 'POST':
        accion = request.POST.get('accion')
        comentario = request.POST.get('comentario', '').strip()

        if accion == 'aprobar':
            estado_anterior = solicitud.estado
            solicitud.cambiar_estado('aprobada', usuario=request.user, comentario=comentario)
            solicitud.pase_caja_generado = True
            solicitud.save(update_fields=['pase_caja_generado'])

            try:
                enviar_correo_estado_cambiado(solicitud, estado_anterior, comentario)
            except Exception:
                pass

            messages.success(
                request,
                f"Solicitud {solicitud.folio} aprobada. El ciudadano ya puede "
                f"descargar su pase de pago."
            )
            return redirect('usuarios:admin_detalle_solicitud', solicitud_id=solicitud.id)

        elif accion == 'rechazar':
            if not comentario:
                messages.error(request, "Debes indicar un motivo de rechazo.")
            else:
                estado_anterior = solicitud.estado
                solicitud.cambiar_estado('rechazada', usuario=request.user, comentario=comentario)
                try:
                    enviar_correo_estado_cambiado(solicitud, estado_anterior, comentario)
                except Exception:
                    pass
                messages.warning(request, f"Solicitud {solicitud.folio} rechazada.")
                return redirect('usuarios:admin_detalle_solicitud', solicitud_id=solicitud.id)

        elif accion == 'correcciones':
            if not comentario:
                messages.error(request, "Debes indicar qué debe corregir el ciudadano.")
            else:
                estado_anterior = solicitud.estado
                solicitud.cambiar_estado(
                    'requiere_accion',
                    usuario=request.user,
                    comentario=comentario,
                    motivo_accion='corregir_documentos',
                )
                try:
                    enviar_correo_correcciones(solicitud, comentario)
                except Exception:
                    pass
                messages.warning(
                    request,
                    f"Se solicitaron correcciones al folio {solicitud.folio}."
                )
                return redirect('usuarios:admin_detalle_solicitud', solicitud_id=solicitud.id)

        elif accion == 'validar_pago':
            if not (
                solicitud.estado == 'aprobada'
                and solicitud.pago_estado == 'comprobante_cargado'
            ):
                messages.error(
                    request,
                    "Solo se puede validar el pago cuando el comprobante está en revisión."
                )
            else:
                estado_anterior = solicitud.estado
                solicitud.cambiar_estado(
                    'licencia_emitida',
                    usuario=request.user,
                    comentario=comentario or 'Pago validado. Licencia emitida.',
                )

                if not solicitud.ciudadano.folio_licencia:
                    solicitud.ciudadano.asignar_folio_licencia(
                        folio_sugerido=solicitud.folio
                    )
                    solicitud.refresh_from_db()
                    solicitud.ciudadano.refresh_from_db()

                solicitud.refresh_from_db()

                try:
                    enviar_correo_pago_aprobado(solicitud)
                except Exception:
                    pass

                folio_lic = solicitud.ciudadano.folio_licencia or '—'
                messages.success(
                    request,
                    f"Pago validado. Licencia {folio_lic} emitida "
                    f"para {solicitud.ciudadano.nombre_completo}."
                )
                return redirect('usuarios:admin_detalle_solicitud', solicitud_id=solicitud.id)

        elif accion == 'rechazar_pago':
            if not (
                solicitud.estado == 'aprobada'
                and solicitud.pago_estado == 'comprobante_cargado'
            ):
                messages.error(
                    request,
                    "Solo se puede rechazar un comprobante cuando está en revisión."
                )
            elif not comentario:
                messages.error(request, "Debes indicar el motivo del rechazo del comprobante.")
            else:
                estado_anterior = solicitud.estado
                solicitud.cambiar_estado(
                    'requiere_accion',
                    usuario=request.user,
                    comentario=comentario,
                    motivo_accion='resubir_comprobante',
                    pago_estado='comprobante_rechazado',
                )
                try:
                    enviar_correo_pago_rechazado(solicitud, comentario)
                except Exception:
                    pass
                messages.warning(
                    request,
                    f"Comprobante rechazado para el folio {solicitud.folio}."
                )
                return redirect('usuarios:admin_detalle_solicitud', solicitud_id=solicitud.id)

        elif accion == 'comentar':
            if not comentario:
                messages.error(request, "Escribe un comentario.")
            else:
                HistorialEstado.objects.create(
                    solicitud=solicitud,
                    estado_anterior=solicitud.estado,
                    estado_nuevo=solicitud.estado,
                    usuario=request.user,
                    comentario=comentario,
                )
                messages.info(request, "Comentario agregado al historial.")
                return redirect('usuarios:admin_detalle_solicitud', solicitud_id=solicitud.id)

    contexto = {
        'solicitud': solicitud,
        'datos_personales': getattr(solicitud, 'datos_personales', None),
        'domicilio': getattr(solicitud, 'domicilio_identificacion', None),
        'documentos': getattr(solicitud, 'documentos_negocio', None),
        'cursos': getattr(solicitud, 'cursos_capacitaciones', None),
        'historial': solicitud.historial.all(),
        'folio_licencia_ciudadano': solicitud.ciudadano.folio_licencia,
    }
    return render(request, 'usuarios/admin/detalle_solicitud.html', contexto)


# ============================================================
# DESCARGAR PASE DE CAJA (ADMIN)
# ============================================================

@staff_member_required
def admin_descargar_pase_caja(request, solicitud_id):
    """Permite al admin descargar el pase de caja en PDF."""
    solicitud = get_object_or_404(
        Solicitud.objects.select_related('ciudadano', 'ciudadano__user'),
        id=solicitud_id,
    )

    if solicitud.estado != 'aprobada':
        messages.error(
            request,
            "Solo se puede generar el pase de caja de solicitudes aprobadas."
        )
        return redirect('usuarios:admin_detalle_solicitud', solicitud_id=solicitud.id)

    try:
        buffer = generar_pase_caja(solicitud)
    except Exception as e:
        messages.error(request, f"Error al generar el pase de caja: {e}")
        return redirect('usuarios:admin_detalle_solicitud', solicitud_id=solicitud.id)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="pase_caja_{solicitud.folio}.pdf"'
    return response


# ============================================================
# DESCARGAR LICENCIA (ADMIN)
# ============================================================

@staff_member_required
def admin_descargar_licencia(request, solicitud_id):
    """Permite al admin descargar la licencia emitida en PDF."""
    solicitud = get_object_or_404(
        Solicitud.objects.select_related('ciudadano', 'ciudadano__user'),
        id=solicitud_id,
    )

    if solicitud.estado != 'licencia_emitida':
        messages.error(
            request,
            "Solo se puede descargar la licencia cuando ya fue emitida."
        )
        return redirect('usuarios:admin_detalle_solicitud', solicitud_id=solicitud.id)

    folio_lic = solicitud.ciudadano.folio_licencia
    if not folio_lic:
        folio_lic = solicitud.ciudadano.asignar_folio_licencia(
            folio_sugerido=solicitud.folio
        )
        messages.info(
            request,
            f"Se asignó automáticamente el folio de licencia: {folio_lic}"
        )

    try:
        buffer = generar_licencia(solicitud)
    except Exception as e:
        messages.error(request, f"Error al generar la licencia: {e}")
        return redirect('usuarios:admin_detalle_solicitud', solicitud_id=solicitud.id)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="licencia_{folio_lic}.pdf"'
    return response


# ============================================================
# EXPORTAR A EXCEL
# ============================================================

@staff_member_required
def admin_exportar_excel(request):
    """Exporta a Excel TODAS las solicitudes ordenadas, con filtros opcionales."""
    qs = (
        Solicitud.objects
        .exclude(estado='borrador')
        .select_related('ciudadano', 'ciudadano__user', 'datos_personales')
        .order_by('-fecha_envio')
    )

    estado = request.GET.get('estado', '')
    tipo = request.GET.get('tipo', '')
    folio = request.GET.get('folio', '').strip()
    fecha_desde = request.GET.get('desde', '')
    fecha_hasta = request.GET.get('hasta', '')
    orden = request.GET.get('orden', '-fecha_envio')

    if estado:
        qs = qs.filter(estado=estado)
    if tipo:
        qs = qs.filter(tipo_tramite=tipo)
    if folio:
        qs = qs.filter(ciudadano__folio_licencia__icontains=folio)
    if fecha_desde:
        qs = qs.filter(fecha_envio__date__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha_envio__date__lte=fecha_hasta)

    ordenes_validos = ['-fecha_envio', 'fecha_envio']
    if orden in ordenes_validos:
        qs = qs.order_by(orden)
    else:
        qs = qs.order_by('-fecha_envio')

    wb = Workbook()
    ws = wb.active
    ws.title = "Solicitudes"

    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="991547", end_color="991547", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    border = Border(
        left=Side(style='thin', color='d1d5db'),
        right=Side(style='thin', color='d1d5db'),
        top=Side(style='thin', color='d1d5db'),
        bottom=Side(style='thin', color='d1d5db'),
    )

    encabezados = [
        'Folio agente', 'Folio trámite', 'Ciudadano', 'Empresa',
        'Email', 'Teléfono', 'Tipo de trámite', 'Estado',
        'Sub-estado pago', 'Avance (%)', 'Número de oficio', 'Municipio',
        'Fecha de envío', 'Fecha emisión licencia', 'Vigencia padrón',
    ]

    for col_num, titulo in enumerate(encabezados, 1):
        cell = ws.cell(row=1, column=col_num, value=titulo)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = border

    for row_num, s in enumerate(qs, 2):
        municipio = ''
        dom = getattr(s, 'domicilio_identificacion', None)
        if dom and dom.municipio:
            municipio = dom.municipio

        empresa_val = s.ciudadano.empresa.nombre if s.ciudadano.empresa else ''

        ws.cell(row=row_num, column=1, value=s.ciudadano.folio_licencia or '').border = border
        ws.cell(row=row_num, column=2, value=s.folio or '').border = border
        ws.cell(row=row_num, column=3, value=s.ciudadano.nombre_completo or '').border = border
        ws.cell(row=row_num, column=4, value=empresa_val).border = border
        ws.cell(row=row_num, column=5, value=s.ciudadano.user.email or '').border = border
        ws.cell(row=row_num, column=6, value=s.ciudadano.telefono or '').border = border
        ws.cell(row=row_num, column=7, value=s.get_tipo_tramite_display()).border = border
        ws.cell(row=row_num, column=8, value=s.get_estado_display()).border = border
        ws.cell(row=row_num, column=9, value=s.get_pago_estado_display()).border = border
        ws.cell(row=row_num, column=10, value=s.porcentaje_avance).border = border
        ws.cell(row=row_num, column=11, value=s.numero_oficio or '').border = border
        ws.cell(row=row_num, column=12, value=municipio).border = border
        ws.cell(
            row=row_num, column=13,
            value=s.fecha_envio.strftime('%d/%m/%Y %H:%M') if s.fecha_envio else ''
        ).border = border
        ws.cell(
            row=row_num, column=14,
            value=s.fecha_emision_licencia.strftime('%d/%m/%Y %H:%M') if s.fecha_emision_licencia else ''
        ).border = border
        ws.cell(
            row=row_num, column=15,
            value=s.fecha_vigencia_padron.strftime('%d/%m/%Y') if s.fecha_vigencia_padron else ''
        ).border = border

    anchos = [14, 16, 32, 28, 30, 14, 30, 28, 22, 12, 24, 20, 20, 22, 18]
    for i, ancho in enumerate(anchos, 1):
        ws.column_dimensions[get_column_letter(i)].width = ancho

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:O{ws.max_row}"

    ws2 = wb.create_sheet("Resumen")
    ws2['A1'] = 'Resumen de solicitudes'
    ws2['A1'].font = Font(bold=True, size=14, color="991547")
    ws2.merge_cells('A1:B1')

    ws2['A3'] = 'Estado'
    ws2['B3'] = 'Cantidad'
    ws2['A3'].font = header_font
    ws2['B3'].font = header_font
    ws2['A3'].fill = header_fill
    ws2['B3'].fill = header_fill
    ws2['A3'].alignment = header_align
    ws2['B3'].alignment = header_align

    fila = 4
    for valor, etiqueta in ESTADOS_SOLICITUD:
        count = qs.filter(estado=valor).count()
        ws2.cell(row=fila, column=1, value=etiqueta).border = border
        ws2.cell(row=fila, column=2, value=count).border = border
        ws2.cell(row=fila, column=2).alignment = Alignment(horizontal="center")
        fila += 1

    ws2.cell(row=fila, column=1, value='TOTAL').font = Font(bold=True)
    ws2.cell(row=fila, column=1).border = border
    ws2.cell(row=fila, column=2, value=qs.count()).font = Font(bold=True)
    ws2.cell(row=fila, column=2).border = border
    ws2.cell(row=fila, column=2).alignment = Alignment(horizontal="center")

    ws2.column_dimensions['A'].width = 40
    ws2.column_dimensions['B'].width = 15

    partes = ['solicitudes']
    if estado:
        partes.append(estado)
    if tipo:
        partes.append(tipo)
    partes.append(datetime.now().strftime('%Y%m%d_%H%M'))
    filename = "_".join(partes) + ".xlsx"

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


# ============================================================
# EDITAR SOLICITUD (ADMIN)
# ============================================================

@staff_member_required
def admin_editar_solicitud(request, solicitud_id):
    """Permite al admin editar cualquier campo de una solicitud."""
    solicitud = get_object_or_404(
        Solicitud.objects.select_related('ciudadano', 'ciudadano__user'),
        id=solicitud_id,
    )

    datos, _ = DatosPersonales.objects.get_or_create(solicitud=solicitud)
    domicilio, _ = DomicilioIdentificacion.objects.get_or_create(solicitud=solicitud)
    documentos, _ = DocumentosNegocio.objects.get_or_create(solicitud=solicitud)
    cursos, _ = CursosCapacitaciones.objects.get_or_create(solicitud=solicitud)

    if request.method == 'POST':
        cambios = []

        # ============================================================
        # CIUDADANO (nombre, empresa, teléfono)
        # ============================================================
        nuevo_nombre = request.POST.get('nombre_completo', '').strip().upper()
        if nuevo_nombre and nuevo_nombre != solicitud.ciudadano.nombre_completo:
            cambios.append(f"Nombre: '{solicitud.ciudadano.nombre_completo}' → '{nuevo_nombre}'")
            solicitud.ciudadano.nombre_completo = nuevo_nombre

        empresa_nombre = request.POST.get('empresa_nombre', '').strip().upper()
        empresa_actual = solicitud.ciudadano.empresa.nombre if solicitud.ciudadano.empresa else ''
        if empresa_nombre != empresa_actual:
            if empresa_nombre:
                empresa = Empresa.objects.filter(nombre__iexact=empresa_nombre).first()
                if not empresa:
                    empresa = Empresa.objects.create(nombre=empresa_nombre)
                solicitud.ciudadano.empresa = empresa
                cambios.append(f"Empresa: '{empresa_actual}' → '{empresa_nombre}'")
            else:
                solicitud.ciudadano.empresa = None
                cambios.append(f"Empresa: '{empresa_actual}' → (vacío)")

        nuevo_telefono = request.POST.get('telefono', '').strip()
        if nuevo_telefono and nuevo_telefono != solicitud.ciudadano.telefono:
            cambios.append(f"Teléfono: '{solicitud.ciudadano.telefono}' → '{nuevo_telefono}'")
            solicitud.ciudadano.telefono = nuevo_telefono

        # ============================================================
        # EMAIL
        # ============================================================
        nuevo_email = request.POST.get('email', '').strip().lower()
        if nuevo_email and nuevo_email != solicitud.ciudadano.user.email:
            existe = User.objects.filter(email__iexact=nuevo_email).exclude(
                pk=solicitud.ciudadano.user.pk
            ).exists()
            if existe:
                messages.error(request, f"El email '{nuevo_email}' ya está registrado.")
                return redirect('usuarios:admin_editar_solicitud', solicitud_id=solicitud.id)
            cambios.append(f"Email: '{solicitud.ciudadano.user.email}' → '{nuevo_email}'")
            solicitud.ciudadano.user.email = nuevo_email
            solicitud.ciudadano.user.username = nuevo_email
            solicitud.ciudadano.user.save()

        # ============================================================
        # DATOS PERSONALES
        # ============================================================
        nuevos_campos = {
            'regimen_fiscal': request.POST.get('regimen_fiscal', '').strip(),
            'sexo': request.POST.get('sexo', '').strip(),
            'rfc': request.POST.get('rfc', '').strip().upper(),
            'curp': request.POST.get('curp', '').strip().upper(),
            'tipo_tramite': request.POST.get('tipo_tramite', '').strip(),
        }
        for campo, valor in nuevos_campos.items():
            if valor and valor != getattr(datos, campo):
                cambios.append(f"{campo}: '{getattr(datos, campo)}' → '{valor}'")
                setattr(datos, campo, valor)
        datos.save()

        # ============================================================
        # DOMICILIO
        # ============================================================
        nuevo_municipio = request.POST.get('municipio', '').strip().upper()
        if nuevo_municipio != domicilio.municipio:
            cambios.append(f"Municipio: '{domicilio.municipio}' → '{nuevo_municipio}'")
            domicilio.municipio = nuevo_municipio

        nueva_direccion = request.POST.get('calle_numero_colonia_cp', '').strip().upper()
        if nueva_direccion != domicilio.calle_numero_colonia_cp:
            cambios.append("Dirección actualizada")
            domicilio.calle_numero_colonia_cp = nueva_direccion

        if request.FILES.get('comprobante_domicilio'):
            cambios.append("Comprobante de domicilio reemplazado")
            domicilio.comprobante_domicilio = request.FILES['comprobante_domicilio']
        if request.FILES.get('identificacion_oficial'):
            cambios.append("Identificación oficial reemplazada")
            domicilio.identificacion_oficial = request.FILES['identificacion_oficial']
        if request.FILES.get('foto_agente'):
            cambios.append("Foto del agente reemplazada")
            domicilio.foto_agente = request.FILES['foto_agente']
        domicilio.save()

        # ============================================================
        # DOCUMENTOS
        # ============================================================
        docs_campos = [
            'constancia_situacion_fiscal', 'constancia_profeco',
            'carta_no_antecedentes', 'carta_bajo_protesta',
            'acta_constitutiva', 'poder_notarial', 'logotipo_empresa',
            'constancia_inscripcion_anterior',
        ]
        for campo in docs_campos:
            if request.FILES.get(campo):
                cambios.append(f"{campo} reemplazado")
                setattr(documentos, campo, request.FILES[campo])
        documentos.save()

        # ============================================================
        # CURSOS
        # ============================================================
        if request.FILES.get('carta_compromiso'):
            cambios.append("Carta compromiso reemplazada")
            cursos.carta_compromiso = request.FILES['carta_compromiso']
        cursos.save()

        # ============================================================
        # SOLICITUD (estado, folio, oficio, fechas, motivo, pago, comentario)
        # ============================================================
        nuevo_estado = request.POST.get('estado', '').strip()
        estado_anterior = solicitud.estado
        if nuevo_estado and nuevo_estado != estado_anterior:
            cambios.append(f"Estado: '{estado_anterior}' → '{nuevo_estado}'")
            solicitud.estado = nuevo_estado

        nuevo_folio = request.POST.get('folio', '').strip().upper()
        if nuevo_folio and nuevo_folio != solicitud.folio:
            existe = Solicitud.objects.filter(folio=nuevo_folio).exclude(
                pk=solicitud.pk
            ).exists()
            if existe:
                messages.error(request, f"El folio '{nuevo_folio}' ya existe en otra solicitud.")
                return redirect('usuarios:admin_editar_solicitud', solicitud_id=solicitud.id)
            cambios.append(f"Folio: '{solicitud.folio}' → '{nuevo_folio}'")
            solicitud.folio = nuevo_folio

        nuevo_oficio = request.POST.get('numero_oficio', '').strip()
        if nuevo_oficio != solicitud.numero_oficio:
            cambios.append(f"Número de oficio: '{solicitud.numero_oficio}' → '{nuevo_oficio}'")
            solicitud.numero_oficio = nuevo_oficio

        fecha_alta = request.POST.get('fecha_alta_padron', '').strip()
        if fecha_alta:
            try:
                solicitud.fecha_alta_padron = datetime.strptime(fecha_alta, '%Y-%m-%d').date()
            except ValueError:
                pass

        fecha_vigencia = request.POST.get('fecha_vigencia_padron', '').strip()
        if fecha_vigencia:
            try:
                solicitud.fecha_vigencia_padron = datetime.strptime(fecha_vigencia, '%Y-%m-%d').date()
            except ValueError:
                pass

        motivo = request.POST.get('motivo_accion', '').strip()
        if motivo != solicitud.motivo_accion:
            solicitud.motivo_accion = motivo

        pago_estado = request.POST.get('pago_estado', '').strip()
        if pago_estado != solicitud.pago_estado:
            cambios.append(f"Pago estado: '{solicitud.pago_estado}' → '{pago_estado}'")
            solicitud.pago_estado = pago_estado

        comentario = request.POST.get('comentario_admin', '').strip()
        if comentario != solicitud.comentario_admin:
            cambios.append("Comentario admin actualizado")
            solicitud.comentario_admin = comentario

        # ============================================================
        # GUARDAR SOLICITUD Y CIUDADANO ANTES DE VERIFICAR FOLIO
        # ============================================================
        solicitud.save()
        solicitud.ciudadano.save()

        # ============================================================
        # FOLIO DE LICENCIA (con manejo de conflicto)
        # ============================================================
        nuevo_folio_lic = request.POST.get('folio_licencia', '').strip().upper()
        # Normalizar: quitar prefijo AM- si lo tiene
        if nuevo_folio_lic.startswith('AM-'):
            nuevo_folio_lic = nuevo_folio_lic[3:]

        if nuevo_folio_lic != (solicitud.ciudadano.folio_licencia or ''):
            if nuevo_folio_lic:
                conflicto = Ciudadano.objects.filter(
                    folio_licencia=nuevo_folio_lic
                ).exclude(pk=solicitud.ciudadano.pk).first()

                if conflicto:
                    request.session['folio_conflicto'] = {
                        'solicitud_id': solicitud.id,
                        'nuevo_folio': nuevo_folio_lic,
                        'conflicto_ciudadano_id': conflicto.id,
                        'cambios_previos': cambios,
                    }
                    return redirect('usuarios:admin_conflicto_folio')

                cambios.append(
                    f"Folio licencia: '{solicitud.ciudadano.folio_licencia}' → '{nuevo_folio_lic}'"
                )
                solicitud.ciudadano.folio_licencia = nuevo_folio_lic
                solicitud.ciudadano.save(update_fields=['folio_licencia'])
            else:
                cambios.append(
                    f"Folio licencia: '{solicitud.ciudadano.folio_licencia}' → (vacío)"
                )
                solicitud.ciudadano.folio_licencia = None
                solicitud.ciudadano.save(update_fields=['folio_licencia'])

        # ============================================================
        # HISTORIAL
        # ============================================================
        if cambios:
            HistorialEstado.objects.create(
                solicitud=solicitud,
                estado_anterior=estado_anterior,
                estado_nuevo=solicitud.estado,
                usuario=request.user,
                comentario="EDITADO POR ADMIN:\n- " + "\n- ".join(cambios),
            )
            messages.success(
                request,
                f"Solicitud {solicitud.folio} actualizada ({len(cambios)} cambios)."
            )
        else:
            messages.info(request, "No hubo cambios.")

        return redirect('usuarios:admin_detalle_solicitud', solicitud_id=solicitud.id)

    contexto = {
        'solicitud': solicitud,
        'datos_personales': datos,
        'domicilio': domicilio,
        'documentos': documentos,
        'cursos': cursos,
        'estados': Solicitud.ESTADOS_SOLICITUD,
        'motivos_accion': Solicitud.MOTIVOS_ACCION,
        'pago_estados': Solicitud.PAGO_ESTADOS,
        'tipos': [
            ('nuevo', 'Nuevo agente'),
            ('revalidacion', 'Revalidación'),
        ],
        'municipios': MUNICIPIOS_TABASCO,
        'regimenes': DatosPersonales.REGIMENES_FISCALES,
        'sexos': DatosPersonales.SEXOS,
        'empresas': Empresa.objects.filter(
            activa=True
        ).order_by('nombre').values_list('nombre', flat=True),
        'folios_ocupados': Ciudadano.objects.filter(
            folio_licencia__isnull=False
        ).exclude(
            folio_licencia=''
        ).exclude(
            pk=solicitud.ciudadano.pk
        ).values_list('folio_licencia', flat=True),
    }
    return render(request, 'usuarios/admin/editar_solicitud.html', contexto)


# ============================================================
# CONFLICTO DE FOLIO — Diálogo A/B
# ============================================================

@staff_member_required
def admin_conflicto_folio(request):
    """Muestra el diálogo cuando el admin intenta asignar un folio ocupado."""
    data = request.session.get('folio_conflicto')
    if not data:
        messages.error(request, "No hay conflicto de folio pendiente.")
        return redirect('usuarios:admin_lista_solicitudes')

    solicitud = get_object_or_404(
        Solicitud.objects.select_related('ciudadano', 'ciudadano__user'),
        id=data['solicitud_id'],
    )
    conflicto = get_object_or_404(
        Ciudadano.objects.select_related('user'),
        id=data['conflicto_ciudadano_id'],
    )

    ultima_solicitud_conflicto = (
        conflicto.solicitudes
        .filter(estado='licencia_emitida')
        .order_by('-fecha_emision_licencia')
        .first()
    )

    contexto = {
        'solicitud': solicitud,
        'conflicto': conflicto,
        'nuevo_folio': data['nuevo_folio'],
        'ultima_solicitud_conflicto': ultima_solicitud_conflicto,
    }
    return render(request, 'usuarios/admin/conflicto_folio.html', contexto)


@staff_member_required
def admin_conflicto_folio_resolver(request):
    """Resuelve el conflicto con la opción elegida (A o B)."""
    if request.method != 'POST':
        return redirect('usuarios:admin_lista_solicitudes')

    data = request.session.get('folio_conflicto')
    if not data:
        messages.error(request, "No hay conflicto de folio pendiente.")
        return redirect('usuarios:admin_lista_solicitudes')

    solicitud = get_object_or_404(
        Solicitud.objects.select_related('ciudadano'),
        id=data['solicitud_id'],
    )
    conflicto = get_object_or_404(
        Ciudadano.objects.select_related('user'),
        id=data['conflicto_ciudadano_id'],
    )
    nuevo_folio = data['nuevo_folio']
    opcion = request.POST.get('opcion', '').strip()
    motivo = request.POST.get('motivo', '').strip()

    if opcion == 'desactivar':
        # Opción A: desactivar al ciudadano que tenía el folio
        nombre_anterior = conflicto.nombre_completo
        conflicto.desactivar(
            motivo=motivo or f'Folio {nuevo_folio} reasignado a {solicitud.ciudadano.nombre_completo}.',
            usuario=request.user,
        )
        conflicto.refresh_from_db()

        # Asignar el folio a la solicitud actual
        solicitud.ciudadano.folio_licencia = nuevo_folio
        solicitud.ciudadano.save(update_fields=['folio_licencia'])
        solicitud.ciudadano.refresh_from_db()

        HistorialEstado.objects.create(
            solicitud=solicitud,
            estado_anterior=solicitud.estado,
            estado_nuevo=solicitud.estado,
            usuario=request.user,
            comentario=(
                f"ADMIN: folio '{nuevo_folio}' reasignado desde "
                f"'{nombre_anterior}' (desactivado). Motivo: {motivo or 'N/D'}"
            ),
        )

        messages.success(
            request,
            f"Folio '{nuevo_folio}' reasignado a "
            f"{solicitud.ciudadano.nombre_completo}. "
            f"{nombre_anterior} fue desactivado y su folio liberado."
        )

    elif opcion == 'reasignar_anterior':
        # Opción B: dar un folio nuevo al ciudadano que lo tenía
        folio_anterior = conflicto.folio_licencia or nuevo_folio

        sufijo = ord('B')
        folio_nuevo_anterior = f"{folio_anterior}-{chr(sufijo)}"
        while Ciudadano.objects.filter(folio_licencia=folio_nuevo_anterior).exists():
            sufijo += 1
            folio_nuevo_anterior = f"{folio_anterior}-{chr(sufijo)}"

        conflicto.folio_licencia = folio_nuevo_anterior
        conflicto.save(update_fields=['folio_licencia'])
        conflicto.refresh_from_db()

        # Asignar el folio original a la solicitud actual
        solicitud.ciudadano.folio_licencia = nuevo_folio
        solicitud.ciudadano.save(update_fields=['folio_licencia'])
        solicitud.ciudadano.refresh_from_db()

        HistorialEstado.objects.create(
            solicitud=solicitud,
            estado_anterior=solicitud.estado,
            estado_nuevo=solicitud.estado,
            usuario=request.user,
            comentario=(
                f"ADMIN: folio '{nuevo_folio}' reasignado. "
                f"'{conflicto.nombre_completo}' recibió nuevo folio '{folio_nuevo_anterior}'."
            ),
        )

        messages.success(
            request,
            f"Folio '{nuevo_folio}' reasignado a "
            f"{solicitud.ciudadano.nombre_completo}. "
            f"{conflicto.nombre_completo} ahora tiene '{folio_nuevo_anterior}'."
        )

    else:
        messages.error(request, "Opción no válida.")
        return redirect('usuarios:admin_conflicto_folio')

    # Limpiar sesión
    if 'folio_conflicto' in request.session:
        del request.session['folio_conflicto']

    return redirect('usuarios:admin_detalle_solicitud', solicitud_id=solicitud.id)