"""Временная диагностика планировщиков."""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from core.models import Task, Project
from core.schedulers import create_scheduler


def main():
    # Воспроизводим твой JSON вручную
    tasks = [
        Task(1, "З1", 5, {"А": 1}),
        Task(2, "З2", 5, {"Б": 1}),
        Task(3, "З3", 5, {"В": 1}),
    ]
    deps = {2: [1], 3: [2]}
    limits = {"А": 4, "Б": 4, "В": 4}
    project = Project(tasks, deps, limits, "Разработка ERP")

    print("=" * 60)
    print("Задачи:")
    for t in project.tasks:
        print(f"  ID={t.id}, name={t.name}, duration={t.duration}, res={t.resources}")
    print("dependencies (нормализованные):", project.dependencies)
    print("get_predecessors():", project.get_predecessors())
    print("get_successors():", project.get_successors())
    print("get_topological_order():", project.get_topological_order())
    print("=" * 60)

    for method in ("serial", "parallel"):
        for rule in ("LPT", "SPT"):
            try:
                sched = create_scheduler(method, project, rule)
                schedule, makespan = sched.schedule()
                print(f"\n{method.upper()} / {rule}:")
                for tid in sorted(schedule):
                    s, e = schedule[tid]
                    print(f"  ID={tid}: start={s}, end={e}, duration={e - s}")
                print(f"  MAKESPAN = {makespan}")
            except Exception as e:
                print(f"\n{method.upper()} / {rule}: ОШИБКА: {e}")

    print("=" * 60)


if __name__ == "__main__":
    main()