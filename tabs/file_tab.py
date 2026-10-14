"""
Содержимое вкладки «Файл» риббона.
"""
import tkinter as tk

from ..theme import COLORS
from .ribbon_widgets import ribbon_group


def build_file_tab(parent: tk.Widget, app) -> None:
    """Строит содержимое вкладки «Файл»."""
    frame = tk.Frame(parent, bg=COLORS['ribbon_tab_active'])
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    ribbon_group(frame, [
        ("💾 Сохранить JSON", app._save),
        ("📂 Загрузить JSON", app._load),
    ])