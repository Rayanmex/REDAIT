"""
Script para reducir las imágenes de la licencia al tamaño correcto
para generar el PDF en tamaño carta horizontal a 300 DPI.
"""
from PIL import Image
import os

# ============================================================
# CONFIGURACIÓN
# ============================================================

CARPETA = r'C:\redait_tabasco\static\images'

# Tamaños destino (ancho, alto) en píxeles
# 3300 x 2550 = carta horizontal a 300 DPI
TAMANO_PORTADAS = (3300, 2550)

# El cuadrito es el marco de la foto. Ajusta si quieres otro tamaño.
# Lo mantenemos proporcional al original (884 x 1177)
TAMANO_CUADRITO = (600, 800)  # aprox 2 x 2.66 pulgadas a 300 DPI

# Calidad de salida (0-100, solo aplica para JPEG; PNG es lossless)
# Para PNG usamos optimize=True que reduce sin perder calidad


# ============================================================
# FUNCIÓN DE REDUCCIÓN
# ============================================================

def reducir(ruta_entrada, tamano_destino, sufijo='_ok'):
    """Reduce una imagen al tamaño destino y la guarda con sufijo."""
    if not os.path.exists(ruta_entrada):
        print(f"❌ No existe: {ruta_entrada}")
        return None

    # Cargar
    img = Image.open(ruta_entrada)
    original_size = img.size

    # Reducir con LANCZOS (alta calidad) manteniendo proporción
    img_red = img.copy()
    img_red.thumbnail(tamano_destino, Image.LANCZOS)

    # Calcular nuevo tamaño (thumbnail mantiene proporción)
    nuevo_size = img_red.size

    # Crear nombre de salida
    nombre, ext = os.path.splitext(ruta_entrada)
    ruta_salida = f"{nombre}{sufijo}{ext}"

    # Guardar
    if ext.lower() in ('.jpg', '.jpeg'):
        img_red = img_red.convert('RGB')
        img_red.save(ruta_salida, 'JPEG', quality=90, optimize=True)
    else:
        img_red.save(ruta_salida, 'PNG', optimize=True)

    # Tamaño del archivo en KB
    peso_kb = os.path.getsize(ruta_salida) / 1024

    print(f"✅ {os.path.basename(ruta_entrada)}")
    print(f"   Original: {original_size[0]} × {original_size[1]} px")
    print(f"   Nuevo:    {nuevo_size[0]} × {nuevo_size[1]} px")
    print(f"   Peso:     {peso_kb:.1f} KB")
    print(f"   Guardado: {ruta_salida}")
    print()

    return ruta_salida


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("REDUCIENDO IMÁGENES DE LICENCIA")
    print("=" * 60)
    print()

    # Reducir portadas
    reducir(
        os.path.join(CARPETA, 'portada_1.png'),
        TAMANO_PORTADAS,
    )
    reducir(
        os.path.join(CARPETA, 'portada_2.png'),
        TAMANO_PORTADAS,
    )

    # Reducir cuadrito
    reducir(
        os.path.join(CARPETA, 'cuadrito.png'),
        TAMANO_CUADRITO,
    )

    print("=" * 60)
    print("✅ PROCESO TERMINADO")
    print("=" * 60)