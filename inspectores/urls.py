from django.urls import path
from . import views

app_name = 'inspectores'

urlpatterns = [
    path('', views.lista, name='lista'),
]