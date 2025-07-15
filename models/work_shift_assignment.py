# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class WorkShiftAssignment(models.Model):
    _name = 'work.shift.assignment'
    _description = 'Asignacion de Empleado a Turno'
    _rec_name = 'employee_id'

    shift_id = fields.Many2one(
        'work.shift.schedule', 
        string='Turno Programado', 
        required=True, 
        ondelete='cascade'
    )
    employee_id = fields.Many2one(
        'hr.employee', 
        string='Empleado', 
        required=True
    )
    status = fields.Selection([
        ('assigned', 'Asignado'),
        ('confirmed', 'Confirmado'),
        ('present', 'Asistió'),
        ('absent', 'Ausente'),
        ('replaced', 'Reemplazado'),
        ('cancelled', 'Cancelado'),
    ], string='Estatus', default='assigned')

    # Campos relacionados para facilitar reportes
    shift_date = fields.Date(related='shift_id.date', string='Fecha', store=True)
    shift_role = fields.Char(related='shift_id.role', string='Rol', store=True)
    branch_id = fields.Many2one(related='shift_id.branch_id', string='Sucursal', store=True)
    shift_hours = fields.Char(string='Horario', compute='_compute_shift_hours', store=True)
    notification_sent = fields.Boolean(string='Notificación Enviada', default=False)
    confirmed_date = fields.Datetime(string='Fecha de Confirmación')
    employee_email = fields.Char(related='employee_id.work_email', string='Email del Empleado')

    @api.depends('shift_id.hour_start', 'shift_id.hour_end')
    def _compute_shift_hours(self):
        for record in self:
            if record.shift_id:
                start_time = f"{int(record.shift_id.hour_start):02d}:{int((record.shift_id.hour_start % 1) * 60):02d}"
                end_time = f"{int(record.shift_id.hour_end):02d}:{int((record.shift_id.hour_end % 1) * 60):02d}"
                record.shift_hours = f"{start_time} - {end_time}"
            else:
                record.shift_hours = ""

    def action_mark_present(self):
        """Marcar empleado como presente"""
        self.status = 'present'
        return True

    def action_mark_absent(self):
        """Marcar empleado como ausente"""
        self.status = 'absent'
        return True

    def action_mark_replaced(self):
        """Marcar empleado como reemplazado"""
        self.status = 'replaced'
        return True

    def action_confirm_assignment(self):
        """Confirmar asignación del empleado"""
        self.status = 'confirmed'
        self.confirmed_date = fields.Datetime.now()
        return True

    def action_cancel_assignment(self):
        """Cancelar asignación del empleado"""
        self.status = 'cancelled'
        return True

    def action_send_notification(self):
        """Enviar notificación por email al empleado"""
        if not self.employee_email:
            raise ValidationError(
                f"El empleado {self.employee_id.name} no tiene email configurado."
            )
        
        # Obtener template de email
        template = self.env.ref('shift_planning.email_template_shift_assignment', raise_if_not_found=False)
        if not template:
            raise ValidationError("No se encontró el template de email para notificaciones.")
        
        # Enviar email
        template.send_mail(self.id, force_send=True)
        self.notification_sent = True
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Notificación Enviada',
                'message': f'Se envió notificación a {self.employee_id.name} ({self.employee_email})',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_resend_notification(self):
        """Reenviar notificación por email"""
        self.notification_sent = False
        return self.action_send_notification()

    @api.constrains('shift_id', 'employee_id')
    def _check_unique_assignment(self):
        for record in self:
            if record.status == 'cancelled':
                continue  # No validar asignaciones canceladas
                
            existing = self.search([
                ('shift_id', '=', record.shift_id.id),
                ('employee_id', '=', record.employee_id.id),
                ('status', '!=', 'cancelled'),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError(
                    f"El empleado {record.employee_id.name} ya está asignado a este turno."
                )

    @api.constrains('shift_id')
    def _check_shift_capacity(self):
        for record in self:
            # Contar asignaciones activas (no canceladas) para este turno
            current_assignments = self.search_count([
                ('shift_id', '=', record.shift_id.id),
                ('status', '!=', 'cancelled')
            ])
            
            if current_assignments > record.shift_id.quantity_required:
                raise ValidationError(
                    f"No se pueden asignar más empleados a este turno. "
                    f"Máximo permitido: {record.shift_id.quantity_required}, "
                    f"Asignados actualmente: {current_assignments}"
                )

    @api.constrains('shift_id', 'employee_id')
    def _check_overlapping_shifts(self):
        """Validar que un empleado no tenga turnos traslapados"""
        for record in self:
            if record.status == 'cancelled':
                continue  # No validar asignaciones canceladas
                
            # Buscar otros turnos activos del mismo empleado en la misma fecha
            overlapping_assignments = self.search([
                ('employee_id', '=', record.employee_id.id),
                ('shift_date', '=', record.shift_date),
                ('status', '!=', 'cancelled'),
                ('id', '!=', record.id)
            ])
            
            for assignment in overlapping_assignments:
                # Verificar si los horarios se traslapan
                shift1_start = record.shift_id.hour_start
                shift1_end = record.shift_id.hour_end
                shift2_start = assignment.shift_id.hour_start
                shift2_end = assignment.shift_id.hour_end
                
                # Lógica de traslape: dos turnos se traslapan si uno empieza antes de que termine el otro
                if (shift1_start < shift2_end and shift1_end > shift2_start):
                    raise ValidationError(
                        f"El empleado {record.employee_id.name} ya tiene un turno asignado "
                        f"que se traslapa con este horario.\n"
                        f"Turno actual: {shift1_start:.2f} - {shift1_end:.2f}\n"
                        f"Turno existente: {shift2_start:.2f} - {shift2_end:.2f}"
                    )