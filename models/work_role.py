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
    
    # Relación con habilidades (lo que requiere este rol)
    skill_ids = fields.Many2many(
        'hr.skill',
        string='Habilidades Requeridas',
        help="Las habilidades que debe tener un empleado para este rol"
    )
    
    # Campo computado para mostrar cuántos empleados pueden hacer este rol
    available_employees_count = fields.Integer(
        string='Empleados Disponibles',
        compute='_compute_available_employees_count',
        help="Cuántos empleados tienen las habilidades para este rol"
    )

    @api.depends('skill_ids')
    def _compute_available_employees_count(self):
        """Calcular cuántos empleados pueden realizar este rol"""
        for role in self:
            if role.skill_ids:
                # Buscar empleados que tengan TODAS las habilidades requeridas
                employees_with_all_skills = self.env['hr.employee'].search([
                    ('skill_ids', 'in', role.skill_ids.ids)
                ])
                
                # Filtrar empleados que tengan TODAS las habilidades (no solo algunas)
                qualified_employees = employees_with_all_skills.filtered(
                    lambda emp: all(skill in emp.skill_ids for skill in role.skill_ids)
                )
                role.available_employees_count = len(qualified_employees)
            else:
                # Si no requiere habilidades específicas, todos los empleados pueden hacerlo
                role.available_employees_count = self.env['hr.employee'].search_count([])

    def action_view_qualified_employees(self):
        """Acción para ver los empleados que pueden realizar este rol"""
        if not self.skill_ids:
            # Si no requiere habilidades específicas, mostrar todos
            domain = []
        else:
            # Buscar empleados con todas las habilidades requeridas
            employees_with_all_skills = self.env['hr.employee'].search([
                ('skill_ids', 'in', self.skill_ids.ids)
            ])
            qualified_employees = employees_with_all_skills.filtered(
                lambda emp: all(skill in emp.skill_ids for skill in self.skill_ids)
            )
            domain = [('id', 'in', qualified_employees.ids)]

        return {
            'name': f'Empleados Calificados para {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {'default_skill_ids': [(6, 0, self.skill_ids.ids)]}
        }