from django.urls import path
from . import views

app_name = 'quejas'

urlpatterns = [
    # Público
    path('', views.enviar_queja, name='enviar'),
    path('confirmacion/<str:folio>/', views.confirmacion, name='confirmacion'),

    # Admin
    path('admin/', views.admin_lista, name='admin_lista'),
    path('admin/<int:queja_id>/', views.admin_detalle, name='admin_detalle'),
]