from django import forms
from .models import Queja


class QuejaForm(forms.ModelForm):
    """Formulario público para enviar quejas, sugerencias o denuncias."""

    class Meta:
        model = Queja
        fields = [
            'tipo', 'nombre_completo', 'email', 'telefono',
            'asunto', 'mensaje', 'archivo_adjunto',
        ]
        widgets = {
            'tipo': forms.Select(attrs={
                'class': 'form-control',
                'style': 'width: 100%; padding: 0.8rem 1rem; border: 2px solid #e5e7eb; border-radius: 12px; font-size: 1rem;',
            }),
            'nombre_completo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tu nombre completo',
                'style': 'width: 100%; padding: 0.8rem 1rem; border: 2px solid #e5e7eb; border-radius: 12px; font-size: 1rem;',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'tu@correo.com',
                'style': 'width: 100%; padding: 0.8rem 1rem; border: 2px solid #e5e7eb; border-radius: 12px; font-size: 1rem;',
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '10 dígitos (opcional)',
                'maxlength': '10',
                'style': 'width: 100%; padding: 0.8rem 1rem; border: 2px solid #e5e7eb; border-radius: 12px; font-size: 1rem;',
            }),
            'asunto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Resumen breve de tu mensaje',
                'style': 'width: 100%; padding: 0.8rem 1rem; border: 2px solid #e5e7eb; border-radius: 12px; font-size: 1rem;',
            }),
            'mensaje': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Describe con detalle tu queja, sugerencia o denuncia...',
                'rows': 6,
                'style': 'width: 100%; padding: 0.8rem 1rem; border: 2px solid #e5e7eb; border-radius: 12px; font-size: 1rem; font-family: inherit; resize: vertical;',
            }),
            'archivo_adjunto': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png',
                'style': 'width: 100%; padding: 0.6rem; border: 2px dashed #e5e7eb; border-radius: 12px; font-size: 0.9rem;',
            }),
        }
        labels = {
            'tipo': 'Tipo de mensaje',
            'nombre_completo': 'Nombre completo',
            'email': 'Correo electrónico',
            'telefono': 'Teléfono (opcional)',
            'asunto': 'Asunto',
            'mensaje': 'Mensaje',
            'archivo_adjunto': 'Adjuntar archivo (opcional)',
        }
        help_texts = {
            'archivo_adjunto': 'Formatos permitidos: PDF, JPG, PNG. Tamaño máximo: 5 MB.',
        }

    def clean_archivo_adjunto(self):
        archivo = self.cleaned_data.get('archivo_adjunto')
        if archivo:
            if archivo.size > 5 * 1024 * 1024:
                raise forms.ValidationError('El archivo no puede pesar más de 5 MB.')
            if not archivo.name.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                raise forms.ValidationError('Formato no válido. Usa PDF, JPG o PNG.')
        return archivo