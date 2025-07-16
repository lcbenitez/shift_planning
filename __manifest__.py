{
    'name': 'Shift Planning',
    'version': '1.1.0',
    'category': 'Human Resources',
    'summary': 'Planificación avanzada de turnos con asignación automática e inteligente',
    'description': """
        Módulo Avanzado para la Gestión de Turnos Laborales
        =================================================
        
        Este módulo permite una gestión completa de turnos laborales con funcionalidades avanzadas:
        
        **Funcionalidades Principales:**
        * Definir roles de trabajo con habilidades requeridas
        * Programar turnos esperados por sucursal, fecha y rol
        * Asignar empleados a turnos específicos manualmente o automáticamente
        * Seguimiento completo de asistencia y estados
        * Sistema de notificaciones por email
        * Reportes detallados de cumplimiento
        
        **Nuevas Funcionalidades Avanzadas:**
        * 🤖 Asignación automática inteligente basada en habilidades y preferencias
        * 📊 Dashboard ejecutivo con métricas y KPIs en tiempo real
        * ⚙️ Configuración flexible del sistema
        * 👤 Preferencias personalizadas de empleados
        * 🎯 Algoritmos de optimización para asignación
        * 📈 Análisis de rendimiento y tendencias
        * ⚠️ Sistema de alertas y notificaciones automáticas
        * 🔄 Validaciones avanzadas de conflictos y límites
        
        **Características Técnicas:**
        * Integración completa con módulos HR de Odoo
        * Validaciones automáticas de traslapes y capacidades
        * Cron jobs para automatización de procesos
        * Reportes exportables en Excel
        * APIs para integraciones externas
        * Optimización de rendimiento con campos computados
        
        **Ideal para:**
        * Empresas con múltiples sucursales
        * Organizaciones con turnos rotativos
        * Negocios que requieren habilidades específicas
        * Compañías que buscan automatizar la planificación
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'depends': [
        'base', 
        'hr', 
        'hr_skills', 
        'mail',
        'web',
        'web_dashboard'
    ],
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },
    'data': [
        # Seguridad
        'security/ir.model.access.csv',
        
        # Datos base
        'data/cron_data.xml',
        'data/email_template.xml',
        
        # Vistas principales
        'views/work_role_views.xml',
        'views/work_shift_schedule_views.xml',
        'views/work_shift_assignment_views.xml',
        
        # Nuevas vistas avanzadas
        'views/shift_config_views.xml',
        'views/employee_preferences_views.xml',
        'views/shift_dashboard_views.xml',
        
        # Reportes
        'views/shift_reports_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'shift_planning/static/src/js/dashboard.js',
            'shift_planning/static/src/css/dashboard.css',
        ],
    },
    'demo': [
        'demo/shift_demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'sequence': 100,
    'images': ['static/description/banner.png'],
    'price': 99.99,
    'currency': 'USD',
    'live_test_url': 'https://demo.tuempresa.com',
}