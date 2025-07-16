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

    @api.model
    def get_chart_data(self):
        """Obtener datos para gráficos"""
        # Datos para gráfico de asistencia semanal
        today = date.today()
        dates = []
        attendance_data = []
        
        for i in range(7):
            check_date = today - timedelta(days=6-i)
            dates.append(check_date.strftime('%a %d'))
            
            day_assignments = self.env['work.shift.assignment'].search([
                ('shift_date', '=', check_date)
            ])
            
            if day_assignments:
                attendance_rate = self._calculate_attendance_rate(day_assignments)
                attendance_data.append(attendance_rate)
            else:
                attendance_data.append(0)
        
        # Datos para gráfico de cobertura por sucursal
        branches = self.env['res.partner'].search([('is_company', '=', True)])
        branch_data = []
        
        for branch in branches:
            branch_shifts = self.env['work.shift.schedule'].search([
                ('branch_id', '=', branch.id),
                ('date', '>=', today - timedelta(days=30)),
                ('date', '<=', today)
            ])
            
            if branch_shifts:
                total_required = sum(shift.quantity_required for shift in branch_shifts)
                total_assigned = sum(shift.assigned_count for shift in branch_shifts)
                coverage = (total_assigned / total_required) * 100 if total_required > 0 else 0
                
                branch_data.append({
                    'name': branch.name,
                    'coverage': coverage,
                    'shifts': len(branch_shifts)
                })
        
        # Datos para gráfico de roles más demandados
        role_data = []
        roles = self.env['work.shift.schedule'].read_group(
            [('date', '>=', today - timedelta(days=30))],
            ['role'],
            ['role']
        )
        
        for role_group in roles:
            role_shifts = self.env['work.shift.schedule'].search([
                ('role', '=', role_group['role']),
                ('date', '>=', today - timedelta(days=30))
            ])
            
            total_required = sum(shift.quantity_required for shift in role_shifts)
            role_data.append({
                'role': role_group['role'],
                'demand': total_required,
                'shifts_count': len(role_shifts)
            })
        
        role_data.sort(key=lambda x: x['demand'], reverse=True)
        
        return {
            'attendance_trend': {
                'dates': dates,
                'data': attendance_data
            },
            'branch_coverage': branch_data,
            'role_demand': role_data[:10]  # Top 10 roles
        }

    @api.model
    def get_upcoming_shifts(self, limit=10):
        """Obtener próximos turnos"""
        upcoming = self.env['work.shift.schedule'].search([
            ('date', '>=', date.today()),
            ('state', '=', 'planned')
        ], order='date asc, hour_start asc', limit=limit)
        
        return [{
            'id': shift.id,
            'date': shift.date,
            'time': f"{shift.hour_start:.1f}-{shift.hour_end:.1f}",
            'role': shift.role,
            'branch': shift.branch_id.name,
            'assigned': shift.assigned_count,
            'required': shift.quantity_required,
            'is_complete': shift.is_complete,
            'status': shift.state
        } for shift in upcoming]

    @api.model
    def get_employee_performance(self, limit=10):
        """Obtener rendimiento de empleados"""
        # Calcular métricas de los últimos 30 días
        date_from = date.today() - timedelta(days=30)
        
        employees = self.env['hr.employee'].search([('active', '=', True)])
        performance_data = []
        
        for employee in employees:
            assignments = self.env['work.shift.assignment'].search([
                ('employee_id', '=', employee.id),
                ('shift_date', '>=', date_from)
            ])
            
            if assignments:
                total_assignments = len(assignments)
                present_count = len(assignments.filtered(lambda a: a.status == 'present'))
                absent_count = len(assignments.filtered(lambda a: a.status == 'absent'))
                
                attendance_rate = (present_count / total_assignments) * 100 if total_assignments > 0 else 0
                
                # Calcular horas trabajadas
                total_hours = sum(
                    a.shift_id.hour_end - a.shift_id.hour_start 
                    for a in assignments.filtered(lambda a: a.status == 'present' and a.shift_id)
                )
                
                performance_data.append({
                    'employee': employee.name,
                    'total_shifts': total_assignments,
                    'attendance_rate': attendance_rate,
                    'total_hours': total_hours,
                    'absent_count': absent_count,
                    'score': attendance_rate + (total_hours / 10)  # Puntaje simple
                })
        
        # Ordenar por puntaje
        performance_data.sort(key=lambda x: x['score'], reverse=True)
        
        return performance_data[:limit]