import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redait_tabasco.settings')
django.setup()

from usuarios.models import Ciudadano, Solicitud
from django.utils import timezone
from datetime import timedelta, date

hoy = timezone.now().date()

folios = ['0310', '0311', '0312', '0313', '0314', '0315', '0316', '0317']

for f in folios:
    c = Ciudadano.objects.filter(folio_licencia=f).first()
    if not c:
        print(f"{f} -> NO ENCONTRADO")
        continue

    print(f"\n{f} · {c.nombre_completo[:45]}")
    sols = list(Solicitud.objects.filter(ciudadano=c))

    # Elegir la mejor solicitud (la que tiene más datos)
    # Criterios: estado != borrador > tiene fecha_vigencia > tiene folio
    mejor = None
    for s in sols:
        score = 0
        if s.estado != 'borrador': score += 100
        if s.fecha_vigencia_padron: score += 50
        if s.folio: score += 25
        if not mejor or score > mejor[0]:
            mejor = (score, s)

    if not mejor:
        print("   ❌ Sin solicitud")
        continue

    s = mejor[1]
    print(f"   Elegida: id={s.id} estado={s.estado} folio={s.folio} vigencia={s.fecha_vigencia_padron}")

    # Actualizar
    s.estado = 'licencia_emitida'
    s.pago_estado = 'pago_validado'
    if not s.folio:
        # Si no tiene folio, le ponemos uno AM-0XXX con base en el folio_licencia
        s.folio = f"AM-{f.zfill(4)}"
    # Vigencia: si tiene una fecha, sumarle 1 año; si no, hoy + 1 año
    if s.fecha_vigencia_padron and s.fecha_vigencia_padron < hoy:
        # Extender 1 año desde la fecha original
        nueva_vigencia = s.fecha_vigencia_padron + timedelta(days=365)
        # Si aún así queda vencida, poner hoy + 1 año
        if nueva_vigencia < hoy:
            nueva_vigencia = hoy + timedelta(days=365)
    else:
        nueva_vigencia = hoy + timedelta(days=365)

    s.fecha_vigencia_padron = nueva_vigencia
    if not s.fecha_alta_padron:
        s.fecha_alta_padron = hoy
    if not s.fecha_emision_licencia:
        s.fecha_emision_licencia = timezone.now()
    s.save()
    print(f"   ✅ Actualizada: estado=licencia_emitida, vigencia={nueva_vigencia}, folio={s.folio}")

print("\n=== VERIFICACIÓN ===")
from django.db.models import Count
sols_vigentes = Solicitud.objects.filter(
    estado='licencia_emitida',
    fecha_vigencia_padron__gte=hoy,
    ciudadano__folio_licencia__isnull=False,
)
print(f"Solicitudes vigentes en padrón: {sols_vigentes.count()}")
print()
print("Con empresa:")
for s in sols_vigentes.filter(ciudadano__empresa__isnull=False).order_by('ciudadano__folio_licencia'):
    print(f"  {s.ciudadano.folio_licencia} -> {s.ciudadano.nombre_completo[:40]}")