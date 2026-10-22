"""
Базовые планировщики (SGS — Schedule Generation Schemes).

- SerialScheduler   — последовательный SGS с топологическим порядком.
- ParallelScheduler — параллельный SGS по дням.
- create_scheduler  — фабрика (serial / parallel / genetic).

Расписание — dict {task_id: (start, end)}, где start включительно,
end исключительно. Makespan = max(end).
"""
from typing import Dict, List, Tuple, Callable

from .models import Task, Project


Schedule = Dict[int, Tuple[int, int]]


# ============================================================================
# ПРАВИЛА ПРИОРИТЕТА
# ============================================================================
def rule_lpt(task, project, scheduled):
    return -task.duration


def rule_spt(task, project, scheduled):
    return task.duration


def rule_mts(task, project, scheduled):
    total = _transitive_successors_duration(task.id, project)
    return -total


def rule_grpw(task, project, scheduled):
    total = _transitive_successors_duration(task.id, project)
    return -(task.duration + total)


def rule_ms(task, project, scheduled):
    return -sum(task.resources.values())


PRIORITY_RULES: Dict[str, Callable] = {
    'LPT': rule_lpt,
    'SPT': rule_spt,
    'MTS': rule_mts,
    'GRPW': rule_grpw,
    'MS': rule_ms,
}


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ
# ============================================================================
def _transitive_successors_duration(task_id: int, project: Project) -> int:
    successors = project.get_successors()
    seen = set()
    stack = list(successors.get(task_id, []))
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(successors.get(node, []))
    duration_map = {t.id: t.duration for t in project.tasks}
    return sum(duration_map.get(n, 0) for n in seen)


def _resource_usage_on_day(schedule, tasks_by_id, day):
    usage: Dict[str, int] = {}
    for tid, (start, end) in schedule.items():
        if start <= day < end:
            for r, amount in tasks_by_id[tid].resources.items():
                usage[r] = usage.get(r, 0) + amount
    return usage


def _can_place(task, start_day, schedule, tasks_by_id, resource_limits):
    for day in range(start_day, start_day + task.duration):
        usage = _resource_usage_on_day(schedule, tasks_by_id, day)
        for r, amount in task.resources.items():
            if usage.get(r, 0) + amount > resource_limits.get(r, 0):
                return False
    return True


def _earliest_feasible_start(task, earliest, schedule, tasks_by_id, resource_limits, horizon):
    day = earliest
    while day <= horizon:
        if _can_place(task, day, schedule, tasks_by_id, resource_limits):
            return day
        day += 1
    return -1


def _topological_priority_order(project, tasks_by_id, rule_fn) -> List[int]:
    """
    Топологическая сортировка с приоритетом внутри уровня готовности.
    Гарантирует, что предшественники идут раньше потомков.
    """
    predecessors = project.get_predecessors()
    remaining = {tid: set(predecessors.get(tid, [])) for tid in tasks_by_id}
    ready = [tid for tid, pr in remaining.items() if not pr]

    empty_schedule: Schedule = {}
    order: List[int] = []

    while ready:
        ready.sort(
            key=lambda tid: rule_fn(tasks_by_id[tid], project, empty_schedule)
        )
        chosen = ready.pop(0)
        order.append(chosen)

        for tid in tasks_by_id:
            if chosen in remaining[tid]:
                remaining[tid].discard(chosen)
                if not remaining[tid] and tid not in order and tid not in ready:
                    ready.append(tid)

    for tid in tasks_by_id:
        if tid not in order:
            order.append(tid)

    return order


def _make_topological(order: List[int], project, tasks_by_id, preds) -> List[int]:
    """
    Преобразует произвольную перестановку задач в топологический порядок,
    максимально близкий к исходной (используется для GA, где crossover
    и mutation могут создать невалидный порядок).
    """
    position = {tid: i for i, tid in enumerate(order)}

    remaining = {tid: set(preds.get(tid, [])) for tid in tasks_by_id}
    ready = [tid for tid, pr in remaining.items() if not pr]

    result: List[int] = []

    while ready:
        ready.sort(key=lambda tid: position.get(tid, 0))
        chosen = ready.pop(0)
        result.append(chosen)

        for tid in tasks_by_id:
            if chosen in remaining[tid]:
                remaining[tid].discard(chosen)
                if not remaining[tid] and tid not in result and tid not in ready:
                    ready.append(tid)

    for tid in tasks_by_id:
        if tid not in result:
            result.append(tid)

    return result

class SerialScheduler:
    """
    Последовательный SGS.

    Порядок по умолчанию — топологическая сортировка с приоритетом.
    Если порядок задан извне (например, GA) — он пересобирается в
    топологически допустимый с сохранением относительного порядка.
    """

    def __init__(self, project: Project, rule: str = 'LPT'):
        self.project = project
        self.rule = rule.upper()
        if self.rule not in PRIORITY_RULES:
            raise ValueError(f"Неизвестное правило: {rule}")
        self.tasks_by_id = {t.id: t for t in project.tasks}
        self.preds = project.get_predecessors()

    def _default_order(self) -> List[int]:
        rule_fn = PRIORITY_RULES[self.rule]
        return _topological_priority_order(self.project, self.tasks_by_id, rule_fn)

    def schedule(self, order: List[int] = None) -> Tuple[Schedule, int]:
        """
        Строит расписание.

        order — необязательный порядок задач (например, из GA).
                Если задан, он пересобирается в топологически
                допустимый с сохранением относительного порядка.
                Если не задан — берётся _default_order().
        """
        if order is None:
            order = self._default_order()
        else:
            order = _make_topological(
                order, self.project, self.tasks_by_id, self.preds
            )

        sched: Schedule = {}
        horizon = sum(t.duration for t in self.project.tasks) + 1

        for tid in order:
            task = self.tasks_by_id[tid]

            # Самое раннее начало по предшественникам: КОНЕЦ самого позднего
            earliest = 0
            for dep in self.preds.get(tid, []):
                if dep in sched:
                    earliest = max(earliest, sched[dep][1])

            start = _earliest_feasible_start(
                task, earliest, sched, self.tasks_by_id,
                self.project.resource_limits, horizon,
            )
            if start < 0:
                raise RuntimeError(
                    f"Не удалось разместить задачу '{task.name}' (ID={tid})"
                )

            sched[tid] = (start, start + task.duration)

        makespan = max((e for _, e in sched.values()), default=0)
        return sched, makespan


# ============================================================================
# PARALLEL SGS
# ============================================================================
class ParallelScheduler:
    """
    Параллельный SGS по дням.
    На каждом дне запускает все задачи, чьи предшественники УЖЕ ЗАВЕРШЕНЫ
    и для которых хватает ресурсов.
    """

    def __init__(self, project: Project, rule: str = 'LPT'):
        self.project = project
        self.rule = rule.upper()
        if self.rule not in PRIORITY_RULES:
            raise ValueError(f"Неизвестное правило: {rule}")
        self.tasks_by_id = {t.id: t for t in project.tasks}
        self.preds = project.get_predecessors()

    def schedule(self) -> Tuple[Schedule, int]:
        sched: Schedule = {}
        remaining = set(self.tasks_by_id.keys())
        ends: Dict[int, int] = {}
        rule_fn = PRIORITY_RULES[self.rule]

        day = 0
        horizon = sum(t.duration for t in self.project.tasks) + 1

        while remaining and day <= horizon:
            ready = []
            for tid in remaining:
                preds = self.preds.get(tid, [])
                # Задача готова, только если ВСЕ её предшественники
                # УЖЕ ЗАВЕРШИЛИСЬ к текущему дню.
                if all(ends.get(dep, float('inf')) <= day for dep in preds):
                    ready.append(tid)

            ready.sort(
                key=lambda tid: rule_fn(self.tasks_by_id[tid], self.project, sched)
            )

            for tid in ready:
                task = self.tasks_by_id[tid]
                if _can_place(task, day, sched, self.tasks_by_id,
                              self.project.resource_limits):
                    sched[tid] = (day, day + task.duration)
                    ends[tid] = day + task.duration
                    remaining.discard(tid)

            day += 1

        if remaining:
            raise RuntimeError(f"Не запустились задачи: {sorted(remaining)}")

        makespan = max((e for _, e in sched.values()), default=0)
        return sched, makespan


# ============================================================================
# ФАБРИКА
# ============================================================================
def create_scheduler(method: str, project: Project, rule: str = 'LPT'):
    method = method.lower()
    if method == 'serial':
        return SerialScheduler(project, rule)
    if method == 'parallel':
        return ParallelScheduler(project, rule)
    if method == 'genetic':
        from .genetic import GeneticScheduler
        return GeneticScheduler(project, rule)
    if method == 'bnb':
        from .bnb import BranchAndBoundScheduler
        return BranchAndBoundScheduler(project, rule, time_limit=None)
    raise ValueError(f"Неизвестный метод: {method}")