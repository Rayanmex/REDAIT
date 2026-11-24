"""
Generación de PDFs del sistema REDAIT:
- Pase de pago (ReportLab)
- Licencia final (Pillow + imágenes institucionales)
"""
import io
import os
import qrcode
from datetime import timedelta

from PIL import Image, ImageDraw, ImageFont

from django.conf import settings
from django.utils import timezone

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage,
)
from reportlab.lib.enums import TA_CENTER


# ============================================================
# CONFIGURACIÓN DE LA LICENCIA
# ============================================================

CARPETA_IMAGENES = os.path.join(settings.BASE_DIR, 'static', 'images')
CARPETA_FUENTES = os.path.join(settings.BASE_DIR, 'static', 'fonts')

ARCHIVO_FRENTE = 'portada_1_ok.png'
ARCHIVO_REVERSO = 'portada_2_ok.png'
ARCHIVO_CUADRITO = 'cuadrito_ok.png'

RUTA_FUENTE_BOLD = os.path.join(CARPETA_FUENTES, 'Montserrat-Bold.ttf')
RUTA_FUENTE_REGULAR = os.path.join(CARPETA_FUENTES, 'Montserrat-Regular.ttf')

# Colores institucionales
ROJO_INSTITUCIONAL = (153, 21, 71)   # #991547
NEGRO = (31, 41, 55)

# Permitir imágenes grandes sin warning de "decompression bomb"
Image.MAX_IMAGE_PIXELS = None

# Coordenadas (en píxeles sobre la imagen 3300 x 2550)
COORDS_FRENTE = {
    'nombre': {
        'x': 1650,            # centro
        'y': 1290,
        'ancho': 2400,
        'alto': 120,
        'tamano_fuente': 80,
        'color': ROJO_INSTITUCIONAL,
        'align': 'center',
    },
    'folio': {
        'x': 2750,
        'y': 1600,
        'ancho': 500,
        'alto': 80,
        'tamano_fuente': 50,
        'color': ROJO_INSTITUCIONAL,
        'align': 'left',
    },
}

COORDS_REVERSO = {
    'foto': {
        'x': 900,
        'y': 750,
        'ancho': 750,
        'alto': 900,
    },
    'cuadrito': {
        'x': 880,
        'y': 730,
        'ancho': 790,
        'alto': 940,
    },
    'qr': {
        'x': 1785,           # ← centrado en el espacio derecho
        'y': 720,           # ← bajado drásticamente (era 500)
        'ancho': 550,
        'alto': 550,
    },
    'fecha_reg_label': {
        'x': 1810,           # ← centrado
        'y': 1370,           # ← bajado drásticamente (era 1150)
        'ancho': 900,
        'alto': 60,
        'tamano_fuente': 45,
        'color': NEGRO,
        'align': 'left',
    },
    'fecha_reg_valor': {
        'x': 1810,
        'y': 1430,           # ← 1220 + 700
        'ancho': 900,
        'alto': 60,
        'tamano_fuente': 42,
        'color': ROJO_INSTITUCIONAL,
        'align': 'left',
    },
    'fecha_vig_label': {
        'x': 1810,
        'y': 1550,           # ← 1340 + 700
        'ancho': 900,
        'alto': 60,
        'tamano_fuente': 45,
        'color': NEGRO,
        'align': 'left',
    },
    'fecha_vig_valor': {
        'x': 1810,
        'y': 1620,           # ← 1410 + 700
        'ancho': 900,
        'alto': 60,
        'tamano_fuente': 42,
        'color': ROJO_INSTITUCIONAL,
        'align': 'left',
    },
}


# ============================================================
# HELPERS GENERALES
# ============================================================

def _generar_qr(url):
    """Genera una imagen QR en memoria a partir de una URL."""
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


def _fuente(ruta, tamano):
    """Carga una fuente TTF con fallback a la default."""
    try:
        return ImageFont.truetype(ruta, tamano)
    except Exception:
        print(f"⚠️  No se encontró la fuente {ruta}, usando default")
        return ImageFont.load_default()


def _fecha_es(dt):
    """Devuelve la fecha en formato '14 de Mayo de 2026'."""
    if not dt:
        return '—'
    MESES = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
    }
    return f"{dt.day} de {MESES[dt.month]} de {dt.year}"


def _dibujar_texto(img, texto, x, y, ancho, alto, tamano_fuente,
                   color, align='left'):
    """Dibuja texto en la posición exacta con alineación."""
    draw = ImageDraw.Draw(img)
    font = _fuente(RUTA_FUENTE_BOLD, tamano_fuente)

    bbox = draw.textbbox((0, 0), texto, font=font)
    ancho_texto = bbox[2] - bbox[0]

    if align == 'center':
        x_final = x - ancho_texto // 2
    elif align == 'right':
        x_final = x + ancho - ancho_texto
    else:
        x_final = x

    draw.text((x_final, y), texto, font=font, fill=color)


def _ajustar_foto_a_marco(ruta_foto, ancho_marco, alto_marco):
    """Recorta y escala la foto tipo 'cover' para llenar el marco sin deformar."""
    foto = Image.open(ruta_foto).convert('RGB')

    ratio_marco = ancho_marco / alto_marco
    ratio_foto = foto.width / foto.height

    if ratio_foto > ratio_marco:
        # Foto más ancha: recortar los lados
        nuevo_ancho = int(foto.height * ratio_marco)
        offset = (foto.width - nuevo_ancho) // 2
        foto = foto.crop((offset, 0, offset + nuevo_ancho, foto.height))
    else:
        # Foto más alta: recortar arriba y abajo
        nuevo_alto = int(foto.width / ratio_marco)
        offset = (foto.height - nuevo_alto) // 2
        foto = foto.crop((0, offset, foto.width, offset + nuevo_alto))

    return foto.resize((ancho_marco, alto_marco), Image.LANCZOS)


# ============================================================
# PASE DE PAGO (ReportLab)
# ============================================================

def _encabezado(styles, story, titulo, subtitulo):
    titulo_style = ParagraphStyle(
        'titulo_hdr', parent=styles['Title'], fontSize=20,
        textColor=colors.HexColor('#991547'), alignment=TA_CENTER, spaceAfter=6,
    )
    sub_style = ParagraphStyle(
        'sub_hdr', parent=styles['Normal'], fontSize=11,
        textColor=colors.HexColor('#6b7280'), alignment=TA_CENTER, spaceAfter=20,
    )
    story.append(Paragraph(titulo, titulo_style))
    story.append(Paragraph(subtitulo, sub_style))


def _tabla_datos(datos, ancho1=4 * cm, ancho2=11 * cm,
                 color_bg='#fef7fa', color_txt='#991547'):
    tabla = Table(datos, colWidths=[ancho1, ancho2])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor(color_bg)),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor(color_txt)),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
    ]))
    return tabla


def _estilo_h2(styles):
    return ParagraphStyle(
        'h2_gen', parent=styles['Heading2'], fontSize=13,
        textColor=colors.HexColor('#991547'), spaceBefore=12, spaceAfter=8,
    )


def _estilo_footer(styles):
    return ParagraphStyle(
        'footer_gen', parent=styles['Normal'], fontSize=8,
        textColor=colors.HexColor('#6b7280'), alignment=TA_CENTER,
    )


def generar_pase_pago(solicitud):
    """Genera el PDF del pase de pago a partir de una solicitud aprobada."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=LETTER,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    story = []

    _encabezado(
        styles, story,
        "REDAIT Tabasco",
        "Registro Estatal de Agentes Inmobiliarios",
    )

    h2 = _estilo_h2(styles)
    story.append(Paragraph(f"<b>Pase de pago · {solicitud.folio}</b>", h2))
    story.append(Spacer(1, 0.4 * cm))

    dp = getattr(solicitud, 'datos_personales', None)
    datos = [
        ['Folio de solicitud', solicitud.folio or '—'],
        ['Número de oficio', solicitud.numero_oficio or '—'],
        ['Ciudadano', solicitud.ciudadano.nombre_completo or '—'],
        ['Email', solicitud.ciudadano.user.email],
        ['Teléfono', solicitud.ciudadano.telefono or '—'],
        ['Tipo de trámite', solicitud.get_tipo_tramite_display()],
    ]
    if dp:
        datos.append(['RFC', dp.rfc or '—'])

    story.append(_tabla_datos(datos))
    story.append(Spacer(1, 0.8 * cm))

    monto = float(solicitud.monto_pago or 0)
    story.append(Paragraph("<b>Monto a pagar</b>", h2))

    monto_style = ParagraphStyle(
        'monto_style', parent=styles['Normal'], fontSize=28,
        textColor=colors.HexColor('#991547'), alignment=TA_CENTER,
        fontName='Helvetica-Bold', spaceAfter=10,
    )
    story.append(Paragraph(f"${monto:,.2f} MXN", monto_style))
    story.append(Spacer(1, 0.6 * cm))

    story.append(Paragraph("<b>Instrucciones de pago</b>", h2))
    instrucciones = (
        "1. Realiza tu pago en cualquier sucursal bancaria o por transferencia.<br/>"
        "2. Banco: BBVA · Cuenta: 0123 4567 8901 2345<br/>"
        f"3. Referencia: <b>{solicitud.folio}</b><br/>"
        "4. Sube tu comprobante en el portal para continuar con el trámite."
    )
    story.append(Paragraph(instrucciones, styles['Normal']))
    story.append(Spacer(1, 1 * cm))

    url = f"{settings.SITE_URL}/usuarios/mi-solicitud/"
    qr_buf = _generar_qr(url)
    story.append(Paragraph(
        "Escanea para ver el estado de tu trámite:",
        ParagraphStyle('qr_txt', parent=styles['Normal'],
                       alignment=TA_CENTER, spaceAfter=10),
    ))
    story.append(RLImage(qr_buf, width=4 * cm, height=4 * cm))

    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        f"<i>Documento generado el {timezone.now().strftime('%d/%m/%Y %H:%M')}</i>",
        _estilo_footer(styles),
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer


# ============================================================
# LICENCIA FINAL (Pillow + imágenes institucionales)
# ============================================================

def _generar_pagina_frente(solicitud):
    """Genera la página 1 (frente) con nombre y folio."""
    ruta_frente = os.path.join(CARPETA_IMAGENES, ARCHIVO_FRENTE)
    img = Image.open(ruta_frente).convert('RGB')

    # Nombre del titular
    cfg = COORDS_FRENTE['nombre']
    _dibujar_texto(
        img,
        (solicitud.ciudadano.nombre_completo or '').upper(),
        cfg['x'], cfg['y'], cfg['ancho'], cfg['alto'],
        cfg['tamano_fuente'], cfg['color'], cfg['align'],
    )

    # Folio (solo el número) — ahora vive en Ciudadano
    cfg = COORDS_FRENTE['folio']
    _dibujar_texto(
        img,
        str(solicitud.ciudadano.folio_licencia or '—'),
        cfg['x'], cfg['y'], cfg['ancho'], cfg['alto'],
        cfg['tamano_fuente'], cfg['color'], cfg['align'],
    )

    return img


def _generar_pagina_reverso(solicitud):
    """Genera la página 2 (reverso) con foto, marco, QR y fechas."""
    ruta_reverso = os.path.join(CARPETA_IMAGENES, ARCHIVO_REVERSO)
    img = Image.open(ruta_reverso).convert('RGBA')

    # ----- Foto del agente -----
    dom = getattr(solicitud, 'domicilio_identificacion', None)
    if dom and dom.foto_agente and os.path.exists(dom.foto_agente.path):
        cfg = COORDS_REVERSO['foto']
        foto = _ajustar_foto_a_marco(dom.foto_agente.path, cfg['ancho'], cfg['alto'])
        img.paste(foto, (cfg['x'], cfg['y']))

    # ----- Cuadrito (marco de la foto) -----
    ruta_cuadrito = os.path.join(CARPETA_IMAGENES, ARCHIVO_CUADRITO)
    if os.path.exists(ruta_cuadrito):
        cfg = COORDS_REVERSO['cuadrito']
        cuadrito = Image.open(ruta_cuadrito).convert('RGBA')
        cuadrito = cuadrito.resize((cfg['ancho'], cfg['alto']), Image.LANCZOS)
        img.paste(cuadrito, (cfg['x'], cfg['y']), cuadrito)

    # ----- QR — usa el folio del Ciudadano -----
    folio_lic = solicitud.ciudadano.folio_licencia or ''
    url = f"{settings.SITE_URL}/usuarios/verificar-licencia/{folio_lic}/"
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

    cfg = COORDS_REVERSO['qr']
    qr_img = qr_img.resize((cfg['ancho'], cfg['alto']), Image.LANCZOS)
    img.paste(qr_img, (cfg['x'], cfg['y']))

    # ----- Fechas -----
    # Etiqueta "Fecha de registro"
    cfg = COORDS_REVERSO['fecha_reg_label']
    _dibujar_texto(
        img, "Fecha de registro:",
        cfg['x'], cfg['y'], cfg['ancho'], cfg['alto'],
        cfg['tamano_fuente'], cfg['color'], cfg['align'],
    )

    # Valor de la fecha de registro
    cfg = COORDS_REVERSO['fecha_reg_valor']
    _dibujar_texto(
        img, _fecha_es(solicitud.fecha_emision_licencia),
        cfg['x'], cfg['y'], cfg['ancho'], cfg['alto'],
        cfg['tamano_fuente'], cfg['color'], cfg['align'],
    )

    # Etiqueta "Fecha de vigencia"
    cfg = COORDS_REVERSO['fecha_vig_label']
    _dibujar_texto(
        img, "Fecha de vigencia:",
        cfg['x'], cfg['y'], cfg['ancho'], cfg['alto'],
        cfg['tamano_fuente'], cfg['color'], cfg['align'],
    )

    # Valor de la fecha de vigencia
    cfg = COORDS_REVERSO['fecha_vig_valor']
    if solicitud.fecha_emision_licencia:
        fecha_vig = solicitud.fecha_emision_licencia + timedelta(days=365)
    else:
        fecha_vig = None
    _dibujar_texto(
        img, _fecha_es(fecha_vig),
        cfg['x'], cfg['y'], cfg['ancho'], cfg['alto'],
        cfg['tamano_fuente'], cfg['color'], cfg['align'],
    )

    return img.convert('RGB')


def generar_licencia(solicitud):
    """Genera el PDF de la licencia (2 páginas: frente y reverso).

    Requiere que el Ciudadano tenga folio_licencia
    y la Solicitud tenga fecha_emision_licencia.
    """
    frente = _generar_pagina_frente(solicitud)
    reverso = _generar_pagina_reverso(solicitud)

    buffer = io.BytesIO()
    frente.save(
        buffer, 'PDF',
        resolution=300.0,
        save_all=True,
        append_images=[reverso],
    )
    buffer.seek(0)
    return buffer