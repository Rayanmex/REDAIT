CHATBOT = {
    'menu_principal': {
        'texto': '👋 ¡Hola! Soy el asistente virtual de REDAIT. ¿En qué puedo ayudarte?',
        'opciones': [
            {'texto': '📋 Requisitos para tramitar', 'destino': 'requisitos'},
            {'texto': '💳 Sobre el pago', 'destino': 'pago'},
            {'texto': '📄 Mis documentos', 'destino': 'documentos'},
            {'texto': '🏢 Sobre el padrón', 'destino': 'padron'},
            {'texto': '📞 Contactar a un asesor', 'destino': 'contacto'},
        ],
    },
    'requisitos': {
        'texto': '¿Qué necesitas saber sobre los requisitos?',
        'opciones': [
            {'texto': '¿Qué documentos necesito?', 'destino': 'req_docs'},
            {'texto': '¿Cuántas horas de cursos?', 'destino': 'req_horas'},
            {'texto': '¿Cuánto cuesta el trámite?', 'destino': 'req_costo'},
            {'texto': '⬅ Volver al menú', 'destino': 'menu_principal'},
        ],
    },
    'req_docs': {
        'texto': (
            '📄 <strong>Documentos requeridos</strong><br><br>'
            'Necesitas subir en el sistema:<br>'
            '• Comprobante de domicilio (no mayor a 2 meses)<br>'
            '• Identificación oficial vigente (INE)<br>'
            '• Foto del agente (color o blanco y negro)<br>'
            '• Constancia de situación fiscal<br>'
            '• Carta de no antecedentes penales<br>'
            '• Carta bajo protesta<br>'
            '• Constancia PROFECO (si aplica)<br>'
            '• Acta constitutiva y poder notarial (si es persona moral)'
        ),
        'opciones': [
            {'texto': '🚀 Iniciar mi trámite', 'url': '/usuarios/paso/1-datos/'},
            {'texto': '⬅ Volver', 'destino': 'requisitos'},
        ],
    },
    'req_horas': {
        'texto': (
            '🎓 <strong>Capacitación requerida</strong><br><br>'
            'La ley exige un mínimo de <strong>30 horas</strong> de cursos '
            'de capacitación inmobiliaria.<br><br>'
            'Puedes cargar varios cursos que sumen al menos 30 horas. '
            'Cada curso debe tener su constancia en PDF.'
        ),
        'opciones': [
            {'texto': '📚 Cargar mis cursos', 'url': '/usuarios/paso/4-cursos/'},
            {'texto': '⬅ Volver', 'destino': 'requisitos'},
        ],
    },
    'req_costo': {
        'texto': (
            '💰 <strong>Costo del trámite</strong><br><br>'
            'El pago corresponde a <strong>6 UMA</strong> '
            '(Unidades de Medida y Actualización).<br><br>'
            'Al aprobarse tu solicitud se genera un pase de pago con el monto exacto.'
        ),
        'opciones': [
            {'texto': '⬅ Volver', 'destino': 'requisitos'},
        ],
    },
    'pago': {
        'texto': '💳 ¿Qué necesitas saber sobre el pago?',
        'opciones': [
            {'texto': '¿Cómo pago mi trámite?', 'destino': 'pago_como'},
            {'texto': '¿Cómo subo mi comprobante?', 'destino': 'pago_comprobante'},
            {'texto': 'Mi comprobante fue rechazado', 'destino': 'pago_rechazado'},
            {'texto': '⬅ Volver al menú', 'destino': 'menu_principal'},
        ],
    },
    'pago_como': {
        'texto': (
            '🏦 <strong>¿Cómo pagar?</strong><br><br>'
            '1. Cuando tu solicitud sea aprobada, podrás descargar tu '
            '<strong>pase de caja</strong> desde tu panel.<br>'
            '2. Con ese pase, paga en cualquier sucursal bancaria.<br>'
            '3. Sube tu comprobante escaneado en el sistema.<br>'
            '4. Un validador revisará tu pago en 24-48 hrs.'
        ),
        'opciones': [
            {'texto': '💳 Ir a mi panel', 'url': '/usuarios/panel/'},
            {'texto': '⬅ Volver', 'destino': 'pago'},
        ],
    },
    'pago_comprobante': {
        'texto': (
            '📤 <strong>Subir comprobante</strong><br><br>'
            'Ve a tu panel, busca la sección de pago y haz clic en '
            '"Subir comprobante".<br><br>'
            'Formatos aceptados: PDF, JPG o PNG. Máximo 5 MB.<br>'
            'No olvides escribir la referencia bancaria.'
        ),
        'opciones': [
            {'texto': '📤 Subir comprobante', 'url': '/usuarios/subir-comprobante/'},
            {'texto': '⬅ Volver', 'destino': 'pago'},
        ],
    },
    'pago_rechazado': {
        'texto': (
            '⚠️ <strong>Comprobante rechazado</strong><br><br>'
            'Si tu comprobante fue rechazado, revisa el motivo en tu panel. '
            'Puedes volver a subir el comprobante corregido las veces que necesites.'
        ),
        'opciones': [
            {'texto': '🔄 Volver a subir', 'url': '/usuarios/subir-comprobante/'},
            {'texto': '⬅ Volver', 'destino': 'pago'},
        ],
    },
    'documentos': {
        'texto': '📄 ¿Qué necesitas sobre tus documentos?',
        'opciones': [
            {'texto': '¿Cómo corrijo un documento?', 'destino': 'docs_corregir'},
            {'texto': 'Mi solicitud requiere correcciones', 'destino': 'docs_correcciones'},
            {'texto': '⬅ Volver al menú', 'destino': 'menu_principal'},
        ],
    },
    'docs_corregir': {
        'texto': (
            '✏️ <strong>Corregir documentos</strong><br><br>'
            'Si un revisor te pidió correcciones, verás un aviso amarillo '
            'en tu panel con el motivo.<br><br>'
            'Ve al paso correspondiente y vuelve a subir el documento.'
        ),
        'opciones': [
            {'texto': '📝 Ir a mis pasos', 'url': '/usuarios/panel/'},
            {'texto': '⬅ Volver', 'destino': 'documentos'},
        ],
    },
    'docs_correcciones': {
        'texto': (
            '🔔 <strong>Correcciones solicitadas</strong><br><br>'
            'Cuando el admin solicita correcciones, tu panel muestra un '
            'aviso con el motivo y un botón para volver a los pasos.'
        ),
        'opciones': [
            {'texto': '📝 Ver mis correcciones', 'url': '/usuarios/panel/'},
            {'texto': '⬅ Volver', 'destino': 'documentos'},
        ],
    },
    'padron': {
        'texto': '🏢 ¿Qué necesitas saber sobre el padrón?',
        'opciones': [
            {'texto': '¿Cómo verifico una licencia?', 'destino': 'padron_verificar'},
            {'texto': '¿Qué es el padrón?', 'destino': 'padron_que'},
            {'texto': '⬅ Volver al menú', 'destino': 'menu_principal'},
        ],
    },
    'padron_verificar': {
        'texto': (
            '🔍 <strong>Verificar una licencia</strong><br><br>'
            'En el padrón público puedes buscar por nombre, empresa o folio.<br>'
            'Si tienes el QR de una licencia, escanéalo para verificar '
            'automáticamente sus datos.'
        ),
        'opciones': [
            {'texto': '🔍 Ver padrón', 'url': '/padron/'},
            {'texto': '⬅ Volver', 'destino': 'padron'},
        ],
    },
    'padron_que': {
        'texto': (
            '📋 <strong>¿Qué es el padrón?</strong><br><br>'
            'El Padrón Oficial de Operadores Inmobiliarios es la lista '
            'de personas y empresas autorizadas por la Secretaría de Turismo '
            'para operar en Tabasco.<br><br>'
            'Se actualiza automáticamente cuando se emite o renueva una licencia.'
        ),
        'opciones': [
            {'texto': '🔍 Ver padrón', 'url': '/padron/'},
            {'texto': '⬅ Volver', 'destino': 'padron'},
        ],
    },
    'contacto': {
        'texto': (
            '📞 <strong>Contacto</strong><br><br>'
            'Si necesitas hablar con un asesor:<br><br>'
            '📞 Teléfono: <strong>(993) 310-9750</strong><br>'
            '✉️ Email: <strong>mirnarosario@tabasco.gob.mx</strong><br>'
            '🕐 Horario: Lunes a viernes 9:00 - 15:00'
        ),
        'opciones': [
            {'texto': '⬅ Volver al menú', 'destino': 'menu_principal'},
        ],
    },
}