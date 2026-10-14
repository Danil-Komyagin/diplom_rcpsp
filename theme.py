"""
Цветовая схема и стили ttk для приложения.

Этот модуль не зависит ни от чего внутри проекта — только от tkinter.
Его импортируют все остальные модули.
"""
from tkinter import ttk


# ============================================================================
# ЦВЕТОВАЯ СХЕМА (стиль Word 2007 + Excel)
# ============================================================================
COLORS = {
    'white': '#ffffff',
    'bg': '#f0f8ff',
    'bg_light': '#e6f2ff',
    'primary': '#3498db',
    'primary_dark': '#2980b9',
    'primary_light': '#aed6f1',
    'header': '#2c3e50',
    'text': '#2c3e50',
    'text_light': '#5d6d7e',
    'success': '#27ae60',
    'warning': '#f39c12',
    'error': '#e74c3c',
    'border': '#aed6f1',
    'input_bg': '#ffffff',
    'ribbon_bg': '#d6e6f5',
    'ribbon_tab_active': '#ffffff',
    'ribbon_tab_inactive': '#c5d9ea',
    'ribbon_border': '#7ba4c7',
    'menu_bg': '#f0f0f0',
    'menu_hover': '#cce4f7',
    # Excel-стиль
    'excel_header_bg': '#217346',
    'excel_header_fg': '#ffffff',
    'excel_row_label_bg': '#e8f5e9',
    'excel_cell_bg': '#ffffff',
    'excel_cell_border': '#a0a0a0',
    'excel_active_border': '#217346',
    # Кнопка "Сохранить" — светло-голубая
    'save_btn_bg': '#d6eaf8',
    'save_btn_fg': '#1b4f72',
    'save_btn_hover': '#aed6f1',
    'save_btn_border': '#85c1e9',
}


def setup_styles():
    """Настраивает стили ttk (общая тема для всего приложения)."""
    style = ttk.Style()
    style.theme_use('clam')

    style.configure('TFrame', background=COLORS['bg'])
    style.configure(
        'TLabelFrame',
        background=COLORS['bg'],
        foreground=COLORS['header'],
        borderwidth=2,
        relief='groove',
    )
    style.configure(
        'TLabelFrame.Label',
        background=COLORS['bg'],
        foreground=COLORS['primary_dark'],
        font=('Arial', 10, 'bold'),
    )
    style.configure(
        'TLabel',
        background=COLORS['bg'],
        foreground=COLORS['text'],
        font=('Arial', 10),
    )
    style.configure(
        'TButton',
        background=COLORS['primary'],
        foreground=COLORS['white'],
        font=('Arial', 10, 'bold'),
        borderwidth=0,
    )
    style.map('TButton', background=[('active', COLORS['primary_dark'])])
    style.configure(
        'TProgressbar',
        background=COLORS['primary'],
        troughcolor=COLORS['bg_light'],
        borderwidth=1,
    )