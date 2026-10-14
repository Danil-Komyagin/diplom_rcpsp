import tkinter as tk
from typing import Callable, Dict, List, Optional, Set


from ..theme import COLORS


class ExcelTaskTable:
    """Таблица задач в стиле Excel."""

    # ------------------------------------------------------------------
    # Размеры
    # ------------------------------------------------------------------
    ROW_HEIGHT = 30
    HEADER_HEIGHT = 30
    BORDER = 1
    INITIAL_ROWS = 10
    RUN_BTN_HEIGHT = 30
    CANVAS_HEIGHT = 248

    MIN_RESOURCE_COLUMNS = 8

    W_NAME = 130
    W_DURATION = 130
    W_DEPS = 130
    W_RESOURCE = 130

    # ------------------------------------------------------------------
    # Конструктор
    # ------------------------------------------------------------------
    def __init__(self, parent: tk.Widget,
                 get_resource_names: Optional[Callable[[], List[str]]] = None,
                 on_run: Optional[Callable] = None):
        self.parent = parent
        self.get_resource_names = get_resource_names or (lambda: [])
        self.on_run = on_run

        self.rows: List[Dict[str, tk.Widget]] = []
        self.row_frames: List[Dict[str, tk.Frame]] = []
        self.header_widgets: Dict[str, tk.Frame] = {}
        self._deps_values: Dict[int, Set[int]] = {}

        self._create_widgets()
        self._rebuild_header()
        self._create_initial_rows()

    # ------------------------------------------------------------------
    # Каркас
    # ------------------------------------------------------------------
    def _create_widgets(self):
        self.outer = tk.Frame(self.parent, bg=COLORS['white'])
        self.outer.pack(fill=tk.BOTH, expand=True, pady=5)

        # === Верхняя часть: canvas + вертикальный скроллбар ===
        top = tk.Frame(self.outer, bg=COLORS['white'])
        top.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            top,
            bg=COLORS['white'],
            height=self.CANVAS_HEIGHT,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.v_scrollbar = tk.Scrollbar(
            top,
            orient=tk.VERTICAL,
            command=self.canvas.yview,
        )
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # === Нижняя часть: слева кнопка, справа h_scrollbar ===
        bottom = tk.Frame(self.outer, bg=COLORS['white'])
        bottom.pack(fill=tk.X)

        btn_holder = tk.Frame(
            bottom,
            bg=COLORS['white'],
            width=130,
            height=self.RUN_BTN_HEIGHT,
        )
        btn_holder.pack(side=tk.LEFT)
        btn_holder.pack_propagate(False)

        self.run_btn = tk.Button(
            btn_holder,
            text="▶ Запустить",
            command=self._on_run_click,
            bg=COLORS['save_btn_bg'],
            fg=COLORS['save_btn_fg'],
            font=('Arial', 10, 'bold'),
            relief='flat',
            bd=0,
            highlightthickness=0,
            cursor='hand2',
            activebackground=COLORS['save_btn_hover'],
            activeforeground=COLORS['save_btn_fg'],
        )
        self.run_btn.pack(fill=tk.BOTH, expand=True)

        scroll_holder = tk.Frame(
            bottom,
            bg=COLORS['white'],
            height=self.RUN_BTN_HEIGHT,
        )
        scroll_holder.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scroll_holder.pack_propagate(False)

        self.h_scrollbar = tk.Scrollbar(
            scroll_holder,
            orient=tk.HORIZONTAL,
            command=self.canvas.xview,
        )
        self.h_scrollbar.pack(side=tk.TOP, fill=tk.X)

        self.canvas.configure(
            xscrollcommand=self.h_scrollbar.set,
            yscrollcommand=self.v_scrollbar.set,
        )

        # Внутренний фрейм
        self.inner = tk.Frame(self.canvas, bg=COLORS['white'])
        self.canvas_window_id = self.canvas.create_window(
            (0, 0), window=self.inner, anchor='nw',
        )

        self.inner.bind('<Configure>', self._on_inner_configure)

        # Прокрутка колёсиком мыши
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-event.delta / 120), 'units')

        def bind_wheel(_):
            self.canvas.bind_all('<MouseWheel>', on_mousewheel)

        def unbind_wheel(_):
            self.canvas.unbind_all('<MouseWheel>')

        self.canvas.bind('<Enter>', bind_wheel)
        self.canvas.bind('<Leave>', unbind_wheel)

    def _on_inner_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _on_run_click(self):
        if self.on_run:
            self.on_run()

    # ------------------------------------------------------------------
    # Пересчёт размеров inner
    # ------------------------------------------------------------------
    def _update_inner_size(self):
        resource_names = self.get_resource_names()
        total_cols = 3 + max(self.MIN_RESOURCE_COLUMNS, len(resource_names))

        total_width = total_cols * self.W_NAME
        total_rows = len(self.rows)
        total_height = (
            self.HEADER_HEIGHT + self.BORDER +
            total_rows * (self.ROW_HEIGHT + self.BORDER)
        )

        self.canvas.itemconfigure(
            self.canvas_window_id,
            width=total_width,
            height=total_height,
        )
        self.canvas.configure(scrollregion=(0, 0, total_width, total_height))

    # ------------------------------------------------------------------
    # Заголовки
    # ------------------------------------------------------------------
    def _rebuild_header(self):
        resource_names = self.get_resource_names()

        fixed = [
            ('name', 'Название', self.W_NAME),
            ('duration', 'Длительность', self.W_DURATION),
            ('deps', 'Зависимости', self.W_DEPS),
        ]
        col_index = 0
        for key, text, width in fixed:
            self._make_header_cell(key, text, col_index, width)
            col_index += 1

        total_cols = max(self.MIN_RESOURCE_COLUMNS, len(resource_names))
        for i in range(total_cols):
            rname = resource_names[i] if i < len(resource_names) else ""
            key = f'res_{i}'
            self._make_header_cell(key, rname, col_index, self.W_RESOURCE)
            col_index += 1

    def _make_header_cell(self, key: str, text: str, col_index: int, width: int):
        x = col_index * width
        y = 0

        label = tk.Label(
            self.inner,
            text=text,
            font=('Arial', 10, 'bold'),
            bg=COLORS['excel_row_label_bg'],
            fg=COLORS['header'],
            anchor=tk.W,
            padx=6,
            bd=0,
            highlightthickness=0,
        )
        label.place(x=x, y=y,
                    width=width - self.BORDER,
                    height=self.HEADER_HEIGHT)

        sep_v = tk.Frame(self.inner, bg=COLORS['excel_cell_border'])
        sep_v.place(x=x + width - self.BORDER, y=y,
                    width=self.BORDER, height=self.HEADER_HEIGHT)

        self.header_widgets[key] = label

    # ------------------------------------------------------------------
    # Строки
    # ------------------------------------------------------------------
    def _create_initial_rows(self):
        for _ in range(self.INITIAL_ROWS):
            self._add_row()
        self._update_inner_size()

    def _add_row(self):
        row_index = len(self.rows)
        resource_names = self.get_resource_names()
        total_cols = max(self.MIN_RESOURCE_COLUMNS, len(resource_names))

        row_cells: Dict[str, tk.Widget] = {}
        row_frames: Dict[str, tk.Frame] = {}

        w, f = self._make_text_cell(row_index, 'name', self.W_NAME)
        row_cells['name'] = w
        row_frames['name'] = f

        w, f = self._make_text_cell(row_index, 'duration', self.W_DURATION)
        row_cells['duration'] = w
        row_frames['duration'] = f

        w, f = self._make_deps_cell(row_index, self.W_DEPS)
        row_cells['deps'] = w
        row_frames['deps'] = f

        for i in range(total_cols):
            key = f'res_{i}'
            w, f = self._make_text_cell(row_index, key, self.W_RESOURCE)
            row_cells[key] = w
            row_frames[key] = f

        for key in ('name', 'duration'):
            self._bind_autoadd(row_cells[key], row_index)
        for i in range(total_cols):
            self._bind_autoadd(row_cells[f'res_{i}'], row_index)

        self.rows.append(row_cells)
        self.row_frames.append(row_frames)

    def _bind_autoadd(self, widget: tk.Widget, row_index: int):
        widget.bind('<KeyRelease>', lambda e, r=row_index: self._on_cell_change(r))
        widget.bind('<FocusOut>',   lambda e, r=row_index: self._on_cell_change(r))

    def _make_text_cell(self, row_index: int, col_key: str, width: int):
        col_index = self._col_index_of(col_key)
        x = col_index * width
        y = (row_index + 1) * (self.ROW_HEIGHT + self.BORDER)

        text = tk.Text(
            self.inner,
            font=('Arial', 10),
            bg=COLORS['excel_cell_bg'],
            fg=COLORS['text'],
            relief='flat',
            bd=0,
            highlightthickness=0,
            wrap='none',
            height=1,
            padx=5, pady=7,
            insertbackground=COLORS['text'],
        )
        text.place(x=x, y=y,
                   width=width - self.BORDER,
                   height=self.ROW_HEIGHT)

        sep_h = tk.Frame(self.inner, bg=COLORS['excel_cell_border'])
        sep_h.place(x=x, y=y + self.ROW_HEIGHT,
                    width=width, height=self.BORDER)

        sep_v = tk.Frame(self.inner, bg=COLORS['excel_cell_border'])
        sep_v.place(x=x + width - self.BORDER, y=y,
                    width=self.BORDER, height=self.ROW_HEIGHT)

        return text, sep_h

    def _make_deps_cell(self, row_index: int, width: int):
        self._deps_values.setdefault(row_index, set())

        col_index = self._col_index_of('deps')
        x = col_index * width
        y = (row_index + 1) * (self.ROW_HEIGHT + self.BORDER)

        cell = tk.Frame(self.inner, bg=COLORS['excel_cell_bg'])
        cell.place(x=x, y=y,
                   width=width - self.BORDER,
                   height=self.ROW_HEIGHT)

        label = tk.Label(
            cell,
            text="",
            font=('Arial', 10),
            bg=COLORS['excel_cell_bg'],
            fg=COLORS['text'],
            anchor=tk.W,
            padx=10,
            bd=0,
            highlightthickness=0,
            cursor='hand2',
        )
        label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        arrow = tk.Label(
            cell,
            text="▼",
            font=('Arial', 8),
            bg=COLORS['excel_cell_bg'],
            fg=COLORS['text_light'],
            padx=4,
            cursor='hand2',
        )
        arrow.pack(side=tk.RIGHT)

        def open_menu(event, r=row_index):
            self._open_deps_menu(r, event)

        label.bind('<Button-1>', open_menu)
        arrow.bind('<Button-1>', open_menu)

        sep_h = tk.Frame(self.inner, bg=COLORS['excel_cell_border'])
        sep_h.place(x=x, y=y + self.ROW_HEIGHT,
                    width=width, height=self.BORDER)

        sep_v = tk.Frame(self.inner, bg=COLORS['excel_cell_border'])
        sep_v.place(x=x + width - self.BORDER, y=y,
                    width=self.BORDER, height=self.ROW_HEIGHT)

        wrapper = {'label': label, 'inner': cell, 'frame': cell, 'arrow': arrow}
        return wrapper, sep_h

    def _open_deps_menu(self, row_index: int, event):
        menu = tk.Menu(self.canvas, tearoff=0, font=('Arial', 10))
        current = self._deps_values.get(row_index, set())

        candidates = []
        for i, row in enumerate(self.rows):
            tid = i + 1
            if tid == row_index + 1:
                continue
            name = row['name'].get('1.0', 'end-1c').strip()
            if not name:
                continue
            candidates.append((tid, name))

        if not candidates:
            menu.add_command(label="(нет доступных задач)", state='disabled')
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
            return

        candidates.sort(key=lambda x: x[0])

        for tid, name in candidates:
            var = tk.BooleanVar(value=(tid in current))

            def toggle(t=tid, v=var, r=row_index):
                if v.get():
                    self._deps_values.setdefault(r, set()).add(t)
                else:
                    self._deps_values.setdefault(r, set()).discard(t)
                self._refresh_deps_label(r)

            menu.add_checkbutton(
                label=f"{name} (ID {tid})",
                variable=var,
                command=toggle,
            )

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _refresh_deps_label(self, row_index: int):
        deps = sorted(self._deps_values.get(row_index, set()))
        text = ",".join(str(d) for d in deps)
        cell = self.rows[row_index]['deps']
        cell['label'].configure(text=text)

    # ------------------------------------------------------------------
    # Вспомогательное
    # ------------------------------------------------------------------
    def _col_index_of(self, col_key: str) -> int:
        if col_key == 'name':
            return 0
        if col_key == 'duration':
            return 1
        if col_key == 'deps':
            return 2
        if col_key.startswith('res_'):
            return 3 + int(col_key.split('_')[1])
        raise ValueError(f"Неизвестный ключ столбца: {col_key}")

    def _on_cell_change(self, row_index: int):
        if row_index != len(self.rows) - 1:
            return

        row = self.rows[row_index]
        has_data = False

        name_val = row['name'].get('1.0', 'end-1c').strip()
        dur_val = row['duration'].get('1.0', 'end-1c').strip()
        if name_val or dur_val:
            has_data = True

        if self._deps_values.get(row_index):
            has_data = True

        for key, widget in row.items():
            if key in ('name', 'duration', 'deps'):
                continue
            try:
                if widget.get('1.0', 'end-1c').strip():
                    has_data = True
                    break
            except AttributeError:
                continue

        if has_data:
            self._add_row()

    # ------------------------------------------------------------------
    # Публичное API
    # ------------------------------------------------------------------
    def get_tasks(self) -> List[dict]:
        resource_names = self.get_resource_names()
        result = []

        for i, row in enumerate(self.rows):
            name = row['name'].get('1.0', 'end-1c').strip()
            dur_str = row['duration'].get('1.0', 'end-1c').strip()

            if not name:
                continue

            try:
                duration = int(dur_str) if dur_str else 0
            except ValueError:
                duration = 0

            resources: Dict[str, int] = {}
            for j, rname in enumerate(resource_names):
                key = f'res_{j}'
                if key not in row:
                    continue
                val_str = row[key].get('1.0', 'end-1c').strip()
                try:
                    val = int(val_str) if val_str else 0
                except ValueError:
                    val = 0
                if val > 0:
                    resources[rname] = val

            result.append({
                'id': i + 1,
                'name': name,
                'duration': duration,
                'resources': resources,
            })

        return result

    def get_dependencies(self) -> Dict[int, List[int]]:
        result: Dict[int, List[int]] = {}
        for i in range(len(self.rows)):
            deps = sorted(self._deps_values.get(i, set()))
            if deps:
                result[i + 1] = deps
        return result

    def _reset_inner(self):
        self.inner.destroy()
        self.inner = tk.Frame(self.canvas, bg=COLORS['white'])
        self.canvas_window_id = self.canvas.create_window(
            (0, 0), window=self.inner, anchor='nw',
        )
        self.inner.bind('<Configure>', self._on_inner_configure)

    def clear(self):
        self._reset_inner()
        self.rows = []
        self.row_frames = []
        self.header_widgets = {}
        self._deps_values = {}

        self.canvas.yview_moveto(0)
        self.canvas.xview_moveto(0)

        self._rebuild_header()
        self._create_initial_rows()

    def rebuild(self):
        self._reset_inner()
        self.rows = []
        self.row_frames = []
        self.header_widgets = {}
        self._deps_values = {}

        self.canvas.yview_moveto(0)
        self.canvas.xview_moveto(0)

        self._rebuild_header()
        self._create_initial_rows()

    def set_tasks(self, tasks: List[dict], dependencies: Dict[int, List[int]]):
        self.clear()

        resource_names = self.get_resource_names()
        n = len(tasks)

        while len(self.rows) < n:
            self._add_row()

        for i, task in enumerate(tasks):
            row = self.rows[i]

            row['name'].delete('1.0', 'end')
            row['name'].insert('1.0', task.get('name', ''))

            row['duration'].delete('1.0', 'end')
            row['duration'].insert('1.0', str(task.get('duration', '')))

            resources = task.get('resources', {})
            for j, rname in enumerate(resource_names):
                key = f'res_{j}'
                if key not in row:
                    continue
                val = resources.get(rname, 0)
                row[key].delete('1.0', 'end')
                row[key].insert('1.0', str(val) if val > 0 else '')

            self._deps_values[i] = set(dependencies.get(task.get('id', i + 1), []))
            self._refresh_deps_label(i)

        self._add_row()
        self._update_inner_size()

        self.canvas.yview_moveto(0)
        self.canvas.xview_moveto(0)