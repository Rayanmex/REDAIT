from django.urls import path
from . import views

app_name = 'padron'

urlpatterns = [
    path('', views.lista, name='lista'),
]