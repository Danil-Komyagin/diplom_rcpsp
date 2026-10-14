"""
Визуализация расписания: диаграмма Ганта и график использования ресурсов.

Зависимости:
- matplotlib (импортируется лениво, чтобы не тянуть GUI-бэкенды при импорте
  модуля ядра).
"""
from typing import Dict, List, Optional

from .models import Project
from .schedulers import Schedule


# ============================================================================
# ОБЩИЕ УТИЛИТЫ
# ============================================================================
def _get_makespan(schedule: Schedule) -> int:
    if not schedule:
        return 0
    return max(end for _, end in schedule.values())


def _color_for_task(task_id: int) -> str:
    """
    Псевдослучайный, но детерминированный цвет для задачи.
    Палитра из 10 приятных оттенков.
    """
    palette = [
        '#3498db', '#e74c3c', '#27ae60', '#f39c12', '#9b59b6',
        '#1abc9c', '#e67e22', '#34495e', '#16a085', '#c0392b',
    ]
    return palette[task_id % len(palette)]


# ============================================================================
# ДИАГРАММА ГАНТА
# ============================================================================
def plot_gantt(
    project: Project,
    schedule: Schedule,
    save_path: Optional[str] = None,
    figsize: tuple = (12, 6),
):
    """
    Рисует диаграмму Ганта: по оси Y — задачи, по оси X — дни.

    save_path — если задан, сохраняет PNG и закрывает фигуру.
                Если None — возвращает фигуру для дальнейшего использования.

    Возвращает matplotlib Figure или None (если сохранил в файл и закрыл).
    """
    import matplotlib
    if save_path is not None:
        matplotlib.use('Agg')  # backend без GUI, для сохранения в файл
    import matplotlib.pyplot as plt

    if not project.tasks:
        raise ValueError("В проекте нет задач")

    makespan = _get_makespan(schedule)
    if makespan == 0:
        raise ValueError("Пустое расписание")

    fig, ax = plt.subplots(figsize=figsize)

    tasks_by_id = {t.id: t for t in project.tasks}
    # Сортируем задачи по времени старта, затем по id — чтобы график был читаемым
    ordered = sorted(
        schedule.items(),
        key=lambda kv: (kv[1][0], kv[0]),
    )

    y_labels = []
    for row_index, (tid, (start, end)) in enumerate(ordered):
        task = tasks_by_id[tid]
        duration = end - start
        ax.barh(
            y=row_index,
            width=duration,
            left=start,
            height=0.6,
            color=_color_for_task(tid),
            edgecolor='black',
            linewidth=0.5,
        )
        y_labels.append(f"ID {tid}: {task.name}")

        # Подпись внутри бара
        ax.text(
            start + duration / 2,
            row_index,
            f"{duration}д",
            ha='center', va='center',
            color='white', fontsize=9, fontweight='bold',
        )

    ax.set_yticks(range(len(ordered)))
    ax.set_yticklabels(y_labels, fontsize=9)
    ax.invert_yaxis()  # чтобы первая задача была сверху
    ax.set_xlabel("День проекта", fontsize=11)
    ax.set_title(f"Диаграмма Ганта — {project.name} (makespan = {makespan})",
                 fontsize=12, fontweight='bold')
    ax.set_xlim(0, makespan)
    ax.grid(axis='x', linestyle='--', alpha=0.5)

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return None
    return fig


# ============================================================================
# ГРАФИК ИСПОЛЬЗОВАНИЯ РЕСУРСОВ
# ============================================================================
def plot_resource_utilization(
    project: Project,
    schedule: Schedule,
    save_path: Optional[str] = None,
    figsize: tuple = (12, 6),
):
    """
    Рисует график использования ресурсов по дням.

    По оси X — дни, по оси Y — суммарное потребление.
    Каждый ресурс — отдельная линия. Лимит — горизонтальная пунктирная линия.

    Возвращает matplotlib Figure или None (если сохранил в файл).
    """
    import matplotlib
    if save_path is not None:
        matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    if not project.resource_limits:
        raise ValueError("В проекте не заданы ресурсы")

    makespan = _get_makespan(schedule)
    if makespan == 0:
        raise ValueError("Пустое расписание")

    tasks_by_id = {t.id: t for t in project.tasks}
    resource_names = list(project.resource_limits.keys())

    # Считаем использование каждого ресурса по дням
    usage: Dict[str, List[int]] = {
        rname: [0] * makespan for rname in resource_names
    }
    for tid, (start, end) in schedule.items():
        for day in range(start, end):
            for rname, amount in tasks_by_id[tid].resources.items():
                if rname in usage:
                    usage[rname][day] += amount

    days = list(range(makespan))

    fig, ax = plt.subplots(figsize=figsize)

    palette = [
        '#3498db', '#e74c3c', '#27ae60', '#f39c12', '#9b59b6',
        '#1abc9c', '#e67e22',
    ]

    for i, rname in enumerate(resource_names):
        color = palette[i % len(palette)]
        ax.plot(
            days,
            usage[rname],
            label=f"{rname} (лимит {project.resource_limits[rname]})",
            color=color,
            linewidth=2,
            marker='o',
            markersize=3,
        )
        # Линия лимита
        ax.axhline(
            y=project.resource_limits[rname],
            color=color,
            linestyle='--',
            linewidth=1,
            alpha=0.6,
        )

    ax.set_xlabel("День проекта", fontsize=11)
    ax.set_ylabel("Использование ресурса", fontsize=11)
    ax.set_title(f"Использование ресурсов — {project.name}",
                 fontsize=12, fontweight='bold')
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_xlim(-0.5, makespan - 0.5 if makespan > 1 else 1)

    # Целочисленные деления по X и Y
    ax.set_xticks(days)
    if makespan > 20:
        # Слишком много дней — реже подписи
        step = max(1, makespan // 20)
        ax.set_xticks(days[::step])

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return None
    return fig