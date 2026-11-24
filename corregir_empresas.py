"""
Limpia empresas duplicadas/basura y crea las que faltan a partir del nombre_completo.
"""
import os
import django
from openpyxl import load_workbook

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redait_tabasco.settings')
django.setup()

from usuarios.models import Ciudadano, Solicitud, Empresa

XLSX_PATH = r'C:\redait_tabasco\agentes.xlsx'
MODO_DRY_RUN = False  # Cambia a True para no aplicar cambios

# ============================================================
# 1. LIMPIAR EMPRESAS BASURA / DUPLICADAS
# ============================================================
print("=" * 70)
print("LIMPIEZA Y CREACIÓN DE EMPRESAS")
print("=" * 70)
print()

# Eliminar GDGVH
gdgvh = Empresa.objects.filter(nombre='GDGVH').first()
if gdgvh:
    print("[DEL] Eliminando empresa basura: GDGVH")
    if not MODO_DRY_RUN:
        gdgvh.delete()

# Eliminar duplicado con coma
duplicado = Empresa.objects.filter(nombre__icontains='TERRANOVA DEL SURESTE,').first()
if duplicado:
    print(f"[DEL] Eliminando duplicado: {duplicado.nombre}")
    if not MODO_DRY_RUN:
        duplicado.delete()

# ============================================================
# 2. LEER EXCEL Y PROCESAR MORALES
# ============================================================
wb = load_workbook(XLSX_PATH, read_only=True, data_only=True)
ws = wb.active

headers = [cell.value for cell in ws[1]]
idx = {h: i for i, h in enumerate(headers)}

creadas = 0
asociadas = 0
sin_solicitud = []

for fila in ws.iter_rows(min_row=2, values_only=True):
    regimen = (fila[idx['Régimen fiscal']] or '').strip().lower()
    if regimen != 'moral':
        continue

    folio = str(fila[idx['Folio']] or '').strip().upper()
    nombre = (fila[idx['Nombre completo']] or '').strip().upper()
    razon_social_excel = (fila[idx['Razón social']] or '').strip().upper()

    # Determinar nombre de la empresa
    razon_social_excel = razon_social_excel.replace(',', '').replace('  ', ' ').strip()

    # Ignorar basura
    if razon_social_excel in ('GDGVH', 'PRUEBA', 'TEST', 'DEMO'):
        continue

    # Si no hay razón social, usar el nombre completo
    nombre_empresa = razon_social_excel or nombre

    if not nombre_empresa:
        continue

    # Buscar solicitud
    solicitud = Solicitud.objects.filter(folio=folio).select_related('ciudadano').first()
    if not solicitud:
        sin_solicitud.append(folio)
        continue

    ciudadano = solicitud.ciudadano

    # Crear o recuperar empresa
    empresa, created = Empresa.objects.get_or_create(
        nombre=nombre_empresa,
        defaults={'razon_social': nombre_empresa}
    )

    if created:
        creadas += 1
        print(f"[+] Empresa creada: {nombre_empresa}")

    # Asociar al ciudadano
    if ciudadano.empresa != empresa:
        if not MODO_DRY_RUN:
            ciudadano.empresa = empresa
            ciudadano.save(update_fields=['empresa'])
        asociadas += 1
        print(f"    → {folio} · {ciudadano.nombre_completo} → {empresa.nombre}")

wb.close()

print()
print("=" * 70)
print("RESUMEN")
print("=" * 70)
print(f"  Empresas creadas:      {creadas}")
print(f"  Ciudadanos asociados:  {asociadas}")
print(f"  Sin solicitud en BD:   {len(sin_solicitud)}")
if sin_solicitud:
    print(f"    {sin_solicitud}")
print("=" * 70)

if MODO_DRY_RUN:
    print()
    print("[!] MODO PRUEBA. Cambia MODO_DRY_RUN = False para aplicar.")