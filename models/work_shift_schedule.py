# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class WorkShiftSchedule(models.Model):
    _name = 'work.shift.schedule'
    _description = 'Programacion Esperada de Turnos'
    _order = 'date desc, hour_start'

    date = fields.Date(string="Fecha", required=True)
    hour_start = fields.Float(string="Hora Inicio", required=True)
    hour_end = fields.Float(string="Hora Fin", required=True)
    branch_id = fields.Many2one(
        'res.partner', 
        string="Sucursal", 
        domain="[('is_company', '=', True)]", 
        required=True
    )
    role = fields.Char(string="Rol", required=True)
    quantity_required = fields.Integer(
        string="Cantidad Requerida", 
        required=True, 
        default=1
    )
    state = fields.Selection([
        ('planned', 'Programado'),
        ('done', 'Completado'),
    ], string="Estado", default='planned')
    assignment_ids = fields.One2many(
        'work.shift.assignment', 
        'shift_id', 
        string='Asignaciones'
    )
    
    # Campos computados para control
    assigned_count = fields.Integer(
        string='Empleados Asignados',
        compute='_compute_assigned_count',
        store=True
    )
    is_complete = fields.Boolean(
        string='Turno Completo',
        compute='_compute_is_complete',
        store=True
    )
    remaining_slots = fields.Integer(
        string='Espacios Restantes',
        compute='_compute_remaining_slots',
        store=True
    )

    @api.depends('assignment_ids', 'assignment_ids.status')
    def _compute_assigned_count(self):
        for record in self:
            # Contar solo asignaciones activas (no canceladas)
            record.assigned_count = len(record.assignment_ids.filtered(
                lambda a: a.status != 'cancelled'
            ))
    
    @api.depends('assigned_count', 'quantity_required')
    def _compute_is_complete(self):
        for record in self:
            record.is_complete = record.assigned_count >= record.quantity_required
    
    @api.depends('assigned_count', 'quantity_required')
    def _compute_remaining_slots(self):
        for record in self:
            record.remaining_slots = record.quantity_required - record.assigned_count

    def action_mark_all_present(self):
        """Marcar todos los empleados asignados como presentes"""
        for assignment in self.assignment_ids:
            if assignment.status == 'assigned':
                assignment.status = 'present'
        return True

    def action_mark_all_absent(self):
        """Marcar todos los empleados asignados como ausentes"""
        for assignment in self.assignment_ids:
            if assignment.status == 'assigned':
                assignment.status = 'absent'
        return True

    def action_auto_mark_attendance(self):
        """Proceso automático para marcar asistencias después del turno"""
        current_time = fields.Datetime.now()
        current_date = current_time.date()
        current_hour = current_time.hour + current_time.minute / 60.0
        
        # Solo procesar si el turno ya terminó
        if self.date == current_date and current_hour > self.hour_end:
            # Marcar como ausentes a los que siguen en estado 'assigned'
            for assignment in self.assignment_ids:
                if assignment.status in ['assigned', 'confirmed']:
                    assignment.status = 'absent'
            return True
        return False

    def action_confirm_all_assignments(self):
        """Confirmar todas las asignaciones del turno"""
        confirmed_count = 0
        for assignment in self.assignment_ids:
            if assignment.status == 'assigned':
                assignment.action_confirm_assignment()
                confirmed_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Asignaciones Confirmadas',
                'message': f'Se confirmaron {confirmed_count} asignaciones',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_send_all_notifications(self):
        """Enviar notificaciones a todos los empleados asignados"""
        sent_count = 0
        error_count = 0
        errors = []
        
        for assignment in self.assignment_ids:
            if assignment.status in ['assigned', 'confirmed'] and not assignment.notification_sent:
                try:
                    if assignment.employee_email:
                        assignment.action_send_notification()
                        sent_count += 1
                    else:
                        error_count += 1
                        errors.append(f"{assignment.employee_id.name} (sin email)")
                except Exception as e:
                    error_count += 1
                    errors.append(f"{assignment.employee_id.name} (error: {str(e)})")
        
        message = f'Notificaciones enviadas: {sent_count}'
        if error_count > 0:
            message += f'\nErrores: {error_count}'
            if errors:
                message += f'\n- {", ".join(errors[:3])}'
                if len(errors) > 3:
                    message += f' y {len(errors) - 3} más...'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Notificaciones Enviadas',
                'message': message,
                'type': 'success' if error_count == 0 else 'warning',
                'sticky': True if error_count > 0 else False,
            }
        }

    def action_clear_all_assignments(self):
        """Limpiar todas las asignaciones del turno"""
        assignment_count = len(self.assignment_ids)
        self.assignment_ids.unlink()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Asignaciones Eliminadas',
                'message': f'Se eliminaron {assignment_count} asignaciones',
                'type': 'info',
                'sticky': False,
            }
        }

    def action_cancel_all_assignments(self):
        """Cancelar todas las asignaciones del turno"""
        cancelled_count = 0
        for assignment in self.assignment_ids:
            if assignment.status not in ['cancelled', 'present']:
                assignment.status = 'cancelled'
                cancelled_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Asignaciones Canceladas',
                'message': f'Se cancelaron {cancelled_count} asignaciones',
                'type': 'info',
                'sticky': False,
            }
        }

    @api.model
    def cron_auto_mark_attendance(self):
        """Cron job para marcar automáticamente las asistencias"""
        current_time = fields.Datetime.now()
        current_date = current_time.date()
        current_hour = current_time.hour + current_time.minute / 60.0
        
        # Buscar turnos que ya terminaron hoy
        shifts_to_process = self.search([
            ('date', '=', current_date),
            ('hour_end', '<', current_hour),
            ('state', '=', 'planned')
        ])
        
        for shift in shifts_to_process:
            # Marcar ausentes a los que no fueron marcados como presentes
            shift.assignment_ids.filtered(lambda a: a.status in ['assigned', 'confirmed']).write({
                'status': 'absent'
            })
            
            # Marcar el turno como completado
            shift.state = 'done'
            
        return True

    @api.constrains('hour_start', 'hour_end')
    def _check_hours(self):
        for record in self:
            if record.hour_end <= record.hour_start:
                raise ValidationError("La hora de fin debe ser mayor que la hora de inicio.")

    @api.constrains('quantity_required')
    def _check_quantity(self):
        for record in self:
            if record.quantity_required <= 0:
                raise ValidationError("La cantidad requerida debe ser mayor que 0.")