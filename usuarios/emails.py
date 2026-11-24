from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags


# ============================================================
# HELPER GENÉRICO
# ============================================================

def _enviar(destinatario, asunto, template, contexto):
    """Envía un correo con HTML + versión en texto plano."""
    html = render_to_string(template, contexto)
    texto = strip_tags(html)

    msg = EmailMultiAlternatives(
        subject=asunto,
        body=texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[destinatario],
    )
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=True)


# ============================================================
# CORREOS AL CIUDADANO
# ============================================================

def enviar_correo_solicitud_recibida(solicitud):
    """Se envía al ciudadano cuando su solicitud pasa a 'en_revision'."""
    contexto = {
        'solicitud': solicitud,
        'ciudadano': solicitud.ciudadano,
        'site_url': settings.SITE_URL,
    }
    _enviar(
        destinatario=solicitud.ciudadano.user.email,
        asunto=f"REDAIT · Solicitud recibida · Folio {solicitud.folio}",
        template='usuarios/emails/solicitud_recibida.html',
        contexto=contexto,
    )


def enviar_correo_estado_cambiado(solicitud, estado_anterior, comentario=''):
    """Se envía al ciudadano cuando el admin cambia el estado (aprobada/rechazada/correcciones)."""
    asuntos = {
        'aprobada': f"REDAIT · Tu solicitud {solicitud.folio} fue aprobada",
        'rechazada': f"REDAIT · Tu solicitud {solicitud.folio} fue rechazada",
        'correcciones': f"REDAIT · Tu solicitud {solicitud.folio} requiere correcciones",
    }
    asunto = asuntos.get(solicitud.estado)
    if not asunto:
        return

    contexto = {
        'solicitud': solicitud,
        'ciudadano': solicitud.ciudadano,
        'estado_anterior': estado_anterior,
        'comentario': comentario,
        'site_url': settings.SITE_URL,
    }
    _enviar(
        destinatario=solicitud.ciudadano.user.email,
        asunto=asunto,
        template='usuarios/emails/estado_cambiado.html',
        contexto=contexto,
    )


def enviar_correo_pago_aprobado(solicitud):
    """Se envía al ciudadano cuando el admin valida su comprobante de pago."""
    contexto = {
        'solicitud': solicitud,
        'ciudadano': solicitud.ciudadano,
        'site_url': settings.SITE_URL,
    }
    _enviar(
        destinatario=solicitud.ciudadano.user.email,
        asunto=f"REDAIT · Pago validado · Folio {solicitud.folio}",
        template='usuarios/emails/pago_aprobado.html',
        contexto=contexto,
    )


def enviar_correo_pago_rechazado(solicitud, comentario=''):
    """Se envía al ciudadano cuando el admin rechaza su comprobante."""
    contexto = {
        'solicitud': solicitud,
        'ciudadano': solicitud.ciudadano,
        'comentario': comentario,
        'site_url': settings.SITE_URL,
    }
    _enviar(
        destinatario=solicitud.ciudadano.user.email,
        asunto=f"REDAIT · Comprobante rechazado · Folio {solicitud.folio}",
        template='usuarios/emails/pago_rechazado.html',
        contexto=contexto,
    )


def enviar_correo_constancia_emitida(solicitud):
    """Se envía al ciudadano cuando su constancia/licencia está lista."""
    contexto = {
        'solicitud': solicitud,
        'ciudadano': solicitud.ciudadano,
        'site_url': settings.SITE_URL,
    }
    _enviar(
        destinatario=solicitud.ciudadano.user.email,
        asunto=f"REDAIT · ¡Tu licencia está lista! · {solicitud.folio_licencia}",
        template='usuarios/emails/constancia_emitida.html',
        contexto=contexto,
    )


# ============================================================
# CORREOS AL ADMIN
# ============================================================

def enviar_correo_admin_nueva_solicitud(solicitud):
    """Se envía al admin cuando entra una nueva solicitud."""
    contexto = {
        'solicitud': solicitud,
        'ciudadano': solicitud.ciudadano,
        'site_url': settings.SITE_URL,
    }
    _enviar(
        destinatario=settings.ADMIN_NOTIFICATION_EMAIL,
        asunto=f"[REDAIT] Nueva solicitud {solicitud.folio} · {solicitud.ciudadano.nombre_completo}",
        template='usuarios/emails/admin_nueva_solicitud.html',
        contexto=contexto,
    )


def enviar_correo_admin_pago_subido(solicitud):
    """Se envía al admin cuando un ciudadano sube su comprobante."""
    contexto = {
        'solicitud': solicitud,
        'ciudadano': solicitud.ciudadano,
        'site_url': settings.SITE_URL,
    }
    _enviar(
        destinatario=settings.ADMIN_NOTIFICATION_EMAIL,
        asunto=f"[REDAIT] Comprobante de pago subido · {solicitud.folio}",
        template='usuarios/emails/admin_pago_subido.html',
        contexto=contexto,
    )

def enviar_correo_correcciones(solicitud, comentario=''):
    """Se envía al ciudadano cuando el admin pide correcciones."""
    contexto = {
        'solicitud': solicitud,
        'ciudadano': solicitud.ciudadano,
        'comentario': comentario,
        'site_url': settings.SITE_URL,
    }
    _enviar(
        destinatario=solicitud.ciudadano.user.email,
        asunto=f"REDAIT · Tu solicitud {solicitud.folio} requiere correcciones",
        template='usuarios/emails/estado_cambiado.html',
        contexto=contexto,
    )