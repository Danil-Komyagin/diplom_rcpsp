import json
import os
from typing import Dict, List, Optional
from .models import Task, Project


def create_test_project() -> Project:
    """Создаёт тестовый проект (тот самый, который дал 19 дней)"""
    tasks = [
        Task(1, "Анализ требований", 3, {"developers": 1, "testers": 0}),
        Task(2, "Проектирование БД", 4, {"developers": 1, "testers": 0}),
        Task(3, "Верстка интерфейса", 5, {"developers": 2, "testers": 0}),
        Task(4, "Бэкенд разработка", 7, {"developers": 2, "testers": 0}),
        Task(5, "Модульное тестирование", 2, {"developers": 0, "testers": 1}),
        Task(6, "Документация", 3, {"developers": 1, "testers": 0}),
        Task(7, "Деплой", 1, {"developers": 1, "testers": 0}),
    ]

    dependencies = {
        2: [1],
        3: [1],
        4: [2, 3],
        5: [4],
        6: [4],
        7: [5, 6],
    }

    resource_limits = {"developers": 4, "testers": 2}

    return Project(tasks, dependencies, resource_limits, "Тестовый проект")


def load_project_from_json(filepath: str) -> Project:
    """Загружает проект из JSON-файла"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    tasks = [Task(**t) for t in data['tasks']]
    deps = {int(k): v for k, v in data['dependencies'].items()}

    return Project(tasks, deps, data['resource_limits'], data.get('name', 'Project'))


def save_project_to_json(project: Project, filepath: str):
    """Сохраняет проект в JSON-файл"""
    data = {
        'name': project.name,
        'resource_limits': project.resource_limits,
        'tasks': [
            {
                'id': t.id,
                'name': t.name,
                'duration': t.duration,
                'resources': t.resources
            }
            for t in project.tasks
        ],
        'dependencies': {str(k): v for k, v in project.dependencies.items()}
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)