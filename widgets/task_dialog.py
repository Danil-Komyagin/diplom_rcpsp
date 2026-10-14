"""
Модальный диалог для добавления одной задачи.

Используется, если нужно быстро добавить задачу без редактирования таблицы.
В текущей версии GUI не вызывается, но сохранён как вспомогательный инструмент.

Пример:
    dialog = AddTaskDialog(root, resource_limits={'R1': 10, 'R2': 5})
    result = dialog.result
    if result:
        print(result['name'], result['duration'], result['resources'], result['deps'])
"""
import tkinter as tk
from tkinter import messagebox
from typing import Dict, Optional


from ..theme import COLORS


class AddTaskDialog:
    """
    Модальное окно добавления задачи.

    Атрибут result после закрытия:
        None — пользователь отменил,
        dict — {'name': str, 'duration': int, 'resources': {name: int}, 'deps': [int]}.
    """

    def __init__(self, parent: tk.Widget, resource_limits: Dict[str, int]):
        """
        parent — родительское окно.
        resource_limits — {имя_ресурса: лимит}. Используется, чтобы:
            - показать пользователю максимум по каждому ресурсу,
            - сформировать список полей ввода ресурсов.
        """
        self.parent = parent
        self.resource_limits = resource_limits
        self.result: Optional[dict] = None

        # --- Создаём окно ---
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("➕ Добавление задачи")
        self.dialog.geometry("550x550")
        self.dialog.configure(bg=COLORS['bg'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)

        # --- Шапка ---
        header = tk.Frame(self.dialog, bg=COLORS['header'], height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(
            header,
            text="➕ Добавление задачи",
            font=('Arial', 14, 'bold'),
            bg=COLORS['header'],
            fg=COLORS['white'],
        ).pack(pady=12)

        # --- Основная часть ---
        main = tk.Frame(self.dialog, bg=COLORS['bg'], padx=20, pady=15)
        main.pack(fill=tk.BOTH, expand=True)

        # Название
        tk.Label(
            main,
            text="Название задачи:",
            font=('Arial', 10, 'bold'),
            bg=COLORS['bg'], fg=COLORS['header'],
        ).grid(row=0, column=0, sticky=tk.W, pady=5)

        self.name_entry = tk.Entry(
            main, width=35, font=('Arial', 10),
            bg=COLORS['white'], fg=COLORS['text'],
            relief='solid', bd=1,
        )
        self.name_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=10)

        # Длительность
        tk.Label(
            main,
            text="Длительность (дни):",
            font=('Arial', 10, 'bold'),
            bg=COLORS['bg'], fg=COLORS['header'],
        ).grid(row=1, column=0, sticky=tk.W, pady=5)

        self.duration_entry = tk.Entry(
            main, width=10, font=('Arial', 10),
            bg=COLORS['white'], fg=COLORS['text'],
            relief='solid', bd=1,
        )
        self.duration_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=10)
        self.duration_entry.insert(0, "3")

        # Зависимости
        tk.Label(
            main,
            text="Зависит от (ID):",
            font=('Arial', 10, 'bold'),
            bg=COLORS['bg'], fg=COLORS['header'],
        ).grid(row=2, column=0, sticky=tk.W, pady=5)

        self.dep_entry = tk.Entry(
            main, width=35, font=('Arial', 10),
            bg=COLORS['white'], fg=COLORS['text'],
            relief='solid', bd=1,
        )
        self.dep_entry.grid(row=2, column=1, sticky=tk.W, pady=5, padx=10)
        self.dep_entry.insert(0, "")

        # --- Потребление ресурсов ---
        res_frame = tk.LabelFrame(
            main,
            text="📋 Потребление ресурсов",
            font=('Arial', 10, 'bold'),
            bg=COLORS['bg_light'],
            fg=COLORS['primary_dark'],
            padx=10, pady=10,
            relief='groove', bd=2,
        )
        res_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W + tk.E,
                       pady=15, padx=5)

        self.resource_entries: Dict[str, tk.Entry] = {}

        if not self.resource_limits:
            tk.Label(
                res_frame,
                text="Нет доступных ресурсов.\nСначала задайте ресурсы в проекте.",
                font=('Arial', 10, 'italic'),
                bg=COLORS['bg_light'], fg=COLORS['text_light'],
            ).grid(row=0, column=0, columnspan=3, pady=10)
        else:
            for row, rname in enumerate(self.resource_limits.keys()):
                # Имя ресурса
                tk.Label(
                    res_frame,
                    text=f"{rname}:",
                    font=('Arial', 10),
                    bg=COLORS['bg_light'], fg=COLORS['text'],
                ).grid(row=row, column=0, sticky=tk.W, padx=10, pady=3)

                # Поле ввода
                entry = tk.Entry(
                    res_frame, width=10, font=('Arial', 10),
                    bg=COLORS['white'], fg=COLORS['text'],
                    relief='solid', bd=1,
                )
                entry.grid(row=row, column=1, sticky=tk.W, padx=10, pady=3)
                entry.insert(0, "0")

                # Максимум
                tk.Label(
                    res_frame,
                    text=f"(макс: {self.resource_limits[rname]})",
                    font=('Arial', 9, 'italic'),
                    bg=COLORS['bg_light'], fg=COLORS['text_light'],
                ).grid(row=row, column=2, sticky=tk.W, padx=5)

                self.resource_entries[rname] = entry

        # --- Кнопки ---
        btn_frame = tk.Frame(self.dialog, bg=COLORS['bg_light'], pady=15)
        btn_frame.pack(fill=tk.X)

        tk.Button(
            btn_frame,
            text="✅ Добавить",
            command=self._confirm,
            bg=COLORS['success'], fg=COLORS['white'],
            font=('Arial', 11, 'bold'),
            padx=20, pady=8, relief='flat', cursor='hand2',
        ).pack(side=tk.LEFT, padx=20)

        tk.Button(
            btn_frame,
            text="❌ Отмена",
            command=self._cancel,
            bg=COLORS['error'], fg=COLORS['white'],
            font=('Arial', 11, 'bold'),
            padx=20, pady=8, relief='flat', cursor='hand2',
        ).pack(side=tk.LEFT, padx=5)

        # Фокус на первое поле
        self.name_entry.focus_set()

        # Ждём закрытия
        self.dialog.wait_window()

    # ------------------------------------------------------------------
    # Обработчики кнопок
    # ------------------------------------------------------------------
    def _confirm(self):
        """Собирает и валидирует данные, заполняет self.result."""
        try:
            # Название
            name = self.name_entry.get().strip()
            if not name:
                messagebox.showwarning("Внимание", "Введите название задачи!",
                                       parent=self.dialog)
                return

            # Длительность
            try:
                duration = int(self.duration_entry.get().strip())
            except ValueError:
                messagebox.showerror("Ошибка", "Длительность должна быть целым числом!",
                                     parent=self.dialog)
                return
            if duration <= 0:
                messagebox.showwarning("Внимание", "Длительность должна быть > 0!",
                                       parent=self.dialog)
                return

            # Ресурсы
            resources: Dict[str, int] = {}
            for rname, entry in self.resource_entries.items():
                val_str = entry.get().strip()
                try:
                    val = int(val_str) if val_str else 0
                except ValueError:
                    messagebox.showerror(
                        "Ошибка",
                        f"Для ресурса '{rname}' введите целое число.",
                        parent=self.dialog,
                    )
                    return
                if val < 0:
                    messagebox.showwarning(
                        "Внимание",
                        f"Количество ресурса '{rname}' не может быть отрицательным.",
                        parent=self.dialog,
                    )
                    return
                if val > self.resource_limits.get(rname, 0):
                    messagebox.showwarning(
                        "Внимание",
                        f"Задача требует {val} '{rname}', "
                        f"а в проекте доступно только {self.resource_limits[rname]}.",
                        parent=self.dialog,
                    )
                    return
                if val > 0:
                    resources[rname] = val

            if not resources:
                messagebox.showwarning(
                    "Внимание",
                    "Задача должна требовать хотя бы один ресурс!",
                    parent=self.dialog,
                )
                return

            # Зависимости
            dep_text = self.dep_entry.get().strip()
            deps = []
            if dep_text:
                try:
                    deps = [int(x.strip()) for x in dep_text.split(',') if x.strip()]
                except ValueError:
                    messagebox.showerror(
                        "Ошибка",
                        "Зависимости указываются через запятую: 1,2,3",
                        parent=self.dialog,
                    )
                    return

            # Успех
            self.result = {
                'name': name,
                'duration': duration,
                'resources': resources,
                'deps': deps,
            }
            self.dialog.destroy()

        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self.dialog)

    def _cancel(self):
        self.result = None
        self.dialog.destroy()