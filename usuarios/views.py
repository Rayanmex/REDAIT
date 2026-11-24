from functools import wraps
from datetime import timedelta

from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.utils import timezone

from .models import (
    Solicitud,
    Ciudadano,
    Empresa,
    HistorialEstado,
    DatosPersonales,
    DomicilioIdentificacion,
    DocumentosNegocio,
    CursosCapacitaciones,
    Curso,
    MUNICIPIOS_TABASCO,
)

from .forms import RegistroCiudadanoForm
from .emails import (
    enviar_correo_solicitud_recibida,
    enviar_correo_admin_nueva_solicitud,
    enviar_correo_admin_pago_subido,
)
from .pdf import generar_licencia
from .pase_caja import generar_pase_caja


# ============================================================
# DECORADOR: SOLO CIUDADANO (no staff)
# ============================================================

def solo_ciudadano(view_func):
    """Bloquea a los usuarios staff del flujo de ciudadano."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_staff:
            return redirect('usuarios:admin_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped


# ============================================================
# HELPER: obtener (o crear) la solicitud del ciudadano
# ============================================================

def _obtener_solicitud(request):
    """Devuelve (o crea) la solicitud activa del usuario logueado.

    Prioriza la solicitud más reciente que NO esté bloqueada.
    Si todas están bloqueadas, devuelve la más reciente.
    """
    ciudadano, _ = Ciudadano.objects.get_or_create(
        user=request.user,
        defaults={
            'nombre_completo': request.user.get_full_name() or request.user.username,
            'telefono': '0000000000',
        },
    )

    # Primero intenta obtener una solicitud NO bloqueada
    solicitud = (
        Solicitud.objects
        .filter(ciudadano=ciudadano)
        .exclude(estado='licencia_emitida')
        .order_by('-fecha_creacion')
        .first()
    )

    if not solicitud:
        # Si todas están bloqueadas, devuelve la más reciente
        solicitud = (
            Solicitud.objects
            .filter(ciudadano=ciudadano)
            .order_by('-fecha_creacion')
            .first()
        )

    # Si no hay ninguna, la crea
    if not solicitud:
        solicitud = Solicitud.objects.create(ciudadano=ciudadano)

    return solicitud


# ============================================================
# REGISTRO
# ============================================================

def registro_ciudadano(request):
    """Registro público de ciudadanos (agentes inmobiliarios)."""
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('usuarios:admin_dashboard')
        return redirect('usuarios:panel')

    if request.method == 'POST':
        form = RegistroCiudadanoForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f"¡Bienvenido(a), {user.first_name}! Tu cuenta ha sido creada correctamente."
            )
            return redirect('usuarios:panel')
    else:
        form = RegistroCiudadanoForm()

    return render(request, 'usuarios/registro_ciudadano.html', {'form': form})


# ============================================================
# PANEL PRINCIPAL (redirige según rol)
# ============================================================

@login_required
def panel(request):
    """Panel principal del ciudadano con progreso y comentarios del revisor."""
    if request.user.is_staff:
        return redirect('usuarios:admin_dashboard')

    solicitud = _obtener_solicitud(request)
    ciudadano = solicitud.ciudadano

    # Si el ciudadano fue desactivado, bloquear acceso
    if not ciudadano.activo:
        return render(request, 'usuarios/cuenta_desactivada.html', {
            'ciudadano': ciudadano,
        })

    contexto = {
        'solicitud': solicitud,
        'porcentaje': solicitud.porcentaje_avance,
        'pasos_completados': solicitud.pasos_completados,
        'siguiente_paso': solicitud.siguiente_paso,
        'comentarios': solicitud.historial.exclude(comentario='').order_by('-fecha'),
        'licencia_vencida': ciudadano.licencia_vencida,
        'licencia_vigente': ciudadano.licencia_vigente,
    }
    return render(request, 'usuarios/panel.html', contexto)

# ============================================================
# PASO 1: DATOS PERSONALES
# ============================================================

@solo_ciudadano
@login_required
def paso1_datos(request):
    solicitud = _obtener_solicitud(request)

    # Bloqueo si la licencia ya fue emitida
    if solicitud.esta_bloqueado:
        messages.error(request, "Tu licencia ya fue emitida. No puedes modificar tus datos.")
        return redirect('usuarios:panel')

    instancia, _ = DatosPersonales.objects.get_or_create(solicitud=solicitud)
    ciudadano = solicitud.ciudadano

    if request.method == 'POST':
        # -----------------------------
        # DATOS PERSONALES
        # -----------------------------
        instancia.regimen_fiscal = request.POST.get('regimen_fiscal', instancia.regimen_fiscal)
        instancia.sexo = request.POST.get('sexo', instancia.sexo)
        instancia.rfc = request.POST.get('rfc', instancia.rfc)
        instancia.curp = request.POST.get('curp', instancia.curp)
        instancia.tipo_tramite = request.POST.get('tipo_tramite', instancia.tipo_tramite)

        # -----------------------------
        # CIUDADANO (nombre editable)
        # -----------------------------
        nuevo_nombre = request.POST.get('nombre_completo', '').strip().upper()
        if nuevo_nombre:
            ciudadano.nombre_completo = nuevo_nombre

        # -----------------------------
        # EMPRESA (opcional)
        # -----------------------------
        empresa_nombre = request.POST.get('empresa_nombre', '').strip().upper()
        if empresa_nombre:
            # Buscar empresa existente (case insensitive)
            empresa = Empresa.objects.filter(nombre__iexact=empresa_nombre).first()
            if not empresa:
                # Crear nueva empresa
                empresa = Empresa.objects.create(nombre=empresa_nombre)
            ciudadano.empresa = empresa
            ciudadano.empresa_nombre_manual = ''
        else:
            ciudadano.empresa = None
            ciudadano.empresa_nombre_manual = ''

        try:
            instancia.full_clean()
            instancia.completado = True
            instancia.fecha_completado = timezone.now()
            instancia.save()
            ciudadano.save()
            messages.success(request, "Paso 1 guardado correctamente.")
            return redirect('usuarios:paso2_domicilio')
        except Exception as e:
            messages.error(request, f"Revisa los datos: {e}")

    # Lista de empresas para el datalist (autocompletado)
    empresas = Empresa.objects.filter(activa=True).order_by('nombre').values_list('nombre', flat=True)

    return render(request, 'usuarios/paso1_datos.html', {
        'datos': instancia,
        'solicitud': solicitud,
        'empresas': empresas,
    })


# ============================================================
# PASO 2: DOMICILIO E IDENTIFICACIÓN
# ============================================================

@solo_ciudadano
@login_required
def paso2_domicilio(request):
    solicitud = _obtener_solicitud(request)

    # Bloqueo si la licencia ya fue emitida
    if solicitud.esta_bloqueado:
        messages.error(request, "Tu licencia ya fue emitida. No puedes modificar tus datos.")
        return redirect('usuarios:panel')

    instancia, _ = DomicilioIdentificacion.objects.get_or_create(solicitud=solicitud)

    if request.method == 'POST':
        instancia.municipio = request.POST.get('municipio', instancia.municipio)
        instancia.calle_numero_colonia_cp = request.POST.get(
            'calle_numero_colonia_cp', instancia.calle_numero_colonia_cp
        )

        if request.FILES.get('comprobante_domicilio'):
            instancia.comprobante_domicilio = request.FILES['comprobante_domicilio']
        if request.FILES.get('identificacion_oficial'):
            instancia.identificacion_oficial = request.FILES['identificacion_oficial']
        if request.FILES.get('foto_agente'):
            instancia.foto_agente = request.FILES['foto_agente']

        instancia.completado = True
        instancia.fecha_completado = timezone.now()
        instancia.save()

        messages.success(request, "Paso 2 guardado correctamente.")
        return redirect('usuarios:paso3_documentos')

    return render(request, 'usuarios/paso2_domicilio.html', {
        'domicilio': instancia,
        'solicitud': solicitud,
        'municipios': MUNICIPIOS_TABASCO,
    })


# ============================================================
# PASO 3: DOCUMENTOS DEL NEGOCIO
# ============================================================

@solo_ciudadano
@login_required
def paso3_documentos(request):
    solicitud = _obtener_solicitud(request)

    # Bloqueo si la licencia ya fue emitida
    if solicitud.esta_bloqueado:
        messages.error(request, "Tu licencia ya fue emitida. No puedes modificar tus datos.")
        return redirect('usuarios:panel')

    instancia, _ = DocumentosNegocio.objects.get_or_create(solicitud=solicitud)

    if request.method == 'POST':
        # Campos comunes
        if request.FILES.get('constancia_situacion_fiscal'):
            instancia.constancia_situacion_fiscal = request.FILES['constancia_situacion_fiscal']
        if request.FILES.get('constancia_profeco'):
            instancia.constancia_profeco = request.FILES['constancia_profeco']
        if request.FILES.get('carta_no_antecedentes'):
            instancia.carta_no_antecedentes = request.FILES['carta_no_antecedentes']
        if request.FILES.get('carta_bajo_protesta'):
            instancia.carta_bajo_protesta = request.FILES['carta_bajo_protesta']

        # Persona moral
        if request.FILES.get('acta_constitutiva'):
            instancia.acta_constitutiva = request.FILES['acta_constitutiva']
        if request.FILES.get('poder_notarial'):
            instancia.poder_notarial = request.FILES['poder_notarial']
        if request.FILES.get('logotipo_empresa'):
            instancia.logotipo_empresa = request.FILES['logotipo_empresa']

        # Revalidación
        if request.FILES.get('constancia_inscripcion_anterior'):
            instancia.constancia_inscripcion_anterior = request.FILES['constancia_inscripcion_anterior']

        instancia.completado = True
        instancia.fecha_completado = timezone.now()
        instancia.save()

        messages.success(request, "Paso 3 guardado correctamente.")
        return redirect('usuarios:paso4_cursos')

    return render(request, 'usuarios/paso3_documentos.html', {
        'documentos': instancia,
        'solicitud': solicitud,
    })


# ============================================================
# PASO 4: CURSOS Y CAPACITACIONES
# ============================================================

@solo_ciudadano
@login_required
def paso4_cursos(request):
    solicitud = _obtener_solicitud(request)

    # Bloqueo si la licencia ya fue emitida
    if solicitud.esta_bloqueado:
        messages.error(request, "Tu licencia ya fue emitida. No puedes modificar tus datos.")
        return redirect('usuarios:panel')

    instancia, _ = CursosCapacitaciones.objects.get_or_create(solicitud=solicitud)

    if request.method == 'POST':
        accion = request.POST.get('accion', 'guardar')

        # ---------- AGREGAR CURSO ----------
        if accion == 'agregar_curso':
            nombre_curso = request.POST.get('curso_nombre', '').strip().upper()
            horas = request.POST.get('curso_horas', '').strip()
            institucion = request.POST.get('curso_institucion', '').strip().upper()
            fecha_curso = request.POST.get('curso_fecha', '').strip()
            archivo = request.FILES.get('curso_documento')

            if nombre_curso and horas:
                try:
                    curso = Curso(solicitud=solicitud)
                    curso.nombre = nombre_curso
                    curso.horas = int(horas)
                    curso.institucion = institucion
                    if fecha_curso:
                        from datetime import datetime as dt
                        try:
                            curso.fecha_curso = dt.strptime(fecha_curso, '%Y-%m-%d').date()
                        except ValueError:
                            pass
                    if archivo:
                        curso.documento = archivo
                    curso.save()
                    messages.success(request, f"Curso '{nombre_curso}' agregado ({horas}h).")
                except ValueError:
                    messages.error(request, "Las horas deben ser un número entero.")
            else:
                messages.error(request, "El nombre y las horas del curso son obligatorios.")

            return redirect('usuarios:paso4_cursos')

        # ---------- ELIMINAR CURSO ----------
        elif accion == 'eliminar_curso':
            curso_id = request.POST.get('curso_id')
            try:
                curso = Curso.objects.get(id=curso_id, solicitud=solicitud)
                curso.delete()
                messages.info(request, f"Curso '{curso.nombre}' eliminado.")
            except Curso.DoesNotExist:
                messages.error(request, "El curso no existe.")
            return redirect('usuarios:paso4_cursos')

        # ---------- GUARDAR Y CONTINUAR ----------
        else:
            # Guardar carta compromiso
            if request.FILES.get('carta_compromiso'):
                instancia.carta_compromiso = request.FILES['carta_compromiso']

            total_horas = solicitud.total_horas_curso

            # Validar mínimo 30 horas y carta compromiso
            if total_horas < 30:
                messages.error(
                    request,
                    f"Debes acumular al menos 30 horas de capacitación. "
                    f"Actualmente tienes {total_horas}h."
                )
                return redirect('usuarios:paso4_cursos')

            if not instancia.carta_compromiso:
                messages.error(request, "Debes subir la carta de compromiso.")
                return redirect('usuarios:paso4_cursos')

            instancia.completado = True
            instancia.fecha_completado = timezone.now()
            instancia.save()

            messages.success(
                request,
                f"¡Todo listo! Acumulaste {total_horas}h en capacitaciones. "
                f"Revisa tu información antes de enviar."
            )
            return redirect('usuarios:resumen_solicitud')

    # Cursos cargados
    cursos_cargados = solicitud.cursos_cargados.all().order_by('-fecha_curso', '-fecha_subida')
    total_horas = solicitud.total_horas_curso

    return render(request, 'usuarios/paso4_cursos.html', {
        'cursos': instancia,
        'solicitud': solicitud,
        'cursos_cargados': cursos_cargados,
        'total_horas': total_horas,
        'cumple_minimo': total_horas >= 30,
        'horas_restantes': max(0, 30 - total_horas),
    })


# ============================================================
# RESUMEN DE LA SOLICITUD
# ============================================================

@solo_ciudadano
@login_required
def resumen_solicitud(request):
    """Muestra el resumen de los 4 pasos antes de enviar."""
    solicitud = _obtener_solicitud(request)

    # Bloqueo si la licencia ya fue emitida
    if solicitud.esta_bloqueado:
        messages.error(request, "Tu licencia ya fue emitida. No puedes modificar tus datos.")
        return redirect('usuarios:panel')

    completo = all([
        solicitud.paso1_completado,
        solicitud.paso2_completado,
        solicitud.paso3_completado,
        solicitud.paso4_completado,
    ])

    contexto = {
        'solicitud': solicitud,
        'completo': completo,
        'datos_personales': getattr(solicitud, 'datos_personales', None),
        'domicilio': getattr(solicitud, 'domicilio_identificacion', None),
        'documentos': getattr(solicitud, 'documentos_negocio', None),
        'cursos': getattr(solicitud, 'cursos_capacitaciones', None),
    }
    return render(request, 'usuarios/resumen_solicitud.html', contexto)


# ============================================================
# ENVÍO DE LA SOLICITUD (genera folio + manda correos)
# ============================================================

@solo_ciudadano
@login_required
def enviar_solicitud(request):
    """Confirma y envía la solicitud (solo POST)."""
    solicitud = _obtener_solicitud(request)

    # Bloqueo si la licencia ya fue emitida
    if solicitud.esta_bloqueado:
        messages.error(request, "Tu licencia ya fue emitida. No puedes modificar tus datos.")
        return redirect('usuarios:panel')

    if request.method != 'POST':
        return redirect('usuarios:resumen_solicitud')

    # Ya enviada previamente o aprobada
    if solicitud.estado in ('en_revision', 'aprobada') and solicitud.folio:
        messages.info(request, f"Tu solicitud ya fue enviada con folio {solicitud.folio}.")
        return redirect('usuarios:confirmacion_solicitud')

    # Verifica los 4 pasos
    if not all([
        solicitud.paso1_completado,
        solicitud.paso2_completado,
        solicitud.paso3_completado,
        solicitud.paso4_completado,
    ]):
        messages.error(request, "Debes completar los 4 módulos antes de enviar tu solicitud.")
        return redirect('usuarios:resumen_solicitud')

    # ============================================================
    # AUTO-MARCAR REVALIDACIÓN
    # ============================================================
    # Si el ciudadano ya tuvo una licencia emitida antes,
    # esta solicitud es una revalidación.
    ya_tuvo_licencia = Solicitud.objects.filter(
        ciudadano=solicitud.ciudadano,
        estado='licencia_emitida',
    ).exists()

    if ya_tuvo_licencia:
        solicitud.tipo_tramite = 'revalidacion'
        solicitud.renovacion = True
        solicitud.save(update_fields=['tipo_tramite', 'renovacion'])

    # Genera folio y cambia estado a 'en_revision'
    folio = solicitud.enviar()

    # Limpia el comentario anterior si venía de correcciones
    solicitud.comentario_admin = ''
    solicitud.motivo_accion = ''
    solicitud.save(update_fields=['comentario_admin', 'motivo_accion'])

    # Correos automáticos (silenciosos)
    try:
        enviar_correo_solicitud_recibida(solicitud)
    except Exception:
        pass

    try:
        enviar_correo_admin_nueva_solicitud(solicitud)
    except Exception:
        pass

    messages.success(request, f"Tu solicitud fue enviada con folio {folio}.")
    return redirect('usuarios:confirmacion_solicitud')


# ============================================================
# CONFIRMACIÓN
# ============================================================

@solo_ciudadano
@login_required
def confirmacion_solicitud(request):
    """Muestra el mensaje final con el folio."""
    solicitud = _obtener_solicitud(request)
    if not solicitud.folio:
        return redirect('usuarios:resumen_solicitud')
    return render(request, 'usuarios/confirmacion_solicitud.html', {'solicitud': solicitud})


# ============================================================
# MI SOLICITUD (estado)
# ============================================================

@solo_ciudadano
@login_required
def mi_solicitud(request):
    """Estado actual de la solicitud del usuario con historial completo."""
    solicitud = _obtener_solicitud(request)
    return render(request, 'usuarios/mi_solicitud.html', {
        'solicitud': solicitud,
        'historial': solicitud.historial.all(),
    })


# ============================================================
# DESCARGAR PASE DE CAJA (ciudadano)
# ============================================================

@solo_ciudadano
@login_required
def descargar_pase_caja(request):
    """Genera y descarga el pase de caja en PDF."""
    solicitud = _obtener_solicitud(request)

    if solicitud.estado != 'aprobada':
        messages.error(request, "Tu solicitud aún no ha sido aprobada.")
        return redirect('usuarios:mi_solicitud')

    buffer = generar_pase_caja(solicitud)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="pase_caja_{solicitud.folio}.pdf"'
    return response


# ============================================================
# SUBIR COMPROBANTE DE PAGO (ciudadano)
# ============================================================

@solo_ciudadano
@login_required
def subir_comprobante_pago(request):
    """Formulario para que el ciudadano suba su comprobante de pago.

    Estados permitidos:
    - aprobada + pago_estado='sin_comprobante' (primera subida)
    - requiere_accion + motivo_accion='resubir_comprobante' (resubida)
    """
    solicitud = _obtener_solicitud(request)

    # Bloqueo si la licencia ya fue emitida
    if solicitud.esta_bloqueado:
        messages.error(request, "Tu licencia ya fue emitida. No necesitas subir otro comprobante.")
        return redirect('usuarios:panel')

    # Validación de estados permitidos
    puede_subir = (
        (solicitud.estado == 'aprobada' and solicitud.pago_estado == 'sin_comprobante')
        or solicitud.requiere_resubir_comprobante
    )

    if not puede_subir:
        messages.warning(request, "No puedes subir comprobante en este momento.")
        return redirect('usuarios:panel')

    if request.method == 'POST':
        comprobante = request.FILES.get('comprobante_pago')
        referencia = request.POST.get('referencia_pago', '').strip()

        estado_anterior = solicitud.estado

        # Validaciones
        if not comprobante:
            messages.error(request, "Debes adjuntar el comprobante de pago.")
        elif comprobante.size > 5 * 1024 * 1024:
            messages.error(request, "El archivo no puede pesar más de 5 MB.")
        elif not comprobante.name.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
            messages.error(request, "Formato no válido. Usa PDF, JPG o PNG.")
        else:
            solicitud.comprobante_pago = comprobante
            solicitud.referencia_pago = referencia
            solicitud.fecha_comprobante = timezone.now()
            # Vuelve a estado 'aprobada' con pago_estado='comprobante_cargado'
            solicitud.estado = 'aprobada'
            solicitud.pago_estado = 'comprobante_cargado'
            solicitud.motivo_accion = ''
            solicitud.save()

            HistorialEstado.objects.create(
                solicitud=solicitud,
                estado_anterior=estado_anterior,
                estado_nuevo='aprobada',
                usuario=request.user,
                comentario=f"Comprobante subido. Referencia: {referencia or 'N/D'}",
            )

            # Avisa al admin
            try:
                enviar_correo_admin_pago_subido(solicitud)
            except Exception:
                pass

            messages.success(
                request,
                "¡Comprobante recibido! Un validador revisará tu pago en breve."
            )
            return redirect('usuarios:panel')

    return render(request, 'usuarios/subir_comprobante.html', {'solicitud': solicitud})


# ============================================================
# DESCARGAR LICENCIA (ciudadano)
# ============================================================

@solo_ciudadano
@login_required
def descargar_licencia(request):
    """Genera y descarga la licencia en PDF (solo si ya fue emitida)."""
    solicitud = _obtener_solicitud(request)

    # Bloqueo si el ciudadano fue desactivado
    if not solicitud.ciudadano.activo:
        messages.error(
            request,
            "Tu cuenta ha sido desactivada. Contacta a la Secretaría de Turismo."
        )
        return redirect('usuarios:panel')

    if solicitud.estado != 'licencia_emitida':
        messages.error(request, "Tu licencia aún no está disponible.")
        return redirect('usuarios:mi_solicitud')

    # El folio vive en el Ciudadano
    folio_lic = solicitud.ciudadano.folio_licencia
    if not folio_lic or not solicitud.fecha_emision_licencia:
        messages.error(
            request,
            "Tu licencia no tiene los datos completos. Contacta al administrador."
        )
        return redirect('usuarios:mi_solicitud')

    buffer = generar_licencia(solicitud)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="licencia_{folio_lic}.pdf"'
    )
    return response


# ============================================================
# VERIFICACIÓN PÚBLICA DEL PASE DE CAJA (destino del QR)
# ============================================================

def verificar_pase_caja(request, folio):
    """Página pública que muestra los datos del pase de caja."""
    from .models import UMA_CANTIDAD_DEFAULT, UMA_VALOR_DEFAULT, MONTO_PAGO_DEFAULT

    folio = folio.upper().strip()

    solicitud = (
        Solicitud.objects
        .select_related('ciudadano', 'ciudadano__user')
        .filter(folio=folio)
        .first()
    )

    if not solicitud:
        return render(request, 'usuarios/verificacion_pase.html', {
            'estado': 'no_encontrado',
            'folio_buscado': folio,
        }, status=404)

    # Solo aprobadas en adelante muestran el pase como válido
    if solicitud.estado not in ('aprobada', 'licencia_emitida'):
        return render(request, 'usuarios/verificacion_pase.html', {
            'estado': 'no_aprobada',
            'folio_buscado': folio,
            'solicitud': solicitud,
        })


        # Nombre a mostrar
    nombre_mostrar = (
        solicitud.ciudadano.nombre_completo
        or solicitud.ciudadano.user.get_full_name()
        or solicitud.ciudadano.user.username
    )

    # Nombre de la empresa (si tiene)
    empresa_mostrar = ''
    if solicitud.ciudadano.empresa:
        empresa_mostrar = solicitud.ciudadano.empresa.nombre


    contexto = {
        'estado': 'valido',
        'solicitud': solicitud,
        'nombre_mostrar': nombre_mostrar,
        'empresa_mostrar': empresa_mostrar,
        'uma_cantidad': solicitud.uma_cantidad or UMA_CANTIDAD_DEFAULT,
        'uma_valor': solicitud.uma_valor or UMA_VALOR_DEFAULT,
        'monto': solicitud.monto_pago or MONTO_PAGO_DEFAULT,
        'numero_oficio': solicitud.numero_oficio or '—',
        'fecha_emision': solicitud.fecha_pase_caja,
    }
    return render(request, 'usuarios/verificacion_pase.html', contexto)


# ============================================================
# VERIFICACIÓN PÚBLICA DE LICENCIA (destino del QR)
# ============================================================

def verificar_licencia(request, folio):
    """Página pública que muestra los datos oficiales de una licencia emitida.

    Busca por Ciudadano.folio_licencia (no por Solicitud).
    """
    folio = folio.upper().strip()

    # Buscar al ciudadano por su folio
    ciudadano = (
        Ciudadano.objects
        .select_related('user')
        .filter(folio_licencia=folio)
        .first()
    )

    if not ciudadano:
        return render(request, 'usuarios/verificacion_licencia.html', {
            'estado': 'no_encontrado',
            'folio_buscado': folio,
        }, status=404)

    # Obtener la última solicitud emitida del ciudadano
    solicitud = (
        Solicitud.objects
        .filter(ciudadano=ciudadano, estado='licencia_emitida')
        .order_by('-fecha_emision_licencia')
        .first()
    )

    if not solicitud:
        return render(request, 'usuarios/verificacion_licencia.html', {
            'estado': 'no_emitida',
            'ciudadano': ciudadano,
        })

    
    nombre_mostrar = (
        solicitud.ciudadano.nombre_completo
        or solicitud.ciudadano.user.get_full_name()
        or solicitud.ciudadano.user.username
    )

    # Nombre de la empresa (si tiene)
    empresa_mostrar = ''
    if solicitud.ciudadano.empresa:
        empresa_mostrar = solicitud.ciudadano.empresa.nombre

    # Fecha de vigencia (1 año después de la emisión)
    fecha_vigencia = None
    if solicitud.fecha_emision_licencia:
        fecha_vigencia = solicitud.fecha_emision_licencia + timedelta(days=365)

    contexto = {
        'estado': 'valido',
        'solicitud': solicitud,
        'ciudadano': ciudadano,
        'nombre_mostrar': nombre_mostrar,
        'folio_licencia': ciudadano.folio_licencia,
        'fecha_emision': solicitud.fecha_emision_licencia,
        'fecha_vigencia': fecha_vigencia,
        'tipo_tramite': solicitud.get_tipo_tramite_display(),
    }
    return render(request, 'usuarios/verificacion_licencia.html', contexto)


# ============================================================
# AVISO DE PRIVACIDAD (público - sin login)
# ============================================================

def aviso_privacidad(request):
    """Página pública con el aviso de privacidad de la SEDEC."""
    return render(request, 'usuarios/aviso_privacidad.html')