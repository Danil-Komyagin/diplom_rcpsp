"""
Диалог выбора проекта из БД.
"""
import tkinter as tk
from tkinter import messagebox
from typing import Optional

from ..theme import COLORS
from ..core import storage


def open_projects_dialog(root: tk.Widget, user_id: int) -> Optional[int]:
    """
    Показывает список проектов пользователя.
    Возвращает id выбранного проекта или None, если пользователь отменил.
    """
    dialog = tk.Toplevel(root)
    dialog.title("Мои проекты")
    dialog.geometry("600x450")
    dialog.configure(bg=COLORS['bg'])
    dialog.transient(root)
    dialog.grab_set()

    header = tk.Frame(dialog, bg=COLORS['header'], height=45)
    header.pack(fill=tk.X)
    header.pack_propagate(False)
    tk.Label(
        header, text="📁 Мои проекты",
        font=('Arial', 12, 'bold'),
        bg=COLORS['header'], fg=COLORS['white'],
    ).pack(pady=10)

    # Список проектов
    body = tk.Frame(dialog, bg=COLORS['bg'], padx=15, pady=10)
    body.pack(fill=tk.BOTH, expand=True)

    listbox = tk.Listbox(body, font=('Consolas', 10),
                         bg=COLORS['white'], fg=COLORS['text'],
                         selectbackground=COLORS['primary'],
                         selectforeground=COLORS['white'],
                         relief='solid', bd=1)
    listbox.pack(fill=tk.BOTH, expand=True)

    projects = storage.list_projects(user_id)
    for p in projects:
        listbox.insert(tk.END,
                       f"{p['name']}  ({p['task_count']} задач, "
                       f"обновлён {p['updated_at'][:16]})")

    result = {'project_id': None, 'delete_id': None}

    def do_open():
        sel = listbox.curselection()
        if not sel:
            messagebox.showwarning("Внимание", "Выберите проект.", parent=dialog)
            return
        result['project_id'] = projects[sel[0]]['id']
        dialog.destroy()

    def do_delete():
        sel = listbox.curselection()
        if not sel:
            messagebox.showwarning("Внимание", "Выберите проект.", parent=dialog)
            return
        p = projects[sel[0]]
        if not messagebox.askyesno("Удалить?",
                                   f"Удалить проект '{p['name']}'?",
                                   parent=dialog):
            return
        storage.delete_project(p['id'])
        listbox.delete(sel[0])
        projects.pop(sel[0])

    def do_cancel():
        result['project_id'] = None
        dialog.destroy()

    btn_frame = tk.Frame(dialog, bg=COLORS['bg'], pady=10)
    btn_frame.pack(fill=tk.X)

    tk.Button(btn_frame, text="📂 Открыть", command=do_open,
              bg=COLORS['primary'], fg=COLORS['white'],
              font=('Arial', 10, 'bold'),
              padx=20, pady=6, relief='flat', cursor='hand2').pack(side=tk.LEFT, padx=15)

    tk.Button(btn_frame, text="🗑 Удалить", command=do_delete,
              bg=COLORS['error'], fg=COLORS['white'],
              font=('Arial', 10, 'bold'),
              padx=20, pady=6, relief='flat', cursor='hand2').pack(side=tk.LEFT)

    tk.Button(btn_frame, text="Отмена", command=do_cancel,
              bg=COLORS['menu_bg'], fg=COLORS['text'],
              font=('Arial', 10),
              padx=20, pady=6, relief='flat', cursor='hand2').pack(side=tk.RIGHT, padx=15)

    # Двойной клик = открыть
    listbox.bind('<Double-Button-1>', lambda e: do_open())

    dialog.wait_window()
    return result['project_id']