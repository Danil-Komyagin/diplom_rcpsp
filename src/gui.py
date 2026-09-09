import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import json
import threading
import os
from typing import List, Optional, Dict, Any

from .models import Task, Project
from .schedulers import create_scheduler
from .visualizer import plot_gantt, plot_resource_utilization
from .utils import create_test_project, load_project_from_json, save_project_to_json


class CreateProjectDialog:
    """Окно создания проекта: название + ресурсы"""

    def __init__(self, parent):
        self.parent = parent
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("➕ Создание проекта")
        self.dialog.geometry("500x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)

        main = ttk.Frame(self.dialog, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        # Название проекта
        ttk.Label(main, text="Название проекта:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(main, width=40)
        self.name_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        self.name_entry.insert(0, "Мой проект")

        # Ресурсы
        ttk.Label(main, text="Ресурсы (название:количество):", font=('Arial', 10, 'bold')).grid(row=1, column=0,
                                                                                                sticky=tk.W, pady=5)

        self.resources_text = tk.Text(main, height=5, width=40, font=('Consolas', 9))
        self.resources_text.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        self.resources_text.insert(tk.END, "developers:4\ntesters:2\ndesigners:1")

        # Кнопки
        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="✅ Создать", command=self._confirm).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="❌ Отмена", command=self._cancel).pack(side=tk.LEFT, padx=10)

        # Ждём, пока окно закроется
        self.dialog.wait_window()

    def _confirm(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Внимание", "Введите название проекта!")
            return

        # Парсим ресурсы
        resources_text = self.resources_text.get(1.0, tk.END).strip()
        resource_limits = {}
        for line in resources_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            if ':' in line:
                parts = line.split(':')
                if len(parts) == 2:
                    try:
                        res_name = parts[0].strip()
                        res_limit = int(parts[1].strip())
                        if res_limit > 0:
                            resource_limits[res_name] = res_limit
                    except ValueError:
                        pass

        if not resource_limits:
            messagebox.showwarning("Внимание", "Добавьте хотя бы один ресурс!\nФормат: название:количество")
            return

        self.result = {
            'name': name,
            'resource_limits': resource_limits,
            'tasks': [],
            'dependencies': {}
        }
        print(f"[DEBUG] Проект создан: {self.result}")
        self.dialog.destroy()

    def _cancel(self):
        self.result = None
        self.dialog.destroy()


class AddTaskDialog:
    """Окно добавления задачи в проект"""

    def __init__(self, parent, resource_limits: Dict[str, int]):
        self.parent = parent
        self.resource_limits = resource_limits
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("➕ Добавление задачи")
        self.dialog.geometry("500x450")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)

        main = ttk.Frame(self.dialog, padding=15)
        main.pack(fill=tk.BOTH, expand=True)

        # Название задачи
        ttk.Label(main, text="Название задачи:", font=('Arial', 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(main, width=35)
        self.name_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)

        # Длительность
        ttk.Label(main, text="Длительность (дни):", font=('Arial', 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.duration_entry = ttk.Entry(main, width=10)
        self.duration_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        self.duration_entry.insert(0, "3")

        # Зависимости
        ttk.Label(main, text="Зависит от (ID через запятую):", font=('Arial', 10)).grid(row=2, column=0, sticky=tk.W,
                                                                                        pady=5)
        self.dep_entry = ttk.Entry(main, width=35)
        self.dep_entry.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)
        self.dep_entry.insert(0, "")

        # Ресурсы
        ttk.Label(main, text="Потребление ресурсов:", font=('Arial', 10, 'bold')).grid(row=3, column=0, columnspan=2,
                                                                                       sticky=tk.W, pady=10)

        res_frame = ttk.LabelFrame(main, text="Ресурсы", padding=10)
        res_frame.grid(row=4, column=0, columnspan=2, sticky=tk.W + tk.E, pady=5)

        self.resource_entries = {}
        row = 0
        for rt in self.resource_limits.keys():
            ttk.Label(res_frame, text=f"{rt}:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
            entry = ttk.Entry(res_frame, width=8)
            entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
            entry.insert(0, "0")
            self.resource_entries[rt] = entry
            row += 1

        # Кнопки
        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=20)

        ttk.Button(btn_frame, text="✅ Добавить", command=self._confirm).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="❌ Отмена", command=self._cancel).pack(side=tk.LEFT, padx=10)

        # Ждём, пока окно закроется
        self.dialog.wait_window()

    def _confirm(self):
        try:
            name = self.name_entry.get().strip()
            if not name:
                messagebox.showwarning("Внимание", "Введите название задачи!")
                return

            duration = int(self.duration_entry.get())
            if duration <= 0:
                messagebox.showwarning("Внимание", "Длительность должна быть > 0!")
                return

            resources = {}
            for rt, entry in self.resource_entries.items():
                val = int(entry.get() or 0)
                if val > 0:
                    resources[rt] = val

            if not resources:
                messagebox.showwarning("Внимание", "Задача должна требовать хотя бы один ресурс!")
                return

            dep_text = self.dep_entry.get().strip()
            deps = []
            if dep_text:
                try:
                    deps = [int(x.strip()) for x in dep_text.split(',') if x.strip()]
                except ValueError:
                    messagebox.showerror("Ошибка", "Введите ID через запятую!")
                    return

            self.result = {
                'name': name,
                'duration': duration,
                'resources': resources,
                'deps': deps
            }
            print(f"[DEBUG] Задача создана: {self.result}")
            self.dialog.destroy()

        except ValueError:
            messagebox.showerror("Ошибка", "Проверьте введённые числа!")

    def _cancel(self):
        self.result = None
        self.dialog.destroy()


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("RCPSP - Планировщик проектов")
        self.root.geometry("1400x800")
        self.root.minsize(1000, 600)

        # Данные проекта
        self.project_name = ""
        self.resource_limits = {}
        self.tasks = []
        self.dependencies = {}
        self.next_task_id = 1
        self.project = None
        self.schedule = None

        self._create_widgets()
        print("[DEBUG] Приложение запущено")

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ====== ВЕРХНЯЯ ПАНЕЛЬ: УПРАВЛЕНИЕ ======
        control_frame = ttk.LabelFrame(main_frame, text="⚙️ Управление", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        # Строка 1: кнопки
        btn_row = ttk.Frame(control_frame)
        btn_row.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(btn_row, text="➕ Создать проект", command=self._create_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="📂 Загрузить тест", command=self._load_test).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="💾 Сохранить", command=self._save).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="📂 Загрузить", command=self._load).pack(side=tk.LEFT, padx=2)

        # Строка 2: настройки алгоритма
        algo_row = ttk.Frame(control_frame)
        algo_row.pack(fill=tk.X, pady=5)

        ttk.Label(algo_row, text="Метод:").pack(side=tk.LEFT, padx=5)
        self.method_var = tk.StringVar(value="parallel")
        ttk.Combobox(algo_row, textvariable=self.method_var, values=["parallel", "serial"],
                     state="readonly", width=12).pack(side=tk.LEFT, padx=5)

        ttk.Label(algo_row, text="Правило:").pack(side=tk.LEFT, padx=5)
        self.priority_var = tk.StringVar(value="LPT")
        ttk.Combobox(algo_row, textvariable=self.priority_var,
                     values=["LPT", "SPT", "MTS", "GRPW", "MS"],
                     state="readonly", width=10).pack(side=tk.LEFT, padx=5)

        self.run_btn = ttk.Button(algo_row, text="▶ Запустить", command=self._run)
        self.run_btn.pack(side=tk.LEFT, padx=10)

        # Кнопка "Добавить задачу" — справа
        ttk.Button(algo_row, text="➕ Добавить задачу", command=self._add_task).pack(side=tk.RIGHT, padx=5)

        # Прогресс и статус
        self.progress = ttk.Progressbar(control_frame, mode='indeterminate', length=200)
        self.progress.pack(fill=tk.X, pady=5)
        self.progress.pack_forget()

        self.status_label = ttk.Label(control_frame, text="✅ Готов")
        self.status_label.pack(anchor=tk.W, pady=2)

        # ====== ИНФОРМАЦИЯ О ПРОЕКТЕ ======
        info_frame = ttk.LabelFrame(main_frame, text="📋 Информация о проекте", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        self.info_text = ScrolledText(info_frame, font=('Consolas', 9), height=4, bg='#f5f5f5')
        self.info_text.pack(fill=tk.X)
        self.info_text.insert(tk.END, "Создайте или загрузите проект")
        self.info_text.config(state=tk.DISABLED)

        # ====== СПИСОК ЗАДАЧ ======
        task_frame = ttk.LabelFrame(main_frame, text="📋 Задачи", padding=10)
        task_frame.pack(fill=tk.BOTH, expand=True)

        self.task_listbox = tk.Listbox(task_frame, height=8, font=('Consolas', 9))
        self.task_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        btn_task_row = ttk.Frame(task_frame)
        btn_task_row.pack(fill=tk.X)

        ttk.Button(btn_task_row, text="🗑 Удалить задачу", command=self._delete_task).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_task_row, text="🧹 Очистить все", command=self._clear_tasks).pack(side=tk.LEFT, padx=2)

        self.task_count_label = ttk.Label(btn_task_row, text="Всего: 0 задач")
        self.task_count_label.pack(side=tk.RIGHT, padx=5)

        # ====== РЕЗУЛЬТАТЫ ======
        result_frame = ttk.LabelFrame(main_frame, text="📊 Результаты", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True)

        self.result_text = ScrolledText(result_frame, font=('Consolas', 9), height=6, bg='white')
        self.result_text.pack(fill=tk.BOTH, expand=True)

    def _update_display(self):
        """Обновляет всю информацию на экране"""
        print("[DEBUG] _update_display вызван")
        print(f"[DEBUG] resource_limits: {self.resource_limits}")
        print(f"[DEBUG] tasks: {len(self.tasks)}")

        # Обновляем информацию о проекте
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)

        if not self.resource_limits and not self.tasks:
            self.info_text.insert(tk.END, "Проект не создан")
        else:
            deps_count = sum(len(v) for v in self.dependencies.values())
            name = self.project_name if self.project_name else "Без названия"
            info = f"""
📊 СТАТИСТИКА ПРОЕКТА
  • Название: {name}
  • Всего задач: {len(self.tasks)}
  • Зависимостей: {deps_count}
  • Ресурсы: {', '.join(f'{k}: {v}' for k, v in self.resource_limits.items())}
  • Следующий ID задачи: {self.next_task_id}
            """
            self.info_text.insert(tk.END, info)
        self.info_text.config(state=tk.DISABLED)

        # Обновляем список задач
        self.task_listbox.delete(0, tk.END)
        for task in self.tasks:
            deps = self.dependencies.get(task['id'], [])
            dep_str = f"←{','.join(str(d) for d in deps)}" if deps else ""
            res_str = ','.join(f"{k}:{v}" for k, v in task['resources'].items() if v > 0)
            self.task_listbox.insert(tk.END,
                                     f"ID:{task['id']} {task['name']} ({task['duration']}д) [{res_str}] {dep_str}")

        self.task_count_label.config(text=f"Всего: {len(self.tasks)} задач")

    def _create_project(self):
        """Открывает окно создания проекта"""
        print("[DEBUG] _create_project вызван")
        dialog = CreateProjectDialog(self.root)
        result = dialog.result

        print(f"[DEBUG] Результат диалога: {result}")

        if result:
            # Сохраняем данные проекта
            self.project_name = result['name']
            self.resource_limits = result['resource_limits']
            self.tasks = []
            self.dependencies = {}
            self.next_task_id = 1
            self.project = None

            self._update_display()
            self.status_label.config(text=f"✅ Создан проект: {self.project_name}")
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(1.0,
                                    f"✅ Создан проект: {self.project_name}\nДобавьте задачи и запустите планирование.")

            messagebox.showinfo("Успех", f"Проект '{self.project_name}' создан!\nТеперь добавьте задачи.")
        else:
            print("[DEBUG] Результат пустой — проект не создан")

    def _add_task(self):
        """Открывает окно добавления задачи"""
        print("[DEBUG] _add_task вызван")
        print(f"[DEBUG] resource_limits: {self.resource_limits}")

        if not self.resource_limits:
            messagebox.showwarning("Внимание", "Сначала создайте проект с ресурсами!\nНажмите '➕ Создать проект'.")
            return

        dialog = AddTaskDialog(self.root, self.resource_limits)
        result = dialog.result

        print(f"[DEBUG] Результат задачи: {result}")

        if result:
            # Проверяем зависимости
            existing_ids = [t['id'] for t in self.tasks]
            for dep in result['deps']:
                if dep not in existing_ids:
                    messagebox.showwarning("Внимание", f"Задача с ID {dep} не существует!")
                    return

            # Добавляем задачу
            task = {
                'id': self.next_task_id,
                'name': result['name'],
                'duration': result['duration'],
                'resources': result['resources']
            }
            self.tasks.append(task)
            self.dependencies[self.next_task_id] = result['deps']
            self.next_task_id += 1

            self._update_display()
            self.status_label.config(text=f"✅ Добавлена задача: {result['name']}")

    def _delete_task(self):
        """Удаляет выбранную задачу"""
        selection = self.task_listbox.curselection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите задачу для удаления!")
            return

        idx = selection[0]
        task_id = self.tasks[idx]['id']

        # Удаляем задачу
        self.tasks.pop(idx)
        if task_id in self.dependencies:
            del self.dependencies[task_id]

        # Удаляем зависимости
        for key in list(self.dependencies.keys()):
            self.dependencies[key] = [d for d in self.dependencies[key] if d != task_id]
            if not self.dependencies[key]:
                del self.dependencies[key]

        self._update_display()
        self.status_label.config(text="🗑 Задача удалена")

    def _clear_tasks(self):
        """Удаляет все задачи"""
        if not self.tasks:
            return
        if messagebox.askyesno("Подтверждение", "Удалить все задачи?"):
            self.tasks.clear()
            self.dependencies.clear()
            self.next_task_id = 1
            self._update_display()
            self.status_label.config(text="🧹 Все задачи удалены")

    def _load_test(self):
        """Загружает тестовый проект"""
        try:
            project = create_test_project()

            self.project_name = project.name
            self.resource_limits = project.resource_limits
            self.tasks = []
            self.dependencies = {}
            self.next_task_id = 1

            for task in project.tasks:
                self.tasks.append({
                    'id': task.id,
                    'name': task.name,
                    'duration': task.duration,
                    'resources': task.resources
                })
                self.dependencies[task.id] = project.dependencies.get(task.id, [])
                if task.id >= self.next_task_id:
                    self.next_task_id = task.id + 1

            self.project = project
            self._update_display()
            self.status_label.config(text="✅ Загружен тестовый проект")
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(1.0,
                                    f"✅ Загружен тестовый проект\nЗадач: {len(self.tasks)}\nНажмите '▶ Запустить' для планирования.")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить проект: {e}")

    def _build_project(self):
        """Собирает объект Project из текущих данных"""
        if not self.tasks:
            messagebox.showwarning("Внимание", "Добавьте хотя бы одну задачу!")
            return None

        if not self.resource_limits:
            messagebox.showwarning("Внимание", "Добавьте ресурсы!")
            return None

        task_objects = []
        for t in self.tasks:
            task_objects.append(Task(
                id=t['id'],
                name=t['name'],
                duration=t['duration'],
                resources=t['resources']
            ))

        return Project(
            tasks=task_objects,
            dependencies=self.dependencies,
            resource_limits=self.resource_limits,
            name=self.project_name if self.project_name else "Мой проект"
        )

    def _run(self):
        """Запускает планирование"""
        project = self._build_project()
        if not project:
            return

        self.project = project

        self.progress.pack(fill=tk.X, pady=5)
        self.progress.start(10)
        self.run_btn.config(state=tk.DISABLED, text="⏳...")
        self.status_label.config(text="⏳ Выполняется планирование...")
        self.root.update()

        thread = threading.Thread(target=self._run_thread, daemon=True)
        thread.start()

    def _run_thread(self):
        try:
            method = self.method_var.get()
            rule = self.priority_var.get()

            scheduler = create_scheduler(method, self.project, rule)
            schedule, makespan = scheduler.schedule()
            self.schedule = schedule

            self.root.after(0, self._show_results, schedule, makespan, method, rule)
        except Exception as e:
            self.root.after(0, self._show_error, str(e))

    def _show_results(self, schedule, makespan, method, rule):
        self.progress.stop()
        self.progress.pack_forget()
        self.run_btn.config(state=tk.NORMAL, text="▶ Запустить")
        self.status_label.config(text=f"✅ Готово: {makespan} дней")

        text = f"🎯 {method.upper()} + {rule} → {makespan} дней\n\n"
        text += f"{'ID':<4} {'Название':<15} {'Старт':<6} {'Финиш':<6} {'Ресурсы':<15}\n"
        text += "-" * 60 + "\n"

        for task in sorted(self.project.tasks, key=lambda t: schedule.get(t.id, 0)):
            s = schedule.get(task.id, 0)
            f = s + task.duration
            r = ', '.join(f"{k}:{v}" for k, v in task.resources.items())
            text += f"{task.id:<4} {task.name[:14]:<15} {s:<6} {f:<6} {r:<15}\n"

        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(1.0, text)

        os.makedirs("results", exist_ok=True)
        plot_gantt(self.project, schedule, save_path="results/gantt.png")
        plot_resource_utilization(self.project, schedule, save_path="results/resources.png")

        messagebox.showinfo("Готово",
                            f"Планирование завершено!\nДлительность: {makespan} дней\nДиаграммы сохранены в папке results/")

    def _show_error(self, error):
        self.progress.stop()
        self.progress.pack_forget()
        self.run_btn.config(state=tk.NORMAL, text="▶ Запустить")
        self.status_label.config(text=f"❌ Ошибка: {error}")
        messagebox.showerror("Ошибка", error)

    def _save(self):
        """Сохраняет проект в JSON"""
        project = self._build_project()
        if not project:
            return

        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON", "*.json")])
        if path:
            save_project_to_json(project, path)
            messagebox.showinfo("Успех", f"Проект сохранён в {path}")

    def _load(self):
        """Загружает проект из JSON"""
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return

        try:
            project = load_project_from_json(path)

            self.project_name = project.name
            self.resource_limits = project.resource_limits
            self.tasks = []
            self.dependencies = {}
            self.next_task_id = 1

            for task in project.tasks:
                self.tasks.append({
                    'id': task.id,
                    'name': task.name,
                    'duration': task.duration,
                    'resources': task.resources
                })
                self.dependencies[task.id] = project.dependencies.get(task.id, [])
                if task.id >= self.next_task_id:
                    self.next_task_id = task.id + 1

            self.project = project
            self._update_display()
            self.status_label.config(text=f"✅ Загружен: {project.name}")
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(1.0, f"✅ Загружен проект: {project.name}\nЗадач: {len(self.tasks)}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить: {e}")


def run_gui():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    run_gui()