"""
Ядро приложения: модели, планировщики, отчёты, визуализация.

Здесь собраны все публичные сущности ядра. GUI импортирует их отсюда:

    from ..core import Task, Project, create_scheduler
    from ..core import plot_gantt, plot_resource_utilization
    from ..core import load_project_from_json, save_project_to_json
    from ..core import export_resource_table_csv, export_resource_table_txt

Внутренние детали (например, `_transitive_successors_duration`) сюда
не попадают — они доступны только из своих модулей.
"""
# Модели данных
from .models import Task, Project

# Планировщики
from .schedulers import (
    create_scheduler,
    SerialScheduler,
    ParallelScheduler,
    PRIORITY_RULES,
    Schedule,
)

# Генетический алгоритм (нужен отдельно, т.к. фабрика его импортирует)
from .genetic import GeneticScheduler

# Утилиты
from .utils import (
    save_project_to_json,
    load_project_from_json,
    create_test_project,
)

# Отчёты
from .report import (
    export_resource_table_csv,
    export_resource_table_txt,
)

# Визуализация
from .visualizer import (
    plot_gantt,
    plot_resource_utilization,
)


__all__ = [
    # Модели
    'Task', 'Project',
    # Планировщики
    'create_scheduler', 'SerialScheduler', 'ParallelScheduler', 'BranchAndBoundScheduler',
    'GeneticScheduler', 'PRIORITY_RULES', 'Schedule',
    # Утилиты
    'save_project_to_json', 'load_project_from_json', 'create_test_project',
    # Отчёты
    'export_resource_table_csv', 'export_resource_table_txt',
    # Визуализация
    'plot_gantt', 'plot_resource_utilization',
]