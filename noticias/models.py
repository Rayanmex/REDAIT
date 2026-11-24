from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify


# ============================================================
# CATEGORÍA
# ============================================================

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, max_length=120, blank=True)
    color = models.CharField(
        max_length=20,
        default='#991547',
        help_text='Color hexadecimal para la etiqueta (ej. #991547)',
    )
    orden = models.PositiveIntegerField(
        default=0,
        help_text='Menor número = aparece primero',
    )
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)


# ============================================================
# NOTICIA
# ============================================================

class Noticia(models.Model):
    ESTADOS = [
        ('borrador', 'Borrador'),
        ('publicada', 'Publicada'),
        ('archivada', 'Archivada'),
    ]

    # ----- Contenido -----
    titulo = models.CharField(max_length=250)
    slug = models.SlugField(unique=True, max_length=260, blank=True)
    extracto = models.TextField(
        max_length=400,
        help_text='Resumen corto que aparece en el listado (máx. 400 caracteres).',
    )
    contenido = models.TextField(
        help_text='Contenido completo de la noticia (acepta HTML).',
    )

    # ----- Imagen de portada -----
    imagen_portada = models.ImageField(
        upload_to='noticias/portadas/',
        blank=True, null=True,
        help_text='Imagen destacada (1200x630 recomendado)',
    )
    imagen_alt = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text='Texto alternativo para accesibilidad',
    )

    # ----- Clasificación -----
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='noticias',
    )
    autor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='noticias_publicadas',
    )

    # ----- Estado y visibilidad -----
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='borrador',
        db_index=True,
    )
    destacada = models.BooleanField(
        default=False,
        help_text='Aparece en el carrusel del home',
    )

    # ----- Fechas -----
    fecha_publicacion = models.DateTimeField(
        default=timezone.now,
        help_text='Se publica en esta fecha (permite programar)',
    )
    fecha_expiracion = models.DateTimeField(
        null=True, blank=True,
        help_text='Opcional. Después de esta fecha se deja de mostrar.',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    # ----- Estadísticas -----
    vistas = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-destacada', '-fecha_publicacion']
        verbose_name = 'Noticia'
        verbose_name_plural = 'Noticias'
        indexes = [
            models.Index(fields=['estado', '-fecha_publicacion']),
            models.Index(fields=['destacada', 'estado']),
        ]

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        # Slug único automático
        if not self.slug:
            base = slugify(self.titulo)[:240]
            slug = base
            n = 1
            while Noticia.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base}-{n}"
            self.slug = slug
        super().save(*args, **kwargs)

    # ----- Propiedades -----

    @property
    def esta_publicada(self):
        """True si está publicada y no ha expirado."""
        if self.estado != 'publicada':
            return False
        ahora = timezone.now()
        if self.fecha_publicacion > ahora:
            return False
        if self.fecha_expiracion and self.fecha_expiracion < ahora:
            return False
        return True

    @property
    def esta_programada(self):
        """True si está publicada pero aún no llega su fecha."""
        return (
            self.estado == 'publicada'
            and self.fecha_publicacion > timezone.now()
        )

    @property
    def esta_expirada(self):
        """True si ya pasó su fecha de expiración."""
        return (
            self.fecha_expiracion
            and self.fecha_expiracion < timezone.now()
        )

    def incrementar_vista(self):
        """Incrementa el contador de vistas sin disparar save()."""
        Noticia.objects.filter(pk=self.pk).update(vistas=models.F('vistas') + 1)


# ============================================================
# IMAGEN DE GALERÍA
# ============================================================

class ImagenNoticia(models.Model):
    """Imágenes adicionales para una noticia (galería)."""
    noticia = models.ForeignKey(
        Noticia,
        on_delete=models.CASCADE,
        related_name='imagenes_galeria',
    )
    imagen = models.ImageField(
        upload_to='noticias/galeria/',
        help_text='Imagen adicional para la noticia',
    )
    descripcion = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text='Descripción corta de la imagen (opcional)',
    )
    orden = models.PositiveIntegerField(
        default=0,
        help_text='Orden de la imagen en la galería',
    )
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['orden', 'id']
        verbose_name = 'Imagen de galería'
        verbose_name_plural = 'Imágenes de galería'

    def __str__(self):
        return f"Imagen de {self.noticia.titulo[:40]}"