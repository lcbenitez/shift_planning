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
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'depends': [
        'base', 
        'hr', 
        'hr_skills', 
        'mail'
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
        
        # Dashboard
        'views/shift_dashboard_view.xml',
        
        # Vistas adicionales (si existen)
        'views/shift_reports_views.xml',
        
        # Descomenta gradualmente según tengas los archivos:
        # 'views/shift_config_view.xml',
        # 'views/employee_preferences_views.xml',
        # 'views/auto_assign_wizard_views.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'sequence': 100,
}