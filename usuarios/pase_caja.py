# usuarios/pase_caja.py

import io
import os
from datetime import datetime

import qrcode
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.staticfiles import finders
from num2words import num2words


# ============================================================
# CONSTANTES
# ============================================================

MESES_ES = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
]

UMA_CANTIDAD_DEFAULT = 6.00
UMA_VALOR_DEFAULT = 117.31
MONTO_PAGO_DEFAULT = 703.86


# ============================================================
# HELPERS
# ============================================================

def _archivo_a_data_uri(ruta_absoluta):
    """Convierte un archivo local a data URI para que WeasyPrint lo embeba."""
    import base64
    import mimetypes

    if not os.path.exists(ruta_absoluta):
        return ''

    mime, _ = mimetypes.guess_type(ruta_absoluta)
    if not mime:
        mime = 'image/png'

    with open(ruta_absoluta, 'rb') as f:
        data = base64.b64encode(f.read()).decode('ascii')

    return f'data:{mime};base64,{data}'


def _ruta_static(relativa):
    """Encuentra la ruta absoluta de un archivo en static/."""
    ruta = finders.find(relativa)
    if not ruta:
        # Fallback: buscar en BASE_DIR/static
        alt = os.path.join(settings.BASE_DIR, 'static', relativa)
        if os.path.exists(alt):
            return alt
    return ruta or ''


def _generar_qr_data_uri(datos: str) -> str:
    """Genera un QR y lo devuelve como data URI."""
    import base64

    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(datos)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    data = base64.b64encode(buffer.read()).decode('ascii')
    return f'data:image/png;base64,{data}'


def _fecha_en_letra(dt: datetime) -> str:
    return f"{dt.day} de {MESES_ES[dt.month - 1]} de {dt.year}"


def _monto_en_letra(monto: float) -> str:
    """703.86 → 'Setecientos tres pesos, 86/100 M.N.'"""
    entero = int(monto)
    centavos = round((monto - entero) * 100)
    letras = num2words(entero, lang='es').capitalize()
    if centavos == 0:
        return f"{letras} pesos, 00/100 M.N."
    return f"{letras} pesos, {centavos:02d}/100 M.N."


# ============================================================
# GENERADOR PRINCIPAL
# ============================================================

def generar_pase_caja(solicitud):
    """
    Genera el PDF del pase de caja.

    :param solicitud: instancia de Solicitud aprobada.
    :return: BytesIO con el PDF listo para servir.
    """
    from weasyprint import HTML

    hoy = datetime.now()

    # ---------- Nombre del ciudadano ----------
    # Prioridad: Ciudadano > User
    nombre_ciudadano = (
        solicitud.ciudadano.nombre_completo
        or solicitud.ciudadano.user.get_full_name()
        or solicitud.ciudadano.user.username
        or '—'
    )
    nombre_ciudadano = nombre_ciudadano.upper()

    # ---------- Datos del oficio ----------
    numero_oficio = solicitud.numero_oficio or 'TURISMO/DDC/____/2026'
    monto = float(solicitud.monto_pago or MONTO_PAGO_DEFAULT)
    uma_cantidad = float(solicitud.uma_cantidad or UMA_CANTIDAD_DEFAULT)
    uma_valor = float(solicitud.uma_valor or UMA_VALOR_DEFAULT)

    # ---------- Imágenes como data URI ----------
    fondo_path = _ruta_static('images/pase_caja/encabezado_footer.png')
    firma_path = _ruta_static('images/pase_caja/firma.png')

    fondo_url = _archivo_a_data_uri(fondo_path) if fondo_path else ''
    firma_url = _archivo_a_data_uri(firma_path) if firma_path else ''

    # ---------- QR ----------
    qr_data = f"{settings.SITE_URL}/usuarios/verificar/{solicitud.folio}/"
    qr_url = _generar_qr_data_uri(qr_data)

    # ---------- Contexto del template ----------
    contexto = {
        'fondo_url': fondo_url,
        'firma_url': firma_url,
        'qr_url': qr_url,
        'fecha_letra': _fecha_en_letra(hoy),
        'anio': hoy.year,
        'numero_oficio': numero_oficio,
        'nombre_ciudadano': nombre_ciudadano,
        'monto': f"{monto:,.2f}",
        'monto_letra': _monto_en_letra(monto),
        'uma_cantidad': f"{uma_cantidad:.2f}",
        'uma_cantidad_entera': int(uma_cantidad),
        'uma_valor': f"{uma_valor:.2f}",
    }

    html_string = render_to_string('usuarios/pase_caja_pdf.html', contexto)

    # ---------- Generar PDF ----------
    pdf_bytes = HTML(string=html_string).write_pdf()

    output = io.BytesIO(pdf_bytes)
    output.seek(0)
    return output