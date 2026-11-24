from django.contrib import admin
from .models import Categoria, Noticia, ImagenNoticia


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'slug', 'orden', 'activa']
    list_editable = ['orden', 'activa']
    prepopulated_fields = {'slug': ('nombre',)}
    search_fields = ['nombre']


class ImagenNoticiaInline(admin.TabularInline):
    model = ImagenNoticia
    extra = 1
    fields = ['imagen', 'descripcion', 'orden']


@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'categoria', 'estado', 'destacada', 'fecha_publicacion', 'vistas']
    list_filter = ['estado', 'destacada', 'categoria', 'fecha_publicacion']
    search_fields = ['titulo', 'extracto', 'contenido']
    prepopulated_fields = {'slug': ('titulo',)}
    date_hierarchy = 'fecha_publicacion'
    readonly_fields = ['vistas', 'fecha_creacion', 'fecha_actualizacion']
    inlines = [ImagenNoticiaInline]

    fieldsets = (
        ('Contenido', {
            'fields': ('titulo', 'slug', 'extracto', 'contenido')
        }),
        ('Imagen de portada', {
            'fields': ('imagen_portada', 'imagen_alt')
        }),
        ('Clasificación', {
            'fields': ('categoria', 'autor', 'destacada')
        }),
        ('Estado y fechas', {
            'fields': ('estado', 'fecha_publicacion', 'fecha_expiracion')
        }),
        ('Estadísticas', {
            'fields': ('vistas', 'fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )