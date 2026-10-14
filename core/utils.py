"""
Утилиты: сохранение/загрузка проекта в JSON и генерация тестового проекта.
"""
import json
import random
from pathlib import Path
from typing import Optional

from .models import Task, Project


# ============================================================================
# СОХРАНЕНИЕ / ЗАГРУЗКА JSON
# ============================================================================
def save_project_to_json(project: Project, path: str) -> None:
    """
    Сохраняет проект в JSON-файл.

    Формат — тот же, что возвращает Project.to_dict():
        {
            "name": "...",
            "resource_limits": {...},
            "tasks": [...],
            "dependencies": {...}
        }
    """
    data = project.to_dict()
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_project_from_json(path: str) -> Project:
    """
    Загружает проект из JSON-файла.

    Бросает FileNotFoundError, json.JSONDecodeError или ValueError,
    если данные неполные/некорректные.
    """
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("JSON должен содержать объект (dict) на верхнем уровне")

    project = Project.from_dict(data)

    # Базовая валидация — чтобы GUI не падал на битых данных
    errors = project.validate()
    if errors:
        raise ValueError("Некорректный проект:\n" + "\n".join(errors))

    return project


# ============================================================================
# ТЕСТОВЫЙ ПРОЕКТ
# ============================================================================
def create_test_project(
    n_tasks: int = 10,
    n_resources: int = 3,
    seed: Optional[int] = None,
) -> Project:
    """
    Генерирует тестовый RCPSP-проект с n_tasks задачами и n_resources ресурсами.

    Гарантирует, что граф зависимостей — DAG (без циклов): задача i может
    зависеть только от задач с меньшим id.

    Параметры:
        n_tasks: количество задач (>= 2).
        n_resources: количество типов ресурсов (>= 1).
        seed: для воспроизводимости.
    """
    if seed is not None:
        random.seed(seed)

    n_tasks = max(2, int(n_tasks))
    n_resources = max(1, int(n_resources))

    # Ресурсы: R1, R2, ...
    resource_names = [f"R{i + 1}" for i in range(n_resources)]

    # Лимиты ресурсов: 5..15 единиц каждого
    resource_limits = {
        rname: random.randint(5, 15) for rname in resource_names
    }

    # Задачи
    tasks = []
    for i in range(1, n_tasks + 1):
        duration = random.randint(2, 8)

        # Каждая задача требует 1–2 случайных ресурса,
        # но не больше, чем доступно в лимитах
        n_req = random.randint(1, min(2, n_resources))
        chosen = random.sample(resource_names, n_req)
        resources = {}
        for rname in chosen:
            amount = random.randint(1, max(1, resource_limits[rname] // 2))
            resources[rname] = amount

        tasks.append(Task(id=i, name=f"Задача {i}", duration=duration, resources=resources))

    # Зависимости: у каждой задачи (кроме первой) — с вероятностью 0.6
    # 1–2 предшественника с меньшим id.
    dependencies = {}
    for i in range(2, n_tasks + 1):
        if random.random() < 0.6:
            n_deps = random.randint(1, min(2, i - 1))
            preds = random.sample(range(1, i), n_deps)
            dependencies[i] = preds

    project = Project(
        tasks=tasks,
        dependencies=dependencies,
        resource_limits=resource_limits,
        name=f"Тестовый проект ({n_tasks} задач, {n_resources} ресурсов)",
    )

    # Проверим, что сгенерированное валидно
    errors = project.validate()
    if errors:
        # Если что-то не так (маловероятно) — свалимся явно
        raise RuntimeError(
            "Сгенерированный тестовый проект некорректен:\n" + "\n".join(errors)
        )

    return project