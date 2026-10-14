"""
Таблица ресурсов в стиле Excel.

Особенности:
- 10 пустых столбцов по умолчанию.
- Верхняя граница у первой строки таблицы.
- Все элементы выровнены попиксельно через place.
- tk.Text вместо tk.Entry (у Text нет проблемных внутренних отступов).
- Автодобавление столбца при заполнении последнего.
- Кнопка «Сохранить» встроена в левую колонку.
"""
import tkinter as tk
from typing import Callable, Dict, List, Optional

from ..theme import COLORS


class ExcelResourceTable:
    """Таблица ресурсов в стиле Excel."""

    # ------------------------------------------------------------------
    # Размеры (в пикселях)
    # ------------------------------------------------------------------
    ROW_HEIGHT = 30
    LABEL_WIDTH = 130
    CELL_WIDTH = 130
    BORDER = 1
    SAVE_BTN_HEIGHT = 30
    SCROLLBAR_HEIGHT = 0
    INITIAL_COLUMNS = 10

    # ------------------------------------------------------------------
    # Конструктор
    # ------------------------------------------------------------------
    def __init__(self, parent: tk.Widget, on_save: Optional[Callable] = None):
        """
        parent — родительский виджет (фрейм).
        on_save — колбэк, вызывается при нажатии «💾 Сохранить».
        """
        self.parent = parent
        self.on_save = on_save

        # cells[0] = список Text-виджетов для названий
        # cells[1] = список Text-виджетов для количеств
        self.cells: List[List[tk.Text]] = []

        # Сохраняем все фреймы столбцов, чтобы уметь очищать таблицу
        self.column_frames: List[tk.Frame] = []

        self._create_widgets()
        self._create_initial_columns()

    # ------------------------------------------------------------------
    # Каркас
    # ------------------------------------------------------------------
    def _create_widgets(self):
        total_height = (
            self.BORDER +
            self.ROW_HEIGHT +
            self.BORDER +
            self.ROW_HEIGHT +
            self.BORDER +
            self.SCROLLBAR_HEIGHT +
            self.SAVE_BTN_HEIGHT
        )

        outer = tk.Frame(self.parent, bg=COLORS['white'], height=total_height)
        outer.pack(fill=tk.X, pady=5)
        outer.pack_propagate(False)

        # ===== Левая колонка: подписи + кнопка «Сохранить» =====
        labels_container = tk.Frame(
            outer,
            bg=COLORS['excel_cell_border'],
            width=self.LABEL_WIDTH,
            height=total_height,
        )
        labels_container.pack(side=tk.LEFT, fill=tk.Y)
        labels_container.pack_propagate(False)

        inner_w = self.LABEL_WIDTH
        y = self.BORDER

        # Строка «Название»
        self.name_label = tk.Label(
            labels_container,
            text="Название",
            font=('Arial', 10, 'bold'),
            bg=COLORS['excel_row_label_bg'],
            fg=COLORS['header'],
            anchor=tk.W,
            padx=6,
            bd=0,
            highlightthickness=0,
        )
        self.name_label.place(x=0, y=y, width=inner_w, height=self.ROW_HEIGHT)
        y += self.ROW_HEIGHT

        # Разделитель
        sep1 = tk.Frame(labels_container, bg=COLORS['excel_cell_border'])
        sep1.place(x=0, y=y, width=inner_w, height=self.BORDER)
        y += self.BORDER

        # Строка «Количество»
        self.count_label = tk.Label(
            labels_container,
            text="Количество",
            font=('Arial', 10, 'bold'),
            bg=COLORS['excel_row_label_bg'],
            fg=COLORS['header'],
            anchor=tk.W,
            padx=6,
            bd=0,
            highlightthickness=0,
        )
        self.count_label.place(x=0, y=y, width=inner_w, height=self.ROW_HEIGHT)
        y += self.ROW_HEIGHT

        # Нижняя граница таблицы
        sep2 = tk.Frame(labels_container, bg=COLORS['excel_cell_border'])
        sep2.place(x=0, y=y, width=inner_w, height=self.BORDER)
        y += self.BORDER

        # Пустое место под скроллбар
        spacer = tk.Frame(labels_container, bg=COLORS['excel_row_label_bg'])
        spacer.place(x=0, y=y, width=inner_w, height=self.SCROLLBAR_HEIGHT)
        y += self.SCROLLBAR_HEIGHT

        # Кнопка «Сохранить» — на всю ширину левой колонки
        self.save_btn = tk.Button(
            labels_container,
            text="💾 Сохранить",
            command=self._on_save_click,
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
        self.save_btn.place(x=0, y=y, width=inner_w, height=self.SAVE_BTN_HEIGHT)

        # ===== Правая часть: canvas со столбцами =====
        table_container = tk.Frame(outer, bg=COLORS['white'])
        table_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        canvas_height = (
            self.BORDER +
            self.ROW_HEIGHT +
            self.BORDER +
            self.ROW_HEIGHT +
            self.BORDER
        )

        self.canvas = tk.Canvas(
            table_container,
            bg=COLORS['white'],
            height=canvas_height,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(side=tk.TOP, fill=tk.X)

        self.h_scrollbar = tk.Scrollbar(
            table_container,
            orient=tk.HORIZONTAL,
            command=self.canvas.xview,
        )
        self.h_scrollbar.pack(side=tk.TOP, fill=tk.X)

        self.canvas.configure(xscrollcommand=self.h_scrollbar.set)

        # Внутренний фрейм — в нём лежат столбцы
        self.inner = tk.Frame(self.canvas, bg=COLORS['white'])
        self.canvas.create_window((0, 0), window=self.inner, anchor='nw')

        self.inner.bind('<Configure>', self._on_inner_configure)

    def _on_inner_configure(self, event):
        """При изменении размеров внутреннего фрейма — обновляем scrollregion."""
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _on_save_click(self):
        """Прокидывает клик по кнопке наружу."""
        if self.on_save:
            self.on_save()

    # ------------------------------------------------------------------
    # Столбцы
    # ------------------------------------------------------------------
    def _create_initial_columns(self):
        for _ in range(self.INITIAL_COLUMNS):
            self._add_column()

    def _add_column(self):
        """Добавляет новый столбец: (Название, Количество)."""
        col_index = len(self.cells[0]) if self.cells else 0

        col_w = self.CELL_WIDTH
        col_h = (
            self.BORDER +
            self.ROW_HEIGHT +
            self.BORDER +
            self.ROW_HEIGHT +
            self.BORDER
        )

        # Внешний фрейм столбца (фон = цвет границ)
        col_frame = tk.Frame(
            self.inner,
            bg=COLORS['excel_cell_border'],
            width=col_w,
            height=col_h,
        )
        col_frame.grid(row=0, column=col_index, padx=0, pady=0)
        col_frame.grid_propagate(False)
        col_frame.pack_propagate(False)

        cell_w = col_w - self.BORDER

        # --- Верхняя ячейка (Название) ---
        name_text = tk.Text(
            col_frame,
            font=('Arial', 10),
            bg=COLORS['excel_cell_bg'],
            fg=COLORS['text'],
            relief='flat',
            bd=0,
            highlightthickness=0,
            wrap='none',
            height=1,
            padx=5,
            pady=7,
            insertbackground=COLORS['text'],
        )
        name_text.place(x=0, y=self.BORDER, width=cell_w, height=self.ROW_HEIGHT)

        # Разделитель ровно посередине
        sep = tk.Frame(col_frame, bg=COLORS['excel_cell_border'])
        sep.place(x=0, y=self.BORDER + self.ROW_HEIGHT,
                  width=col_w, height=self.BORDER)

        # --- Нижняя ячейка (Количество) ---
        count_text = tk.Text(
            col_frame,
            font=('Arial', 10),
            bg=COLORS['excel_cell_bg'],
            fg=COLORS['text'],
            relief='flat',
            bd=0,
            highlightthickness=0,
            wrap='none',
            height=1,
            padx=5,
            pady=7,
            insertbackground=COLORS['text'],
        )
        count_text.place(x=0,
                         y=self.BORDER + self.ROW_HEIGHT + self.BORDER,
                         width=cell_w, height=self.ROW_HEIGHT)

        # Автодобавление: как только пользователь что-то ввёл
        # в последний столбец — создаём следующий пустой.
        name_text.bind('<KeyRelease>', lambda e, c=col_index: self._on_cell_change(c))
        name_text.bind('<FocusOut>', lambda e, c=col_index: self._on_cell_change(c))
        count_text.bind('<KeyRelease>', lambda e, c=col_index: self._on_cell_change(c))
        count_text.bind('<FocusOut>', lambda e, c=col_index: self._on_cell_change(c))

        if not self.cells:
            self.cells = [[name_text], [count_text]]
        else:
            self.cells[0].append(name_text)
            self.cells[1].append(count_text)

        self.column_frames.append(col_frame)

    def _on_cell_change(self, col_index: int):
        """Если это последний столбец и в нём есть данные — добавляем новый."""
        if col_index != len(self.cells[0]) - 1:
            return

        name_val = self.cells[0][col_index].get('1.0', 'end-1c').strip()
        count_val = self.cells[1][col_index].get('1.0', 'end-1c').strip()

        if name_val or count_val:
            self._add_column()

    # ------------------------------------------------------------------
    # Публичное API
    # ------------------------------------------------------------------
    def add_resource(self, name: str, count: int):
        """
        Добавляет ресурс в первый свободный столбец.
        Используется при загрузке проекта из JSON.
        """
        if self.cells:
            last = len(self.cells[0]) - 1
            name_val = self.cells[0][last].get('1.0', 'end-1c').strip()
            count_val = self.cells[1][last].get('1.0', 'end-1c').strip()
            if name_val or count_val:
                self._add_column()

        last = len(self.cells[0]) - 1
        self.cells[0][last].delete('1.0', 'end')
        self.cells[0][last].insert('1.0', name)
        self.cells[1][last].delete('1.0', 'end')
        self.cells[1][last].insert('1.0', str(count))

        self._add_column()

    def get_resources(self) -> Dict[str, int]:
        """
        Возвращает словарь {имя_ресурса: количество}, собранный из таблицы.
        Пустые ячейки и нули игнорируются.
        """
        resources: Dict[str, int] = {}
        for i in range(len(self.cells[0])):
            name = self.cells[0][i].get('1.0', 'end-1c').strip()
            count_str = self.cells[1][i].get('1.0', 'end-1c').strip()

            if not name:
                continue

            try:
                count = int(count_str) if count_str else 0
                if count > 0:
                    resources[name] = count
            except ValueError:
                pass

        return resources

    def clear(self):
        """Полностью очищает таблицу и создаёт INITIAL_COLUMNS пустых столбцов."""
        for frame in self.column_frames:
            frame.destroy()
        self.cells = []
        self.column_frames = []
        for _ in range(self.INITIAL_COLUMNS):
            self._add_column()