from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from .models import Ciudadano
from django import forms
from django.core.exceptions import ValidationError
from .models import Solicitud



NOMBRES_BASURA = {
    'prueba', 'pruebas', 'test', 'testing', 'asdf', 'asdfasdf',
    'qwerty', 'xxx', 'aaaa', 'aaaaa', 'aaa', '123', '1234',
    'pruebakk', 'prueba2', 'prueba1', 'demo', 'ejemplo',
    'admin', 'administrador', 'usuario', 'user', 'anonimo',
}


class RegistroCiudadanoForm(UserCreationForm):
    nombre_completo = forms.CharField(
        max_length=200,
        min_length=3,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej. Juan Pérez López',
            'pattern': r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü\s\.\-\']+",
            'title': 'Solo letras, espacios, puntos y guiones',
            'autocomplete': 'name',
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Correo electrónico',
            'autocomplete': 'email',
        })
    )
    telefono = forms.CharField(
        max_length=10,
        min_length=10,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '10 dígitos, ej. 9931234567',
            'inputmode': 'numeric',
            'pattern': r'\d{10}',
            'maxlength': '10',
            'title': 'Debe contener exactamente 10 dígitos',
            'autocomplete': 'tel',
            'oninput': "this.value=this.value.replace(/[^0-9]/g,'').slice(0,10)",
        })
    )
    password1 = forms.CharField(
        label="Contraseña",
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña',
            'autocomplete': 'new-password',
        })
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmar contraseña',
            'autocomplete': 'new-password',
        })
    )
    acepto_aviso = forms.BooleanField(
        required=True,
        label="Acepto el Aviso de Privacidad",
        error_messages={'required': 'Debes aceptar el Aviso de Privacidad para continuar.'}
    )

    class Meta:
        model = User
        fields = ('nombre_completo', 'email', 'telefono', 'password1', 'password2', 'acepto_aviso')

    # --------------------------------------------------------
    # VALIDACIÓN: EMAIL
    # --------------------------------------------------------
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(username=email).exists() or User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta registrada con este correo.")
        return email

    # --------------------------------------------------------
    # VALIDACIÓN: NOMBRE COMPLETO
    # --------------------------------------------------------
    def clean_nombre_completo(self):
        nombre = self.cleaned_data.get('nombre_completo', '').strip()
        # Colapsa espacios múltiples
        nombre = ' '.join(nombre.split())

        if len(nombre) < 3:
            raise forms.ValidationError('El nombre es demasiado corto.')

        # Verifica que solo tenga letras, espacios, puntos y guiones
        import re
        if not re.match(r"^[A-Za-zÁÉÍÓÚÑÜáéíóúñü\s\.\-\']+$", nombre):
            raise forms.ValidationError('El nombre solo puede contener letras, espacios, puntos y guiones.')

        # Rechaza nombres basura
        if nombre.lower() in NOMBRES_BASURA:
            raise forms.ValidationError('Ingresa un nombre real.')

        # Debe tener al menos 2 palabras (nombre y apellido)
        if len(nombre.split()) < 2:
            raise forms.ValidationError('Ingresa tu nombre y apellido.')

        # Rechaza nombres con la misma letra repetida (ej. "aaaa bbbb")
        palabras = nombre.split()
        for palabra in palabras:
            if len(palabra) >= 3 and len(set(palabra.lower())) == 1:
                raise forms.ValidationError('El nombre contiene caracteres repetidos no válidos.')

        return nombre

    # --------------------------------------------------------
    # VALIDACIÓN: TELÉFONO
    # --------------------------------------------------------
    def clean_telefono(self):
        tel = self.cleaned_data.get('telefono', '')
        # Solo dígitos
        tel = ''.join(filter(str.isdigit, str(tel)))

        if len(tel) != 10:
            raise forms.ValidationError('El teléfono debe tener exactamente 10 dígitos.')

        # Rechaza números todos iguales (1111111111, 0000000000, etc.)
        if len(set(tel)) == 1:
            raise forms.ValidationError('El teléfono no es válido.')

        # Rechaza secuencias obvias (1234567890, 0123456789)
        secuencias = ['0123456789', '1234567890', '9876543210']
        if tel in secuencias:
            raise forms.ValidationError('El teléfono no es válido.')

        return tel

    # --------------------------------------------------------
    # VALIDACIÓN: ACEPTO AVISO
    # --------------------------------------------------------
    def clean_acepto_aviso(self):
        acepto = self.cleaned_data.get('acepto_aviso')
        if not acepto:
            raise forms.ValidationError('Debes aceptar el Aviso de Privacidad para continuar.')
        return acepto

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['nombre_completo']

        if commit:
            user.save()
            # El signal post_save ya crea Ciudadano y Solicitud,
            # pero por seguridad usamos get_or_create
            ciudadano, _ = Ciudadano.objects.get_or_create(user=user)
            ciudadano.nombre_completo = self.cleaned_data['nombre_completo']
            ciudadano.telefono = self.cleaned_data['telefono']
            ciudadano.acepto_aviso = self.cleaned_data['acepto_aviso']
            ciudadano.fecha_aceptacion_aviso = timezone.now()
            ciudadano.save()

        return user  # ← CLAVE: devolver el User, no el Ciudadano




class ComprobantePagoForm(forms.ModelForm):
    """Formulario para que el ciudadano suba su comprobante de pago."""

    class Meta:
        model = Solicitud
        fields = ['comprobante_pago']
        widgets = {
            'comprobante_pago': forms.ClearableFileInput(attrs={
                'accept': '.pdf,.jpg,.jpeg,.png',
                'class': 'input-file-comprobante',
            })
        }

    def clean_comprobante_pago(self):
        archivo = self.cleaned_data.get('comprobante_pago')

        if not archivo:
            raise ValidationError("Debes adjuntar tu comprobante de pago.")

        # Tamaño máximo: 5 MB
        if archivo.size > 5 * 1024 * 1024:
            raise ValidationError("El archivo no puede pesar más de 5 MB.")

        # Extensiones permitidas
        nombre = archivo.name.lower()
        permitidos = ('.pdf', '.jpg', '.jpeg', '.png')
        if not nombre.endswith(permitidos):
            raise ValidationError(
                "Solo se permiten archivos PDF, JPG o PNG."
            )

        return archivo