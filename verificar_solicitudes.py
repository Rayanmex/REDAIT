import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redait_tabasco.settings')
django.setup()

from usuarios.models import Ciudadano, Solicitud
from django.utils import timezone

hoy = timezone.now().date()
print(f"Hoy: {hoy}")
print()

folios = ['0310', '0311', '0312', '0313', '0314', '0315', '0316', '0317']

for f in folios:
    c = Ciudadano.objects.filter(folio_licencia=f).first()
    if not c:
        print(f"{f} -> NO ENCONTRADO")
        continue

    sols = Solicitud.objects.filter(ciudadano=c)
    print(f"{f} · {c.nombre_completo[:45]:45s}")
    if not sols.exists():
        print(f"   ❌ SIN SOLICITUD")
    else:
        for s in sols:
            vigente = "✅ VIGENTE" if (s.fecha_vigencia_padron and s.fecha_vigencia_padron >= hoy) else "❌ VENCIDA/NULA"
            print(f"   Solicitud: estado={s.estado} | vigencia={s.fecha_vigencia_padron} | {vigente}")
    print()