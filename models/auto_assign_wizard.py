# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


class ShiftAutoAssignWizard(models.TransientModel):
    _name = 'shift.auto.assign.wizard'
    _description = 'Asistente para Asignación Automática de Turnos'

    # Filtros para seleccionar turnos
    date_from = fields.Date(
        string='Fecha Desde',
        required=True,
        default=fields.Date.today
    )
    
    date_to = fields.Date(
        string='Fecha Hasta',
        required=True,
        default=lambda self: fields.Date.today() + timedelta(days=7)
    )
    
    branch_ids = fields.Many2many(
        'res.partner',
        string='Sucursales',
        domain="[('is_company', '=', True)]",
        help="Dejar vacío para incluir todas las sucursales"
    )
    
    role_ids = fields.Many2many(
        'work.role',
        string='Roles',
        help="Dejar vacío para incluir todos los roles"
    )
    
    # Opciones de asignación
    assignment_mode = fields.Selection([
        ('fill_incomplete', 'Completar Turnos Incompletos'),
        ('optimize_all', 'Optimizar Todas las Asignaciones'),
        ('replace_all', 'Reemplazar Todas las Asignaciones'),
    ], string='Modo de Asignación', default='fill_incomplete', required=True)
    
    use_preferences = fields.Boolean(
        string='Usar Preferencias de Empleados',
        default=True,
        help="Considerar las preferencias configuradas de los empleados"
    )
    
    consider_skills = fields.Boolean(
        string='Considerar Habilidades',
        default=True,
        help="Priorizar empleados con habilidades específicas del rol"
    )
    
    respect_work_limits = fields.Boolean(
        string='Respetar Límites de Trabajo',
        default=True,
        help="Respetar límites de horas diarias y semanales"
    )
    
    # Configuraciones avanzadas
    max_shifts_per_employee = fields.Integer(
        string='Máximo Turnos por Empleado',
        default=0,
        help="0 = Sin límite"
    )
    
    priority_urgent_shifts = fields.Boolean(
        string='Priorizar Turnos Urgentes',
        default=True,
        help="Asignar primero turnos marcados como urgentes"
    )
    
    # Resultados
    shifts_to_assign = fields.Integer(
        string='Turnos a Asignar',
        compute='_compute_shifts_to_assign',
        help="Número de turnos que necesitan asignación"
    )
    
    available_employees = fields.Integer(
        string='Empleados Disponibles',
        compute='_compute_available_employees',
        help="Número de empleados disponibles para asignación"
    )
    
    # Campos de resultado después de la asignación
    assigned_count = fields.Integer(
        string='Turnos Asignados',
        readonly=True
    )
    
    failed_count = fields.Integer(
        string='Turnos No Asignados',
        readonly=True
    )
    
    assignment_log = fields.Text(
        string='Log de Asignación',
        readonly=True
    )

    @api.depends('date_from', 'date_to', 'branch_ids', 'role_ids', 'assignment_mode')
    def _compute_shifts_to_assign(self):
        for record in self:
            domain = [
                ('date', '>=', record.date_from),
                ('date', '<=', record.date_to),
                ('state', '=', 'planned')
            ]
            
            if record.branch_ids:
                domain.append(('branch_id', 'in', record.branch_ids.ids))
            
            if record.role_ids:
                domain.append(('role', 'in', record.role_ids.mapped('name')))
            
            shifts = self.env['work.shift.schedule'].search(domain)
            
            if record.assignment_mode == 'fill_incomplete':
                # Solo contar turnos incompletos
                incomplete_shifts = shifts.filtered(lambda s: not s.is_complete)
                record.shifts_to_assign = len(incomplete_shifts)
            else:
                # Contar todos los turnos
                record.shifts_to_assign = len(shifts)

    @api.depends('date_from', 'date_to')
    def _compute_available_employees(self):
        for record in self:
            # Contar empleados activos
            employees = self.env['hr.employee'].search([
                ('active', '=', True)
            ])
            record.available_employees = len(employees)

    def action_preview_assignment(self):
        """Vista previa de la asignación sin confirmar"""
        shifts = self._get_shifts_to_assign()
        
        if not shifts:
            raise UserError("No hay turnos para asignar con los filtros seleccionados.")
        
        # Obtener empleados disponibles
        available_employees = self._get_available_employees()
        
        if not available_employees:
            raise UserError("No hay empleados disponibles para asignación.")
        
        # Crear preview
        preview_data = []
        for shift in shifts[:10]:  # Mostrar solo primeros 10
            suggested_employees = self._get_best_employees_for_shift(
                shift, available_employees
            )
            
            preview_data.append({
                'shift': shift,
                'suggested_employees': suggested_employees[:3],  # Top 3
                'current_assignments': len(shift.assignment_ids.filtered(
                    lambda a: a.status != 'cancelled'
                ))
            })
        
        return {
            'name': 'Vista Previa de Asignación',
            'type': 'ir.actions.act_window',
            'res_model': 'shift.assignment.preview',
            'view_mode': 'tree',
            'target': 'new',
            'context': {
                'default_preview_data': preview_data,
                'default_wizard_id': self.id,
            }
        }

    def action_assign_shifts(self):
        """Ejecutar asignación automática"""
        shifts = self._get_shifts_to_assign()
        
        if not shifts:
            raise UserError("No hay turnos para asignar.")
        
        # Obtener empleados disponibles
        available_employees = self._get_available_employees()
        
        if not available_employees:
            raise UserError("No hay empleados disponibles.")
        
        # Ejecutar asignación
        results = self._execute_assignment(shifts, available_employees)
        
        # Actualizar contadores
        self.assigned_count = results['assigned']
        self.failed_count = results['failed']
        self.assignment_log = results['log']
        
        # Mostrar resultados
        return {
            'name': 'Resultados de Asignación',
            'type': 'ir.actions.act_window',
            'res_model': 'shift.auto.assign.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'show_results': True}
        }

    def _get_shifts_to_assign(self):
        """Obtener turnos que necesitan asignación"""
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'planned')
        ]
        
        if self.branch_ids:
            domain.append(('branch_id', 'in', self.branch_ids.ids))
        
        if self.role_ids:
            domain.append(('role', 'in', self.role_ids.mapped('name')))
        
        shifts = self.env['work.shift.schedule'].search(domain)
        
        if self.assignment_mode == 'fill_incomplete':
            shifts = shifts.filtered(lambda s: not s.is_complete)
        elif self.assignment_mode == 'replace_all':
            # Cancelar asignaciones existentes
            for shift in shifts:
                shift.assignment_ids.filtered(
                    lambda a: a.status not in ['present', 'cancelled']
                ).write({'status': 'cancelled'})
        
        return shifts

    def _get_available_employees(self):
        """Obtener empleados disponibles para asignación"""
        employees = self.env['hr.employee'].search([
            ('active', '=', True)
        ])
        
        return employees

    def _get_best_employees_for_shift(self, shift, available_employees):
        """Obtener los mejores empleados para un turno específico"""
        scored_employees = []
        
        for employee in available_employees:
            score = self._calculate_employee_score(employee, shift)
            if score > 0:  # Solo incluir empleados con puntaje positivo
                scored_employees.append((employee, score))
        
        # Ordenar por puntaje descendente
        scored_employees.sort(key=lambda x: x[1], reverse=True)
        
        return [emp for emp, score in scored_employees]

    def _calculate_employee_score(self, employee, shift):
        """Calcular puntaje de un empleado para un turno específico"""
        score = 0
        
        # Verificar si ya está asignado a este turno
        existing_assignment = self.env['work.shift.assignment'].search([
            ('employee_id', '=', employee.id),
            ('shift_id', '=', shift.id),
            ('status', '!=', 'cancelled')
        ])
        
        if existing_assignment:
            return -1000  # Penalización muy alta
        
        # Verificar conflictos de horario
        if self._has_schedule_conflict(employee, shift):
            return -500  # Penalización alta
        
        # Puntaje base por disponibilidad
        score += employee.availability_score or 50
        
        # Considerar habilidades si está habilitado
        if self.consider_skills:
            role_obj = self.env['work.role'].search([('name', '=', shift.role)], limit=1)
            if role_obj and role_obj.skill_ids:
                # Verificar si el empleado tiene las habilidades requeridas
                required_skills = set(role_obj.skill_ids.ids)
                employee_skills = set(employee.skill_ids.ids)
                
                if required_skills.issubset(employee_skills):
                    score += 30  # Bonus por habilidades exactas
                elif required_skills.intersection(employee_skills):
                    score += 15  # Bonus por habilidades parciales
                else:
                    score -= 20  # Penalización por falta de habilidades
        
        # Considerar preferencias si está habilitado
        if self.use_preferences and employee.shift_preferences_ids:
            preferences = employee.shift_preferences_ids[0]
            preference_score = preferences.get_shift_preference_score(shift)
            score += preference_score
        
        # Verificar límites de trabajo
        if self.respect_work_limits:
            if not self._check_work_limits(employee, shift):
                score -= 100  # Penalización por exceder límites
        
        return score

    def _has_schedule_conflict(self, employee, shift):
        """Verificar si hay conflicto de horario"""
        existing_assignments = self.env['work.shift.assignment'].search([
            ('employee_id', '=', employee.id),
            ('shift_date', '=', shift.date),
            ('status', '!=', 'cancelled')
        ])
        
        for assignment in existing_assignments:
            # Verificar traslape de horarios
            if (shift.hour_start < assignment.shift_id.hour_end and 
                shift.hour_end > assignment.shift_id.hour_start):
                return True
        
        return False

    def _check_work_limits(self, employee, shift):
        """Verificar límites de trabajo del empleado"""
        # Verificar límites diarios
        daily_assignments = self.env['work.shift.assignment'].search([
            ('employee_id', '=', employee.id),
            ('shift_date', '=', shift.date),
            ('status', '!=', 'cancelled')
        ])
        
        daily_hours = sum(
            a.shift_id.hour_end - a.shift_id.hour_start 
            for a in daily_assignments
        )
        
        shift_duration = shift.hour_end - shift.hour_start
        max_daily = 8.0  # Valor por defecto
        
        if employee.shift_preferences_ids:
            max_daily = employee.shift_preferences_ids[0].max_hours_per_day
        
        if daily_hours + shift_duration > max_daily:
            return False
        
        # Verificar límites semanales
        week_start = shift.date - timedelta(days=shift.date.weekday())
        week_end = week_start + timedelta(days=6)
        
        weekly_assignments = self.env['work.shift.assignment'].search([
            ('employee_id', '=', employee.id),
            ('shift_date', '>=', week_start),
            ('shift_date', '<=', week_end),
            ('status', '!=', 'cancelled')
        ])
        
        weekly_hours = sum(
            a.shift_id.hour_end - a.shift_id.hour_start 
            for a in weekly_assignments
        )
        
        max_weekly = 40.0  # Valor por defecto
        
        if employee.shift_preferences_ids:
            max_weekly = employee.shift_preferences_ids[0].max_hours_per_week
        
        if weekly_hours + shift_duration > max_weekly:
            return False
        
        return True

    def _execute_assignment(self, shifts, available_employees):
        """Ejecutar la asignación automática"""
        assigned_count = 0
        failed_count = 0
        log_entries = []
        
        for shift in shifts:
            try:
                # Calcular cuántos empleados necesitamos asignar
                current_assignments = len(shift.assignment_ids.filtered(
                    lambda a: a.status != 'cancelled'
                ))
                
                needed_assignments = shift.quantity_required - current_assignments
                
                if needed_assignments <= 0:
                    continue
                
                # Obtener mejores empleados para este turno
                best_employees = self._get_best_employees_for_shift(
                    shift, available_employees
                )
                
                # Asignar empleados
                assignments_made = 0
                for employee in best_employees:
                    if assignments_made >= needed_assignments:
                        break
                    
                    # Crear asignación
                    self.env['work.shift.assignment'].create({
                        'shift_id': shift.id,
                        'employee_id': employee.id,
                        'status': 'assigned'
                    })
                    
                    assignments_made += 1
                    assigned_count += 1
                    
                    log_entries.append(
                        f"✓ Asignado {employee.name} a {shift.role} "
                        f"({shift.date} {shift.hour_start:.1f}-{shift.hour_end:.1f})"
                    )
                
                if assignments_made < needed_assignments:
                    failed_count += needed_assignments - assignments_made
                    log_entries.append(
                        f"⚠ Turno {shift.role} ({shift.date}) - "
                        f"Solo se asignaron {assignments_made} de {needed_assignments}"
                    )
                
            except Exception as e:
                failed_count += 1
                log_entries.append(f"❌ Error en turno {shift.role} ({shift.date}): {str(e)}")
        
        return {
            'assigned': assigned_count,
            'failed': failed_count,
            'log': '\n'.join(log_entries)
        }

    def action_view_assigned_shifts(self):
        """Ver turnos asignados"""
        return {
            'name': 'Turnos Asignados',
            'type': 'ir.actions.act_window',
            'res_model': 'work.shift.assignment',
            'view_mode': 'tree,form',
            'domain': [
                ('shift_date', '>=', self.date_from),
                ('shift_date', '<=', self.date_to),
                ('status', 'in', ['assigned', 'confirmed'])
            ],
            'context': {
                'search_default_group_by_date': 1,
                'search_default_group_by_employee': 1,
            }
        }