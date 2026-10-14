"""
Содержимое вкладки «База данных» риббона.
"""
import tkinter as tk

from ..theme import COLORS
from .ribbon_widgets import ribbon_group


def build_db_tab(parent: tk.Widget, app) -> None:
    """Строит содержимое вкладки «База данных»."""
    frame = tk.Frame(parent, bg=COLORS['ribbon_tab_active'])
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    ribbon_group(frame, [
        ("💾 Сохранить проект", app._db_save_stub),
        ("📂 Загрузить проект", app._db_load_stub),
    ])