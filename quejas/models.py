from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator


telefono_validator = RegexValidator(
    regex=r'^\d{10}$',
    message='El teléfono debe tener 10 dígitos (solo números).'
)


class Queja(models.Model):
    """Queja, sugerencia o denuncia enviada por un ciudadano."""

    TIPOS = [
        ('queja', 'Queja'),
        ('sugerencia', 'Sugerencia'),
        ('denuncia', 'Denuncia'),
        ('otro', 'Otro'),
    ]

    ESTADOS = [
        ('nueva', 'Nueva'),
        ('en_revision', 'En revisión'),
        ('atendida', 'Atendida'),
        ('cerrada', 'Cerrada'),
        ('archivada', 'Archivada'),
    ]

    # ===== Datos del solicitante =====
    nombre_completo = models.CharField(max_length=200)
    email = models.EmailField()
    telefono = models.CharField(
        max_length=10,
        blank=True,
        default='',
        validators=[telefono_validator],
    )

    # ===== Contenido =====
    tipo = models.CharField(max_length=20, choices=TIPOS, default='queja')
    asunto = models.CharField(max_length=200)
    mensaje = models.TextField(
        help_text='Describe tu queja, sugerencia o denuncia con detalle.'
    )

    # ===== Adjunto opcional =====
    archivo_adjunto = models.FileField(
        upload_to='quejas/adjuntos/',
        blank=True, null=True,
        help_text='Puedes adjuntar una imagen o PDF (opcional).',
    )

    # ===== Control interno =====
    folio = models.CharField(
        max_length=20, unique=True, null=True, blank=True, db_index=True
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default='nueva')
    comentario_interno = models.TextField(
        blank=True, default='',
        help_text='Notas internas del personal (no visibles al ciudadano).',
    )
    atendida_por = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='quejas_atendidas',
    )

    # ===== Fechas =====
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_atencion = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Queja / Sugerencia'
        verbose_name_plural = 'Quejas y Sugerencias'

    def __str__(self):
        return f"{self.folio or '#' + str(self.id)} - {self.asunto}"

    def save(self, *args, **kwargs):
        # Normaliza nombre
        if self.nombre_completo:
            self.nombre_completo = ' '.join(self.nombre_completo.split()).upper()
        if self.email:
            self.email = self.email.lower().strip()
        super().save(*args, **kwargs)

    # ---------- Generadores ----------

    def generar_folio(self):
        """Genera folio Q-YYYY-XXXX (ej: Q-2026-0001). Reinicia cada año."""
        anio = timezone.now().year
        prefijo = f"Q-{anio}-"

        ultimo = (
            Queja.objects
            .filter(folio__startswith=prefijo)
            .order_by('-folio')
            .first()
        )

        if ultimo and ultimo.folio:
            try:
                consecutivo = int(ultimo.folio.split('-')[-1]) + 1
            except (ValueError, IndexError):
                consecutivo = 1
        else:
            consecutivo = 1

        folio = f"{prefijo}{str(consecutivo).zfill(4)}"
        while Queja.objects.filter(folio=folio).exists():
            consecutivo += 1
            folio = f"{prefijo}{str(consecutivo).zfill(4)}"
        return folio

    def enviar(self):
        """Asigna folio y marca como nueva."""
        if not self.folio:
            self.folio = self.generar_folio()
        self.estado = 'nueva'
        self.save()
        return self.folio