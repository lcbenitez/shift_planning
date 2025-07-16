# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


class ShiftAutoAssignWizard(models.TransientModel):
    _name = 'shift.auto.assign.wizard'
    _description = 'Asistente para Asignación Automática de Turnos'

    # Filtros básicos
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
    
    # Opciones básicas
    assignment_mode = fields.Selection([
        ('fill_incomplete', 'Completar Turnos Incompletos'),
        ('replace_all', 'Reemplazar Todas las Asignaciones'),
    ], string='Modo de Asignación', default='fill_incomplete', required=True)
    
    use_preferences = fields.Boolean(
        string='Usar Preferencias de Empleados',
        default=True
    )
    
    # Resultados
    shifts_to_assign = fields.Integer(
        string='Turnos a Asignar',
        compute='_compute_shifts_to_assign'
    )
    
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

    @api.depends('date_from', 'date_to', 'branch_ids', 'assignment_mode')
    def _compute_shifts_to_assign(self):
        for record in self:
            domain = [
                ('date', '>=', record.date_from),
                ('date', '<=', record.date_to),
                ('state', '=', 'planned')
            ]
            
            if record.branch_ids:
                domain.append(('branch_id', 'in', record.branch_ids.ids))
            
            shifts = self.env['work.shift.schedule'].search(domain)
            
            if record.assignment_mode == 'fill_incomplete':
                incomplete_shifts = shifts.filtered(lambda s: not s.is_complete)
                record.shifts_to_assign = len(incomplete_shifts)
            else:
                record.shifts_to_assign = len(shifts)

    def action_assign_shifts(self):
        """Ejecutar asignación automática básica"""
        shifts = self._get_shifts_to_assign()
        
        if not shifts:
            raise UserError("No hay turnos para asignar.")
        
        # Obtener empleados disponibles
        available_employees = self.env['hr.employee'].search([
            ('active', '=', True)
        ])
        
        if not available_employees:
            raise UserError("No hay empleados disponibles.")
        
        # Ejecutar asignación simple
        results = self._execute_simple_assignment(shifts, available_employees)
        
        # Actualizar contadores
        self.assigned_count = results['assigned']
        self.failed_count = results['failed']
        self.assignment_log = results['log']
        
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

    def _execute_simple_assignment(self, shifts, available_employees):
        """Ejecutar asignación simple"""
        assigned_count = 0
        failed_count = 0
        log_entries = []
        
        for shift in shifts:
            try:
                # Calcular cuántos empleados necesitamos
                current_assignments = len(shift.assignment_ids.filtered(
                    lambda a: a.status != 'cancelled'
                ))
                
                needed_assignments = shift.quantity_required - current_assignments
                
                if needed_assignments <= 0:
                    continue
                
                # Asignar empleados disponibles
                assignments_made = 0
                for employee in available_employees:
                    if assignments_made >= needed_assignments:
                        break
                    
                    # Verificar si ya está asignado
                    existing = self.env['work.shift.assignment'].search([
                        ('shift_id', '=', shift.id),
                        ('employee_id', '=', employee.id),
                        ('status', '!=', 'cancelled')
                    ])
                    
                    if existing:
                        continue
                    
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