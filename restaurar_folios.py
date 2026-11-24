"""
Restaura los folios de licencia del JSON de migración al modelo Ciudadano.
"""
import os
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redait_tabasco.settings')
django.setup()

from usuarios.models import Ciudadano, Solicitud

ARCHIVO_JSON = r'C:\redait_tabasco\migracion\agentes_migrados.json'

print("=" * 70)
print("RESTAURACION DE FOLIOS DE LICENCIA")
print("=" * 70)
print()

with open(ARCHIVO_JSON, encoding='utf-8') as f:
    agentes = json.load(f)

print(f"[BOX] {len(agentes)} agentes en el JSON")
print()

# MODO PRUEBA: True = no escribe nada
MODO_DRY_RUN = False

actualizados = 0
sin_solicitud = 0
ya_tenian = 0
errores = 0

for i, agente in enumerate(agentes, 1):
    folio_am = agente['folio']
    folio_corto = folio_am.replace('AM-', '')
    nombre = (agente.get('nombre') or '')[:40]

    print(f"[{i:3d}] {folio_am} - {nombre}")

    try:
        solicitud = Solicitud.objects.filter(folio=folio_am).first()
        if not solicitud:
            print(f"      [!] Solicitud {folio_am} NO existe")
            sin_solicitud += 1
            continue

        ciudadano = solicitud.ciudadano

        if ciudadano.folio_licencia:
            print(f"      [=] Ya tiene folio: {ciudadano.folio_licencia}")
            ya_tenian += 1
            continue

        if not MODO_DRY_RUN:
            ciudadano.folio_licencia = folio_corto
            if not ciudadano.fecha_primera_emision and solicitud.fecha_emision_licencia:
                ciudadano.fecha_primera_emision = solicitud.fecha_emision_licencia
            ciudadano.save(update_fields=['folio_licencia', 'fecha_primera_emision'])
            print(f"      [OK] folio asignado: {folio_corto}")
        else:
            print(f"      [OK] [DRY] folio asignado: {folio_corto}")

        actualizados += 1

    except Exception as e:
        print(f"      [X] Error: {e}")
        errores += 1

print()
print("=" * 70)
print("RESUMEN")
print("=" * 70)
print(f"  [OK]  Actualizados:   {actualizados}")
print(f"  [=]   Ya tenian:      {ya_tenian}")
print(f"  [!]   Sin solicitud:  {sin_solicitud}")
print(f"  [X]   Errores:        {errores}")
print(f"  [#]   Total:          {len(agentes)}")
print("=" * 70)

if MODO_DRY_RUN:
    print()
    print("[!] MODO PRUEBA: no se guardo nada.")
    print("Para aplicar de verdad, cambia MODO_DRY_RUN = False")