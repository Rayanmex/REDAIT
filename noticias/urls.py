from django.urls import path
from . import views

app_name = 'noticias'

urlpatterns = [
    # Público
    path('', views.lista_noticias, name='lista'),
    path('<slug:slug>/', views.detalle_noticia, name='detalle'),

    # Admin - Lista y CRUD
    path('admin-panel/noticias/', views.admin_lista, name='admin_lista'),
    path('admin-panel/noticias/crear/', views.admin_crear, name='admin_crear'),
    path('admin-panel/noticias/<int:noticia_id>/editar/', views.admin_editar, name='admin_editar'),
    path('admin-panel/noticias/<int:noticia_id>/eliminar/', views.admin_eliminar, name='admin_eliminar'),
    path('admin-panel/noticias/<int:noticia_id>/toggle-destacada/', views.admin_toggle_destacada, name='admin_toggle_destacada'),

    # Admin - Categorías
    path('admin-panel/noticias/categorias/', views.admin_categorias, name='admin_categorias'),
    path('admin-panel/noticias/categorias/<int:categoria_id>/eliminar/', views.admin_categoria_eliminar, name='admin_categoria_eliminar'),

    # Admin - Imágenes de galería
    path('admin-panel/noticias/imagenes/<int:imagen_id>/eliminar/', views.admin_eliminar_imagen, name='admin_eliminar_imagen'),
]