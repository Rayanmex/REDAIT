import sqlite3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redait_tabasco.settings')
django.setup()

from usuarios.models import Ciudadano

conn = sqlite3.connect(r'C:\redait_tabasco\db_backup_antes_migracion.sqlite3')
cur = conn.cursor()

cur.execute("""
    SELECT dp.nombre_completo, c.nombre_completo, c.id
    FROM usuarios_datospersonales dp
    INNER JOIN usuarios_solicitud s ON s.id = dp.solicitud_id
    INNER JOIN usuarios_ciudadano c ON c.id = s.ciudadano_id
    WHERE dp.regimen_fiscal = 'pm'
""")
rows = cur.fetchall()
conn.close()

print("=" * 80)
print(f"Personas morales en el backup: {len(rows)}")
print("=" * 80)
print()

for nombre_dp, nombre_ciudadano, ciudadano_id_viejo in rows:
    print(f"DP (DatosPersonales): {nombre_dp!r}")

    if nombre_ciudadano:
        match = Ciudadano.objects.filter(
            nombre_completo__iexact=nombre_ciudadano.strip()
        ).first()
        print(f"CK (Ciudadano viejo): {nombre_ciudadano!r}")
        print(f"Match en BD actual:   {match.nombre_completo if match else '❌ NO ENCONTRADO'}")
    else:
        print(f"CK (Ciudadano viejo): ❌ VACÍO en el backup")

    print()