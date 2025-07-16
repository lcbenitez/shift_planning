# -*- coding: utf-8 -*-
# Importar todos los modelos del módulo de planificación de turnos

# Modelos base
from . import work_role
from . import work_shift_schedule
from . import work_shift_assignment

# Modelos de reportes
from . import shift_reports

# Nuevos modelos avanzados
from . import shift_config
from . import employee_preferences
from . import shift_auto_assign_wizard
from . import shift_dashboard