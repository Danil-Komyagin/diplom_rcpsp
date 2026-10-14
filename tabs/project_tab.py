"""
Содержимое вкладки «Проект» риббона.
"""
import tkinter as tk

from ..theme import COLORS
from .ribbon_widgets import ribbon_group, ribbon_separator


def build_project_tab(parent: tk.Widget, app) -> None:
    """Строит содержимое вкладки «Проект»."""
    frame = tk.Frame(parent, bg=COLORS['ribbon_tab_active'])
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    ribbon_group(frame, [
        ("⚙️ Установить метод", app._set_method_dialog),
    ])
    ribbon_group(frame, [
        ("⚙️ Установить правило", app._set_rule_dialog),
    ])

    ribbon_separator(frame)

    ribbon_group(frame, [
        ("ℹ️ О проекте", app._project_info_stub),
    ])

    ribbon_separator(frame)

    ribbon_group(frame, [
        ("🎲 Загрузить демо", app._load_demo_project),
    ])

    ribbon_separator(frame)

    ribbon_group(frame, [
        ("📊 Сохранить отчёт", app._export_resource_table),
    ])