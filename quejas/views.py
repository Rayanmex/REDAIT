from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from .models import Queja
from .forms import QuejaForm


def enviar_queja(request):
    """Formulario público para enviar quejas, sugerencias o denuncias."""
    if request.method == 'POST':
        form = QuejaForm(request.POST, request.FILES)
        if form.is_valid():
            queja = form.save(commit=False)
            queja.save()

            # Genera folio
            folio = queja.enviar()

            # Correo al ciudadano (silencioso)
            try:
                send_mail(
                    subject=f'Recibimos tu mensaje - Folio {folio}',
                    message=(
                        f'Hola {queja.nombre_completo},\n\n'
                        f'Hemos recibido tu {queja.get_tipo_display().lower()} '
                        f'con el folio {folio}.\n\n'
                        f'Asunto: {queja.asunto}\n\n'
                        f'Te daremos respuesta a la brevedad posible.\n\n'
                        f'Saludos,\n'
                        f'Secretaría de Turismo de Tabasco'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[queja.email],
                    fail_silently=True,
                )
            except Exception:
                pass

            # Correo al admin (silencioso)
            try:
                send_mail(
                    subject=f'Nueva {queja.get_tipo_display()} - Folio {folio}',
                    message=(
                        f'Se recibió una nueva {queja.get_tipo_display().lower()}.\n\n'
                        f'Folio: {folio}\n'
                        f'Tipo: {queja.get_tipo_display()}\n'
                        f'Nombre: {queja.nombre_completo}\n'
                        f'Email: {queja.email}\n'
                        f'Teléfono: {queja.telefono or "—"}\n'
                        f'Asunto: {queja.asunto}\n\n'
                        f'Mensaje:\n{queja.mensaje}\n'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],
                    fail_silently=True,
                )
            except Exception:
                pass

            messages.success(
                request,
                f'¡Gracias! Tu mensaje fue recibido con el folio {folio}.'
            )
            return redirect('quejas:confirmacion', folio=folio)
    else:
        form = QuejaForm()

    return render(request, 'quejas/enviar.html', {'form': form})


def confirmacion(request, folio):
    """Muestra la confirmación con el folio generado."""
    queja = get_object_or_404(Queja, folio=folio)
    return render(request, 'quejas/confirmacion.html', {'queja': queja})


# ============================================================
# PANEL ADMIN
# ============================================================

@staff_member_required
def admin_lista(request):
    """Lista de quejas para el panel administrativo."""
    qs = Queja.objects.all().order_by('-fecha_creacion')

    estado = request.GET.get('estado', '')
    tipo = request.GET.get('tipo', '')
    busqueda = request.GET.get('q', '').strip()

    if estado:
        qs = qs.filter(estado=estado)
    if tipo:
        qs = qs.filter(tipo=tipo)
    if busqueda:
        qs = qs.filter(asunto__icontains=busqueda) | qs.filter(nombre_completo__icontains=busqueda)

    contexto = {
        'quejas': qs,
        'total': qs.count(),
        'estados': Queja.ESTADOS,
        'tipos': Queja.TIPOS,
        'filtros': {
            'estado': estado,
            'tipo': tipo,
            'q': busqueda,
        },
    }
    return render(request, 'quejas/admin/lista.html', contexto)


@staff_member_required
def admin_detalle(request, queja_id):
    """Detalle de una queja + cambio de estado."""
    queja = get_object_or_404(Queja, id=queja_id)

    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado', '').strip()
        comentario = request.POST.get('comentario_interno', '').strip()

        if nuevo_estado and nuevo_estado != queja.estado:
            queja.estado = nuevo_estado
            if nuevo_estado == 'atendida' and not queja.fecha_atencion:
                queja.fecha_atencion = timezone.now()
                queja.atendida_por = request.user

        if comentario != queja.comentario_interno:
            queja.comentario_interno = comentario

        queja.save()
        messages.success(request, f'Queja {queja.folio} actualizada.')
        return redirect('quejas:admin_detalle', queja_id=queja.id)

    return render(request, 'quejas/admin/detalle.html', {'queja': queja})