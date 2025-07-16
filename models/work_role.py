# -*- coding: utf-8 -*-
from odoo import models, fields, api


class WorkRole(models.Model):
    _name = 'work.role'
    _description = 'Roles de Trabajo'
    _order = 'name'

    name = fields.Char(
        string='Nombre del Rol', 
        required=True,
        help="Ejemplo: Mesero, Barista, Cocinero Plancha"
    )
    
    description = fields.Text(
        string='Descripción',
        help="Describe las responsabilidades de este rol"
    )
    
    active = fields.Boolean(
        string='Activo', 
        default=True,
        help="Si está inactivo, no aparecerá en las selecciones"
    )
    
    # Campo computado para mostrar cuántos empleados pueden hacer este rol
    available_employees_count = fields.Integer(
        string='Empleados Disponibles',
        compute='_compute_available_employees_count',
        help="Cuántos empleados activos hay en el sistema"
    )

    @api.depends('name')
    def _compute_available_employees_count(self):
        """Calcular cuántos empleados están disponibles"""
        for role in self:
            # Simplificado: contar todos los empleados activos
            role.available_employees_count = self.env['hr.employee'].search_count([
                ('active', '=', True)
            ])

    def action_view_qualified_employees(self):
        """Acción para ver los empleados activos"""
        return {
            'name': f'Empleados Disponibles para {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'tree,form',
            'domain': [('active', '=', True)],
            'context': {'default_active': True}
        }