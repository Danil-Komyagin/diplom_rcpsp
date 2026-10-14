"""
Прокручиваемая таблица использования ресурсов по дням.

Используется для двух отчётов:
- потребность ресурсов (сколько занято в каждый день),
- доступность ресурсов (сколько свободно в каждый день).

Структура:
    Строки    — ресурсы (R1, R2, ...).
    Столбцы   — дни (Д.1, Д.2, ...).

Особенности:
- Вертикальный скроллбар справа.
- Горизонтальный скроллбар снизу.
- +1 запасная строка снизу для «воздуха».
"""
import tkinter as tk
from typing import Dict, List


from ..theme import COLORS


class ResourceUsageTable:
    """Таблица использования ресурсов по дням."""

    ROW_HEIGHT = 30
    HEADER_HEIGHT = 30
    BORDER = 1

    W_LABEL = 130    # ширина столбца с названием ресурса
    W_CELL = 60      # ширина ячейки одного дня

    # ------------------------------------------------------------------
    # Конструктор
    # ------------------------------------------------------------------
    def __init__(self, parent: tk.Widget,
                 title: str = "",
                 mode: str = "usage"):
        self.parent = parent
        self.title = title
        self.mode = mode

        self.resource_names: List[str] = []
        self.resource_limits: Dict[str, int] = {}
        self.schedule: Dict[int, tuple] = {}
        self.makespan: int = 0

        self._create_widgets()

    # ------------------------------------------------------------------
    # Каркас
    # ------------------------------------------------------------------
    def _create_widgets(self):
        self.outer = tk.Frame(self.parent, bg=COLORS['white'])
        self.outer.pack(fill=tk.BOTH, expand=True)

        if self.title:
            title_lbl = tk.Label(
                self.outer,
                text=self.title,
                font=('Arial', 10, 'bold'),
                bg=COLORS['white'],
                fg=COLORS['header'],
                anchor=tk.W,
            )
            title_lbl.pack(fill=tk.X, padx=4, pady=(4, 2))

        # === Верхняя часть: canvas + вертикальный скроллбар ===
        top = tk.Frame(self.outer, bg=COLORS['white'])
        top.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            top,
            bg=COLORS['white'],
            height=100,
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

        # === Нижняя часть: горизонтальный скроллбар ===
        self.h_scrollbar = tk.Scrollbar(
            self.outer,
            orient=tk.HORIZONTAL,
            command=self.canvas.xview,
        )
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas.configure(
            xscrollcommand=self.h_scrollbar.set,
            yscrollcommand=self.v_scrollbar.set,
        )

        self.inner = tk.Frame(self.canvas, bg=COLORS['white'])
        self.canvas_window_id = self.canvas.create_window(
            (0, 0), window=self.inner, anchor='nw',
        )

    # ------------------------------------------------------------------
    # Публичное API
    # ------------------------------------------------------------------
    def update_data(self,
                    resource_names: List[str],
                    resource_limits: Dict[str, int],
                    schedule: Dict[int, tuple],
                    makespan: int,
                    tasks_by_id: Dict[int, object]):
        """Заполняет таблицу данными."""
        self.resource_names = list(resource_names)
        self.resource_limits = dict(resource_limits)
        self.schedule = schedule
        self.makespan = makespan

        self._clear_inner()
        self._build(tasks_by_id)

    # ------------------------------------------------------------------
    # Служебное
    # ------------------------------------------------------------------
    def _clear_inner(self):
        self.inner.destroy()
        self.inner = tk.Frame(self.canvas, bg=COLORS['white'])
        self.canvas_window_id = self.canvas.create_window(
            (0, 0), window=self.inner, anchor='nw',
        )

    def _update_inner_size(self, total_cols: int, total_rows: int):
        """
        total_rows — число РЕАЛЬНЫХ строк (ресурсов).
        К нему добавляем +1 запасную строку снизу.
        """
        rows_with_padding = total_rows + 1

        total_width = self.W_LABEL + total_cols * (self.W_CELL + self.BORDER)
        total_height = (
            self.HEADER_HEIGHT + self.BORDER +
            rows_with_padding * (self.ROW_HEIGHT + self.BORDER)
        )

        self.canvas.itemconfigure(
            self.canvas_window_id,
            width=total_width,
            height=total_height,
        )
        self.canvas.configure(
            width=min(total_width, 900),
            height=min(total_height, 200),
            scrollregion=(0, 0, total_width, total_height),
        )

    # ------------------------------------------------------------------
    # Построение таблицы
    # ------------------------------------------------------------------
    def _build(self, tasks_by_id: Dict[int, object]):
        if not self.resource_names or self.makespan <= 0:
            empty = tk.Label(
                self.inner,
                text="Нет данных. Запустите планирование.",
                font=('Arial', 10, 'italic'),
                bg=COLORS['white'],
                fg=COLORS['text_light'],
            )
            empty.place(x=0, y=0, width=400, height=self.HEADER_HEIGHT)
            self._update_inner_size(total_cols=1, total_rows=0)
            return

        n_cols = self.makespan
        n_rows = len(self.resource_names)

        # Заголовки: пустая ячейка + Д.1..N
        self._make_header_cell(0, "")
        for d in range(n_cols):
            self._make_header_cell(d + 1, f"Д.{d + 1}")

        # Строки: ресурс + значения по дням
        for r, rname in enumerate(self.resource_names):
            self._make_label_cell(r, rname)
            for d in range(n_cols):
                value = self._compute_value(rname, d, tasks_by_id)
                self._make_data_cell(r, d + 1, value)

        self._update_inner_size(total_cols=n_cols + 1, total_rows=n_rows)

    def _compute_value(self, rname: str, day: int,
                       tasks_by_id: Dict[int, object]) -> int:
        """Считает значение для ячейки: занято или свободно."""
        used = 0
        for tid, (start, end) in self.schedule.items():
            if start <= day < end:
                task = tasks_by_id.get(tid)
                if task is not None:
                    used += task.resources.get(rname, 0)

        limit = self.resource_limits.get(rname, 0)

        if self.mode == 'usage':
            return used
        else:
            return max(0, limit - used)

    # ------------------------------------------------------------------
    # Ячейки
    # ------------------------------------------------------------------
    def _make_header_cell(self, col_index: int, text: str):
        x = self._x_of_col(col_index)
        y = 0
        width = self.W_LABEL if col_index == 0 else self.W_CELL

        label = tk.Label(
            self.inner,
            text=text,
            font=('Arial', 9, 'bold'),
            bg=COLORS['excel_row_label_bg'],
            fg=COLORS['header'],
            anchor=tk.CENTER,
            bd=0,
            highlightthickness=0,
        )
        label.place(x=x, y=y, width=width, height=self.HEADER_HEIGHT)

        sep = tk.Frame(self.inner, bg=COLORS['excel_cell_border'])
        sep.place(x=x + width, y=y, width=self.BORDER, height=self.HEADER_HEIGHT)

    def _make_label_cell(self, row_index: int, text: str):
        x = 0
        y = (row_index + 1) * (self.ROW_HEIGHT + self.BORDER)

        label = tk.Label(
            self.inner,
            text=text,
            font=('Arial', 9, 'bold'),
            bg=COLORS['excel_row_label_bg'],
            fg=COLORS['header'],
            anchor=tk.W,
            padx=6,
            bd=0,
            highlightthickness=0,
        )
        label.place(x=x, y=y, width=self.W_LABEL, height=self.ROW_HEIGHT)

        sep_h = tk.Frame(self.inner, bg=COLORS['excel_cell_border'])
        sep_h.place(x=x, y=y + self.ROW_HEIGHT,
                    width=self.W_LABEL, height=self.BORDER)

        sep_v = tk.Frame(self.inner, bg=COLORS['excel_cell_border'])
        sep_v.place(x=x + self.W_LABEL, y=y,
                    width=self.BORDER, height=self.ROW_HEIGHT)

    def _make_data_cell(self, row_index: int, col_index: int, value: int):
        x = self._x_of_col(col_index)
        y = (row_index + 1) * (self.ROW_HEIGHT + self.BORDER)

        bg = COLORS['excel_cell_bg']
        if self.mode == 'usage':
            limit = self.resource_limits.get(
                self.resource_names[row_index], 0)
            if limit > 0:
                ratio = value / limit
                if ratio >= 0.99:
                    bg = '#ffcccc'   # плотно занято
                elif ratio >= 0.6:
                    bg = '#ffe4b3'   # средне
                else:
                    bg = '#e6f7e6'   # свободно

        label = tk.Label(
            self.inner,
            text=str(value),
            font=('Arial', 9),
            bg=bg,
            fg=COLORS['text'],
            anchor=tk.CENTER,
            bd=0,
            highlightthickness=0,
        )
        label.place(x=x, y=y, width=self.W_CELL, height=self.ROW_HEIGHT)

        sep_h = tk.Frame(self.inner, bg=COLORS['excel_cell_border'])
        sep_h.place(x=x, y=y + self.ROW_HEIGHT,
                    width=self.W_CELL, height=self.BORDER)

        sep_v = tk.Frame(self.inner, bg=COLORS['excel_cell_border'])
        sep_v.place(x=x + self.W_CELL, y=y,
                    width=self.BORDER, height=self.ROW_HEIGHT)

    def _x_of_col(self, col_index: int) -> int:
        """Смещение по X для столбца: первый — W_LABEL, дальше — W_CELL."""
        if col_index == 0:
            return 0
        return self.W_LABEL + self.BORDER + (col_index - 1) * (self.W_CELL + self.BORDER)