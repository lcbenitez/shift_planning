# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class EmployeeShiftPreferences(models.Model):
    _name = 'employee.shift.preferences'
    _description = 'Preferencias de Turnos de Empleados'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one(
        'hr.employee', 
        string='Empleado', 
        required=True,
        ondelete='cascade'
    )
    
    # Preferencias de horario
    preferred_morning = fields.Boolean(
        string='Prefiere Mañana',
        help="Prefiere turnos matutinos (6:00 - 14:00)"
    )
    
    preferred_afternoon = fields.Boolean(
        string='Prefiere Tarde',
        help="Prefiere turnos vespertinos (14:00 - 22:00)"
    )
    
    preferred_night = fields.Boolean(
        string='Prefiere Noche',
        help="Prefiere turnos nocturnos (22:00 - 6:00)"
    )
    
    # Días de la semana preferidos
    preferred_monday = fields.Boolean(string='Lunes', default=True)
    preferred_tuesday = fields.Boolean(string='Martes', default=True)
    preferred_wednesday = fields.Boolean(string='Miércoles', default=True)
    preferred_thursday = fields.Boolean(string='Jueves', default=True)
    preferred_friday = fields.Boolean(string='Viernes', default=True)
    preferred_saturday = fields.Boolean(string='Sábado', default=False)
    preferred_sunday = fields.Boolean(string='Domingo', default=False)
    
    # Sucursales preferidas
    preferred_branch_ids = fields.Many2many(
        'res.partner',
        string='Sucursales Preferidas',
        domain="[('is_company', '=', True)]"
    )
    
    # Roles preferidos
    preferred_role_ids = fields.Many2many(
        'work.role',
        string='Roles Preferidos'
    )
    
    # Configuraciones de disponibilidad
    max_hours_per_day = fields.Float(
        string='Máximo Horas por Día',
        default=8.0,
        help="Máximo de horas que puede trabajar por día"
    )
    
    max_hours_per_week = fields.Float(
        string='Máximo Horas por Semana',
        default=40.0,
        help="Máximo de horas que puede trabajar por semana"
    )
    
    min_rest_hours = fields.Float(
        string='Mínimo Descanso Entre Turnos',
        default=8.0,
        help="Horas mínimas de descanso entre turnos"
    )
    
    # Disponibilidad por urgencia
    available_for_urgent = fields.Boolean(
        string='Disponible para Urgencias',
        default=True,
        help="Puede ser llamado para cubrir turnos urgentes"
    )
    
    # Configuraciones de notificaciones
    notification_advance_hours = fields.Integer(
        string='Anticipación de Notificación (horas)',
        default=24,
        help="Horas de anticipación para recibir notificaciones"
    )
    
    # Notas adicionales
    notes = fields.Text(
        string='Notas Adicionales',
        help="Información adicional sobre preferencias o restricciones"
    )
    
    # Campos computados
    is_available_today = fields.Boolean(
        string='Disponible Hoy',
        compute='_compute_availability_today'
    )
    
    current_week_hours = fields.Float(
        string='Horas Esta Semana',
        compute='_compute_current_week_hours'
    )

    @api.depends('employee_id')
    def _compute_availability_today(self):
        """Calcular si el empleado está disponible hoy"""
        today = fields.Date.today()
        weekday = today.weekday()  # 0=Monday, 6=Sunday
        
        for record in self:
            # Mapear día de la semana a campo de preferencia
            weekday_fields = [
                'preferred_monday', 'preferred_tuesday', 'preferred_wednesday',
                'preferred_thursday', 'preferred_friday', 'preferred_saturday',
                'preferred_sunday'
            ]
            
            if weekday < len(weekday_fields):
                record.is_available_today = getattr(record, weekday_fields[weekday])
            else:
                record.is_available_today = False

    @api.depends('employee_id')
    def _compute_current_week_hours(self):
        """Calcular horas trabajadas esta semana"""
        for record in self:
            # Calcular inicio y fin de semana
            today = fields.Date.today()
            start_week = today - fields.Timedelta(days=today.weekday())
            end_week = start_week + fields.Timedelta(days=6)
            
            # Buscar asignaciones de esta semana
            assignments = self.env['work.shift.assignment'].search([
                ('employee_id', '=', record.employee_id.id),
                ('shift_date', '>=', start_week),
                ('shift_date', '<=', end_week),
                ('status', 'in', ['confirmed', 'present'])
            ])
            
            # Calcular horas totales
            total_hours = 0
            for assignment in assignments:
                if assignment.shift_id:
                    duration = assignment.shift_id.hour_end - assignment.shift_id.hour_start
                    total_hours += duration
            
            record.current_week_hours = total_hours

    def get_shift_preference_score(self, shift):
        """Calcular puntaje de preferencia para un turno específico"""
        score = 0
        
        # Verificar preferencias de horario
        if shift.hour_start >= 6 and shift.hour_start < 14 and self.preferred_morning:
            score += 10
        elif shift.hour_start >= 14 and shift.hour_start < 22 and self.preferred_afternoon:
            score += 10
        elif (shift.hour_start >= 22 or shift.hour_start < 6) and self.preferred_night:
            score += 10
        
        # Verificar día de la semana
        weekday = shift.date.weekday()
        weekday_fields = [
            'preferred_monday', 'preferred_tuesday', 'preferred_wednesday',
            'preferred_thursday', 'preferred_friday', 'preferred_saturday',
            'preferred_sunday'
        ]
        
        if weekday < len(weekday_fields) and getattr(self, weekday_fields[weekday]):
            score += 5
        
        # Verificar sucursal preferida
        if shift.branch_id in self.preferred_branch_ids:
            score += 8
        
        # Verificar rol preferido
        role_obj = self.env['work.role'].search([('name', '=', shift.role)], limit=1)
        if role_obj and role_obj in self.preferred_role_ids:
            score += 8
        
        return score

    @api.constrains('max_hours_per_day')
    def _check_max_hours_per_day(self):
        for record in self:
            if record.max_hours_per_day <= 0 or record.max_hours_per_day > 24:
                raise ValidationError("Las horas máximas por día deben estar entre 1 y 24.")

    @api.constrains('max_hours_per_week')
    def _check_max_hours_per_week(self):
        for record in self:
            if record.max_hours_per_week <= 0 or record.max_hours_per_week > 168:
                raise ValidationError("Las horas máximas por semana deben estar entre 1 y 168.")


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    shift_preferences_ids = fields.One2many(
        'employee.shift.preferences',
        'employee_id',
        string='Preferencias de Turnos'
    )
    
    # Campo computado para acceso rápido a preferencias
    has_shift_preferences = fields.Boolean(
        string='Tiene Preferencias',
        compute='_compute_has_shift_preferences'
    )
    
    availability_score = fields.Float(
        string='Puntaje de Disponibilidad',
        compute='_compute_availability_score',
        help="Puntaje basado en disponibilidad y preferencias"
    )

    @api.depends('shift_preferences_ids')
    def _compute_has_shift_preferences(self):
        for record in self:
            record.has_shift_preferences = bool(record.shift_preferences_ids)

    @api.depends('shift_preferences_ids')
    def _compute_availability_score(self):
        for record in self:
            if record.shift_preferences_ids:
                # Calcular puntaje basado en disponibilidad y preferencias
                prefs = record.shift_preferences_ids[0]
                score = 50  # Puntaje base
                
                # Bonus por disponibilidad para urgencias
                if prefs.available_for_urgent:
                    score += 20
                
                # Bonus por flexibilidad en días
                weekday_prefs = [
                    prefs.preferred_monday, prefs.preferred_tuesday,
                    prefs.preferred_wednesday, prefs.preferred_thursday,
                    prefs.preferred_friday, prefs.preferred_saturday,
                    prefs.preferred_sunday
                ]
                available_days = sum(weekday_prefs)
                score += (available_days / 7) * 20
                
                # Bonus por flexibilidad en horarios
                time_prefs = [
                    prefs.preferred_morning, prefs.preferred_afternoon,
                    prefs.preferred_night
                ]
                available_times = sum(time_prefs)
                score += (available_times / 3) * 10
                
                record.availability_score = score
            else:
                record.availability_score = 30  # Puntaje bajo si no tiene preferencias

    def action_configure_shift_preferences(self):
        """Abrir configuración de preferencias de turno"""
        preference = self.shift_preferences_ids and self.shift_preferences_ids[0]
        
        if not preference:
            preference = self.env['employee.shift.preferences'].create({
                'employee_id': self.id
            })
        
        return {
            'name': 'Configurar Preferencias de Turno',
            'type': 'ir.actions.act_window',
            'res_model': 'employee.shift.preferences',
            'res_id': preference.id,
            'view_mode': 'form',
            'target': 'new',
        }