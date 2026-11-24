"""
Importa datos del Excel agentes.xlsx a la BD.
- Crea Empresas desde la columna "Razón social"
- Actualiza Ciudadano, DatosPersonales y DomicilioIdentificacion
- Reporta agentes del Excel que NO existen en la BD
"""
import os
import django
from openpyxl import load_workbook

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'redait_tabasco.settings')
django.setup()

from usuarios.models import (
    Ciudadano, Solicitud, Empresa,
    DatosPersonales, DomicilioIdentificacion,
)

XLSX_PATH = r'C:\redait_tabasco\agentes.xlsx'

# MODO PRUEBA
MODO_DRY_RUN = False

# ============================================================
# MAPEO DE MUNICIPIOS (Excel → BD)
# ============================================================
MUNICIPIOS_MAP = {
    'centro': 'CENTRO',
    'cardenas': 'CÁRDENAS',
    'cárdenas': 'CÁRDENAS',
    'nacajuca': 'NACAJUCA',
    'balancan': 'BALANCÁN',
    'balancán': 'BALANCÁN',
    'macuspana': 'MACUSPANA',
    'tenosique': 'TENOSIQUE',
    'jalpa_mendez': 'JALPA DE MÉNDEZ',
    'jalpa de méndez': 'JALPA DE MÉNDEZ',
    'comalcalco': 'COMALCALCO',
    'centla': 'CENTLA',
    'cunduacan': 'CUNDUACÁN',
    'cunduacán': 'CUNDUACÁN',
    'huimanguillo': 'HUIMANGUILLO',
    'jalapa': 'JALAPA',
    'jonuta': 'JONUTA',
    'paraíso': 'PARAÍSO',
    'paraiso': 'PARAÍSO',
    'tacotalpa': 'TACOTALPA',
    'teapa': 'TEAPA',
    'emiliano zapata': 'EMILIANO ZAPATA',
}

# MAPEO SEXO
SEXO_MAP = {
    'hombre': 'H',
    'mujer': 'M',
    'n': 'X',
    'h': 'H',
    'm': 'M',
}

# MAPEO RÉGIMEN FISCAL
REGIMEN_MAP = {
    'fisica': 'pfae',
    'física': 'pfae',
    'moral': 'pm',
}

# ============================================================
# LEER EXCEL
# ============================================================
print("=" * 70)
print("IMPORTACIÓN DE AGENTES DESDE EXCEL")
print("=" * 70)
print()

if not os.path.exists(XLSX_PATH):
    print(f"[X] No existe el Excel: {XLSX_PATH}")
    exit(1)

wb = load_workbook(XLSX_PATH, read_only=True, data_only=True)
ws = wb.active

# Leer encabezados
headers = [cell.value for cell in ws[1]]
print(f"Headers: {headers}")
print()

# Índices de columnas (0-based)
idx = {h: i for i, h in enumerate(headers)}

filas = list(ws.iter_rows(min_row=2, values_only=True))
wb.close()

print(f"[#] Filas en el Excel: {len(filas)}")
print()

# ============================================================
# PROCESAR
# ============================================================
stats = {
    'agentes_procesados': 0,
    'no_encontrados': [],
    'empresas_creadas': 0,
    'ciudadanos_actualizados': 0,
    'datos_personales_actualizados': 0,
    'domicilios_actualizados': 0,
    'emails_actualizados': 0,
    'errores': [],
}

# Cache de empresas
empresas_cache = {}

for i, fila in enumerate(filas, start=2):
    try:
        folio = fila[idx.get('Folio', 0)]
        if not folio:
            continue

        folio = str(folio).strip().upper()
        if not folio.startswith('AM-'):
            continue

        stats['agentes_procesados'] += 1

        # Buscar solicitud
        solicitud = Solicitud.objects.filter(folio=folio).select_related('ciudadano').first()
        if not solicitud:
            stats['no_encontrados'].append(folio)
            continue

        ciudadano = solicitud.ciudadano

        # ---------- EXTRAER DATOS DEL EXCEL ----------
        nombre = (fila[idx.get('Nombre completo', 1)] or '').strip().upper()
        rfc = (fila[idx.get('RFC', 2)] or '').strip().upper()
        curp = (fila[idx.get('CURP', 3)] or '').strip().upper()
        direccion = (fila[idx.get('Dirección', 4)] or '').strip().upper()
        municipio_raw = (fila[idx.get('Municipio', 5)] or '').strip().lower()
        sexo_raw = (fila[idx.get('Sexo', 6)] or '').strip().lower()
        razon_social = (fila[idx.get('Razón social', 7)] or '').strip().upper()
        regimen_raw = (fila[idx.get('Régimen fiscal', 8)] or '').strip().lower()
        email = (fila[idx.get('Usuario (email)', 11)] or '').strip().lower()

        municipio = MUNICIPIOS_MAP.get(municipio_raw, '') if municipio_raw else ''
        sexo = SEXO_MAP.get(sexo_raw, 'H')
        regimen = REGIMEN_MAP.get(regimen_raw, 'pfae')

        # ---------- EMPRESA (si es persona moral) ----------
                # ---------- EMPRESA (si es persona moral) ----------
        # Ignorar basura de prueba
        razon_social_limpia = razon_social.replace(',', '').strip()

        razones_ignorar = {'GDGVH', 'PRUEBA', 'TEST', 'DEMO'}

        if razon_social_limpia and regimen == 'pm' and razon_social_limpia.upper() not in razones_ignorar:
            razon_social = razon_social_limpia
            empresa = empresas_cache.get(razon_social)
            if not empresa:
                empresa, created = Empresa.objects.get_or_create(
                    nombre=razon_social,
                    defaults={'razon_social': razon_social}
                )
                empresas_cache[razon_social] = empresa
                if created:
                    stats['empresas_creadas'] += 1
                    if MODO_DRY_RUN:
                        print(f"[EMPRESA] {razon_social}")

            if ciudadano.empresa != empresa:
                if not MODO_DRY_RUN:
                    ciudadano.empresa = empresa

        # ---------- CIUDADANO ----------
        cambios_ciudadano = False
        if not ciudadano.nombre_completo and nombre:
            ciudadano.nombre_completo = nombre
            cambios_ciudadano = True

        if email and not ciudadano.user.email:
            if not MODO_DRY_RUN:
                ciudadano.user.email = email
                ciudadano.user.username = email
                ciudadano.user.save()
            stats['emails_actualizados'] += 1

        if cambios_ciudadano or ciudadano.empresa:
            if not MODO_DRY_RUN:
                ciudadano.save()
            stats['ciudadanos_actualizados'] += 1

        # ---------- DATOS PERSONALES ----------
        dp, _ = DatosPersonales.objects.get_or_create(solicitud=solicitud)
        cambios_dp = False

        if rfc and dp.rfc != rfc:
            dp.rfc = rfc
            cambios_dp = True
        if curp and dp.curp != curp:
            dp.curp = curp
            cambios_dp = True
        if sexo and dp.sexo != sexo:
            dp.sexo = sexo
            cambios_dp = True
        if regimen and dp.regimen_fiscal != regimen:
            dp.regimen_fiscal = regimen
            cambios_dp = True

        if cambios_dp:
            if not MODO_DRY_RUN:
                dp.save()
            stats['datos_personales_actualizados'] += 1

        # ---------- DOMICILIO ----------
        dom, _ = DomicilioIdentificacion.objects.get_or_create(solicitud=solicitud)
        cambios_dom = False

        if municipio and dom.municipio != municipio:
            dom.municipio = municipio
            cambios_dom = True
        if direccion and not dom.calle_numero_colonia_cp:
            dom.calle_numero_colonia_cp = direccion
            cambios_dom = True

        if cambios_dom:
            if not MODO_DRY_RUN:
                dom.save()
            stats['domicilios_actualizados'] += 1

    except Exception as e:
        stats['errores'].append(f"Fila {i} ({folio}): {str(e)}")

# ============================================================
# RESUMEN
# ============================================================
print("=" * 70)
print("RESUMEN")
print("=" * 70)
print(f"  Agentes procesados:              {stats['agentes_procesados']}")
print(f"  No encontrados en BD:            {len(stats['no_encontrados'])}")
print(f"  Empresas creadas:                {stats['empresas_creadas']}")
print(f"  Ciudadanos actualizados:         {stats['ciudadanos_actualizados']}")
print(f"  Datos personales actualizados:   {stats['datos_personales_actualizados']}")
print(f"  Domicilios actualizados:         {stats['domicilios_actualizados']}")
print(f"  Emails actualizados:             {stats['emails_actualizados']}")
print(f"  Errores:                         {len(stats['errores'])}")
print("=" * 70)

if stats['no_encontrados']:
    print()
    print(f"[!] Agentes del Excel que NO existen en la BD ({len(stats['no_encontrados'])}):")
    for folio in stats['no_encontrados'][:30]:
        print(f"    • {folio}")
    if len(stats['no_encontrados']) > 30:
        print(f"    ... y {len(stats['no_encontrados']) - 30} más")

if stats['errores']:
    print()
    print(f"[X] Errores:")
    for err in stats['errores'][:10]:
        print(f"    • {err}")

if MODO_DRY_RUN:
    print()
    print("[!] MODO PRUEBA: no se guardó nada.")
    print("    Cambia MODO_DRY_RUN = False para aplicar.")