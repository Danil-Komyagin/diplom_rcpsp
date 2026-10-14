"""
Точка входа в приложение.

Запуск (из родительской папки, где лежит сам пакет):

    python -m diplom_rcpsp

Почему через `-m`, а не `python __main__.py`:
    Внутри проекта используются относительные импорты
    (from .app import App, from ..theme import COLORS и т.д.).
    Такие импорты работают только когда пакет запускается целиком.
    `python -m <пакет>` как раз это и делает.

Если папка называется иначе (не `diplom_rcpsp`), замени имя в команде
на фактическое имя папки.
"""
import tkinter as tk

from .app import App


def run_gui():
    """Создаёт главное окно и запускает event loop."""
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    run_gui()