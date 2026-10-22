"""
Содержимое вкладки «База данных» риббона.

Кнопки:
- 🔐 Войти / 🚪 Выйти — авторизация,
- 💾 Сохранить проект — требует входа,
- 📂 Загрузить проект — требует входа.
"""
import tkinter as tk

from ..theme import COLORS
from .ribbon_widgets import ribbon_group


def build_db_tab(parent: tk.Widget, app) -> None:
    """Строит содержимое вкладки «База данных»."""
    frame = tk.Frame(parent, bg=COLORS['ribbon_tab_active'])
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # --- Группа «Аккаунт» ---
    user_label = "Войти" if app.user_id is None else "Выйти"
    user_command = app._db_login if app.user_id is None else app._db_logout
    ribbon_group(frame, [
        (f"🔐 {user_label}" if app.user_id is None else f"🚪 {user_label}",
         user_command),
    ])

    # --- Группа «Проекты в БД» ---
    ribbon_group(frame, [
        ("💾 Сохранить проект", app._db_save_stub),
        ("📂 Загрузить проект", app._db_load_stub),
    ])

    # Если пользователь вошёл — показываем его имя
    if app.user_id is not None:
        try:
            from ..core import storage
            username = storage.get_username(app.user_id)
            if username:
                info = tk.Label(
                    frame,
                    text=f"👤 {username}",
                    font=('Arial', 10, 'bold'),
                    bg=COLORS['ribbon_tab_active'],
                    fg=COLORS['success'],
                )
                info.pack(side=tk.LEFT, padx=10)
        except Exception:
            pass