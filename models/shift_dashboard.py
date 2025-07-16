# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta, date
from odoo.exceptions import UserError


class ShiftDashboard(models.Model):
    _name = 'shift.dashboard'
    _description = 'Dashboard de Turnos'
    _auto = False

    # Campos básicos para el dashboard
    name = fields.Char(string='Dashboard', default='Dashboard de Turnos')

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
            'context': {'default_date': fields.Date.today()}
        }

    def action_auto_assign(self):
        """Abrir asignación automática - Simplificado"""
        try:
            # Verificar si el modelo existe
            if 'shift.auto.assign.wizard' in self.env:
                return {
                    'name': 'Asignación Automática',
                    'type': 'ir.actions.act_window',
                    'res_model': 'shift.auto.assign.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                }
            else:
                raise UserError("La funcionalidad de asignación automática no está disponible.")
        except Exception as e:
            # Fallback: Ir a la vista de asignaciones
            return {
                'name': 'Asignaciones de Turnos',
                'type': 'ir.actions.act_window',
                'res_model': 'work.shift.assignment',
                'view_mode': 'tree,form',
                'target': 'current',
            }

    def action_generate_report(self):
        """Generar reporte - Simplificado"""
        try:
            # Verificar si el modelo existe
            if 'shift.branch.report' in self.env:
                return {
                    'name': 'Generar Reporte',
                    'type': 'ir.actions.act_window',
                    'res_model': 'shift.branch.report',
                    'view_mode': 'form',
                    'target': 'new',
                }
            else:
                raise UserError("La funcionalidad de reportes no está disponible.")
        except Exception as e:
            # Fallback: Ir a vista de turnos
            return {
                'name': 'Turnos Programados',
                'type': 'ir.actions.act_window',
                'res_model': 'work.shift.schedule',
                'view_mode': 'tree,form',
                'target': 'current',
            }

    def action_open_config(self):
        """Abrir configuración - Simplificado"""
        try:
            # Verificar si el modelo existe
            if 'shift.planning.config' in self.env:
                return {
                    'name': 'Configuración de Turnos',
                    'type': 'ir.actions.act_window',
                    'res_model': 'shift.planning.config',
                    'view_mode': 'form',
                    'target': 'new',
                }
            else:
                raise UserError("La funcionalidad de configuración no está disponible.")
        except Exception as e:
            # Fallback: Ir a configuración general
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Configuración',
                    'message': 'La configuración avanzada estará disponible próximamente.',
                    'type': 'info',
                    'sticky': False,
                }
            }

    def action_view_shifts(self):
        """Ver turnos programados"""
        return {
            'name': 'Turnos Programados',
            'type': 'ir.actions.act_window',
            'res_model': 'work.shift.schedule',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_view_assignments(self):
        """Ver asignaciones"""
        return {
            'name': 'Asignaciones de Turnos',
            'type': 'ir.actions.act_window',
            'res_model': 'work.shift.assignment',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_view_employees(self):
        """Ver empleados"""
        return {
            'name': 'Empleados',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_view_roles(self):
        """Ver roles de trabajo"""
        return {
            'name': 'Roles de Trabajo',
            'type': 'ir.actions.act_window',
            'res_model': 'work.role',
            'view_mode': 'tree,form',
            'target': 'current',
        }

    @api.model
    def get_dashboard_data(self):
        """Obtener datos del dashboard de forma segura"""
        try:
            today = date.today()
            
            # Datos básicos
            shifts_today = self.env['work.shift.schedule'].search_count([
                ('date', '=', today),
                ('state', '=', 'planned')
            ])
            
            assignments_today = self.env['work.shift.assignment'].search_count([
                ('shift_date', '=', today)
            ])
            
            active_employees = self.env['hr.employee'].search_count([
                ('active', '=', True)
            ])
            
            active_roles = self.env['work.role'].search_count([
                ('active', '=', True)
            ])
            
            return {
                'today': {
                    'shifts': shifts_today,
                    'assignments': assignments_today,
                    'employees': active_employees,
                    'roles': active_roles,
                },
                'status': 'success'
            }
        except Exception as e:
            return {
                'error': str(e),
                'status': 'error'
            }