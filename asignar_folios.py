import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redait_tabasco.settings')
django.setup()

from usuarios.models import Ciudadano

# Calcular siguiente folio
nums = [
    int(f) for f in Ciudadano.objects
    .exclude(folio_licencia__isnull=True)
    .exclude(folio_licencia='')
    .values_list('folio_licencia', flat=True)
    if f and f.isdigit()
]
siguiente = max(nums) + 1 if nums else 1
print(f"Siguiente folio: {siguiente:04d}")
print()

# Ciudadanos con empresa sin folio
sin_folio = Ciudadano.objects.filter(
    empresa__isnull=False,
    folio_licencia__isnull=True
).order_by('id')

print(f"Ciudadanos a asignar: {sin_folio.count()}")
print()

for c in sin_folio:
    while Ciudadano.objects.filter(folio_licencia=f"{siguiente:04d}").exists():
        siguiente += 1
    folio = f"{siguiente:04d}"
    c.folio_licencia = folio
    c.save()
    print(f"OK {folio} -> {c.nombre_completo}")
    siguiente += 1

print()
print("=== VERIFICACION ===")
con_empresa = Ciudadano.objects.filter(
    folio_licencia__isnull=False,
    empresa__isnull=False
)
print(f"Total con folio + empresa: {con_empresa.count()}")
for c in con_empresa.order_by('folio_licencia'):
    print(f"  {c.folio_licencia} -> {c.nombre_completo} | {c.empresa.nombre}")