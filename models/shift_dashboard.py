# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta, date
from odoo.exceptions import UserError


class ShiftDashboard(models.Model):
    _name = 'shift.dashboard'
    _description = 'Dashboard de Turnos'
    _auto = False

    # Campos para estadísticas
    total_shifts_today = fields.Integer(string='Turnos Hoy')
    total_employees_assigned = fields.Integer(string='Empleados Asignados')
    attendance_rate = fields.Float(string='Tasa de Asistencia (%)')
    shifts_coverage = fields.Float(string='Cobertura de Turnos (%)')
    
    # Métricas semanales
    weekly_shifts = fields.Integer(string='Turnos Esta Semana')
    weekly_hours = fields.Float(string='Horas Esta Semana')
    weekly_attendance = fields.Float(string='Asistencia Semanal (%)')
    
    # Métricas mensuales
    monthly_shifts = fields.Integer(string='Turnos Este Mes')
    monthly_coverage = fields.Float(string='Cobertura Mensual (%)')
    
    # Alertas
    urgent_shifts = fields.Integer(string='Turnos Urgentes')
    incomplete_shifts = fields.Integer(string='Turnos Incompletos')
    conflicting_assignments = fields.Integer(string='Asignaciones en Conflicto')

    def init(self):
        # Esta vista no necesita tabla física
        pass

    def action_new_shift(self):
        """Crear nuevo turno"""
        return {
            'name': 'Nuevo Turno',
            'type': 'ir.actions.act_window',
            'res_model': 'work.shift.schedule',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_auto_assign(self):
        """Abrir asignación automática"""
        return {
            'name': 'Asignación Automática',
            'type': 'ir.actions.act_window',
            'res_model': 'shift.auto.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_generate_report(self):
        """Generar reporte"""
        return {
            'name': 'Generar Reporte',
            'type': 'ir.actions.act_window',
            'res_model': 'shift.branch.report',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_open_config(self):
        """Abrir configuración"""
        return {
            'name': 'Configuración de Turnos',
            'type': 'ir.actions.act_window',
            'res_model': 'shift.planning.config',
            'view_mode': 'form',
            'target': 'new',
        }

    @api.model
    def get_dashboard_data(self):
        """Obtener datos del dashboard"""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        month_start = today.replace(day=1)
        
        # Turnos de hoy
        today_shifts = self.env['work.shift.schedule'].search([
            ('date', '=', today),
            ('state', '=', 'planned')
        ])
        
        # Asignaciones de hoy
        today_assignments = self.env['work.shift.assignment'].search([
            ('shift_date', '=', today)
        ])
        
        # Asignaciones de esta semana
        week_assignments = self.env['work.shift.assignment'].search([
            ('shift_date', '>=', week_start),
            ('shift_date', '<=', week_end)
        ])
        
        # Asignaciones del mes
        month_assignments = self.env['work.shift.assignment'].search([
            ('shift_date', '>=', month_start),
            ('shift_date', '<=', today)
        ])
        
        # Calcular métricas
        data = {
            'today': {
                'total_shifts': len(today_shifts),
                'total_assignments': len(today_assignments),
                'present_count': len(today_assignments.filtered(lambda a: a.status == 'present')),
                'absent_count': len(today_assignments.filtered(lambda a: a.status == 'absent')),
                'pending_count': len(today_assignments.filtered(lambda a: a.status in ['assigned', 'confirmed'])),
            },
            'week': {
                'total_shifts': len(self.env['work.shift.schedule'].search([
                    ('date', '>=', week_start),
                    ('date', '<=', week_end)
                ])),
                'total_assignments': len(week_assignments),
                'total_hours': sum(
                    a.shift_id.hour_end - a.shift_id.hour_start 
                    for a in week_assignments.filtered(lambda a: a.shift_id)
                ),
                'attendance_rate': self._calculate_attendance_rate(week_assignments),
            },
            'month': {
                'total_shifts': len(self.env['work.shift.schedule'].search([
                    ('date', '>=', month_start),
                    ('date', '<=', today)
                ])),
                'total_assignments': len(month_assignments),
                'coverage_rate': self._calculate_coverage_rate(month_start, today),
            },
            'alerts': {
                'incomplete_shifts': len(self.env['work.shift.schedule'].search([
                    ('date', '>=', today),
                    ('state', '=', 'planned'),
                    ('is_complete', '=', False)
                ])),
                'no_email_employees': len(self.env['hr.employee'].search([
                    ('active', '=', True),
                    ('work_email', '=', False)
                ])),
                'conflicting_assignments': self._count_conflicting_assignments(),
            }
        }
        
        return data

    def _calculate_attendance_rate(self, assignments):
        """Calcular tasa de asistencia"""
        if not assignments:
            return 0.0
        
        completed_assignments = assignments.filtered(
            lambda a: a.status in ['present', 'absent']
        )
        
        if not completed_assignments:
            return 0.0
        
        present_assignments = completed_assignments.filtered(
            lambda a: a.status == 'present'
        )
        
        return (len(present_assignments) / len(completed_assignments)) * 100

    def _calculate_coverage_rate(self, date_from, date_to):
        """Calcular tasa de cobertura de turnos"""
        shifts = self.env['work.shift.schedule'].search([
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ])
        
        if not shifts:
            return 0.0
        
        total_required = sum(shift.quantity_required for shift in shifts)
        total_assigned = sum(shift.assigned_count for shift in shifts)
        
        return (total_assigned / total_required) * 100 if total_required > 0 else 0.0

    def _count_conflicting_assignments(self):
        """Contar asignaciones en conflicto"""
        # Buscar empleados con múltiples asignaciones el mismo día
        today = date.today()
        future_date = today + timedelta(days=30)
        
        assignments = self.env['work.shift.assignment'].search([
            ('shift_date', '>=', today),
            ('shift_date', '<=', future_date),
            ('status', '!=', 'cancelled')
        ])
        
        conflicts = 0
        grouped_by_employee_date = {}
        
        for assignment in assignments:
            key = (assignment.employee_id.id, assignment.shift_date)
            if key not in grouped_by_employee_date:
                grouped_by_employee_date[key] = []
            grouped_by_employee_date[key].append(assignment)
        
        # Verificar traslapes
        for key, employee_assignments in grouped_by_employee_date.items():
            if len(employee_assignments) > 1:
                for i, assignment1 in enumerate(employee_assignments):
                    for assignment2 in employee_assignments[i+1:]:
                        if self._assignments_overlap(assignment1, assignment2):
                            conflicts += 1
        
        return conflicts

    def _assignments_overlap(self, assignment1, assignment2):
        """Verificar si dos asignaciones se traslapan"""
        shift1 = assignment1.shift_id
        shift2 = assignment2.shift_id
        
        return (shift1.hour_start < shift2.hour_end and 
                shift1.hour_end > shift2.hour_start)