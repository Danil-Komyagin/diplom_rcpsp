"""
Диалог входа и регистрации.
"""
import tkinter as tk
from tkinter import messagebox
from typing import Optional

from ..theme import COLORS
from ..core import storage


def open_login_dialog(root: tk.Widget) -> Optional[int]:
    """
    Открывает диалог входа/регистрации.
    Возвращает id пользователя или None, если пользователь закрыл окно.
    """
    dialog = tk.Toplevel(root)
    dialog.title("Вход в систему")
    dialog.geometry("380x320")
    dialog.configure(bg=COLORS['bg'])
    dialog.transient(root)
    dialog.grab_set()
    dialog.resizable(False, False)

    header = tk.Frame(dialog, bg=COLORS['header'], height=50)
    header.pack(fill=tk.X)
    header.pack_propagate(False)
    tk.Label(
        header, text="🔐 Вход в систему",
        font=('Arial', 13, 'bold'),
        bg=COLORS['header'], fg=COLORS['white'],
    ).pack(pady=12)

    body = tk.Frame(dialog, bg=COLORS['bg'], padx=20, pady=15)
    body.pack(fill=tk.BOTH, expand=True)

    # Логин
    tk.Label(body, text="Логин:", font=('Arial', 10, 'bold'),
             bg=COLORS['bg'], fg=COLORS['header']).pack(anchor=tk.W, pady=(5, 2))
    username_entry = tk.Entry(body, font=('Arial', 11),
                              bg=COLORS['white'], fg=COLORS['text'],
                              relief='solid', bd=1)
    username_entry.pack(fill=tk.X, ipady=4)

    # Пароль
    tk.Label(body, text="Пароль:", font=('Arial', 10, 'bold'),
             bg=COLORS['bg'], fg=COLORS['header']).pack(anchor=tk.W, pady=(10, 2))
    password_entry = tk.Entry(body, font=('Arial', 11), show='*',
                              bg=COLORS['white'], fg=COLORS['text'],
                              relief='solid', bd=1)
    password_entry.pack(fill=tk.X, ipady=4)

    result = {'user_id': None}

    def do_login():
        username = username_entry.get().strip()
        password = password_entry.get()
        if not username or not password:
            messagebox.showwarning("Внимание", "Введите логин и пароль.",
                                   parent=dialog)
            return
        uid = storage.authenticate_user(username, password)
        if uid is None:
            messagebox.showerror("Ошибка", "Неверный логин или пароль.",
                                 parent=dialog)
            return
        result['user_id'] = uid
        dialog.destroy()

    def do_register():
        username = username_entry.get().strip()
        password = password_entry.get()
        if not username or not password:
            messagebox.showwarning("Внимание", "Введите логин и пароль.",
                                   parent=dialog)
            return
        if len(password) < 4:
            messagebox.showwarning("Внимание", "Пароль должен быть не короче 4 символов.",
                                   parent=dialog)
            return
        uid = storage.register_user(username, password)
        if uid is None:
            messagebox.showerror("Ошибка",
                                 f"Логин '{username}' уже занят.",
                                 parent=dialog)
            return
        messagebox.showinfo("Успех", f"Пользователь '{username}' зарегистрирован.",
                            parent=dialog)
        result['user_id'] = uid
        dialog.destroy()

    def do_cancel():
        result['user_id'] = None
        dialog.destroy()

    btn_frame = tk.Frame(dialog, bg=COLORS['bg'], pady=15)
    btn_frame.pack(fill=tk.X)

    tk.Button(btn_frame, text="Войти", command=do_login,
              bg=COLORS['primary'], fg=COLORS['white'],
              font=('Arial', 10, 'bold'),
              padx=20, pady=6, relief='flat', cursor='hand2').pack(side=tk.LEFT, padx=20)

    tk.Button(btn_frame, text="Регистрация", command=do_register,
              bg=COLORS['success'], fg=COLORS['white'],
              font=('Arial', 10, 'bold'),
              padx=20, pady=6, relief='flat', cursor='hand2').pack(side=tk.LEFT)

    tk.Button(btn_frame, text="Отмена", command=do_cancel,
              bg=COLORS['menu_bg'], fg=COLORS['text'],
              font=('Arial', 10),
              padx=20, pady=6, relief='flat', cursor='hand2').pack(side=tk.RIGHT, padx=20)

    # Enter = Войти, Esc = Отмена
    dialog.bind('<Return>', lambda e: do_login())
    dialog.bind('<Escape>', lambda e: do_cancel())
    dialog.protocol("WM_DELETE_WINDOW", do_cancel)

    username_entry.focus_set()

    dialog.wait_window()
    return result['user_id']