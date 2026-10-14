"""
Точный метод Branch and Bound для задачи RCPSP.

Идея:
    - Ветвление: хронологическое. На каждом узле дерева ставим одну задачу
      в расписание (в самый ранний допустимый день).
    - Оценка: нижняя оценка (LB) для частичного расписания.
        * LB1 = критический путь (max по цепочкам, а не сумма потомков),
        * LB2 = ресурсная оценка (общая работа / лимит).
        LB = max(LB1, LB2, текущий максимум конца задачи).
    - Отсечение: если LB >= UB — ветвь отбрасывается.
    - Верхняя оценка: получается эвристикой (SerialSGS) до запуска B&B.
    - Таймаут: если задан time_limit (не None) — по его истечении
      возвращается лучшее найденное решение. Если None — считает
      до нахождения оптимума (может занять очень долго).

Работает с расписанием в формате {task_id: (start, end)}.
"""
import time
from typing import Dict, List, Optional, Tuple

from .models import Project, Task
from .schedulers import (
    Schedule, SerialScheduler,
    _can_place,
)


# ============================================================================
# B&B
# ============================================================================
class BranchAndBoundScheduler:
    """
    Branch and Bound для RCPSP.

    Параметры:
        time_limit   — максимальное время работы в секундах.
                       None = без ограничения (считает до оптимума).
        initial_rule — правило приоритета для начальной верхней оценки.

    Использование:
        scheduler = BranchAndBoundScheduler(project, time_limit=None)
        schedule, makespan = scheduler.schedule()
    """

    def __init__(self,
                 project: Project,
                 rule: str = 'LPT',
                 time_limit: Optional[float] = None):
        self.project = project
        self.rule = rule.upper()
        self.time_limit = time_limit          # None = без ограничения

        self.tasks_by_id: Dict[int, Task] = {t.id: t for t in project.tasks}
        self.preds: Dict[int, List[int]] = project.get_predecessors()
        self.succs: Dict[int, List[int]] = project.get_successors()

        self.task_ids: List[int] = [t.id for t in project.tasks]

        self._start_time: float = 0.0

        self._best_schedule: Optional[Schedule] = None
        self._best_makespan: int = float('inf')

        self._branching_order: List[int] = []

        # Диагностика — счётчик итераций
        self._counter: int = 0

        # Кэш для _longest_successor_chain (пересчитываем один раз)
        self._chain_cache: Dict[int, int] = {}

    # ------------------------------------------------------------------
    # Публичное API
    # ------------------------------------------------------------------
    def schedule(self) -> Tuple[Schedule, int]:
        """Запускает B&B и возвращает лучшее найденное расписание."""
        self._start_time = time.time()
        self._counter = 0

        # 1. Начальная верхняя оценка — SerialSGS
        initial_sched, initial_makespan = SerialScheduler(
            self.project, self.rule
        ).schedule()
        self._best_schedule = initial_sched
        self._best_makespan = initial_makespan

        # 2. Порядок обхода задач
        self._branching_order = self._build_branching_order()

        # 3. Рекурсивный поиск
        self._search(
            schedule={},
            remaining=set(self.task_ids),
            current_max_end=0,
        )

        return self._best_schedule, self._best_makespan

    # ------------------------------------------------------------------
    # Вспомогательное
    # ------------------------------------------------------------------
    def _timed_out(self) -> bool:
        """Проверяет, истёк ли таймаут (если он задан)."""
        if self.time_limit is None:
            return False
        return time.time() - self._start_time > self.time_limit

    def _build_branching_order(self) -> List[int]:
        """
        Порядок обхода задач: топологическая сортировка с приоритетом
        внутри уровня готовности.
        """
        from .schedulers import PRIORITY_RULES
        rule_fn = PRIORITY_RULES.get(self.rule)

        remaining = {tid: set(self.preds.get(tid, [])) for tid in self.task_ids}
        ready = [tid for tid, pr in remaining.items() if not pr]

        order: List[int] = []
        while ready:
            ready.sort(
                key=lambda tid: rule_fn(
                    self.tasks_by_id[tid], self.project, {}
                )
            )
            chosen = ready.pop(0)
            order.append(chosen)

            for tid in self.task_ids:
                if chosen in remaining[tid]:
                    remaining[tid].discard(chosen)
                    if not remaining[tid] and tid not in order and tid not in ready:
                        ready.append(tid)

        for tid in self.task_ids:
            if tid not in order:
                order.append(tid)

        return order

    def _longest_successor_chain(self, tid: int) -> int:
        """
        Самый длинный путь по длительностям от задачи tid до её потомков
        (не включая саму tid). Считается один раз и кэшируется.
        """
        if tid in self._chain_cache:
            return self._chain_cache[tid]

        best = 0
        for nxt in self.succs.get(tid, []):
            chain = self.tasks_by_id[nxt].duration + self._longest_successor_chain(nxt)
            if chain > best:
                best = chain

        self._chain_cache[tid] = best
        return best

    # ------------------------------------------------------------------
    # Нижняя оценка
    # ------------------------------------------------------------------
    def _lower_bound(self,
                     schedule: Schedule,
                     current_max_end: int) -> int:
        """
        Нижняя оценка для текущего частичного расписания.

        LB = max(
            current_max_end,
            критический путь среди незапланированных задач,
            ресурсная нижняя оценка
        )
        """
        # 1. Текущий максимум конца
        lb = current_max_end

        # 2. Критический путь для незапланированных задач
        for tid in self.task_ids:
            if tid in schedule:
                continue

            earliest = 0
            for dep in self.preds.get(tid, []):
                if dep in schedule:
                    if schedule[dep][1] > earliest:
                        earliest = schedule[dep][1]

            duration = self.tasks_by_id[tid].duration
            chain = self._longest_successor_chain(tid)

            lb = max(lb, earliest + duration + chain)

        # 3. Ресурсная нижняя оценка (округление вверх)
        used: Dict[str, int] = {r: 0 for r in self.project.resource_limits}
        for tid in self.task_ids:
            if tid in schedule:
                continue
            t = self.tasks_by_id[tid]
            for r, amount in t.resources.items():
                used[r] = used.get(r, 0) + amount * t.duration

        for r, total in used.items():
            cap = self.project.resource_limits.get(r, 1)
            if cap > 0:
                lb_rb = (total + cap - 1) // cap    # ceil(total / cap)
                if lb_rb > lb:
                    lb = lb_rb

        return lb

    # ------------------------------------------------------------------
    # Рекурсивный поиск
    # ------------------------------------------------------------------
    def _search(self,
                schedule: Schedule,
                remaining: set,
                current_max_end: int):
        """
        Рекурсивный поиск B&B.
        """
        self._counter += 1

        # Диагностика: раз в 100 000 итераций печатаем прогресс
        if self._counter % 100_000 == 0:
            print(f"[B&B] итераций: {self._counter}, "
                  f"UB = {self._best_makespan}, "
                  f"remaining = {len(remaining)}")

        # Проверка таймаута
        if self._timed_out():
            return

        # Все задачи расписаны — обновляем UB
        if not remaining:
            if current_max_end < self._best_makespan:
                self._best_makespan = current_max_end
                self._best_schedule = dict(schedule)
                print(f"[B&B] новый UB: {self._best_makespan} "
                      f"(итерация {self._counter})")
            return

        # Отсечение по нижней оценке
        lb = self._lower_bound(schedule, current_max_end)
        if lb >= self._best_makespan:
            return

        # Выбираем задачу для ветвления
        candidate = None
        for tid in self._branching_order:
            if tid in remaining:
                if all(dep in schedule for dep in self.preds.get(tid, [])):
                    candidate = tid
                    break

        if candidate is None:
            return

        task = self.tasks_by_id[candidate]

        # Самое раннее начало по предшественникам
        earliest = 0
        for dep in self.preds.get(candidate, []):
            if dep in schedule:
                if schedule[dep][1] > earliest:
                    earliest = schedule[dep][1]

        # Самый поздний допустимый день: UB - duration
        horizon = self._best_makespan - task.duration
        if horizon < earliest:
            return

        # Перебираем все допустимые дни от earliest до horizon
        for start_day in range(earliest, horizon + 1):
            if self._timed_out():
                return

            if _can_place(task, start_day, schedule,
                          self.tasks_by_id, self.project.resource_limits):
                new_schedule = dict(schedule)
                new_schedule[candidate] = (start_day, start_day + task.duration)
                new_remaining = remaining - {candidate}
                new_max = current_max_end
                end_day = start_day + task.duration
                if end_day > new_max:
                    new_max = end_day

                # Отсечение: если и так хуже UB — этот день не подходит,
                # но более поздние тем более хуже, поэтому break
                if new_max >= self._best_makespan:
                    break

                self._search(new_schedule, new_remaining, new_max)