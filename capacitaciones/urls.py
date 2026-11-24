from django.urls import path
from . import views

app_name = 'capacitaciones'

urlpatterns = [
    path('', views.lista, name='lista'),
]