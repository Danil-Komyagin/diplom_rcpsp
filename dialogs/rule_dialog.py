"""
Диалог выбора правила приоритета задач.

Правила (см. core.schedulers.PRIORITY_RULES):
- LPT  — Longest Processing Time (длинные задачи — первыми)
- SPT  — Shortest Processing Time (короткие задачи — первыми)
- MTS  — Most Total Successors (много потомков — выше приоритет)
- GRPW — Greatest Rank Positional Weight (длительность + потомки)
- MS   — Most Resources (больше ресурсов — выше приоритет)

Используется в App._set_rule_dialog. Открывается модально,
возвращает выбранное правило или None, если пользователь отменил.
"""
import tkinter as tk
from typing import Optional


from ..theme import COLORS


# Единый источник истины: код правила + человекочитаемая подпись.
AVAILABLE_RULES = [
    ("LPT",  "LPT — длинные задачи первыми"),
    ("SPT",  "SPT — короткие задачи первыми"),
    ("MTS",  "MTS — максимум потомков"),
    ("GRPW", "GRPW — вес задачи + потомки"),
    ("MS",   "MS  — максимум ресурсов"),
]


def open_rule_dialog(root: tk.Widget, current_value: str = "LPT") -> Optional[str]:
    """
    Открывает модальный диалог выбора правила приоритета.

    root — родительское окно.
    current_value — текущее выбранное правило (отмечается в радиокнопках).

    Возвращает код выбранного правила ('LPT', 'SPT', ...) или None,
    если пользователь закрыл окно без выбора.
    """
    dialog = tk.Toplevel(root)
    dialog.title("Установить правило")
    dialog.geometry("380x280")
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
        text="⚙️ Правило приоритета",
        font=('Arial', 12, 'bold'),
        bg=COLORS['header'], fg=COLORS['white'],
    ).pack(pady=10)

    # Основная часть
    body = tk.Frame(dialog, bg=COLORS['bg'], padx=20, pady=15)
    body.pack(fill=tk.BOTH, expand=True)

    tk.Label(
        body,
        text="Выберите правило сортировки задач:",
        font=('Arial', 10, 'bold'),
        bg=COLORS['bg'], fg=COLORS['header'],
    ).pack(anchor=tk.W, pady=(0, 8))

    rule_var = tk.StringVar(value=current_value)

    for value, label in AVAILABLE_RULES:
        tk.Radiobutton(
            body,
            text=label,
            variable=rule_var,
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
        result['value'] = rule_var.get()
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

    dialog.protocol("WM_DELETE_WINDOW", cancel)

    dialog.wait_window()
    return result['value']