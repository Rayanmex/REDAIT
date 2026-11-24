"""
Script para probar la generación del certificado de licencia.
Ajusta las coordenadas aquí y vuelve a ejecutar para iterar rápido.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redait_tabasco.settings')
django.setup()

from datetime import timedelta
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

from usuarios.models import Solicitud

Image.MAX_IMAGE_PIXELS = None


# ============================================================
# CONFIGURACIÓN
# ============================================================

CARPETA_IMAGENES = r'C:\redait_tabasco\static\images'
ARCHIVO_FRENTE = 'portada_1_ok.png'
ARCHIVO_REVERSO = 'portada_2_ok.png'
ARCHIVO_CUADRITO = 'cuadrito_ok.png'

ANCHO_PAGINA = 3300
ALTO_PAGINA = 2550

# Fuente TTF
RUTA_FUENTE_BOLD = r'C:\redait_tabasco\static\fonts\Montserrat-Bold.ttf'
RUTA_FUENTE_REGULAR = r'C:\redait_tabasco\static\fonts\Montserrat-Regular.ttf'

# Colores
ROJO_INSTITUCIONAL = (153, 21, 71)  # #991547
NEGRO = (31, 41, 55)


# ============================================================
# COORDENADAS (en píxeles sobre la imagen 3300 x 2550)
# ============================================================
# Fórmula: cada columna = 330 px, cada fila = 255 px
# C1 = 0-330, C2 = 330-660, C3 = 660-990, C4 = 990-1320,
# C5 = 1320-1650, C6 = 1650-1980, C7 = 1980-2310,
# C8 = 2310-2640, C9 = 2640-2970, C10 = 2970-3300
#
# F1 = 0-255, F2 = 255-510, F3 = 510-765, F4 = 765-1020,
# F5 = 1020-1275, F6 = 1275-1530, F7 = 1530-1785,
# F8 = 1785-2040, F9 = 2040-2295, F10 = 2295-2550

COORDS_FRENTE = {
    # Nombre del titular (centro, debajo de F5)
    'nombre': {
        'x': ANCHO_PAGINA // 2,
        'y': 1290,
        'ancho': 2400,
        'alto': 120,
        'tamano_fuente': 80,
        'color': ROJO_INSTITUCIONAL,
        'align': 'center',
    },
    # Folio (al final del texto legal)
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
    # Foto del agente
    'foto': {
        'x': 800,
        'y': 800,
        'ancho': 850,
        'alto': 1100,
    },
    # Marco de la foto (el cuadrito)
    'cuadrito': {
        'x': 780,
        'y': 780,
        'ancho': 900,
        'alto': 1150,
    },
    # QR
    'qr': {
        'x': 1800,
        'y': 780,
        'ancho': 700,
        'alto': 700,
    },
    # Etiqueta "Fecha de registro"
    'fecha_reg_label': {
        'x': 1830,
        'y': 1500,
        'ancho': 900,
        'alto': 60,
        'tamano_fuente': 55,
        'color': NEGRO,
        'align': 'left',
    },
    # Valor de la fecha de registro (debajo de la etiqueta)
    'fecha_reg_valor': {
        'x': 1830,
        'y': 1570,
        'ancho': 900,
        'alto': 60,
        'tamano_fuente': 50,
        'color': ROJO_INSTITUCIONAL,
        'align': 'left',
    },
    # Etiqueta "Fecha de vigencia"
    'fecha_vig_label': {
        'x': 1830,
        'y': 1680,
        'ancho': 900,
        'alto': 60,
        'tamano_fuente': 55,
        'color': NEGRO,
        'align': 'left',
    },
    # Valor de la fecha de vigencia (debajo de su etiqueta)
    'fecha_vig_valor': {
        'x': 1830,
        'y': 1750,
        'ancho': 900,
        'alto': 60,
        'tamano_fuente': 50,
        'color': ROJO_INSTITUCIONAL,
        'align': 'left',
    },
}


# ============================================================
# HELPERS
# ============================================================

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


# ============================================================
# GENERACIÓN
# ============================================================

def generar_pagina_frente(solicitud):
    """Genera la página 1 (frente) con el nombre y folio."""
    img = Image.open(os.path.join(CARPETA_IMAGENES, ARCHIVO_FRENTE)).convert('RGB')

    # Nombre del titular
    cfg = COORDS_FRENTE['nombre']
    _dibujar_texto(
        img,
        solicitud.ciudadano.nombre_completo.upper(),
        cfg['x'], cfg['y'], cfg['ancho'], cfg['alto'],
        cfg['tamano_fuente'], cfg['color'], cfg['align'],
    )

    # Folio
    cfg = COORDS_FRENTE['folio']
    _dibujar_texto(
        img,
        str(solicitud.folio_licencia or '—'),
        cfg['x'], cfg['y'], cfg['ancho'], cfg['alto'],
        cfg['tamano_fuente'], cfg['color'], cfg['align'],
    )

    return img


def generar_pagina_reverso(solicitud):
    """Genera la página 2 (reverso) con foto, QR y fechas."""
    img = Image.open(os.path.join(CARPETA_IMAGENES, ARCHIVO_REVERSO)).convert('RGBA')

    # ----- Foto del agente -----
    dom = getattr(solicitud, 'domicilio_identificacion', None)
    if dom and dom.foto_agente and os.path.exists(dom.foto_agente.path):
        cfg = COORDS_REVERSO['foto']
        foto = Image.open(dom.foto_agente.path).convert('RGB')

        # Ajuste tipo "cover": recorta y escala sin deformar
        ratio_marco = cfg['ancho'] / cfg['alto']
        ratio_foto = foto.width / foto.height

        if ratio_foto > ratio_marco:
            nuevo_ancho = int(foto.height * ratio_marco)
            offset = (foto.width - nuevo_ancho) // 2
            foto = foto.crop((offset, 0, offset + nuevo_ancho, foto.height))
        else:
            nuevo_alto = int(foto.width / ratio_marco)
            offset = (foto.height - nuevo_alto) // 2
            foto = foto.crop((0, offset, foto.width, offset + nuevo_alto))

        foto = foto.resize((cfg['ancho'], cfg['alto']), Image.LANCZOS)
        img.paste(foto, (cfg['x'], cfg['y']))

    # ----- Cuadrito (marco de la foto) -----
    if os.path.exists(os.path.join(CARPETA_IMAGENES, ARCHIVO_CUADRITO)):
        cfg = COORDS_REVERSO['cuadrito']
        cuadrito = Image.open(os.path.join(CARPETA_IMAGENES, ARCHIVO_CUADRITO)).convert('RGBA')
        cuadrito = cuadrito.resize((cfg['ancho'], cfg['alto']), Image.LANCZOS)
        img.paste(cuadrito, (cfg['x'], cfg['y']), cuadrito)

    # ----- QR -----
    import qrcode
    url = f"http://127.0.0.1:8000/usuarios/verificar-licencia/{solicitud.folio_licencia}/"
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


def generar_licencia_prueba(solicitud):
    """Genera un PDF con las 2 páginas de la licencia."""
    frente = generar_pagina_frente(solicitud)
    reverso = generar_pagina_reverso(solicitud)

    salida = 'test_licencia.pdf'
    frente.save(salida, 'PDF', resolution=300.0, save_all=True, append_images=[reverso])
    print(f"✅ Generado: {os.path.abspath(salida)}")
    return salida


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("GENERANDO LICENCIA DE PRUEBA")
    print("=" * 60)
    print()

    solicitud = (
        Solicitud.objects
        .filter(folio_licencia__isnull=False)
        .first()
    )

    if not solicitud:
        print("⚠️  No hay solicitudes con folio_licencia.")
        print("Generando con la primera solicitud disponible...")
        solicitud = Solicitud.objects.filter(folio__isnull=False).first()

    if not solicitud:
        print("❌ No hay solicitudes en la BD.")
        exit(1)

    print(f"Usando solicitud: {solicitud.folio}")
    print(f"Ciudadano: {solicitud.ciudadano.nombre_completo or '(sin nombre)'}")
    print(f"Folio licencia: {solicitud.folio_licencia or '(sin folio)'}")
    print()

    generar_licencia_prueba(solicitud)

    print()
    print("=" * 60)
    print("Abre test_licencia.pdf en C:\\redait_tabasco\\")
    print("=" * 60)