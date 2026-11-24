from django.urls import path
from . import views

app_name = 'licencias'

urlpatterns = [
    path('iniciar/', views.iniciar_tramite, name='iniciar'),
]