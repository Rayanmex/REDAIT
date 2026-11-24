"""
Genera versiones con cuadrícula de las imágenes de la licencia
para definir las coordenadas exactas de cada elemento.
"""
from PIL import Image, ImageDraw, ImageFont
import os

Image.MAX_IMAGE_PIXELS = None  # evita el DecompressionBombWarning

CARPETA = r'C:\redait_tabasco\static\images'


def generar_grid(nombre_archivo):
    ruta = os.path.join(CARPETA, nombre_archivo)
    img = Image.open(ruta).convert('RGBA')
    ancho, alto = img.size

    # Capa transparente para dibujar
    overlay = Image.new('RGBA', (ancho, alto), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 10 columnas y 10 filas
    cols, filas = 10, 10

    # Líneas verticales
    for i in range(1, cols):
        x = int(ancho * i / cols)
        draw.line([(x, 0), (x, alto)], fill=(255, 0, 0, 180), width=3)
        # Número de columna
        draw.text((x + 5, 10), f"C{i}", fill=(255, 0, 0, 255))

    # Líneas horizontales
    for j in range(1, filas):
        y = int(alto * j / filas)
        draw.line([(0, y), (ancho, y)], fill=(0, 0, 255, 180), width=3)
        # Número de fila
        draw.text((10, y + 5), f"F{j}", fill=(0, 0, 255, 255))

    # Etiquetas de esquina
    draw.text((5, 5), "0,0", fill=(0, 0, 0, 255))

    # Combinar
    resultado = Image.alpha_composite(img, overlay).convert('RGB')

    # Guardar como JPG (más liviano que PNG)
    nombre, _ = os.path.splitext(nombre_archivo)
    salida = os.path.join(CARPETA, f"{nombre}_grid.jpg")
    resultado.save(salida, 'JPEG', quality=85)

    print(f"✅ {salida}")
    print(f"   Tamaño: {ancho} × {alto} px")
    print()


if __name__ == '__main__':
    print("=" * 60)
    print("GENERANDO CUADRÍCULAS")
    print("=" * 60)
    print()

    generar_grid('portada_1_ok.png')
    generar_grid('portada_2_ok.png')

    print("=" * 60)
    print("✅ LISTO. Abre portada_1_grid.jpg y portada_2_grid.jpg")
    print("=" * 60)