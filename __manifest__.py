{
    'name': 'Shift Planning',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Planificación de turnos esperados por rol y sucursal',
    'description': """
        Módulo para la gestión de turnos laborales
        ==========================================
        
        Este módulo permite:
        * Definir roles de trabajo con habilidades requeridas
        * Programar turnos esperados por sucursal, fecha y rol
        * Asignar empleados a turnos específicos
        * Seguimiento de asistencia y estados
        * Reportes de cumplimiento de turnos
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'depends': ['base', 'hr', 'hr_skills', 'mail'],
    'data': [
       'security/ir.model.access.csv',
       'data/cron_data.xml',
       'data/email_template.xml',
       'views/work_role_views.xml',
       'views/work_shift_schedule_views.xml',
       'views/work_shift_assignment_views.xml',
     ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}