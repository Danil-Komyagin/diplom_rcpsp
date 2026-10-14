"""
Диалог выбора метода планирования.

Методы:
- parallel — параллельный SGS,
- serial   — последовательный SGS,
- genetic  — генетический алгоритм,
- bnb      — точный метод Branch and Bound.

Используется в App._set_method_dialog. Открывается модально,
возвращает выбранное значение или None, если пользователь отменил.
"""
import tkinter as tk
from typing import Optional


from ..theme import COLORS


AVAILABLE_METHODS = [
    ("parallel", "Параллельный SGS"),
    ("serial",   "Последовательный SGS"),
    ("genetic",  "Генетический алгоритм"),
    ("bnb",      "Branch and Bound (точный)"),
]


def open_method_dialog(root: tk.Widget, current_value: str = "parallel") -> Optional[str]:
    """
    Открывает модальный диалог выбора метода.

    root — родительское окно.
    current_value — текущий выбранный метод.

    Возвращает код метода или None, если пользователь отменил.
    """
    dialog = tk.Toplevel(root)
    dialog.title("Установить метод")
    dialog.geometry("360x260")
    dialog.configure(bg=COLORS['bg'])
    dialog.transient(root)
    dialog.grab_set()
    dialog.resizable(False, False)

    # Шапка
    header = tk.Frame(dialog, bg=COLORS['header'], height=45)
    header.pack(fill=tk.X)
    header.pack_propagate(False)
    tk.Label(
        header,
        text="⚙️ Метод планирования",
        font=('Arial', 12, 'bold'),
        bg=COLORS['header'], fg=COLORS['white'],
    ).pack(pady=10)

    # Основная часть
    body = tk.Frame(dialog, bg=COLORS['bg'], padx=20, pady=15)
    body.pack(fill=tk.BOTH, expand=True)

    tk.Label(
        body,
        text="Выберите метод:",
        font=('Arial', 10, 'bold'),
        bg=COLORS['bg'], fg=COLORS['header'],
    ).pack(anchor=tk.W, pady=(0, 8))

    method_var = tk.StringVar(value=current_value)

    for value, label in AVAILABLE_METHODS:
        tk.Radiobutton(
            body,
            text=label,
            variable=method_var,
            value=value,
            font=('Arial', 10),
            bg=COLORS['bg'],
            fg=COLORS['text'],
            activebackground=COLORS['bg'],
            selectcolor=COLORS['white'],
            anchor=tk.W,
            padx=4,
        ).pack(fill=tk.X, pady=2)

    # Результат и кнопки
    result = {'value': None}

    def apply():
        result['value'] = method_var.get()
        dialog.destroy()

    def cancel():
        result['value'] = None
        dialog.destroy()

    btn_frame = tk.Frame(dialog, bg=COLORS['bg'], pady=10)
    btn_frame.pack(fill=tk.X)

    tk.Button(
        btn_frame,
        text="OK",
        command=apply,
        bg=COLORS['primary'], fg=COLORS['white'],
        font=('Arial', 10, 'bold'),
        padx=20, pady=6, relief='flat', cursor='hand2',
    ).pack(side=tk.LEFT, padx=20)

    tk.Button(
        btn_frame,
        text="Отмена",
        command=cancel,
        bg=COLORS['menu_bg'], fg=COLORS['text'],
        font=('Arial', 10),
        padx=20, pady=6, relief='flat', cursor='hand2',
    ).pack(side=tk.LEFT)

    # Enter = OK, Esc = Отмена, крестик = Отмена
    dialog.bind('<Return>', lambda e: apply())
    dialog.bind('<Escape>', lambda e: cancel())
    dialog.protocol("WM_DELETE_WINDOW", cancel)

    dialog.wait_window()
    return result['value']