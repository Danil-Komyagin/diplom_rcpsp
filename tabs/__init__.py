"""Вкладки риббона."""
from .file_tab import build_file_tab
from .project_tab import build_project_tab
from .db_tab import build_db_tab
from .ribbon_widgets import ribbon_button, ribbon_group, ribbon_separator


__all__ = [
    'build_file_tab',
    'build_project_tab',
    'build_db_tab',
    'ribbon_button',
    'ribbon_group',
    'ribbon_separator',
]