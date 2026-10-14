"""
Модальные диалоги приложения.

Реэкспорты, чтобы в app.py можно было писать:

    from .dialogs import (
        open_method_dialog, open_rule_dialog,
        ask_start_date, ask_export_format,
    )
"""
from .method_dialog import open_method_dialog, AVAILABLE_METHODS
from .rule_dialog import open_rule_dialog, AVAILABLE_RULES
from .export_dialog import ask_start_date, ask_export_format


__all__ = [
    'open_method_dialog',
    'open_rule_dialog',
    'ask_start_date',
    'ask_export_format',
    'AVAILABLE_METHODS',
    'AVAILABLE_RULES',
]