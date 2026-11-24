from django.urls import path
from . import views, views_admin

app_name = 'usuarios'

urlpatterns = [
    # ============================================================
    # REGISTRO Y PANEL
    # ============================================================
    path('registro/', views.registro_ciudadano, name='registro_ciudadano'),
    path('panel/', views.panel, name='panel'),

    # ============================================================
    # PASOS DEL REGISTRO (ciudadano)
    # ============================================================
    path('paso/1-datos/', views.paso1_datos, name='paso1_datos'),
    path('paso/2-domicilio/', views.paso2_domicilio, name='paso2_domicilio'),
    path('paso/3-documentos/', views.paso3_documentos, name='paso3_documentos'),
    path('paso/4-cursos/', views.paso4_cursos, name='paso4_cursos'),

    # ============================================================
    # SOLICITUD (resumen, envío, confirmación, estado)
    # ============================================================
    path('solicitud/resumen/', views.resumen_solicitud, name='resumen_solicitud'),
    path('solicitud/enviar/', views.enviar_solicitud, name='enviar_solicitud'),
    path('solicitud/confirmacion/', views.confirmacion_solicitud, name='confirmacion_solicitud'),
    path('mi-solicitud/', views.mi_solicitud, name='mi_solicitud'),

    # ============================================================
    # FLUJO DE PAGO Y LICENCIA (ciudadano)
    # ============================================================
    path('pase-caja/', views.descargar_pase_caja, name='descargar_pase_caja'),
    path('subir-comprobante/', views.subir_comprobante_pago, name='subir_comprobante_pago'),
    path('descargar-licencia/', views.descargar_licencia, name='descargar_licencia'),

    # ============================================================
    # VERIFICACIÓN PÚBLICA (destino de los QR)
    # ============================================================
    path('verificar/<str:folio>/', views.verificar_pase_caja, name='verificar_pase_caja'),
    path('verificar-licencia/<str:folio>/', views.verificar_licencia, name='verificar_licencia'),

    # ============================================================
    # AVISO DE PRIVACIDAD (público)
    # ============================================================
    path('aviso-privacidad/', views.aviso_privacidad, name='aviso_privacidad'),

    # ============================================================
    # ADMIN PANEL
    # ============================================================
    path('admin-panel/', views_admin.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/solicitudes/', views_admin.admin_lista_solicitudes, name='admin_lista_solicitudes'),
    path('admin-panel/solicitudes/exportar/', views_admin.admin_exportar_excel, name='admin_exportar_excel'),

    path(
        'admin-panel/solicitudes/<int:solicitud_id>/',
        views_admin.admin_detalle_solicitud,
        name='admin_detalle_solicitud',
    ),
    path(
        'admin-panel/solicitudes/<int:solicitud_id>/pase-caja/',
        views_admin.admin_descargar_pase_caja,
        name='admin_descargar_pase_caja',
    ),
    path(
        'admin-panel/solicitudes/<int:solicitud_id>/licencia/',
        views_admin.admin_descargar_licencia,
        name='admin_descargar_licencia',
    ),
    path(
        'admin-panel/solicitudes/<int:solicitud_id>/editar/',
        views_admin.admin_editar_solicitud,
        name='admin_editar_solicitud',
    ),

    # Conflicto de folio (nuevo)
    path(
        'admin-panel/conflicto-folio/',
        views_admin.admin_conflicto_folio,
        name='admin_conflicto_folio',
    ),
    path(
        'admin-panel/conflicto-folio/resolver/',
        views_admin.admin_conflicto_folio_resolver,
        name='admin_conflicto_folio_resolver',
    ),
]