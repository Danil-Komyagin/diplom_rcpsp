"""
Диалоги для экспорта таблицы ресурсов.

Два диалога:
- ask_start_date   — ввод даты начала проекта (ДД.ММ.ГГГГ),
- ask_export_format — выбор формата выгрузки (CSV / TXT).

Используются в App._export_resource_table.
"""
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from typing import Optional


from ..theme import COLORS


# ============================================================================
# ВВОД ДАТЫ СТАРТА
# ============================================================================
def ask_start_date(root: tk.Widget) -> Optional[datetime]:
    """
    Спрашивает дату начала проекта.

    Возвращает datetime или None, если пользователь отменил ввод.
    По умолчанию подставляется сегодняшняя дата.
    """
    dialog = tk.Toplevel(root)
    dialog.title("Дата начала проекта")
    dialog.geometry("380x200")
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
        text="📅 Дата начала проекта",
        font=('Arial', 12, 'bold'),
        bg=COLORS['header'], fg=COLORS['white'],
    ).pack(pady=10)

    # Тело
    body = tk.Frame(dialog, bg=COLORS['bg'], padx=20, pady=15)
    body.pack(fill=tk.BOTH, expand=True)

    tk.Label(
        body,
        text="Введите дату в формате ДД.ММ.ГГГГ:",
        font=('Arial', 10),
        bg=COLORS['bg'], fg=COLORS['text'],
    ).pack(anchor=tk.W, pady=(0, 8))

    date_entry = tk.Entry(
        body,
        width=20,
        font=('Arial', 12),
        bg=COLORS['white'], fg=COLORS['text'],
        relief='solid', bd=1,
        justify=tk.CENTER,
    )
    date_entry.pack(pady=5, ipady=4)
    date_entry.insert(0, datetime.now().strftime("%d.%m.%Y"))
    date_entry.focus_set()
    date_entry.select_range(0, tk.END)

    result = {'date': None}

    def confirm():
        text = date_entry.get().strip()
        try:
            result['date'] = datetime.strptime(text, "%d.%m.%Y")
            dialog.destroy()
        except ValueError:
            messagebox.showerror(
                "Ошибка",
                "Неверный формат даты.\nИспользуйте ДД.ММ.ГГГГ, например 01.01.2025",
                parent=dialog,
            )

    def cancel():
        result['date'] = None
        dialog.destroy()

    # Кнопки
    btn_frame = tk.Frame(dialog, bg=COLORS['bg'], pady=10)
    btn_frame.pack(fill=tk.X)

    tk.Button(
        btn_frame,
        text="✅ ОК",
        command=confirm,
        bg=COLORS['success'], fg=COLORS['white'],
        font=('Arial', 10, 'bold'),
        padx=20, pady=6, relief='flat', cursor='hand2',
    ).pack(side=tk.LEFT, padx=20)

    tk.Button(
        btn_frame,
        text="❌ Отмена",
        command=cancel,
        bg=COLORS['error'], fg=COLORS['white'],
        font=('Arial', 10, 'bold'),
        padx=20, pady=6, relief='flat', cursor='hand2',
    ).pack(side=tk.LEFT)

    # Enter подтверждает, Esc отменяет
    dialog.bind('<Return>', lambda e: confirm())
    dialog.bind('<Escape>', lambda e: cancel())
    dialog.protocol("WM_DELETE_WINDOW", cancel)

    dialog.wait_window()
    return result['date']


# ============================================================================
# ВЫБОР ФОРМАТА ЭКСПОРТА
# ============================================================================
def ask_export_format(root: tk.Widget, default: str = "csv") -> Optional[str]:
    """
    Спрашивает формат выгрузки.

    Возвращает 'csv' или 'txt' либо None, если пользователь отменил.
    """
    dialog = tk.Toplevel(root)
    dialog.title("Формат выгрузки")
    dialog.geometry("340x220")
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
        text="📄 Формат выгрузки",
        font=('Arial', 12, 'bold'),
        bg=COLORS['header'], fg=COLORS['white'],
    ).pack(pady=10)

    # Тело
    body = tk.Frame(dialog, bg=COLORS['bg'], padx=20, pady=15)
    body.pack(fill=tk.BOTH, expand=True)

    tk.Label(
        body,
        text="Выберите формат файла:",
        font=('Arial', 10, 'bold'),
        bg=COLORS['bg'], fg=COLORS['header'],
    ).pack(anchor=tk.W, pady=(0, 8))

    format_var = tk.StringVar(value=default)

    tk.Radiobutton(
        body,
        text="CSV (для Excel)",
        variable=format_var,
        value="csv",
        font=('Arial', 10),
        bg=COLORS['bg'],
        fg=COLORS['text'],
        activebackground=COLORS['bg'],
        selectcolor=COLORS['white'],
        anchor=tk.W,
        padx=4,
    ).pack(fill=tk.X, pady=2)

    tk.Radiobutton(
        body,
        text="TXT (для Word)",
        variable=format_var,
        value="txt",
        font=('Arial', 10),
        bg=COLORS['bg'],
        fg=COLORS['text'],
        activebackground=COLORS['bg'],
        selectcolor=COLORS['white'],
        anchor=tk.W,
        padx=4,
    ).pack(fill=tk.X, pady=2)

    result = {'value': None}

    def apply():
        result['value'] = format_var.get()
        dialog.destroy()

    def cancel():
        result['value'] = None
        dialog.destroy()

    # Кнопки
    btn_frame = tk.Frame(dialog, bg=COLORS['bg'], pady=10)
    btn_frame.pack(fill=tk.X)

    tk.Button(
        btn_frame,
        text="✅ Выгрузить",
        command=apply,
        bg=COLORS['primary'], fg=COLORS['white'],
        font=('Arial', 10, 'bold'),
        padx=20, pady=6, relief='flat', cursor='hand2',
    ).pack(side=tk.LEFT, padx=20)

    tk.Button(
        btn_frame,
        text="❌ Отмена",
        command=cancel,
        bg=COLORS['menu_bg'], fg=COLORS['text'],
        font=('Arial', 10),
        padx=20, pady=6, relief='flat', cursor='hand2',
    ).pack(side=tk.LEFT)

    dialog.bind('<Escape>', lambda e: cancel())
    dialog.protocol("WM_DELETE_WINDOW", cancel)

    dialog.wait_window()
    return result['value']