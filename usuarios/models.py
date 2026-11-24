from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import RegexValidator, MinLengthValidator
from django.utils import timezone


# ============================================================
# VALIDADORES REUTILIZABLES
# ============================================================

telefono_validator = RegexValidator(
    regex=r'^\d{10}$',
    message='El teléfono debe tener exactamente 10 dígitos (solo números).'
)

rfc_validator = RegexValidator(
    regex=r'^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$',
    message='El RFC no tiene un formato válido (ej. XAXX010101000).'
)

curp_validator = RegexValidator(
    regex=r'^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d$',
    message='La CURP no tiene un formato válido (18 caracteres).'
)

nombre_validator = RegexValidator(
    regex=r"^[A-Za-zÁÉÍÓÚÑÜáéíóúñü\s\.\-\']+$",
    message='El nombre solo puede contener letras, espacios, puntos y guiones.'
)


# ============================================================
# CONSTANTES
# ============================================================

MUNICIPIOS_TABASCO = [
    ('BALANCÁN', 'Balancán'),
    ('CÁRDENAS', 'Cárdenas'),
    ('CENTLA', 'Centla'),
    ('CENTRO', 'Centro (Villahermosa)'),
    ('COMALCALCO', 'Comalcalco'),
    ('CUNDUACÁN', 'Cunduacán'),
    ('EMILIANO ZAPATA', 'Emiliano Zapata'),
    ('HUIMANGUILLO', 'Huimanguillo'),
    ('JALAPA', 'Jalapa'),
    ('JALPA DE MÉNDEZ', 'Jalpa de Méndez'),
    ('JONUTA', 'Jonuta'),
    ('MACUSPANA', 'Macuspana'),
    ('NACAJUCA', 'Nacajuca'),
    ('PARAÍSO', 'Paraíso'),
    ('TACOTALPA', 'Tacotalpa'),
    ('TEAPA', 'Teapa'),
    ('TENOSIQUE', 'Tenosique'),
]

TIPOS_TRAMITE = [
    ('nuevo', 'Registro de nuevo agente inmobiliario'),
    ('revalidacion', 'Revalidación'),
]

# ============================================================
# 6 ESTADOS PRINCIPALES DEL FLUJO
# ============================================================

ESTADOS_SOLICITUD = [
    ('borrador', 'Borrador'),
    ('en_revision', 'En revisión'),
    ('aprobada', 'Aprobada · Ciclo de pago'),
    ('requiere_accion', 'Requiere acción del ciudadano'),
    ('rechazada', 'Rechazada'),
    ('licencia_emitida', 'Licencia emitida'),
]

MOTIVOS_ACCION = [
    ('corregir_documentos', 'Corregir documentos'),
    ('resubir_comprobante', 'Volver a subir comprobante'),
]

PAGO_ESTADOS = [
    ('sin_comprobante', 'Sin comprobante'),
    ('comprobante_cargado', 'Comprobante en revisión'),
    ('comprobante_rechazado', 'Comprobante rechazado'),
    ('pago_validado', 'Pago validado'),
]

ESTADOS_BLOQUEADOS = [
    'licencia_emitida',
]

# Valores por defecto para el cálculo del pago (UMA)
UMA_CANTIDAD_DEFAULT = 6.00
UMA_VALOR_DEFAULT = 117.31
MONTO_PAGO_DEFAULT = 703.86

# Mínimo de horas de capacitación requeridas por ley
HORAS_MINIMAS_CAPACITACION = 30


# ============================================================
# EMPRESA / CORPORATIVO
# ============================================================

class Empresa(models.Model):
    """Empresa o corporativo inmobiliario.

    Los ciudadanos pueden estar asociados a una empresa (opcional).
    Permite agrupar agentes por empresa en el padrón.
    """
    nombre = models.CharField(
        max_length=250,
        unique=True,
        verbose_name='Nombre de la empresa',
        help_text='Nombre comercial o razón social corta.',
    )
    razon_social = models.CharField(
        max_length=250,
        blank=True,
        default='',
        verbose_name='Razón social',
    )
    rfc = models.CharField(
        max_length=13,
        blank=True,
        default='',
        verbose_name='RFC',
    )
    telefono = models.CharField(
        max_length=10,
        blank=True,
        default='',
        validators=[telefono_validator],
        verbose_name='Teléfono',
    )
    direccion = models.TextField(
        blank=True,
        default='',
        verbose_name='Dirección',
    )
    activa = models.BooleanField(
        default=True,
        verbose_name='Activa',
        help_text='Desmarca si la empresa ya no opera.',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = ' '.join(self.nombre.split()).upper()
        if self.razon_social:
            self.razon_social = ' '.join(self.razon_social.split()).upper()
        if self.rfc:
            self.rfc = self.rfc.upper().strip()

        if self.folio_licencia:
            self.folio_licencia = str(self.folio_licencia).upper().strip()
            if self.folio_licencia.startswith('AM-'):
                self.folio_licencia = self.folio_licencia[3:]
            if not self.folio_licencia:
                self.folio_licencia = None

        # Normaliza el teléfono
        if self.telefono:
            self.telefono = (
                str(self.telefono)
                .replace(' ', '').replace('-', '')
                .replace('(', '').replace(')', '').replace('+', '')
            )
            if len(self.telefono) == 12 and self.telefono.startswith('52'):
                self.telefono = self.telefono[2:]
            elif len(self.telefono) == 13 and self.telefono.startswith('521'):
                self.telefono = self.telefono[3:]
        super().save(*args, **kwargs)

    @property
    def total_agentes(self):
        """Cantidad de agentes activos asociados a esta empresa."""
        return self.agentes.filter(
            folio_licencia__isnull=False
        ).count()


# ============================================================
# CIUDADANO (perfil del User)
# ============================================================

class Ciudadano(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ciudadano')
    nombre_completo = models.CharField(
        max_length=200,
        validators=[MinLengthValidator(3), nombre_validator],
    )
    telefono = models.CharField(
        max_length=10,
        validators=[telefono_validator],
        help_text='10 dígitos, sin espacios ni guiones.',
    )

    # ===== EMPRESA (opcional) =====
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agentes',
        verbose_name='Empresa',
        help_text='Empresa o corporativo al que pertenece (opcional).',
    )
    empresa_nombre_manual = models.CharField(
        max_length=250,
        blank=True,
        default='',
        verbose_name='Nombre de empresa (si no está registrada)',
        help_text='Solo si la empresa no está en el catálogo.',
    )

    # ===== FOLIO DE LICENCIA (del AGENTE, no del trámite) =====
    folio_licencia = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Folio de licencia',
        help_text='Número consecutivo único del agente (sin prefijo AM-). '
                  'No cambia en revalidaciones.',
    )
    fecha_primera_emision = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de primera emisión',
        help_text='Cuándo se emitió la primera licencia al agente.',
    )

    # ===== ESTADO DEL CIUDADANO =====
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
        help_text='Desmarca si el ciudadano ya no opera. '
                  'No aparecerá en el padrón ni podrá descargar licencia.',
    )
    fecha_desactivacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de desactivación',
    )
    motivo_desactivacion = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='Motivo de desactivación',
    )

    acepto_aviso = models.BooleanField(default=False)
    fecha_aceptacion_aviso = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.nombre_completo} ({self.user.email})"

    def save(self, *args, **kwargs):
        # Normaliza el teléfono
        if self.telefono:
            self.telefono = (
                str(self.telefono)
                .replace(' ', '')
                .replace('-', '')
                .replace('(', '')
                .replace(')', '')
                .replace('+', '')
            )
            if len(self.telefono) == 12 and self.telefono.startswith('52'):
                self.telefono = self.telefono[2:]
            elif len(self.telefono) == 13 and self.telefono.startswith('521'):
                self.telefono = self.telefono[3:]

        # Nombres en MAYÚSCULAS
        if self.nombre_completo:
            self.nombre_completo = ' '.join(self.nombre_completo.split()).upper()
        if self.empresa_nombre_manual:
            self.empresa_nombre_manual = ' '.join(self.empresa_nombre_manual.split()).upper()

        super().save(*args, **kwargs)

    @property
    def nombre_empresa_display(self):
        """Devuelve el nombre de la empresa, venga de FK o manual."""
        if self.empresa:
            return self.empresa.nombre
        return self.empresa_nombre_manual or '—'

    def asignar_folio_licencia(self, folio_sugerido=None):
        """Asigna folio_licencia al Ciudadano si aún no lo tiene."""
        if self.folio_licencia:
            return self.folio_licencia

        if folio_sugerido:
            numero = folio_sugerido.replace('AM-', '')
        else:
            total = Ciudadano.objects.filter(
                folio_licencia__isnull=False
            ).exclude(pk=self.pk).count()
            numero = str(total + 1).zfill(4)

        folio = numero
        sufijo = 0
        while Ciudadano.objects.filter(folio_licencia=folio).exclude(pk=self.pk).exists():
            sufijo += 1
            folio = f"{numero}-{sufijo}"

        self.folio_licencia = folio
        if not self.fecha_primera_emision:
            self.fecha_primera_emision = timezone.now()
        self.save(update_fields=['folio_licencia', 'fecha_primera_emision'])
        return folio

    def desactivar(self, motivo='', usuario=None):
        """Desactiva al ciudadano y libera su folio de licencia."""
        self.activo = False
        self.fecha_desactivacion = timezone.now()
        self.motivo_desactivacion = motivo or 'Desactivado por el administrador.'
        self.folio_licencia = None
        self.save(update_fields=[
            'activo', 'fecha_desactivacion', 'motivo_desactivacion',
            'folio_licencia',
        ])

    def reactivar(self, usuario=None):
        """Reactiva al ciudadano (sin folio, deberá asignársele uno)."""
        self.activo = True
        self.fecha_desactivacion = None
        self.motivo_desactivacion = ''
        self.save(update_fields=[
            'activo', 'fecha_desactivacion', 'motivo_desactivacion',
        ])

    @property
    def ultima_solicitud_emitida(self):
        """Devuelve la última solicitud con licencia emitida, o None."""
        return (
            self.solicitudes
            .filter(estado='licencia_emitida')
            .order_by('-fecha_emision_licencia')
            .first()
        )

    @property
    def licencia_vigente(self):
        """True si tiene licencia emitida y vigente (no vencida)."""
        if not self.folio_licencia:
            return False
        ultima = self.ultima_solicitud_emitida
        if not ultima or not ultima.fecha_vigencia_padron:
            return False
        return ultima.fecha_vigencia_padron >= timezone.now().date()

    @property
    def licencia_vencida(self):
        """True si tuvo licencia pero ya venció."""
        if not self.folio_licencia:
            return False
        ultima = self.ultima_solicitud_emitida
        if not ultima or not ultima.fecha_vigencia_padron:
            return False
        return ultima.fecha_vigencia_padron < timezone.now().date()


# ============================================================
# SOLICITUD / TRÁMITE
# ============================================================

class Solicitud(models.Model):
    ESTADOS_SOLICITUD = ESTADOS_SOLICITUD
    MOTIVOS_ACCION = MOTIVOS_ACCION
    PAGO_ESTADOS = PAGO_ESTADOS

    ciudadano = models.ForeignKey(
        Ciudadano, on_delete=models.CASCADE, related_name='solicitudes'
    )
    tipo_tramite = models.CharField(
        max_length=30, choices=TIPOS_TRAMITE, default='nuevo'
    )
    estado = models.CharField(
        max_length=30, choices=ESTADOS_SOLICITUD, default='borrador'
    )

    motivo_accion = models.CharField(
        max_length=30,
        choices=MOTIVOS_ACCION,
        blank=True,
        default='',
        verbose_name='Motivo de la acción requerida',
    )

    pago_estado = models.CharField(
        max_length=25,
        choices=PAGO_ESTADOS,
        default='sin_comprobante',
        verbose_name='Estado del pago',
    )

    folio = models.CharField(
        max_length=20, unique=True, null=True, blank=True, db_index=True
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)

    fecha_alta_padron = models.DateField(null=True, blank=True)
    fecha_vigencia_padron = models.DateField(null=True, blank=True)
    renovacion = models.BooleanField(default=False)

    numero_oficio = models.CharField(
        max_length=60, blank=True, default='', db_index=True
    )
    fecha_pase_caja = models.DateTimeField(null=True, blank=True)
    monto_pago = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True, default=None,
        verbose_name='Monto de pago',
    )
    uma_cantidad = models.DecimalField(
        max_digits=6, decimal_places=2, default=UMA_CANTIDAD_DEFAULT
    )
    uma_valor = models.DecimalField(
        max_digits=10, decimal_places=2, default=UMA_VALOR_DEFAULT
    )
    pase_caja_generado = models.BooleanField(default=False)

    comprobante_pago = models.FileField(
        upload_to='comprobantes_pago/',
        blank=True, null=True,
        verbose_name='Comprobante de pago',
    )
    referencia_pago = models.CharField(
        max_length=100, blank=True, default='',
        verbose_name='Referencia / folio bancario',
    )
    fecha_comprobante = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Fecha de subida del comprobante',
    )
    comentario_comprobante = models.TextField(
        blank=True, default='',
        verbose_name='Comentario del admin sobre el comprobante',
    )

    validador_pago = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pagos_validados',
        verbose_name='Validador del pago',
    )
    fecha_emision_licencia = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Fecha de emisión de esta licencia',
        help_text='La fecha en que se emitió ESTA solicitud '
                  '(cambia en cada revalidación).',
    )

    comentario_admin = models.TextField(
        blank=True, default='',
        verbose_name='Comentario del admin',
    )
    fecha_revision = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Última fecha de revisión',
    )

    def __str__(self):
        return f"Solicitud {self.folio or '#' + str(self.id)} - {self.ciudadano.nombre_completo}"

    # ---------- Propiedades de bloqueo y tipo ----------

    @property
    def esta_bloqueado(self):
        return self.estado in ESTADOS_BLOQUEADOS

    @property
    def es_persona_moral(self):
        dp = getattr(self, 'datos_personales', None)
        if dp and dp.regimen_fiscal == 'pm':
            return True
        return False

    @property
    def es_revalidacion(self):
        return self.tipo_tramite == 'revalidacion'

    @property
    def es_nuevo(self):
        return self.tipo_tramite == 'nuevo'

    @property
    def requiere_corregir_documentos(self):
        return (
            self.estado == 'requiere_accion'
            and self.motivo_accion == 'corregir_documentos'
        )

    @property
    def requiere_resubir_comprobante(self):
        return (
            self.estado == 'requiere_accion'
            and self.motivo_accion == 'resubir_comprobante'
        )

    @property
    def puede_editar(self):
        return self.estado in ('borrador', 'requiere_accion')

    @property
    def estado_display_completo(self):
        if self.estado == 'aprobada':
            return f"Aprobada · {self.get_pago_estado_display()}"
        if self.estado == 'requiere_accion' and self.motivo_accion:
            return f"Requiere acción · {self.get_motivo_accion_display()}"
        return self.get_estado_display()

    # ---------- Totales de cursos ----------

    @property
    def total_horas_curso(self):
        """Suma de todas las horas de cursos cargados en esta solicitud."""
        resultado = self.cursos_cargados.aggregate(t=Sum('horas'))
        return resultado['t'] or 0

    @property
    def cumple_minimo_horas(self):
        """True si tiene al menos 30 horas acumuladas."""
        return self.total_horas_curso >= HORAS_MINIMAS_CAPACITACION

    @property
    def total_documentos_curso(self):
        """Cantidad de documentos de curso cargados."""
        return self.cursos_cargados.count()

    # ---------- Generadores de folio ----------

    def generar_folio(self):
        from django.db.models.functions import Cast, Substr
        from django.db.models import IntegerField

        ultimo = (
            Solicitud.objects
            .filter(folio__isnull=False, folio__startswith='AM-')
            .annotate(num=Cast(Substr('folio', 4), output_field=IntegerField()))
            .order_by('-num')
            .first()
        )

        siguiente = (ultimo.num if ultimo and ultimo.num else 0) + 1
        folio = f"AM-{str(siguiente).zfill(4)}"

        while Solicitud.objects.filter(folio=folio).exists():
            siguiente += 1
            folio = f"AM-{str(siguiente).zfill(4)}"
        return folio

    def generar_numero_oficio(self):
        anio = timezone.now().year
        ultimo = (
            Solicitud.objects
            .filter(
                numero_oficio__isnull=False,
                numero_oficio__endswith=f'/{anio}',
            )
            .order_by('-numero_oficio')
            .first()
        )

        if ultimo and ultimo.numero_oficio:
            try:
                parte = ultimo.numero_oficio.split('/')[2]
                consecutivo = int(parte) + 1
            except (IndexError, ValueError):
                consecutivo = 1
        else:
            consecutivo = 1

        numero = f"TURISMO/DDC/{str(consecutivo).zfill(4)}/{anio}"
        while Solicitud.objects.filter(numero_oficio=numero).exists():
            consecutivo += 1
            numero = f"TURISMO/DDC/{str(consecutivo).zfill(4)}/{anio}"
        return numero

    # ---------- Acciones ----------

    def enviar(self):
        if not self.folio:
            self.folio = self.generar_folio()
        self.estado = 'en_revision'
        self.motivo_accion = ''
        self.fecha_envio = timezone.now()
        self.save()
        return self.folio

    # ---------- Propiedades de pasos ----------

    @property
    def paso1_completado(self):
        return hasattr(self, 'datos_personales') and self.datos_personales.completado

    @property
    def paso2_completado(self):
        return hasattr(self, 'domicilio_identificacion') and self.domicilio_identificacion.completado

    @property
    def paso3_completado(self):
        return hasattr(self, 'documentos_negocio') and self.documentos_negocio.completado

    @property
    def paso4_completado(self):
        return hasattr(self, 'cursos_capacitaciones') and self.cursos_capacitaciones.completado

    @property
    def pasos_completados(self):
        return sum([
            self.paso1_completado,
            self.paso2_completado,
            self.paso3_completado,
            self.paso4_completado,
        ])

    @property
    def porcentaje_avance(self):
        return int((self.pasos_completados / 4) * 100)

    @property
    def siguiente_paso(self):
        if not self.paso1_completado: return 1
        if not self.paso2_completado: return 2
        if not self.paso3_completado: return 3
        if not self.paso4_completado: return 4
        return 0

    # ---------- Cambio de estado ----------

    def cambiar_estado(self, nuevo_estado, usuario=None, comentario='',
                       motivo_accion='', pago_estado=''):
        estado_anterior = self.estado

        if estado_anterior == nuevo_estado and not comentario:
            return

        if nuevo_estado == 'requiere_accion':
            if motivo_accion == 'corregir_documentos':
                if estado_anterior in ('aprobada', 'requiere_accion'):
                    self.pase_caja_generado = False
                    self.numero_oficio = ''
                    self.fecha_pase_caja = None
                    self.monto_pago = None
                    self.comprobante_pago = None
                    self.fecha_comprobante = None
                    self.pago_estado = 'sin_comprobante'
                self.comentario_admin = comentario

            elif motivo_accion == 'resubir_comprobante':
                self.comentario_comprobante = comentario
                self.pago_estado = 'comprobante_rechazado'

            self.motivo_accion = motivo_accion or 'corregir_documentos'

        if nuevo_estado == 'aprobada' and estado_anterior != 'aprobada':
            if not self.numero_oficio:
                self.numero_oficio = self.generar_numero_oficio()
            self.fecha_pase_caja = timezone.now()
            self.monto_pago = MONTO_PAGO_DEFAULT
            self.pase_caja_generado = True
            self.motivo_accion = ''
            if not self.pago_estado or self.pago_estado == 'comprobante_rechazado':
                self.pago_estado = 'sin_comprobante'

        if nuevo_estado == 'licencia_emitida' and estado_anterior != 'licencia_emitida':
            self.ciudadano.asignar_folio_licencia(folio_sugerido=self.folio)
            self.fecha_emision_licencia = timezone.now()
            self.validador_pago = usuario

            from datetime import timedelta
            self.fecha_alta_padron = timezone.now().date()
            self.fecha_vigencia_padron = (timezone.now() + timedelta(days=365)).date()

            self.pago_estado = 'pago_validado'
            self.motivo_accion = ''

        if pago_estado:
            self.pago_estado = pago_estado

        self.estado = nuevo_estado
        self.fecha_revision = timezone.now()
        self.save()

        HistorialEstado.objects.create(
            solicitud=self,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            usuario=usuario,
            comentario=comentario,
        )


# ============================================================
# PASO 1: DATOS PERSONALES
# ============================================================

class DatosPersonales(models.Model):
    REGIMENES_FISCALES = [
        ('pfae', 'Persona física con actividad empresarial (PFAE)'),
        ('pm', 'Persona moral'),
    ]

    SEXOS = [
        ('H', 'Hombre'),
        ('M', 'Mujer'),
        ('X', 'Otro / Prefiero no decir'),
    ]

    solicitud = models.OneToOneField(
        Solicitud, on_delete=models.CASCADE, related_name='datos_personales'
    )

    regimen_fiscal = models.CharField(
        max_length=20, choices=REGIMENES_FISCALES, default='pfae'
    )
    sexo = models.CharField(max_length=1, choices=SEXOS, default='H')
    rfc = models.CharField(
        max_length=13,
        validators=[rfc_validator],
        verbose_name="RFC",
    )
    curp = models.CharField(
        max_length=18,
        blank=True,
        default='',
        verbose_name="CURP",
    )
    tipo_tramite = models.CharField(
        max_length=30, choices=TIPOS_TRAMITE, default='nuevo'
    )

    completado = models.BooleanField(default=False)
    fecha_completado = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Datos personales - {self.solicitud.ciudadano.nombre_completo}"

    def save(self, *args, **kwargs):
        if self.rfc:
            self.rfc = self.rfc.upper().strip()
        if self.curp:
            self.curp = self.curp.upper().strip()
        super().save(*args, **kwargs)


# ============================================================
# PASO 2: DOMICILIO E IDENTIFICACIÓN
# ============================================================

class DomicilioIdentificacion(models.Model):
    solicitud = models.OneToOneField(
        Solicitud, on_delete=models.CASCADE,
        related_name='domicilio_identificacion'
    )

    municipio = models.CharField(
        max_length=100,
        choices=MUNICIPIOS_TABASCO,
        blank=True,
        default='',
    )
    calle_numero_colonia_cp = models.TextField(
        verbose_name="Calle, Número, Colonia y Código Postal",
        blank=True,
    )

    comprobante_domicilio = models.FileField(
        upload_to='documentos/domicilio/',
        blank=True, null=True,
        verbose_name="Comprobante de domicilio actualizado (no mayor a 2 meses)"
    )
    identificacion_oficial = models.FileField(
        upload_to='documentos/identificacion/',
        blank=True, null=True,
        verbose_name="Copia de Identificación oficial vigente con fotografía (INE)"
    )
    foto_agente = models.ImageField(
        upload_to='documentos/fotos/',
        blank=True, null=True,
        verbose_name="Foto a color o blanco y negro digitalizada del agente inmobiliario"
    )

    completado = models.BooleanField(default=False)
    fecha_completado = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Domicilio - {self.solicitud.ciudadano.nombre_completo}"

    def save(self, *args, **kwargs):
        if self.calle_numero_colonia_cp:
            self.calle_numero_colonia_cp = ' '.join(self.calle_numero_colonia_cp.split()).upper()
        super().save(*args, **kwargs)


# ============================================================
# PASO 3: DOCUMENTOS LEGALES DEL NEGOCIO
# ============================================================

class DocumentosNegocio(models.Model):
    solicitud = models.OneToOneField(
        Solicitud, on_delete=models.CASCADE,
        related_name='documentos_negocio'
    )

    constancia_situacion_fiscal = models.FileField(
        upload_to='documentos/negocio/',
        blank=True, null=True,
        verbose_name="Constancia de situación fiscal actualizada"
    )
    constancia_profeco = models.FileField(
        upload_to='documentos/negocio/',
        blank=True, null=True,
        verbose_name="Constancia de registro ante PROFECO del Contrato de Adhesión"
    )
    carta_no_antecedentes = models.FileField(
        upload_to='documentos/negocio/',
        blank=True, null=True,
        verbose_name="Carta de no antecedentes penales por delitos patrimoniales"
    )
    carta_bajo_protesta = models.FileField(
        upload_to='documentos/negocio/',
        blank=True, null=True,
        verbose_name="Carta de Bajo Protesta de Decir Verdad (SEDEC)"
    )

    acta_constitutiva = models.FileField(
        upload_to='documentos/negocio/',
        blank=True, null=True,
        verbose_name="Copia del Acta Constitutiva de la Sociedad"
    )
    poder_notarial = models.FileField(
        upload_to='documentos/negocio/',
        blank=True, null=True,
        verbose_name="Poder notarial del representante legal"
    )
    logotipo_empresa = models.ImageField(
        upload_to='documentos/negocio/',
        blank=True, null=True,
        verbose_name="Logotipo de la empresa"
    )

    constancia_inscripcion_anterior = models.FileField(
        upload_to='documentos/negocio/',
        blank=True, null=True,
        verbose_name="Copia de la Constancia de Inscripción anterior (licencia previa)"
    )

    completado = models.BooleanField(default=False)
    fecha_completado = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Documentos negocio - {self.solicitud.ciudadano.nombre_completo}"


# ============================================================
# PASO 4: CURSOS (MÚLTIPLES) + CURSOS CAPACITACIONES
# ============================================================

class Curso(models.Model):
    """Un curso individual cargado por el ciudadano.

    Cada curso tiene su documento PDF y una cantidad de horas.
    La suma de todos los cursos del trámite debe ser >= 30 horas.
    """
    solicitud = models.ForeignKey(
        Solicitud,
        on_delete=models.CASCADE,
        related_name='cursos_cargados',
    )
    nombre = models.CharField(
        max_length=250,
        verbose_name='Nombre del curso',
    )
    horas = models.PositiveIntegerField(
        verbose_name='Horas',
        help_text='Cantidad de horas efectivas del curso.',
    )
    institucion = models.CharField(
        max_length=250,
        blank=True,
        default='',
        verbose_name='Institución que lo impartió',
    )
    fecha_curso = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha del curso',
    )
    documento = models.FileField(
        upload_to='documentos/cursos/',
        blank=True, null=True,
        verbose_name='Diploma o constancia (PDF)',
    )
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_curso', '-fecha_subida']
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'

    def __str__(self):
        return f"{self.nombre} ({self.horas}h)"


class CursosCapacitaciones(models.Model):
    """Contenedor de cursos del trámite + carta compromiso."""
    solicitud = models.OneToOneField(
        Solicitud, on_delete=models.CASCADE,
        related_name='cursos_capacitaciones'
    )

    carta_compromiso = models.FileField(
        upload_to='documentos/cursos/',
        blank=True, null=True,
        verbose_name="Carta de compromiso a cumplir los Programas de Capacitación y Actualización"
    )

    completado = models.BooleanField(default=False)
    fecha_completado = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Cursos - {self.solicitud.ciudadano.nombre_completo}"

    @property
    def total_horas(self):
        resultado = self.solicitud.cursos_cargados.aggregate(t=Sum('horas'))
        return resultado['t'] or 0


# ============================================================
# HISTORIAL DE ESTADOS
# ============================================================

class HistorialEstado(models.Model):
    ESTADOS = ESTADOS_SOLICITUD

    solicitud = models.ForeignKey(
        Solicitud, on_delete=models.CASCADE, related_name='historial'
    )
    estado_anterior = models.CharField(max_length=30, choices=ESTADOS, blank=True)
    estado_nuevo = models.CharField(max_length=30, choices=ESTADOS)
    comentario = models.TextField(blank=True)
    usuario = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Historial de estado'
        verbose_name_plural = 'Historial de estados'

    def __str__(self):
        return f"{self.solicitud.folio} → {self.get_estado_nuevo_display()}"


# ============================================================
# SIGNAL: crear Ciudadano al crear User
# ============================================================

@receiver(post_save, sender=User)
def crear_ciudadano(sender, instance, created, **kwargs):
    if created:
        Ciudadano.objects.get_or_create(user=instance)