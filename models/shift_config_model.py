# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ShiftPlanningConfig(models.TransientModel):
    _name = 'shift.planning.config'
    _description = 'Configuración de Planificación de Turnos'
    _inherit = 'res.config.settings'

    # Configuraciones de notificaciones
    notification_advance_hours = fields.Integer(
        string='Horas de Anticipación para Notificaciones',
        default=24,
        help="Cuántas horas antes del turno enviar la notificación"
    )
    
    reminder_hours = fields.Integer(
        string='Horas para Recordatorio',
        default=2,
        help="Cuántas horas antes del turno enviar recordatorio"
    )
    
    auto_mark_absent_hours = fields.Integer(
        string='Horas para Marcar Ausente Automáticamente',
        default=1,
        help="Cuántas horas después del inicio marcar como ausente si no se reporta"
    )
    
    # Configuraciones de horarios
    min_shift_duration = fields.Float(
        string='Duración Mínima de Turno (horas)',
        default=2.0,
        help="Duración mínima permitida para un turno"
    )
    
    max_shift_duration = fields.Float(
        string='Duración Máxima de Turno (horas)',
        default=12.0,
        help="Duración máxima permitida para un turno"
    )
    
    max_daily_hours = fields.Float(
        string='Máximo de Horas Diarias por Empleado',
        default=8.0,
        help="Máximo de horas que puede trabajar un empleado por día"
    )
    
    min_rest_between_shifts = fields.Float(
        string='Descanso Mínimo Entre Turnos (horas)',
        default=8.0,
        help="Tiempo mínimo de descanso entre turnos para el mismo empleado"
    )
    
    # Configuraciones de asignación automática
    auto_assign_enabled = fields.Boolean(
        string='Habilitar Asignación Automática',
        default=False,
        help="Permitir asignación automática de empleados a turnos"
    )
    
    prefer_skills_match = fields.Boolean(
        string='Priorizar Coincidencia de Habilidades',
        default=True,
        help="Priorizar empleados con habilidades exactas para el rol"
    )
    
    consider_employee_preferences = fields.Boolean(
        string='Considerar Preferencias de Empleados',
        default=True,
        help="Considerar horarios preferidos de empleados en asignación"
    )
    
    # Configuraciones de reportes
    default_report_period = fields.Selection([
        ('daily', 'Diario'),
        ('weekly', 'Semanal'),
        ('monthly', 'Mensual'),
    ], string='Período de Reporte por Defecto', default='weekly')
    
    # Configuraciones de aprobación
    require_manager_approval = fields.Boolean(
        string='Requerir Aprobación de Gerente',
        default=False,
        help="Los turnos requieren aprobación de gerente antes de ser confirmados"
    )
    
    # Configuraciones de penalizaciones
    enable_attendance_penalties = fields.Boolean(
        string='Habilitar Penalizaciones por Asistencia',
        default=False,
        help="Aplicar penalizaciones por ausencias injustificadas"
    )
    
    @api.model
    def get_values(self):
        res = super().get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        res.update({
            'notification_advance_hours': int(ICPSudo.get_param('shift_planning.notification_advance_hours', 24)),
            'reminder_hours': int(ICPSudo.get_param('shift_planning.reminder_hours', 2)),
            'auto_mark_absent_hours': int(ICPSudo.get_param('shift_planning.auto_mark_absent_hours', 1)),
            'min_shift_duration': float(ICPSudo.get_param('shift_planning.min_shift_duration', 2.0)),
            'max_shift_duration': float(ICPSudo.get_param('shift_planning.max_shift_duration', 12.0)),
            'max_daily_hours': float(ICPSudo.get_param('shift_planning.max_daily_hours', 8.0)),
            'min_rest_between_shifts': float(ICPSudo.get_param('shift_planning.min_rest_between_shifts', 8.0)),
            'auto_assign_enabled': ICPSudo.get_param('shift_planning.auto_assign_enabled', False),
            'prefer_skills_match': ICPSudo.get_param('shift_planning.prefer_skills_match', True),
            'consider_employee_preferences': ICPSudo.get_param('shift_planning.consider_employee_preferences', True),
            'default_report_period': ICPSudo.get_param('shift_planning.default_report_period', 'weekly'),
            'require_manager_approval': ICPSudo.get_param('shift_planning.require_manager_approval', False),
            'enable_attendance_penalties': ICPSudo.get_param('shift_planning.enable_attendance_penalties', False),
        })
        return res

    def set_values(self):
        super().set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        ICPSudo.set_param('shift_planning.notification_advance_hours', self.notification_advance_hours)
        ICPSudo.set_param('shift_planning.reminder_hours', self.reminder_hours)
        ICPSudo.set_param('shift_planning.auto_mark_absent_hours', self.auto_mark_absent_hours)
        ICPSudo.set_param('shift_planning.min_shift_duration', self.min_shift_duration)
        ICPSudo.set_param('shift_planning.max_shift_duration', self.max_shift_duration)
        ICPSudo.set_param('shift_planning.max_daily_hours', self.max_daily_hours)
        ICPSudo.set_param('shift_planning.min_rest_between_shifts', self.min_rest_between_shifts)
        ICPSudo.set_param('shift_planning.auto_assign_enabled', self.auto_assign_enabled)
        ICPSudo.set_param('shift_planning.prefer_skills_match', self.prefer_skills_match)
        ICPSudo.set_param('shift_planning.consider_employee_preferences', self.consider_employee_preferences)
        ICPSudo.set_param('shift_planning.default_report_period', self.default_report_period)
        ICPSudo.set_param('shift_planning.require_manager_approval', self.require_manager_approval)
        ICPSudo.set_param('shift_planning.enable_attendance_penalties', self.enable_attendance_penalties)