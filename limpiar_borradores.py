"""
Elimina las Solicitudes en estado 'borrador' que estén completamente vacías.
Es decir: sin pasos completados, sin archivos, sin comprobante.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redait_tabasco.settings')
django.setup()

from usuarios.models import Solicitud

print("=" * 70)
print("LIMPIEZA DE BORRADORES VACIOS")
print("=" * 70)
print()

# Modo prueba
MODO_DRY_RUN = True

# Query: borradores sin ningún subregistro
borradores_vacios = Solicitud.objects.filter(
    estado='borrador',
    datos_personales__isnull=True,
    domicilio_identificacion__isnull=True,
    documentos_negocio__isnull=True,
    cursos_capacitaciones__isnull=True,
    comprobante_pago='',
)

total = borradores_vacios.count()
print(f"[BOX] Borradores completamente vacios: {total}")
print()

# Verificar que no tengan folio ni historial
con_folio = borradores_vacios.exclude(folio__isnull=True).count()
con_historial = 0
for s in borradores_vacios:
    if s.historial.exists():
        con_historial += 1

print(f"  - Con folio asignado:   {con_folio}")
print(f"  - Con historial:        {con_historial}")
print()

if con_folio > 0 or con_historial > 0:
    print("[!] ADVERTENCIA: Algunos borradores tienen folio o historial.")
    print("    Revisalos manualmente antes de eliminar.")
    print()
    for s in borradores_vacios.exclude(folio__isnull=True)[:10]:
        print(f"    - {s.folio} · {s.ciudadano.nombre_completo[:40]}")
    exit()

if MODO_DRY_RUN:
    print("[!] MODO PRUEBA: no se elimino nada.")
    print("    Cambia MODO_DRY_RUN = False para aplicar.")
else:
    eliminados = borradores_vacios.delete()
    print(f"[OK] Eliminados: {eliminados[0]} registros")

print()
print("=" * 70)