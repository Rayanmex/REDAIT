from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('licencias/', include('licencias.urls')),
    path('padron/', include('padron.urls')),          # ← Para padrón
    path('capacitaciones/', include('capacitaciones.urls')),
    path('quejas/', include('quejas.urls')),
    path('usuarios/', include('usuarios.urls')),
    # path('inspectores/', include('inspectores.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('noticias/', include('noticias.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)