from django.contrib import admin
from .models import Queja


@admin.register(Queja)
class QuejaAdmin(admin.ModelAdmin):
    list_display = ('folio', 'tipo', 'nombre_completo', 'email', 'estado', 'fecha_creacion')
    list_filter = ('tipo', 'estado', 'fecha_creacion')
    search_fields = ('folio', 'nombre_completo', 'email', 'asunto', 'mensaje')
    readonly_fields = ('folio', 'fecha_creacion', 'fecha_actualizacion')
    ordering = ('-fecha_creacion',)

    fieldsets = (
        ('Datos del solicitante', {
            'fields': ('nombre_completo', 'email', 'telefono')
        }),
        ('Contenido', {
            'fields': ('tipo', 'asunto', 'mensaje', 'archivo_adjunto')
        }),
        ('Control interno', {
            'fields': ('folio', 'estado', 'comentario_interno', 'atendida_por', 'fecha_atencion')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )