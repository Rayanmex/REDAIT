"""
Verifica el estado actual de las solicitudes y qué tienen cargado.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redait_tabasco.settings')
django.setup()

from usuarios.models import Solicitud

# Contar por estado
print("=" * 70)
print("SOLICITUDES POR ESTADO")
print("=" * 70)

from django.db.models import Count
estados = Solicitud.objects.values('estado').annotate(total=Count('id')).order_by('-total')

for e in estados:
    print(f"  {e['estado']:25s} → {e['total']:4d}")

print()
print("=" * 70)
print("DETALLE DE SOLICITUDES CON PAGO VALIDADO O CONSTANCIA EMITIDA")
print("=" * 70)

qs = Solicitud.objects.filter(
    estado__in=['pago_validado', 'constancia_emitida']
).select_related('ciudadano')

if not qs.exists():
    print("⚠️  No hay solicitudes con pago validado o constancia emitida.")
    print()
    print("Esto significa que:")
    print("  - Nadie ha subido comprobante de pago, o")
    print("  - El admin no ha validado ningún pago todavía")
else:
    for s in qs:
        print(f"  Folio: {s.folio}")
        print(f"    Estado: {s.estado}")
        print(f"    Ciudadano: {s.ciudadano.nombre_completo or '(sin nombre)'}")
        print(f"    Folio licencia: {s.folio_licencia or '(sin folio)'}")
        print(f"    Fecha emisión: {s.fecha_emision_licencia or '(sin fecha)'}")
        print(f"    Tiene comprobante: {'Sí' if s.comprobante_pago else 'No'}")
        print()