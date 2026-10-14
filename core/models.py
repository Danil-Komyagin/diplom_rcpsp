"""
Модели данных проекта: Task и Project.

Используются во всём ядре (планировщики, отчёты, визуализация)
и в GUI (через сериализацию в dict).
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ============================================================================
# ЗАДАЧА
# ============================================================================
@dataclass
class Task:
    """
    Задача проекта.

    Атрибуты:
        id: уникальный идентификатор (в рамках проекта).
        name: название задачи.
        duration: длительность в днях (целое > 0).
        resources: словарь {имя_ресурса: количество} — сколько ресурсов
                   каждого типа требует задача.
    """
    id: int
    name: str
    duration: int
    resources: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        """Приводим типы и валидируем базовые поля."""
        self.id = int(self.id)
        self.duration = int(self.duration)
        if self.duration <= 0:
            raise ValueError(f"Задача '{self.name}': длительность должна быть > 0")
        # ресурсы: приводим значения к int и убираем нулевые
        self.resources = {
            str(k): int(v)
            for k, v in (self.resources or {}).items()
            if int(v) > 0
        }

    def to_dict(self) -> dict:
        """Сериализация в dict (для JSON/БД)."""
        return {
            'id': self.id,
            'name': self.name,
            'duration': self.duration,
            'resources': dict(self.resources),
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Task':
        """Восстановление из dict."""
        return cls(
            id=data['id'],
            name=data['name'],
            duration=data['duration'],
            resources=data.get('resources', {}),
        )


# ============================================================================
# ПРОЕКТ
# ============================================================================
@dataclass
class Project:
    """
    Проект: набор задач + зависимости + лимиты ресурсов.

    Атрибуты:
        tasks: список Task.
        dependencies: {task_id: [dep_id, ...]} — от каких задач зависит задача.
        resource_limits: {имя_ресурса: доступное_количество}.
        name: название проекта.
    """
    tasks: List[Task] = field(default_factory=list)
    dependencies: Dict[int, List[int]] = field(default_factory=dict)
    resource_limits: Dict[str, int] = field(default_factory=dict)
    name: str = "Мой проект"

    def __post_init__(self):
        # нормализуем зависимости: ключи — int, значения — список int
        normalized = {}
        for k, v in (self.dependencies or {}).items():
            try:
                key = int(k)
            except (TypeError, ValueError):
                continue
            deps = []
            for d in (v or []):
                try:
                    di = int(d)
                except (TypeError, ValueError):
                    continue
                if di != key and di not in deps:
                    deps.append(di)
            if deps:
                normalized[key] = deps
        self.dependencies = normalized

        # нормализуем лимиты ресурсов
        self.resource_limits = {
            str(k): int(v)
            for k, v in (self.resource_limits or {}).items()
            if int(v) > 0
        }

    # ------------------------------------------------------------------
    # Удобные свойства
    # ------------------------------------------------------------------
    @property
    def task_count(self) -> int:
        return len(self.tasks)

    def get_task(self, task_id: int) -> Optional[Task]:
        """Найти задачу по id."""
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None

    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """Алиас для get_task — совместимость со старым API."""
        return self.get_task(task_id)

    def get_task_ids(self) -> List[int]:
        return [t.id for t in self.tasks]

    def get_resource_names(self) -> List[str]:
        return list(self.resource_limits.keys())

    # ------------------------------------------------------------------
    # Валидация
    # ------------------------------------------------------------------
    def validate(self) -> List[str]:
        """
        Возвращает список ошибок. Пустой список = проект валиден.
        Не бросает исключение — вызывающий сам решает, что делать.
        """
        errors = []
        ids = [t.id for t in self.tasks]

        # 1. Уникальность id
        if len(ids) != len(set(ids)):
            errors.append("Есть задачи с дублирующимися ID")

        # 2. Ссылки на существующие задачи
        id_set = set(ids)
        for task_id, deps in self.dependencies.items():
            if task_id not in id_set:
                errors.append(f"Зависимости ссылаются на несуществующую задачу ID={task_id}")
            for d in deps:
                if d not in id_set:
                    errors.append(f"Задача ID={task_id} зависит от несуществующей ID={d}")

        # 3. Ресурсы задач входят в лимиты (по имени)
        resource_names = set(self.resource_limits.keys())
        for t in self.tasks:
            for rname in t.resources:
                if rname not in resource_names:
                    errors.append(
                        f"Задача '{t.name}' использует ресурс '{rname}', "
                        f"которого нет в лимитах проекта"
                    )

        # 4. Нет циклов в зависимостях
        if self._has_cycle():
            errors.append("Обнаружен цикл в зависимостях задач")

        return errors

    def _has_cycle(self) -> bool:
        """Проверка на цикл в графе зависимостей (DFS)."""
        visited = set()
        stack = set()

        def dfs(node):
            if node in stack:
                return True
            if node in visited:
                return False
            visited.add(node)
            stack.add(node)
            for dep in self.dependencies.get(node, []):
                if dfs(dep):
                    return True
            stack.remove(node)
            return False

        return any(dfs(t.id) for t in self.tasks if t.id not in visited)

    # ------------------------------------------------------------------
    # Работа с графом зависимостей
    # ------------------------------------------------------------------
    def get_predecessors(self) -> Dict[int, List[int]]:
        """
        Возвращает {task_id: [список его предшественников]}.
        """
        preds: Dict[int, List[int]] = {t.id: [] for t in self.tasks}
        for tid, deps in self.dependencies.items():
            preds.setdefault(tid, [])
            for d in deps:
                if d not in preds[tid]:
                    preds[tid].append(d)
        return preds

    def get_successors(self) -> Dict[int, List[int]]:
        """
        Возвращает {task_id: [список его прямых потомков]}.
        """
        succs: Dict[int, List[int]] = {t.id: [] for t in self.tasks}
        for tid, deps in self.dependencies.items():
            for d in deps:
                succs.setdefault(d, [])
                if tid not in succs[d]:
                    succs[d].append(tid)
        return succs

    def get_topological_order(self) -> List[int]:
        """
        Топологическая сортировка задач (алгоритм Кана).
        Возвращает список ID, в котором предшественники идут раньше потомков.
        Бросает ValueError, если в графе есть цикл.
        """
        from collections import deque

        successors = self.get_successors()
        predecessors = self.get_predecessors()

        # Входящие степени
        in_degree = {t.id: len(predecessors.get(t.id, [])) for t in self.tasks}

        # Очередь из задач без предшественников
        queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
        result: List[int] = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for nxt in successors.get(node, []):
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        if len(result) != len(self.tasks):
            raise ValueError("В графе зависимостей обнаружен цикл!")

        return result

    # ------------------------------------------------------------------
    # Сериализация
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        """В dict (для JSON/БД)."""
        return {
            'name': self.name,
            'resource_limits': dict(self.resource_limits),
            'tasks': [t.to_dict() for t in self.tasks],
            'dependencies': {str(k): list(v) for k, v in self.dependencies.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Project':
        """Из dict."""
        tasks = [Task.from_dict(t) for t in data.get('tasks', [])]
        deps = {}
        for k, v in data.get('dependencies', {}).items():
            deps[int(k)] = list(v)
        return cls(
            tasks=tasks,
            dependencies=deps,
            resource_limits=data.get('resource_limits', {}),
            name=data.get('name', 'Мой проект'),
        )