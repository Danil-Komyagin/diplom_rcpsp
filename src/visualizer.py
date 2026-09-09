from typing import Dict, Optional
import matplotlib.pyplot as plt
import numpy as np
import os

from .models import Project


def plot_gantt(project: Project, schedule: Dict[int, int],
               title: str = "Диаграмма Ганта",
               save_path: Optional[str] = None):
    """Строит диаграмму Ганта"""
    fig, ax = plt.subplots(figsize=(12, max(6, len(project.tasks) * 0.5)))

    sorted_tasks = sorted(project.tasks, key=lambda t: schedule.get(t.id, 0))
    colors = plt.cm.Set3(np.linspace(0, 1, len(project.tasks)))

    for idx, task in enumerate(sorted_tasks):
        start = schedule.get(task.id, 0)
        duration = task.duration
        ax.barh(idx, duration, left=start, color=colors[idx % len(colors)],
                edgecolor='black', linewidth=0.5, alpha=0.8)
        if duration > 2:
            ax.text(start + duration / 2, idx, task.name[:15],
                    ha='center', va='center', fontsize=8)

    ax.set_yticks(range(len(project.tasks)))
    ax.set_yticklabels([f"{t.id}: {t.name[:12]}" for t in sorted_tasks], fontsize=8)
    ax.set_xlabel("Время (дни)", fontsize=10)
    ax.set_title(title, fontsize=12, weight='bold')
    ax.grid(True, alpha=0.3)

    max_time = max(schedule.values()) + max(t.duration for t in sorted_tasks) + 2
    ax.set_xlim(0, max_time)

    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path) or '.', exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    return fig


def plot_resource_utilization(project: Project, schedule: Dict[int, int],
                              title: str = "Использование ресурсов",
                              save_path: Optional[str] = None):
    """Строит график использования ресурсов"""
    if not schedule:
        return None

    makespan = max(schedule.get(t.id, 0) + t.duration for t in project.tasks)
    if makespan <= 0:
        makespan = 10
    time_points = list(range(makespan + 1))

    fig, ax = plt.subplots(figsize=(12, 5))
    colors = {'developers': '#3498db', 'testers': '#e74c3c', 'designers': '#2ecc71'}

    for rt in project.resource_limits.keys():
        usage = []
        for t in time_points:
            used = 0
            for task in project.tasks:
                if task.id in schedule:
                    start = schedule[task.id]
                    if start <= t < start + task.duration:
                        used += task.resources.get(rt, 0)
            usage.append(used)
        if any(usage):
            color = colors.get(rt, '#95a5a6')
            ax.plot(time_points, usage, label=rt, color=color, linewidth=2)
            ax.fill_between(time_points, 0, usage, alpha=0.2, color=color)

    for rt, limit in project.resource_limits.items():
        color = colors.get(rt, '#95a5a6')
        ax.axhline(y=limit, color=color, linestyle='--', linewidth=1.5,
                   alpha=0.7, label=f"{rt} лимит: {limit}")

    ax.set_xlabel("Время (дни)", fontsize=10)
    ax.set_ylabel("Использование ресурсов", fontsize=10)
    ax.set_title(title, fontsize=12, weight='bold')
    ax.legend(loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.3)

    if save_path:
        os.makedirs(os.path.dirname(save_path) or '.', exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    return fig