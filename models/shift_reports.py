# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import base64
import io
from datetime import datetime, timedelta

try:
    import xlsxwriter
    XLSXWRITER_AVAILABLE = True
except ImportError:
    XLSXWRITER_AVAILABLE = False


class ShiftBranchReport(models.TransientModel):
    _name = 'shift.branch.report'
    _description = 'Reporte por Sucursal de Turnos'

    date_from = fields.Date(string='Fecha Desde', required=True, default=fields.Date.today)
    date_to = fields.Date(string='Fecha Hasta', required=True, default=fields.Date.today)
    branch_ids = fields.Many2many('res.partner', string='Sucursales', 
                                  domain="[('is_company', '=', True)]")
    report_type = fields.Selection([
        ('summary', 'Resumen por Sucursal'),
        ('detailed', 'Detallado por Empleado'),
        ('attendance', 'Reporte de Asistencias'),
    ], string='Tipo de Reporte', default='summary', required=True)

    def action_generate_report(self):
        """Generar reporte según el tipo seleccionado"""
        if self.report_type == 'attendance':
            return self.action_view_attendance_report()
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Reporte Generado',
                    'message': f'Reporte de tipo {self.report_type} para el período {self.date_from} - {self.date_to}',
                    'type': 'success',
                    'sticky': False,
                }
            }

    def action_view_attendance_report(self):
        """Vista de reporte de asistencias"""
        domain = [
            ('shift_date', '>=', self.date_from),
            ('shift_date', '<=', self.date_to),
        ]
        if self.branch_ids:
            domain.append(('branch_id', 'in', self.branch_ids.ids))
            
        return {
            'name': 'Reporte de Asistencias',
            'type': 'ir.actions.act_window',
            'res_model': 'work.shift.assignment',
            'view_mode': 'tree',
            'domain': domain,
            'context': {
                'search_default_group_by_date': 1,
                'search_default_group_by_status': 1,
            }
        }

    def action_export_excel(self):
        """Exportar datos básicos a CSV"""
        if not XLSXWRITER_AVAILABLE:
            # Crear CSV básico si no hay xlsxwriter
            return self._export_csv()
        
        try:
            # Crear archivo Excel en memoria
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            
            # Crear hoja simple con datos básicos
            worksheet = workbook.add_worksheet('Reporte de Turnos')
            
            # Headers básicos
            headers = ['Fecha', 'Empleado', 'Sucursal', 'Rol', 'Estado']
            for col, header in enumerate(headers):
                worksheet.write(0, col, header)
            
            # Obtener datos
            domain = [
                ('shift_date', '>=', self.date_from),
                ('shift_date', '<=', self.date_to),
            ]
            if self.branch_ids:
                domain.append(('branch_id', 'in', self.branch_ids.ids))
                
            assignments = self.env['work.shift.assignment'].search(domain, limit=1000)
            
            # Escribir datos
            for row, assignment in enumerate(assignments, 1):
                worksheet.write(row, 0, assignment.shift_date.strftime('%d/%m/%Y') if assignment.shift_date else '')
                worksheet.write(row, 1, assignment.employee_id.name or '')
                worksheet.write(row, 2, assignment.branch_id.name or '')
                worksheet.write(row, 3, assignment.shift_role or '')
                worksheet.write(row, 4, dict(assignment._fields['status'].selection).get(assignment.status, assignment.status))
            
            workbook.close()
            output.seek(0)
            
            # Crear archivo adjunto
            filename = f'Reporte_Turnos_{self.date_from}_{self.date_to}.xlsx'
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(output.read()),
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            })
            
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'new',
            }
            
        except Exception as e:
            raise ValidationError(f"Error al generar Excel: {str(e)}")

    def _export_csv(self):
        """Exportar datos básicos a CSV como alternativa"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Exportación no disponible',
                'message': 'Instala xlsxwriter para habilitar la exportación a Excel: pip install xlsxwriter',
                'type': 'warning',
                'sticky': True,
            }
        }