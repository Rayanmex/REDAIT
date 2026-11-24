from django import forms
from .models import Noticia, Categoria, ImagenNoticia


# ============================================================
# WIDGET PERSONALIZADO PARA MÚLTIPLES ARCHIVOS
# ============================================================

class MultipleFileInput(forms.Widget):
    """Widget que permite subir varios archivos a la vez.

    Django 6 bloquea 'multiple' en FileInput/ClearableFileInput,
    así que creamos uno desde cero.
    """
    input_type = 'file'
    needs_multipart_form = True

    def __init__(self, attrs=None):
        default_attrs = {'multiple': True}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def value_from_datadict(self, data, files, name):
        """Devuelve una lista de archivos."""
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        return files.get(name)

    def value_omitted_from_data(self, data, files, name):
        return False

    def format_value(self, value):
        """No renderizar valor (es un input file)."""
        return None


class MultipleFileField(forms.FileField):
    """FileField que acepta múltiples archivos."""
    widget = MultipleFileInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput)
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        """Valida una lista de archivos."""
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(d, initial) for d in data]
        elif data not in self.empty_values:
            return [single_clean(data, initial)]
        return []


# ============================================================
# FORMULARIO DE NOTICIA
# ============================================================

class NoticiaForm(forms.ModelForm):
    # Campo extra para subir varias imágenes a la vez
    imagenes_galeria = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
        }),
        label='Imágenes adicionales (galería)',
        help_text='Puedes seleccionar varias imágenes a la vez (Ctrl+clic o Cmd+clic).',
    )

    class Meta:
        model = Noticia
        fields = [
            'titulo', 'extracto', 'contenido',
            'imagen_portada', 'imagen_alt',
            'categoria', 'estado', 'destacada',
            'fecha_publicacion', 'fecha_expiracion',
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Título de la noticia',
            }),
            'extracto': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'maxlength': 400,
                'placeholder': 'Resumen corto para el listado...',
            }),
            'contenido': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 15,
            }),
            'imagen_portada': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'imagen_alt': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción de la imagen',
            }),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'destacada': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'fecha_publicacion': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }),
            'fecha_expiracion': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }),
        }
        labels = {
            'titulo': 'Título',
            'extracto': 'Extracto',
            'contenido': 'Contenido',
            'imagen_portada': 'Imagen de portada',
            'imagen_alt': 'Texto alternativo',
            'categoria': 'Categoría',
            'estado': 'Estado',
            'destacada': 'Destacar en el home',
            'fecha_publicacion': 'Fecha de publicación',
            'fecha_expiracion': 'Fecha de expiración',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_expiracion'].required = False
        self.fields['imagen_portada'].required = False
        self.fields['fecha_publicacion'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['fecha_expiracion'].input_formats = ['%Y-%m-%dT%H:%M']

        # Categorías activas + opción vacía
        self.fields['categoria'].queryset = (
            Categoria.objects.filter(activa=True).order_by('orden', 'nombre')
        )
        self.fields['categoria'].empty_label = '— Sin categoría —'


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'color', 'orden', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
            }),
            'orden': forms.NumberInput(attrs={'class': 'form-control'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }