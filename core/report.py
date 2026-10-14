"""
Экспорт отчётов: таблица использования ресурсов по дням.

Формат таблицы:
    Строки — ресурсы + строка "Задачи" (список ID задач, активных в этот день).
    Столбцы — дни проекта (реальные даты, начиная с заданной даты старта).
    В ячейке — суммарное потребление ресурса в этот день.

Функции:
    export_resource_table_csv(project, schedule, path, start_date) -> bool
    export_resource_table_txt(project, schedule, path, start_date) -> bool
"""
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from .models import Project
from .schedulers import Schedule


# ============================================================================
# ОБЩИЕ УТИЛИТЫ
# ============================================================================
def _day_labels(start_date: datetime, makespan: int) -> List[str]:
    """
    Список меток дней: 'День 1 (01.01.2025)', 'День 2 (02.01.2025)' и т.д.
    Если start_date не задан — просто 'День 1', 'День 2', ...
    """
    labels = []
    for d in range(makespan):
        if start_date is not None:
            date = start_date + timedelta(days=d)
            labels.append(f"День {d + 1}\n({date.strftime('%d.%m.%Y')})")
        else:
            labels.append(f"День {d + 1}")
    return labels


def _tasks_active_on_day(schedule: Schedule, day: int) -> List[int]:
    """Список ID задач, активных в указанный день (сортирован по возрастанию)."""
    active = [tid for tid, (start, end) in schedule.items() if start <= day < end]
    return sorted(active)


def _resource_usage_row(
    project: Project,
    schedule: Schedule,
    resource_name: str,
    makespan: int,
) -> List[int]:
    """
    Строка использования одного ресурса по всем дням проекта.
    В ячейке — суммарное потребление ресурса в этот день.
    """
    tasks_by_id = {t.id: t for t in project.tasks}
    row = []
    for day in range(makespan):
        total = 0
        for tid, (start, end) in schedule.items():
            if start <= day < end:
                total += tasks_by_id[tid].resources.get(resource_name, 0)
        row.append(total)
    return row


def _build_table(
    project: Project,
    schedule: Schedule,
    start_date: datetime,
) -> Tuple[List[str], List[List[str]]]:
    """
    Строит таблицу: (заголовки, строки).

    Заголовки:
        ['Ресурс / День', 'День 1 (...)', 'День 2 (...)', ...]

    Строки:
        [['Ресурс R1', usage1, usage2, ...],
         ['Ресурс R2', ...],
         ...,
         ['Задачи', '1,3', '1,3,5', '5', ...]]
    """
    if not schedule:
        raise ValueError("Пустое расписание — нечего выгружать")

    makespan = max(end for _, end in schedule.values())
    day_labels = _day_labels(start_date, makespan)

    headers = ["Ресурс / День"] + day_labels
    rows: List[List[str]] = []

    # Строка по каждому ресурсу
    for rname in project.resource_limits.keys():
        usage_row = _resource_usage_row(project, schedule, rname, makespan)
        rows.append([rname] + [str(v) for v in usage_row])

    # Строка "Лимит" — общий лимит каждого ресурса (для наглядности)
    limit_row = ["Лимит"] + [""] * makespan
    rows.append(limit_row)
    for rname in project.resource_limits.keys():
        rows[-1] = rows[-1]  # placeholder — оставим для наглядности в будущем

    # Строка "Задачи" — какие задачи активны в этот день
    tasks_row = ["Задачи"]
    for day in range(makespan):
        active = _tasks_active_on_day(schedule, day)
        tasks_row.append(", ".join(str(t) for t in active))
    rows.append(tasks_row)

    return headers, rows


# ============================================================================
# CSV (для Excel)
# ============================================================================
def export_resource_table_csv(
    project: Project,
    schedule: Schedule,
    path: str,
    start_date: datetime = None,
) -> bool:
    """
    Выгружает таблицу ресурсов в CSV-файл.

    start_date — дата начала проекта (для реальных дат в шапке).
    Возвращает True при успехе, False при ошибке.
    """
    try:
        headers, rows = _build_table(project, schedule, start_date)

        # Excel корректно открывает CSV с BOM utf-8-sig
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow([project.name])
            writer.writerow([])
            writer.writerow(headers)
            writer.writerows(rows)

        return True
    except Exception as e:
        print(f"Ошибка экспорта в CSV: {e}")
        return False


# ============================================================================
# TXT (для Word)
# ============================================================================
def export_resource_table_txt(
    project: Project,
    schedule: Schedule,
    path: str,
    start_date: datetime = None,
) -> bool:
    """
    Выгружает таблицу ресурсов в текстовый файл.

    Формат — простая ASCII-таблица с рамками из символов +, -, |.
    Хорошо копируется в Word.
    """
    try:
        headers, rows = _build_table(project, schedule, start_date)

        # Ширины столбцов
        n_cols = len(headers)
        widths = [0] * n_cols
        for i, h in enumerate(headers):
            # В заголовке может быть \n — берём самую длинную строку
            w = max((len(line) for line in str(h).split('\n')), default=0)
            widths[i] = max(widths[i], w)
        for row in rows:
            for i, cell in enumerate(row):
                w = max((len(line) for line in str(cell).split('\n')), default=0)
                widths[i] = max(widths[i], w)

        # Немного padding
        widths = [w + 2 for w in widths]

        def format_row(cells, align='left'):
            parts = []
            for i, cell in enumerate(cells):
                s = str(cell)
                # Если в ячейке есть \n — склеим в одну строку для TXT
                s = s.replace('\n', ' ')
                if align == 'center':
                    parts.append(s.center(widths[i]))
                else:
                    parts.append(s.ljust(widths[i]))
            return "|" + "|".join(parts) + "|"

        def separator():
            return "+" + "+".join("-" * w for w in widths) + "+"

        lines = []
        lines.append(project.name)
        lines.append("")
        lines.append(separator())
        lines.append(format_row(headers, align='center'))
        lines.append(separator())
        for row in rows:
            lines.append(format_row(row))
        lines.append(separator())

        with open(path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

        return True
    except Exception as e:
        print(f"Ошибка экспорта в TXT: {e}")
        return False