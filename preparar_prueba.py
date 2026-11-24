"""
Prepara una solicitud de prueba con nombre, folio de licencia, fechas y foto.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redait_tabasco.settings')
django.setup()

from django.utils import timezone
from django.core.files import File
from usuarios.models import Solicitud


# ============================================================
# CONFIGURACIÓN
# ============================================================

# Foto de prueba (cualquiera de la carpeta personas_gemini)
RUTA_FOTO_PRUEBA = r'C:\redait_tabasco\static\images\personas_gemini\carlos_alberto_chacon_castro.png'

# Datos de prueba
NOMBRE_PRUEBA = "CARLOS ALBERTO CHACON CASTRO"
FOLIO_LICENCIA_PRUEBA = "0295"  # solo el número, como lo quieres


# ============================================================
# EJECUCIÓN
# ============================================================

# Toma la primera solicitud
s = Solicitud.objects.filter(folio__isnull=False).first()

if not s:
    print("❌ No hay solicitudes con folio")
    exit(1)

print(f"Preparando solicitud {s.folio}...")

# 1. Nombre del ciudadano
s.ciudadano.nombre_completo = NOMBRE_PRUEBA
s.ciudadano.save()
print(f"✅ Nombre: {s.ciudadano.nombre_completo}")

# 2. Folio de licencia
s.folio_licencia = FOLIO_LICENCIA_PRUEBA
print(f"✅ Folio licencia: {s.folio_licencia}")

# 3. Fechas
s.fecha_emision_licencia = timezone.now()
print(f"✅ Fecha emisión: {s.fecha_emision_licencia.strftime('%d/%m/%Y')}")

s.save()

# 4. Foto del agente
dom = getattr(s, 'domicilio_identificacion', None)
if not dom:
    from usuarios.models import DomicilioIdentificacion
    dom = DomicilioIdentificacion.objects.create(solicitud=s)

if os.path.exists(RUTA_FOTO_PRUEBA):
    with open(RUTA_FOTO_PRUEBA, 'rb') as f:
        # Borrar la foto anterior si existe
        if dom.foto_agente:
            try:
                dom.foto_agente.delete(save=False)
            except Exception:
                pass
        dom.foto_agente.save('foto_prueba.png', File(f), save=True)
    print(f"✅ Foto del agente: {dom.foto_agente.name}")
else:
    print(f"⚠️  No existe la foto: {RUTA_FOTO_PRUEBA}")

print()
print("=" * 60)
print("Listo. Ahora corre: python test_licencia.py")
print("=" * 60)