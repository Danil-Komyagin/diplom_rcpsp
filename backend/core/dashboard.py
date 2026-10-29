"""
Генерация дашборда: диаграмма Ганта + таблицы ресурсов на одной картинке.

Возвращает PIL.Image.Image, который потом можно положить на tk.Canvas
с прокруткой.

Структура дашборда (сверху вниз):
    📈 Диаграмма Ганта
    📊 Потребность ресурсов по дням
    📈 Доступность ресурсов по дням
"""
from typing import Dict, List

from PIL import Image, ImageDraw, ImageFont

from .models import Project
from .schedulers import Schedule


# ============================================================================
# РАЗМЕРЫ
# ============================================================================
PADDING = 10
ROW_HEIGHT = 26
HEADER_HEIGHT = 26
LABEL_WIDTH = 160
DAY_WIDTH = 32
GANTT_BAR_HEIGHT = 18
SECTION_GAP = 20


# ============================================================================
# ЦВЕТА
# ============================================================================
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY_BORDER = (160, 160, 160)
HEADER_BG = (232, 245, 233)
TEXT = (44, 62, 80)
TEXT_LIGHT = (93, 109, 126)

BAR_COLORS = [
    (52, 152, 219), (231, 76, 60), (39, 174, 96), (243, 156, 18),
    (155, 89, 182), (26, 188, 156), (230, 126, 34), (52, 73, 94),
    (22, 160, 133), (192, 57, 43),
]


# ============================================================================
# ШРИФТЫ
# ============================================================================
def _get_font(size: int = 11):
    """Пытается загрузить шрифт, если не получилось — дефолтный."""
    for name in ("arial.ttf", "DejaVuSans.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================================
def build_dashboard(project: Project, schedule: Schedule) -> Image.Image:
    """
    Строит единую картинку:
        [Диаграмма Ганта]
        [Таблица потребности]
        [Таблица доступности]

    Возвращает PIL.Image.Image.
    """
    if not project.tasks or not schedule:
        img = Image.new('RGB', (800, 200), WHITE)
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), "Нет данных. Запустите планирование.",
                  fill=TEXT_LIGHT, font=_get_font(14))
        return img

    task_ids = list(schedule.keys())
    makespan = max(end for _, end in schedule.values())
    resource_names = list(project.resource_limits.keys())
    tasks_by_id = {t.id: t for t in project.tasks}

    n_tasks = len(task_ids)
    n_resources = len(resource_names)

    # Высота диаграммы Ганта
    gantt_height = HEADER_HEIGHT + n_tasks * ROW_HEIGHT

    # Высота каждой таблицы
    table_height = HEADER_HEIGHT + n_resources * ROW_HEIGHT

    # Общая ширина
    total_width = LABEL_WIDTH + makespan * DAY_WIDTH + PADDING * 2

    # Общая высота
    total_height = (
        PADDING +
        gantt_height + 30 +    # +30 на заголовок
        SECTION_GAP +
        table_height + 30 +
        SECTION_GAP +
        table_height + 30 +
        PADDING
    )

    img = Image.new('RGB', (total_width, total_height), WHITE)
    draw = ImageDraw.Draw(img)

    font_bold = _get_font(12)
    font_normal = _get_font(11)
    font_small = _get_font(9)

    y = PADDING

    # ============================================================
    # 1. ДИАГРАММА ГАНТА
    # ============================================================
    draw.text((PADDING, y), f"📈 Диаграмма Ганта — makespan = {makespan} дней",
              fill=TEXT, font=font_bold)
    y += 30

    # Заголовки дней
    x0 = PADDING + LABEL_WIDTH
    for d in range(makespan):
        x1 = x0 + d * DAY_WIDTH
        draw.rectangle([x1, y, x1 + DAY_WIDTH, y + HEADER_HEIGHT],
                       fill=HEADER_BG, outline=GRAY_BORDER)
        draw.text((x1 + 4, y + 6), f"{d + 1}", fill=TEXT, font=font_small)

    # Метка "Задачи"
    draw.rectangle([PADDING, y, PADDING + LABEL_WIDTH, y + HEADER_HEIGHT],
                   fill=HEADER_BG, outline=GRAY_BORDER)
    draw.text((PADDING + 6, y + 6), "Задачи", fill=TEXT, font=font_small)
    y += HEADER_HEIGHT

    # Строки задач
    ordered = sorted(schedule.items(), key=lambda kv: (kv[1][0], kv[0]))
    for tid, (start, end) in ordered:
        task = tasks_by_id.get(tid)
        if task is None:
            continue

        # Метка задачи
        draw.rectangle([PADDING, y, PADDING + LABEL_WIDTH, y + ROW_HEIGHT],
                       fill=WHITE, outline=GRAY_BORDER)
        label = f"ID{tid}: {task.name}"
        if len(label) > 22:
            label = label[:22]
        draw.text((PADDING + 6, y + 6), label, fill=TEXT, font=font_normal)

        # Пустые ячейки дней
        for d in range(makespan):
            cx = PADDING + LABEL_WIDTH + d * DAY_WIDTH
            draw.rectangle([cx, y, cx + DAY_WIDTH, y + ROW_HEIGHT],
                           fill=WHITE, outline=GRAY_BORDER)

        # Полоса задачи
        bar_x = PADDING + LABEL_WIDTH + start * DAY_WIDTH
        bar_w = (end - start) * DAY_WIDTH
        bar_color = BAR_COLORS[tid % len(BAR_COLORS)]

        bar_top = y + (ROW_HEIGHT - GANTT_BAR_HEIGHT) // 2
        bar_bottom = y + (ROW_HEIGHT + GANTT_BAR_HEIGHT) // 2
        draw.rectangle([bar_x, bar_top, bar_x + bar_w, bar_bottom],
                       fill=bar_color, outline=BLACK)

        # Подпись длительности
        duration = end - start
        draw.text((bar_x + 4, y + 7), f"{duration}д",
                  fill=WHITE, font=font_small)

        y += ROW_HEIGHT

    y += SECTION_GAP

    # ============================================================
    # 2. ТАБЛИЦА ПОТРЕБНОСТИ РЕСУРСОВ
    # ============================================================
    draw.text((PADDING, y), "📊 Потребность ресурсов по дням",
              fill=TEXT, font=font_bold)
    y += 30

    _draw_resource_table(draw, y, project, schedule, makespan,
                         resource_names, tasks_by_id, mode='usage',
                         font_normal=font_normal, font_small=font_small)
    y += table_height + SECTION_GAP

    # ============================================================
    # 3. ТАБЛИЦА ДОСТУПНОСТИ РЕСУРСОВ
    # ============================================================
    draw.text((PADDING, y), "📈 Доступность ресурсов по дням",
              fill=TEXT, font=font_bold)
    y += 30

    _draw_resource_table(draw, y, project, schedule, makespan,
                         resource_names, tasks_by_id, mode='available',
                         font_normal=font_normal, font_small=font_small)

    return img


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ
# ============================================================================
def _draw_resource_table(draw, y_start, project, schedule, makespan,
                         resource_names, tasks_by_id, mode,
                         font_normal, font_small):
    """Рисует одну таблицу использования ресурсов."""
    y = y_start

    # Заголовки
    draw.rectangle([PADDING, y, PADDING + LABEL_WIDTH, y + HEADER_HEIGHT],
                   fill=HEADER_BG, outline=GRAY_BORDER)
    draw.text((PADDING + 6, y + 6), "Ресурс", fill=TEXT, font=font_small)

    for d in range(makespan):
        cx = PADDING + LABEL_WIDTH + d * DAY_WIDTH
        draw.rectangle([cx, y, cx + DAY_WIDTH, y + HEADER_HEIGHT],
                       fill=HEADER_BG, outline=GRAY_BORDER)
        draw.text((cx + 4, y + 6), f"Д{d + 1}", fill=TEXT, font=font_small)
    y += HEADER_HEIGHT

    # Строки ресурсов
    for rname in resource_names:
        # Метка ресурса
        draw.rectangle([PADDING, y, PADDING + LABEL_WIDTH, y + ROW_HEIGHT],
                       fill=HEADER_BG, outline=GRAY_BORDER)
        label = rname
        if len(label) > 22:
            label = label[:22]
        draw.text((PADDING + 6, y + 6), label, fill=TEXT, font=font_normal)

        for d in range(makespan):
            cx = PADDING + LABEL_WIDTH + d * DAY_WIDTH
            value = _compute_resource_value(schedule, tasks_by_id,
                                            rname, d, mode,
                                            project.resource_limits)
            draw.rectangle([cx, y, cx + DAY_WIDTH, y + ROW_HEIGHT],
                           fill=WHITE, outline=GRAY_BORDER)
            # Центрируем число в ячейке
            text_x = cx + DAY_WIDTH // 2 - 4
            draw.text((text_x, y + 6), str(value), fill=TEXT, font=font_small)

        y += ROW_HEIGHT


def _compute_resource_value(schedule, tasks_by_id, rname, day, mode, limits) -> int:
    """Считает значение ячейки — занято или свободно."""
    used = 0
    for tid, (start, end) in schedule.items():
        if start <= day < end:
            task = tasks_by_id.get(tid)
            if task is not None:
                used += task.resources.get(rname, 0)
    if mode == 'usage':
        return used
    else:
        return max(0, limits.get(rname, 0) - used)