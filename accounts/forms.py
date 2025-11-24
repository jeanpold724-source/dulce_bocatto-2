from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User

class RegistroForm(UserCreationForm):
    email = forms.EmailField(label='Correo electrónico')
    phone = forms.CharField(label='Teléfono', required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'password1', 'password2']

class LoginForm(AuthenticationForm):
    username = forms.EmailField(label='Correo electrónico')


from .models_db import Insumo

class InsumoForm(forms.ModelForm):
    class Meta:
        model = Insumo
        fields = ["nombre", "unidad_medida", "cantidad_disponible"]

# ---------- CU29 ----------
from django import forms
from .models_db import Calificacion

class CalificacionForm(forms.ModelForm):
    class Meta:
        model = Calificacion
        fields = ['puntaje', 'comentario']
        widgets = {
            'puntaje': forms.Select(choices=[(i, i) for i in range(1, 6)]),  # Opciones de 1 a 5 estrellas
            'comentario': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Deja tu comentario...'}),
        }


from django import forms
from .models_db import Descuento


class DescuentoForm(forms.ModelForm):
    class Meta:
        model = Descuento
        fields = ["nombre", "tipo", "valor", "activo"]
        labels = {
            "nombre": "Nombre de la promoción",
            "tipo": "Tipo de descuento",
            "valor": "Valor (monto o %)",
            "activo": "Activo",
        }
