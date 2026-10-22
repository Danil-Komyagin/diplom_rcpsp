"""
Главное окно приложения (класс App).
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os

from PIL import ImageTk

from .theme import COLORS, setup_styles
from .core import (
    Task, Project,
    create_scheduler,
    plot_gantt, plot_resource_utilization,
    load_project_from_json, save_project_to_json,
    export_resource_table_csv, export_resource_table_txt,
)
from .core.dashboard import build_dashboard
from .widgets import ExcelResourceTable, ExcelTaskTable
from .tabs import build_file_tab, build_project_tab, build_db_tab
from .dialogs import (
    open_method_dialog, open_rule_dialog,
    ask_start_date, ask_export_format,
)


class App:
    """Главное окно приложения."""

    # ==================================================================
    # ИНИЦИАЛИЗАЦИЯ
    # ==================================================================
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("RCPSP - Планировщик проектов")
        self.root.state('zoomed')
        self.root.minsize(1000, 600)
        self.root.configure(bg=COLORS['bg'])

        setup_styles()

        self.project_name: str = "Мой проект"
        self.resource_limits: dict = {}
        self.tasks: list = []
        self.dependencies: dict = {}
        self.project = None
        self.schedule = None

        self.method_var = tk.StringVar(value="parallel")
        self.priority_var = tk.StringVar(value="LPT")

        # Авторизация — не требуется для запуска
        self.user_id = None
        self._current_db_project_id = None

        self._create_widgets()

    # ==================================================================
    # СБОРКА UI
    # ==================================================================
    def _create_widgets(self):
        self._create_ribbon()

        # ===== Прокручиваемая область под риббоном =====
        scroll_outer = tk.Frame(self.root, bg=COLORS['bg'])
        scroll_outer.pack(fill=tk.BOTH, expand=True)

        self.main_canvas = tk.Canvas(
            scroll_outer,
            bg=COLORS['bg'],
            highlightthickness=0,
            bd=0,
        )
        self.main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        main_vscroll = tk.Scrollbar(
            scroll_outer,
            orient=tk.VERTICAL,
            command=self.main_canvas.yview,
        )
        main_vscroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.main_canvas.configure(yscrollcommand=main_vscroll.set)

        main_frame = tk.Frame(self.main_canvas, bg=COLORS['bg'], padx=10, pady=10)

        self.main_canvas_window = self.main_canvas.create_window(
            (0, 0), window=main_frame, anchor='nw',
        )

        def on_main_frame_configure(event):
            self.main_canvas.configure(scrollregion=self.main_canvas.bbox('all'))

        main_frame.bind('<Configure>', on_main_frame_configure)

        def on_canvas_configure(event):
            self.main_canvas.itemconfigure(
                self.main_canvas_window, width=event.width,
            )

        self.main_canvas.bind('<Configure>', on_canvas_configure)

        def on_mousewheel(event):
            self.main_canvas.yview_scroll(int(-event.delta / 120), 'units')

        def bind_mousewheel(event):
            self.main_canvas.bind_all('<MouseWheel>', on_mousewheel)

        def unbind_mousewheel(event):
            self.main_canvas.unbind_all('<MouseWheel>')

        self.main_canvas.bind('<Enter>', bind_mousewheel)
        self.main_canvas.bind('<Leave>', unbind_mousewheel)

        # ===== Таблица ресурсов =====
        res_frame = tk.LabelFrame(
            main_frame, text="📋 Ресурсы",
            font=('Arial', 11, 'bold'),
            bg=COLORS['white'], fg=COLORS['primary_dark'],
            padx=15, pady=10, relief='groove', bd=2,
        )
        res_frame.pack(fill=tk.X, pady=(0, 10))

        self.resource_table = ExcelResourceTable(
            res_frame, on_save=self._save_project_settings,
        )

        # ===== Таблица задач =====
        task_frame = tk.LabelFrame(
            main_frame, text="📋 Задачи проекта",
            font=('Arial', 11, 'bold'),
            bg=COLORS['white'], fg=COLORS['primary_dark'],
            padx=15, pady=10, relief='groove', bd=2,
        )
        task_frame.pack(fill=tk.BOTH, expand=False)

        self.task_table = ExcelTaskTable(
            task_frame,
            get_resource_names=lambda: list(self.resource_limits.keys()),
            on_run=self._run,
        )

        # ===== Дашборд (диаграмма Ганта + таблицы ресурсов) =====
        dashboard_frame = tk.LabelFrame(
            main_frame, text="📈 Дашборд проекта",
            font=('Arial', 11, 'bold'),
            bg=COLORS['white'], fg=COLORS['primary_dark'],
            padx=10, pady=10, relief='groove', bd=2,
        )
        dashboard_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        dash_container = tk.Frame(dashboard_frame, bg=COLORS['white'])
        dash_container.pack(fill=tk.BOTH, expand=True)

        self.dash_canvas = tk.Canvas(
            dash_container,
            bg=COLORS['white'],
            height=500,
            highlightthickness=0,
            bd=0,
        )
        self.dash_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.dash_v_scroll = tk.Scrollbar(
            dash_container, orient=tk.VERTICAL,
            command=self.dash_canvas.yview,
        )
        self.dash_v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.dash_h_scroll = tk.Scrollbar(
            dashboard_frame, orient=tk.HORIZONTAL,
            command=self.dash_canvas.xview,
        )
        self.dash_h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.dash_canvas.configure(
            xscrollcommand=self.dash_h_scroll.set,
            yscrollcommand=self.dash_v_scroll.set,
        )

        self.dash_inner = tk.Frame(self.dash_canvas, bg=COLORS['white'])
        self.dash_canvas_window = self.dash_canvas.create_window(
            (0, 0), window=self.dash_inner, anchor='nw',
        )

        self._show_dashboard_placeholder()

        # Прокрутка колёсиком для дашборда
        def on_dash_wheel(event):
            self.dash_canvas.yview_scroll(int(-event.delta / 120), 'units')

        def bind_dash_wheel(_):
            self.dash_canvas.bind_all('<MouseWheel>', on_dash_wheel)

        def unbind_dash_wheel(_):
            self.dash_canvas.unbind_all('<MouseWheel>')

        self.dash_canvas.bind('<Enter>', bind_dash_wheel)
        self.dash_canvas.bind('<Leave>', unbind_dash_wheel)

        # ===== Прогресс-бар =====
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate', length=200)
        self.progress.pack(fill=tk.X, pady=5)
        self.progress.pack_forget()

        # ===== Статус-строка =====
        self.status_label = tk.Label(
            main_frame, text="✅ Готов",
            font=('Arial', 10, 'italic'),
            bg=COLORS['bg'], fg=COLORS['text_light'],
        )
        self.status_label.pack(anchor=tk.W, pady=2)

    def _show_dashboard_placeholder(self):
        """Показывает заглушку на дашборде."""
        for w in self.dash_inner.winfo_children():
            w.destroy()
        tk.Label(
            self.dash_inner,
            text="Запустите планирование, чтобы увидеть дашборд",
            font=('Arial', 11, 'italic'),
            bg=COLORS['white'],
            fg=COLORS['text_light'],
        ).pack(padx=20, pady=20)
        self.dash_canvas.configure(scrollregion=(0, 0, 0, 0))

    # ==================================================================
    # РИББОН
    # ==================================================================
    def _create_ribbon(self):
        tab_bar = tk.Frame(self.root, bg=COLORS['ribbon_bg'], height=30)
        tab_bar.pack(fill=tk.X)
        tab_bar.pack_propagate(False)

        self.ribbon_tabs: dict = {}

        tabs = [
            ("Файл", build_file_tab),
            ("Проект", build_project_tab),
            ("База данных", build_db_tab),
        ]

        for tab_name, builder in tabs:
            btn = tk.Button(
                tab_bar, text=tab_name,
                font=('Arial', 10),
                bg=COLORS['ribbon_tab_inactive'],
                fg=COLORS['header'],
                relief='flat', padx=20, pady=5, cursor='hand2',
            )
            btn.pack(side=tk.LEFT, padx=1, pady=3)
            btn.configure(command=lambda n=tab_name, b=builder: self._switch_tab(n, b))
            self.ribbon_tabs[tab_name] = btn

        self.ribbon_content_frame = tk.Frame(
            self.root, bg=COLORS['ribbon_tab_active'], height=50,
            highlightbackground=COLORS['ribbon_border'],
            highlightthickness=1,
        )
        self.ribbon_content_frame.pack(fill=tk.X)
        self.ribbon_content_frame.pack_propagate(False)

        self._switch_tab("Файл", build_file_tab)

    def _switch_tab(self, tab_name: str, builder):
        for name, btn in self.ribbon_tabs.items():
            if name == tab_name:
                btn.configure(bg=COLORS['ribbon_tab_active'], fg=COLORS['primary_dark'])
            else:
                btn.configure(bg=COLORS['ribbon_tab_inactive'], fg=COLORS['header'])

        for widget in self.ribbon_content_frame.winfo_children():
            widget.destroy()

        builder(self.ribbon_content_frame, self)

    # ==================================================================
    # АВТОРИЗАЦИЯ
    # ==================================================================
    def _db_login(self):
        """Открывает диалог входа / регистрации."""
        from .dialogs.login_dialog import open_login_dialog

        user_id = open_login_dialog(self.root)
        if user_id is None:
            return

        self.user_id = user_id
        from .core import storage
        username = storage.get_username(user_id)
        self.status_label.config(
            text=f"👤 Вы вошли как {username}",
            fg=COLORS['success'],
        )
        self._switch_tab("База данных", build_db_tab)

    def _db_logout(self):
        """Выходит из системы."""
        if not messagebox.askyesno("Выход", "Выйти из учётной записи?"):
            return
        self.user_id = None
        self._current_db_project_id = None
        self.status_label.config(
            text="🚪 Вы вышли из системы",
            fg=COLORS['text_light'],
        )
        self._switch_tab("База данных", build_db_tab)

    def _require_login(self) -> bool:
        """Проверяет, вошёл ли пользователь."""
        if self.user_id is None:
            messagebox.showwarning(
                "Требуется вход",
                "Для работы с базой данных нужно войти.\n\n"
                "Нажмите «🔐 Войти» во вкладке «База данных».",
            )
            return False
        return True

    # ==================================================================
    # ОБЁРТКИ НАД ДИАЛОГАМИ
    # ==================================================================
    def _set_method_dialog(self):
        current = self.method_var.get()
        result = open_method_dialog(self.root, current)
        if result:
            self.method_var.set(result)
            self.status_label.config(text=f"⚙️ Метод: {result}", fg=COLORS['primary_dark'])

    def _set_rule_dialog(self):
        current = self.priority_var.get()
        result = open_rule_dialog(self.root, current)
        if result:
            self.priority_var.set(result)
            self.status_label.config(text=f"⚙️ Правило: {result}", fg=COLORS['primary_dark'])

    def _project_info_stub(self):
        info = (
            f"📊 Информация о проекте\n\n"
            f"Название: {self.project_name or 'не задано'}\n"
            f"Ресурсов: {len(self.resource_limits)}\n"
            f"Задач: {len(self.tasks)}\n"
            f"Метод: {self.method_var.get()}\n"
            f"Правило: {self.priority_var.get()}\n"
        )
        if self.user_id is not None:
            from .core import storage
            username = storage.get_username(self.user_id)
            info += f"Пользователь: {username}\n"
        messagebox.showinfo("Информация о проекте", info)

    # ==================================================================
    # БАЗА ДАННЫХ
    # ==================================================================
    def _db_save_stub(self):
        """Сохраняет проект в БД."""
        if not self._require_login():
            return

        project = self._build_project()
        if project is None:
            return

        try:
            from .core import storage
            project_id = storage.save_project(self.user_id, project)
            self._current_db_project_id = project_id
            messagebox.showinfo(
                "Успех",
                f"Проект '{project.name}' сохранён в БД.\nID: {project_id}",
            )
            self.status_label.config(
                text=f"💾 Сохранено в БД: {project.name}",
                fg=COLORS['success'],
            )
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", str(e))

    def _db_load_stub(self):
        """Загружает проект из БД."""
        if not self._require_login():
            return

        from .dialogs.projects_dialog import open_projects_dialog
        from .core import storage

        project_id = open_projects_dialog(self.root, self.user_id)
        if project_id is None:
            return

        try:
            project = storage.load_project(project_id)
            if project is None:
                messagebox.showerror("Ошибка", "Проект не найден.")
                return
        except Exception as e:
            messagebox.showerror("Ошибка загрузки", str(e))
            return

        self._apply_project(project)
        self._current_db_project_id = project_id
        self.status_label.config(
            text=f"📁 Загружен из БД: {project.name}",
            fg=COLORS['success'],
        )

    # ==================================================================
    # ПРИМЕНЕНИЕ ПРОЕКТА К UI
    # ==================================================================
    def _apply_project(self, project: Project):
        """Универсальная заливка проекта в UI (используется в _load, _db_load_stub, _load_demo_project)."""
        self.project_name = project.name
        self.resource_limits = dict(project.resource_limits)
        self.project = project
        self.schedule = None

        self.resource_table.clear()
        for rname, count in project.resource_limits.items():
            self.resource_table.add_resource(rname, count)

        self.task_table.rebuild()
        tasks_for_table = [
            {
                'id': t.id, 'name': t.name,
                'duration': t.duration, 'resources': dict(t.resources),
            }
            for t in project.tasks
        ]
        self.task_table.set_tasks(tasks_for_table, project.dependencies)

        self._sync_from_table()
        self._show_dashboard_placeholder()

    # ==================================================================
    # ВСПОМОГАТЕЛЬНЫЕ
    # ==================================================================
    def _create_button(self, parent, text: str, command, color: str = None):
        if color is None:
            color = COLORS['primary']
        return tk.Button(
            parent, text=text, command=command,
            bg=color, fg=COLORS['white'],
            font=('Arial', 10, 'bold'),
            padx=12, pady=5, relief='flat', cursor='hand2',
            activebackground=COLORS['primary_dark'],
            activeforeground=COLORS['white'],
        )

    def _sync_from_table(self):
        self.tasks = self.task_table.get_tasks()
        self.dependencies = self.task_table.get_dependencies()
        self.status_label.config(text="✏️ Изменено", fg=COLORS['text_light'])

    # ==================================================================
    # ДАШБОРД
    # ==================================================================
    def _draw_dashboard(self, schedule: dict, makespan: int):
        """Рисует дашборд на canvas."""
        try:
            img = build_dashboard(self.project, schedule)
        except Exception as e:
            messagebox.showerror("Ошибка дашборда", str(e))
            return

        photo = ImageTk.PhotoImage(img)

        for w in self.dash_inner.winfo_children():
            w.destroy()

        label = tk.Label(self.dash_inner, image=photo, bg=COLORS['white'])
        label.image = photo
        label.pack()

        self.dash_inner.update_idletasks()
        self.dash_canvas.itemconfigure(
            self.dash_canvas_window,
            width=img.width,
            height=img.height,
        )
        self.dash_canvas.configure(
            scrollregion=(0, 0, img.width, img.height),
        )
        self.dash_canvas.xview_moveto(0)
        self.dash_canvas.yview_moveto(0)

    # ==================================================================
    # СОХРАНЕНИЕ НАСТРОЕК ПРОЕКТА
    # ==================================================================
    def _save_project_settings(self):
        name = self.project_name or "Мой проект"

        resource_limits = self.resource_table.get_resources()
        if not resource_limits:
            messagebox.showwarning(
                "Внимание",
                "Добавьте хотя бы один ресурс!\n\n"
                "Заполните строку 'Название' и 'Количество' в таблице.",
            )
            return

        existing_tasks = self.task_table.get_tasks()
        existing_deps = self.task_table.get_dependencies()

        self.project_name = name
        self.resource_limits = resource_limits
        self.project = None

        self.task_table.rebuild()
        if existing_tasks:
            self.task_table.set_tasks(existing_tasks, existing_deps)

        self._sync_from_table()
        self.status_label.config(text=f"✅ Проект '{name}' сохранён", fg=COLORS['success'])

        messagebox.showinfo(
            "Успех",
            f"Настройки проекта сохранены!\n\n"
            f"Название: {name}\n"
            f"Ресурсов: {len(resource_limits)}\n"
            f"Список: {', '.join(f'{k}({v})' for k, v in resource_limits.items())}",
        )

    # ==================================================================
    # СБОРКА PROJECT
    # ==================================================================
    def _build_project(self):
        self._sync_from_table()

        if not self.tasks:
            messagebox.showwarning("Внимание", "Добавьте хотя бы одну задачу!")
            return None

        if not self.resource_limits:
            messagebox.showwarning("Внимание", "Сохраните настройки проекта с ресурсами!")
            return None

        task_objects = []
        for t in self.tasks:
            try:
                task_objects.append(Task(
                    id=t['id'], name=t['name'],
                    duration=t['duration'], resources=t['resources'],
                ))
            except ValueError as e:
                messagebox.showerror(
                    "Ошибка в задаче",
                    f"Задача ID={t['id']} '{t['name']}':\n{e}",
                )
                return None

        project = Project(
            tasks=task_objects,
            dependencies=self.dependencies,
            resource_limits=self.resource_limits,
            name=self.project_name or "Мой проект",
        )

        errors = project.validate()
        if errors:
            messagebox.showerror(
                "Ошибка в проекте",
                "Проект содержит ошибки:\n\n" + "\n".join(errors),
            )
            return None

        return project

    # ==================================================================
    # ДЕМО-ПРОЕКТ
    # ==================================================================
    def _load_demo_project(self):
        if not messagebox.askyesno(
            "Демо-проект",
            "Загрузить демонстрационный проект?\n\n"
            "Текущие данные будут потеряны.",
        ):
            return

        from .core.utils import create_test_project

        try:
            project = create_test_project(n_tasks=12, n_resources=3, seed=42)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать демо-проект:\n{e}")
            return

        self._apply_project(project)
        self._current_db_project_id = None
        self.status_label.config(
            text=f"🎲 Загружен демо-проект: {project.name}",
            fg=COLORS['primary_dark'],
        )

    # ==================================================================
    # ЗАПУСК ПЛАНИРОВАНИЯ
    # ==================================================================
    def _run(self):
        project = self._build_project()
        if project is None:
            return

        self.project = project
        method = self.method_var.get()
        rule = self.priority_var.get()

        self._show_dashboard_placeholder()

        self.progress.pack(fill=tk.X, pady=5)
        self.progress.start(10)
        self.status_label.config(text="⏳ Выполняется планирование...",
                                 fg=COLORS['warning'])
        self.root.update()

        thread = threading.Thread(
            target=self._run_thread, args=(method, rule), daemon=True,
        )
        thread.start()

    def _run_thread(self, method: str, rule: str):
        try:
            scheduler = create_scheduler(method, self.project, rule)
            schedule, makespan = scheduler.schedule()
            self.schedule = schedule
            self.root.after(0, self._show_results, schedule, makespan)
        except Exception as e:
            self.root.after(0, self._show_error, str(e))

    def _show_results(self, schedule: dict, makespan: int):
        self.progress.stop()
        self.progress.pack_forget()
        self.status_label.config(text=f"✅ Готово: {makespan} дней", fg=COLORS['success'])

        # Сохраняем PNG в папку results
        os.makedirs("results", exist_ok=True)
        try:
            plot_gantt(self.project, schedule, save_path="results/gantt.png")
            plot_resource_utilization(self.project, schedule,
                                      save_path="results/resources.png")
        except Exception as e:
            messagebox.showwarning("Диаграммы",
                                   f"Не удалось сохранить диаграммы:\n{e}")

        # Рисуем дашборд
        try:
            self._draw_dashboard(schedule, makespan)
        except Exception as e:
            messagebox.showwarning(
                "Дашборд",
                f"Не удалось отрисовать дашборд:\n{e}",
            )

        # Сохраняем историю расчёта (если проект есть в БД)
        try:
            if (self.user_id is not None and self.project
                    and self._current_db_project_id is not None):
                from .core import storage
                storage.save_schedule(
                    self._current_db_project_id,
                    self.method_var.get(),
                    self.priority_var.get(),
                    makespan,
                )
        except Exception:
            pass

        messagebox.showinfo(
            "Готово",
            f"Планирование завершено!\n"
            f"Длительность проекта: {makespan} дней\n\n"
            f"Дашборд показан в окне.\n"
            f"PNG-файлы сохранены в папке results/",
        )

    def _show_error(self, error: str):
        self.progress.stop()
        self.progress.pack_forget()
        self.status_label.config(text=f"❌ Ошибка: {error}", fg=COLORS['error'])
        messagebox.showerror("Ошибка планирования", error)

    # ==================================================================
    # СОХРАНЕНИЕ / ЗАГРУЗКА JSON
    # ==================================================================
    def _save(self):
        project = self._build_project()
        if project is None:
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"{project.name}.json",
        )
        if not path:
            return

        try:
            save_project_to_json(project, path)
            messagebox.showinfo("Успех", f"Проект сохранён в:\n{path}")
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", str(e))

    def _load(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            project = load_project_from_json(path)
        except Exception as e:
            messagebox.showerror("Ошибка загрузки", str(e))
            return

        self._apply_project(project)
        self._current_db_project_id = None
        self.status_label.config(text=f"✅ Загружен: {project.name}", fg=COLORS['success'])

    # ==================================================================
    # ЭКСПОРТ ТАБЛИЦЫ РЕСУРСОВ
    # ==================================================================
    def _export_resource_table(self):
        if not self.project or not self.schedule:
            messagebox.showwarning("Внимание", "Сначала запустите планирование!")
            return

        start_date = ask_start_date(self.root)
        if start_date is None:
            return

        fmt = ask_export_format(self.root, default="csv")
        if fmt is None:
            return

        if fmt == "csv":
            ext = ".csv"
            filetypes = [("CSV files", "*.csv"), ("All files", "*.*")]
        else:
            ext = ".txt"
            filetypes = [("Text files", "*.txt"), ("All files", "*.*")]

        default_name = f"resource_table_{start_date.strftime('%Y%m%d')}{ext}"

        path = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=filetypes,
            initialfile=default_name,
        )
        if not path:
            return

        if fmt == "csv":
            success = export_resource_table_csv(self.project, self.schedule, path, start_date)
        else:
            success = export_resource_table_txt(self.project, self.schedule, path, start_date)

        if success:
            messagebox.showinfo("Успех", f"Таблица выгружена в:\n{path}")
            self.status_label.config(
                text=f"📊 Отчёт сохранён: {os.path.basename(path)}",
                fg=COLORS['success'],
            )
        else:
            messagebox.showerror(
                "Ошибка",
                "Не удалось выгрузить таблицу.\nПодробности — в консоли.",
            )


# ======================================================================
# ТОЧКА ВХОДА
# ======================================================================
def run_gui():
    """Запускает приложение."""
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    run_gui()