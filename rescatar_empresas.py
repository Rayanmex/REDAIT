"""
Crea Empresas a partir de las personas morales del backup.
NO las asocia automáticamente porque los ciudadanos están vacíos.
El admin podrá asociarlas manualmente después.
"""
import sqlite3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redait_tabasco.settings')
django.setup()

from usuarios.models import Empresa

BACKUP_PATH = r'C:\redait_tabasco\db_backup_antes_migracion.sqlite3'

# Modo prueba
MODO_DRY_RUN = True

print("=" * 70)
print("CREACIÓN DE EMPRESAS DESDE BACKUP")
print("=" * 70)
print()

if not os.path.exists(BACKUP_PATH):
    print(f"[X] No existe el backup en: {BACKUP_PATH}")
    exit(1)

conn = sqlite3.connect(BACKUP_PATH)
cursor = conn.cursor()

cursor.execute("""
    SELECT DISTINCT dp.nombre_completo, dp.rfc
    FROM usuarios_datospersonales dp
    WHERE dp.regimen_fiscal = 'pm'
    AND dp.nombre_completo IS NOT NULL
    AND dp.nombre_completo != ''
""")
personas_morales = cursor.fetchall()
conn.close()

print(f"[#] Personas morales únicas: {len(personas_morales)}")
print()

for nombre_emp, rfc in personas_morales:
    print(f"  • {nombre_emp}")
    print(f"    RFC: {rfc or '—'}")
    print()

if MODO_DRY_RUN:
    print("[!] MODO PRUEBA: no se creó nada.")
    print("    Cambia MODO_DRY_RUN = False para aplicar.")
    exit(0)

# ============================================================
# CREAR EMPRESAS
# ============================================================
print("=" * 70)
print("APLICANDO CAMBIOS...")
print("=" * 70)
print()

creadas = 0
ya_existian = 0

for nombre_emp, rfc in personas_morales:
    nombre_norm = nombre_emp.strip().upper()
    rfc_norm = (rfc or '').strip().upper()

    empresa, created = Empresa.objects.get_or_create(
        nombre=nombre_norm,
        defaults={
            'razon_social': nombre_norm,
            'rfc': rfc_norm,
        }
    )

    if created:
        creadas += 1
        print(f"[+] {nombre_norm}")
    else:
        ya_existian += 1
        print(f"[=] Ya existía: {nombre_norm}")

print()
print("=" * 70)
print("RESUMEN")
print("=" * 70)
print(f"  Empresas creadas:      {creadas}")
print(f"  Empresas ya existentes: {ya_existian}")
print("=" * 70)
print()
print("[i] IMPORTANTE: las empresas NO se asociaron a ciudadanos.")
print("    El admin debe asociarlas manualmente desde el editor de solicitud.")