"""
Общие виджеты для вкладок риббона.

Все вкладки используют одну функцию ribbon_button и один хелпер
ribbon_group — так стиль кнопок и отступы гарантированно совпадают.

Отступы вынесены в константы: если нужно изменить промежутки —
меняй только эти две строки.
"""
import tkinter as tk

from ..theme import COLORS


# Единые отступы для всего риббона
GROUP_PADX = 4          # отступ от группы до её соседей
BUTTON_PADX = 7         # отступ между кнопками внутри группы
SEPARATOR_PADX = 0      # отступ вокруг вертикальной полоски


def ribbon_button(parent: tk.Widget, text: str, command) -> tk.Button:
    """Кнопка риббона — единый стиль для всех вкладок."""
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=COLORS['menu_bg'],
        fg=COLORS['text'],
        font=('Arial', 9),
        padx=12, pady=6,
        relief='groove',
        bd=1,
        cursor='hand2',
        activebackground=COLORS['menu_hover'],
    )


def ribbon_group(parent: tk.Widget, buttons: list) -> tk.Frame:
    """
    Строит группу кнопок риббона.

    buttons — список кортежей (text, command).
    Отступы групп и кнопок — из констант, чтобы всё было одинаково.
    """
    group = tk.Frame(parent, bg=COLORS['ribbon_tab_active'])
    group.pack(side=tk.LEFT, padx=GROUP_PADX)

    for i, (text, command) in enumerate(buttons):
        # У первой кнопки левый padx не нужен — его задаёт группа
        left_pad = 0 if i == 0 else BUTTON_PADX
        ribbon_button(group, text, command).pack(
            side=tk.LEFT, padx=(left_pad, 0)
        )

    return group


def ribbon_separator(parent: tk.Widget) -> tk.Frame:
    """Тонкая вертикальная полоска между группами."""
    return None
