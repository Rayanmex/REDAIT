# usuarios/management/commands/cargar_padron.py

import os
from datetime import datetime, date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth.models import User
from openpyxl import load_workbook

from usuarios.models import (
    Ciudadano,
    Solicitud,
    DatosPersonales,
    DomicilioIdentificacion,
    DocumentosNegocio,
    CursosCapacitaciones,
)


# ============================================================
# CONSTANTES
# ============================================================

ARCHIVO_DEFAULT = 'agentes.xlsx'
HOJA_DEFAULT = 'Agentes'
EMAIL_ADMIN_EXCLUIDO = 'sedec@tabasco.gob.mx'


# ============================================================
# HELPERS DE PARSEO
# ============================================================

def _parse_fecha(valor):
    """Convierte un valor de celda (date, datetime o string) a date, o None."""
    if valor is None or valor == '':
        return None

    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor

    valor_str = str(valor).strip()
    if not valor_str:
        return None

    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(valor_str, fmt).date()
        except ValueError:
            continue
    return None


def _parse_bool_renovacion(valor):
    """'Sí' → True, 'No' o vacío → False."""
    if valor is None:
        return False
    return str(valor).strip().lower() in ('sí', 'si', 'yes', 'true', '1')


def _map_sexo(valor):
    if not valor:
        return 'X'
    v = str(valor).strip().lower()
    if v in ('hombre', 'h', 'masculino', 'm'):
        return 'H'
    if v in ('mujer', 'femenino', 'f'):
        return 'M'
    return 'X'


def _map_regimen(valor):
    if not valor:
        return 'pf'
    v = str(valor).strip().lower()
    if v in ('fisica', 'física', 'fisico', 'físico', 'pf'):
        return 'pf'
    if v in ('moral', 'pm'):
        return 'pm'
    return 'pf'


def _map_estado(estatus):
    v = str(estatus or '').strip().lower()
    if v == 'aprobado':
        return 'aprobada'
    return 'borrador'


def _pasos_por_etapa(progreso, estado):
    v = str(progreso or '').strip().lower()
    p1 = p2 = p3 = p4 = False

    if 'etapa 1' in v:
        p1 = True
    elif 'etapa 2' in v:
        p1 = p2 = True
    elif 'etapa 3' in v:
        p1 = p2 = p3 = True

    if estado == 'aprobada':
        p1 = p2 = p3 = p4 = True

    return p1, p2, p3, p4


# ============================================================
# COMANDO
# ============================================================

class Command(BaseCommand):
    help = 'Carga el padrón histórico desde agentes.xlsx (hoja Agentes).'

    def add_arguments(self, parser):
        parser.add_argument('--archivo', type=str, default=ARCHIVO_DEFAULT)
        parser.add_argument('--hoja', type=str, default=HOJA_DEFAULT)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        archivo = options['archivo']
        hoja = options['hoja']

        if not os.path.exists(archivo):
            raise CommandError(f"No se encontró '{archivo}'.")

        registros = self._leer_excel(archivo, hoja)
        total = len(registros)

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 60))
        self.stdout.write(self.style.MIGRATE_HEADING('📋 Carga de padrón REDAIT'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 60))
        self.stdout.write(f'Archivo:    {archivo}')
        self.stdout.write(f'Hoja:       {hoja}')
        self.stdout.write(f'Registros:  {total}')
        self.stdout.write(f'Modo:       {"DRY RUN (sin guardar)" if dry_run else "REAL"}')
        self.stdout.write('')

        creados = 0
        actualizados = 0
        solicitudes_nuevas = 0
        saltados = []

        # ---------- Ejecutar ----------
        if dry_run:
            # Sin atomic: solo leer y contar sin escribir
            for i, reg in enumerate(registros, 1):
                folio = reg.get('folio', '').strip()
                email = (reg.get('email') or '').strip().lower()
                nombre = reg.get('nombre_completo', '?')

                if not email:
                    saltados.append((folio, nombre, 'sin email'))
                    continue
                if email == EMAIL_ADMIN_EXCLUIDO:
                    saltados.append((folio, nombre, 'es el admin'))
                    continue
                if not folio:
                    saltados.append((folio, nombre, 'sin folio'))
                    continue

                # En dry-run solo verificamos si el User ya existe
                existe = User.objects.filter(username=email).exists()
                if existe:
                    actualizados += 1
                else:
                    creados += 1

                # Contamos solicitudes nuevas solo si el folio no existe
                if not Solicitud.objects.filter(folio=folio).exists():
                    solicitudes_nuevas += 1

                if i % 50 == 0:
                    self.stdout.write(f'  ...{i} procesados')
        else:
            with transaction.atomic():
                for i, reg in enumerate(registros, 1):
                    folio = reg.get('folio', '').strip()
                    email = (reg.get('email') or '').strip().lower()
                    nombre = reg.get('nombre_completo', '?')

                    if not email:
                        saltados.append((folio, nombre, 'sin email'))
                        continue
                    if email == EMAIL_ADMIN_EXCLUIDO:
                        saltados.append((folio, nombre, 'es el admin'))
                        continue
                    if not folio:
                        saltados.append((folio, nombre, 'sin folio'))
                        continue

                    try:
                        user_creado, sol_creada = self._procesar_registro(reg, email)
                        if user_creado:
                            creados += 1
                        else:
                            actualizados += 1
                        if sol_creada:
                            solicitudes_nuevas += 1
                    except Exception as e:
                        saltados.append((folio, nombre, f'error: {e}'))

                    if i % 50 == 0:
                        self.stdout.write(f'  ...{i} procesados')

        # ---------- Reporte ----------
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 60))
        self.stdout.write(self.style.MIGRATE_HEADING('📊 REPORTE'))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'✅ Users creados:       {creados}'))
        self.stdout.write(self.style.WARNING(f'♻️  Users existentes:    {actualizados}'))
        self.stdout.write(f'📄 Solicitudes nuevas:  {solicitudes_nuevas}')

        if saltados:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(
                f'❌ Filas saltadas: {len(saltados)}'
            ))
            for folio, nombre, motivo in saltados:
                self.stdout.write(f'   {folio or "(sin folio)"} - {nombre}: {motivo}')

        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                '🔍 DRY RUN: no se guardó nada. Corre sin --dry-run para aplicar.'
            ))

        self.stdout.write('')

    # ============================================================
    # LECTURA DEL EXCEL
    # ============================================================

    def _leer_excel(self, archivo, hoja):
        wb = load_workbook(archivo, data_only=True)

        if hoja not in wb.sheetnames:
            raise CommandError(
                f"La hoja '{hoja}' no existe. Hojas: {', '.join(wb.sheetnames)}"
            )

        ws = wb[hoja]
        headers = [(c.value or '').strip() for c in ws[1]]
        idx = {h: i for i, h in enumerate(headers)}

        def get(valores, nombre_col):
            i = idx.get(nombre_col)
            if i is None or i >= len(valores):
                return ''
            v = valores[i]
            if v is None:
                return ''
            return v if isinstance(v, (datetime, date)) else str(v).strip()

        registros = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(v not in (None, '') for v in row):
                continue

            registros.append({
                'folio':           get(row, 'Folio'),
                'nombre_completo': get(row, 'Nombre completo'),
                'rfc':             get(row, 'RFC'),
                'curp':            get(row, 'CURP'),
                'direccion':       get(row, 'Dirección'),
                'municipio':       get(row, 'Municipio'),
                'sexo':            get(row, 'Sexo'),
                'razon_social':    get(row, 'Razón social'),
                'regimen_fiscal':  get(row, 'Régimen fiscal'),
                'estatus':         get(row, 'Estatus'),
                'progreso':        get(row, 'Progreso'),
                'email':           get(row, 'Usuario (email)'),
                'renovacion':      get(row, 'Renovación'),
                'fecha_alta':      get(row, 'Fecha Alta'),
                'fecha_vigencia':  get(row, 'Fecha Vigencia'),
            })
        return registros

    # ============================================================
    # PROCESAMIENTO
    # ============================================================

    def _procesar_registro(self, reg, email):
        """Crea o actualiza todo el árbol del ciudadano."""
        folio = reg['folio']
        nombre = str(reg['nombre_completo']).strip()
        estado = _map_estado(reg.get('estatus'))
        p1, p2, p3, p4 = _pasos_por_etapa(reg.get('progreso'), estado)

        # 1) User
        partes = nombre.split()
        first_name = partes[0].title() if partes else ''
        last_name = ' '.join(partes[1:]).title() if len(partes) > 1 else ''

        user, user_creado = User.objects.get_or_create(
            username=email,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'is_active': True,
            },
        )
        if not user_creado and not user.email:
            user.email = email
            user.save(update_fields=['email'])

        # 2) Ciudadano
        ciudadano, _ = Ciudadano.objects.get_or_create(
            user=user,
            defaults={
                'nombre_completo': nombre or 'Sin nombre',
                'telefono': '0000000000',
                'razon_social': str(reg.get('razon_social', '') or ''),
            },
        )
        if reg.get('razon_social') and not ciudadano.razon_social:
            ciudadano.razon_social = str(reg['razon_social'])
            ciudadano.save(update_fields=['razon_social'])

        # 3) Solicitud
        solicitud, sol_creada = Solicitud.objects.get_or_create(
            ciudadano=ciudadano,
            folio=folio,
        )
        solicitud.estado = estado
        solicitud.tipo_tramite = 'nuevo'
        solicitud.renovacion = _parse_bool_renovacion(reg.get('renovacion'))
        solicitud.fecha_alta_padron = _parse_fecha(reg.get('fecha_alta'))
        solicitud.fecha_vigencia_padron = _parse_fecha(reg.get('fecha_vigencia'))

        if estado == 'aprobada' and not solicitud.fecha_envio:
            solicitud.fecha_envio = solicitud.fecha_creacion

        solicitud.save()

        # 4) Paso 1
        dp, _ = DatosPersonales.objects.get_or_create(solicitud=solicitud)
        dp.nombre_completo = nombre or 'Sin nombre'
        dp.rfc = str(reg.get('rfc') or '') or dp.rfc or 'XAXX010101000'
        dp.curp = str(reg.get('curp') or '') or dp.curp or 'XAXX010101HDFXXX00'
        dp.sexo = _map_sexo(reg.get('sexo'))
        dp.regimen_fiscal = _map_regimen(reg.get('regimen_fiscal'))
        dp.completado = p1
        if p1 and not dp.fecha_completado:
            dp.fecha_completado = solicitud.fecha_creacion
        dp.save()

        # 5) Paso 2
        dom, _ = DomicilioIdentificacion.objects.get_or_create(solicitud=solicitud)
        dom.municipio = str(reg.get('municipio') or '')
        dom.calle_numero_colonia_cp = str(reg.get('direccion') or '')
        dom.completado = p2
        if p2 and not dom.fecha_completado:
            dom.fecha_completado = solicitud.fecha_creacion
        dom.save()

        # 6) Paso 3
        doc, _ = DocumentosNegocio.objects.get_or_create(solicitud=solicitud)
        doc.completado = p3
        if p3 and not doc.fecha_completado:
            doc.fecha_completado = solicitud.fecha_creacion
        doc.save()

        # 7) Paso 4
        cur, _ = CursosCapacitaciones.objects.get_or_create(solicitud=solicitud)
        cur.completado = p4
        if p4 and not cur.fecha_completado:
            cur.fecha_completado = solicitud.fecha_creacion
        cur.save()

        return user_creado, sol_creada