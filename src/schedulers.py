from typing import Dict, List, Set, Tuple, Callable
from collections import defaultdict
import copy
import heapq

from .models import Project, Task


class PriorityRule:
    """Правила приоритета для выбора задач"""

    @staticmethod
    def lpt(project: Project, task_id: int) -> int:
        """Longest Processing Time - сначала длинные задачи"""
        return project.get_task_by_id(task_id).duration

    @staticmethod
    def spt(project: Project, task_id: int) -> int:
        """Shortest Processing Time - сначала короткие задачи"""
        return -project.get_task_by_id(task_id).duration

    @staticmethod
    def mts(project: Project, task_id: int) -> int:
        """Most Total Successors - задачи с наибольшим количеством потомков"""
        successors = project.get_successors()

        def count_all(t_id: int, visited: Set[int]) -> int:
            if t_id in visited:
                return 0
            visited.add(t_id)
            count = len(successors.get(t_id, []))
            for succ in successors.get(t_id, []):
                count += count_all(succ, visited)
            return count

        return count_all(task_id, set())

    @staticmethod
    def grpw(project: Project, task_id: int) -> float:
        """Greatest Resource Priority Weight - учитывает ресурсы и длительность"""
        task = project.get_task_by_id(task_id)
        return task.duration * sum(task.resources.values())

    @staticmethod
    def ms(project: Project, task_id: int) -> int:
        """Maximum Successors - задачи с наибольшим количеством прямых последователей"""
        successors = project.get_successors()
        return len(successors.get(task_id, []))


class ParallelScheduler:
    """
    Параллельный эвристический алгоритм.
    Продвигается по времени, запуская задачи при наличии свободных ресурсов.
    """

    def __init__(self, project: Project, priority_func: Callable, priority_name: str):
        self.project = copy.deepcopy(project)
        self.priority_func = priority_func
        self.priority_name = priority_name

    def _check_resources(self, task: Task, usage: Dict[str, int]) -> bool:
        """Проверяет, хватает ли ресурсов для задачи"""
        for rt, needed in task.resources.items():
            available = self.project.resource_limits.get(rt, 0) - usage.get(rt, 0)
            if needed > available:
                return False
        return True

    def schedule(self) -> Tuple[Dict[int, int], int]:
        """
        Основной метод построения расписания.
        Возвращает: (расписание {task_id: start_time}, общая длительность)
        """
        tasks = {task.id: task for task in self.project.tasks}
        predecessors = self.project.get_predecessors()

        scheduled = set()
        in_progress = {}
        usage = {rt: 0 for rt in self.project.resource_limits.keys()}
        schedule = {}
        current_time = 0
        total = len(self.project.tasks)

        def get_ready() -> list:
            ready = []
            for task in self.project.tasks:
                if task.id in scheduled or task.id in in_progress:
                    continue
                all_done = all(p in scheduled for p in predecessors.get(task.id, []))
                if all_done:
                    ready.append(task.id)
            return ready

        while len(scheduled) < total:
            # 1. Освобождаем завершённые задачи
            to_remove = []
            for tid, finish in list(in_progress.items()):
                if finish <= current_time:
                    task = tasks[tid]
                    for rt, val in task.resources.items():
                        usage[rt] = usage.get(rt, 0) - val
                    scheduled.add(tid)
                    to_remove.append(tid)
            for tid in to_remove:
                del in_progress[tid]

            # 2. Находим готовые задачи
            ready = get_ready()

            # 3. Сортируем по приоритету (убывание)
            ready.sort(key=lambda tid: self.priority_func(self.project, tid), reverse=True)

            # 4. Запускаем задачи
            for tid in ready:
                task = tasks[tid]
                if self._check_resources(task, usage):
                    task.start_time = current_time
                    task.finish_time = current_time + task.duration
                    schedule[tid] = current_time
                    in_progress[tid] = current_time + task.duration
                    for rt, val in task.resources.items():
                        usage[rt] = usage.get(rt, 0) + val

            # 5. Переходим к следующему событию
            if in_progress:
                current_time = min(in_progress.values())
            else:
                if len(scheduled) < total:
                    current_time += 1
                    if current_time > 10000:
                        break

        makespan = max(t.finish_time for t in self.project.tasks if t.finish_time is not None)
        return schedule, makespan


class SerialScheduler:
    """
    Последовательный эвристический алгоритм.
    Назначает задачи одну за другой без учёта параллельности.
    """

    def __init__(self, project: Project, priority_func: Callable, priority_name: str):
        self.project = copy.deepcopy(project)
        self.priority_func = priority_func
        self.priority_name = priority_name

    def _check_resources(self, task: Task, usage: Dict[str, int]) -> bool:
        for rt, needed in task.resources.items():
            available = self.project.resource_limits.get(rt, 0) - usage.get(rt, 0)
            if needed > available:
                return False
        return True

    def schedule(self) -> Tuple[Dict[int, int], int]:
        tasks = {task.id: task for task in self.project.tasks}
        predecessors = self.project.get_predecessors()
        topo_order = self.project.get_topological_order()

        scheduled = set()
        schedule = {}
        current_time = 0
        usage = {rt: 0 for rt in self.project.resource_limits.keys()}

        ready_heap = []

        def is_ready(task_id: int) -> bool:
            if task_id in scheduled:
                return False
            for pred in predecessors.get(task_id, []):
                if pred not in scheduled:
                    return False
            return True

        for task_id in topo_order:
            if is_ready(task_id):
                priority = self.priority_func(self.project, task_id)
                heapq.heappush(ready_heap, (-priority, task_id))

        while ready_heap:
            _, task_id = heapq.heappop(ready_heap)

            if not is_ready(task_id):
                continue

            task = tasks[task_id]

            if self._check_resources(task, usage):
                task.start_time = current_time
                task.finish_time = current_time + task.duration
                schedule[task_id] = current_time
                scheduled.add(task_id)

                for rt, val in task.resources.items():
                    usage[rt] = usage.get(rt, 0) + val

                current_time += task.duration

                for rt, val in task.resources.items():
                    usage[rt] = usage.get(rt, 0) - val

                for next_id in topo_order:
                    if is_ready(next_id) and next_id not in scheduled:
                        already = any(item[1] == next_id for item in ready_heap)
                        if not already:
                            priority = self.priority_func(self.project, next_id)
                            heapq.heappush(ready_heap, (-priority, next_id))
            else:
                priority = self.priority_func(self.project, task_id)
                heapq.heappush(ready_heap, (-priority, task_id))
                current_time += 1
                if current_time > 10000:
                    break

        makespan = max(task.finish_time for task in self.project.tasks if task.finish_time is not None)
        return schedule, makespan


def create_scheduler(method: str, project: Project, rule: str):
    """
    Фабрика для создания планировщика.
    method: "parallel" или "serial"
    rule: "LPT", "SPT", "MTS", "GRPW", "MS"
    """
    rules = {
        "LPT": PriorityRule.lpt,
        "SPT": PriorityRule.spt,
        "MTS": PriorityRule.mts,
        "GRPW": PriorityRule.grpw,
        "MS": PriorityRule.ms,
    }
    if rule not in rules:
        raise ValueError(f"Неизвестное правило: {rule}")

    if method == "parallel":
        return ParallelScheduler(project, rules[rule], rule)
    elif method == "serial":
        return SerialScheduler(project, rules[rule], rule)
    else:
        raise ValueError(f"Неизвестный метод: {method}")