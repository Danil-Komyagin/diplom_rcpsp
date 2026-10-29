"""
Генетический алгоритм для задачи RCPSP.

Идея:
- Особь (хромосома) — это перестановка ID всех задач проекта.
- Fitness особи — makespan, полученный при вызове SerialScheduler
  с этой перестановкой в качестве порядка задач.
- Чем меньше makespan, тем лучше особь.

Операторы:
- Селекция: турнирная (k случайных, побеждает лучший).
- Кроссовер: order crossover (OX1) — сохраняет относительный порядок.
- Мутация: swap двух случайных генов.
- Элитизм: несколько лучших особей переходят в следующее поколение
  без изменений.
"""
import random
from typing import Dict, List, Tuple

from .models import Project
from .schedulers import SerialScheduler, Schedule


# ============================================================================
# ПАРАМЕТРЫ ПО УМОЛЧАНИЮ
# ============================================================================
DEFAULT_POPULATION_SIZE = 30
DEFAULT_GENERATIONS = 50
DEFAULT_MUTATION_RATE = 0.15
DEFAULT_TOURNAMENT_SIZE = 3
DEFAULT_ELITE_SIZE = 2


# ============================================================================
# ГЕНЕТИЧЕСКИЙ ПЛАНИРОВЩИК
# ============================================================================
class GeneticScheduler:
    """
    Генетический алгоритм для RCPSP.

    Использование:
        scheduler = GeneticScheduler(project, rule='LPT')
        schedule, makespan = scheduler.schedule()

    Все параметры ГА можно переопределить в конструкторе.
    """

    def __init__(
        self,
        project: Project,
        rule: str = 'LPT',
        population_size: int = DEFAULT_POPULATION_SIZE,
        generations: int = DEFAULT_GENERATIONS,
        mutation_rate: float = DEFAULT_MUTATION_RATE,
        tournament_size: int = DEFAULT_TOURNAMENT_SIZE,
        elite_size: int = DEFAULT_ELITE_SIZE,
        seed: int = None,
    ):
        self.project = project
        self.rule = rule
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.tournament_size = tournament_size
        self.elite_size = elite_size

        if seed is not None:
            random.seed(seed)

        # Список ID всех задач проекта
        self.task_ids: List[int] = [t.id for t in project.tasks]
        self.n = len(self.task_ids)
        if self.n == 0:
            raise ValueError("Проект не содержит задач")

        # SerialScheduler используется для оценки каждой особи
        self._evaluator = SerialScheduler(project, rule=rule)

        # Кэш: перестановка (в виде tuple) -> makespan
        self._fitness_cache: Dict[Tuple[int, ...], int] = {}

    # ------------------------------------------------------------------
    # ПУБЛИЧНОЕ API
    # ------------------------------------------------------------------
    def schedule(self) -> Tuple[Schedule, int]:
        """
        Запускает ГА и возвращает лучшее найденное расписание.
        """
        population = self._init_population()

        # Сортируем по fitness (меньше — лучше)
        population = sorted(population, key=self._fitness)

        for generation in range(self.generations):
            new_population = population[: self.elite_size]  # элитизм

            # Добираем популяцию до нужного размера
            while len(new_population) < self.population_size:
                parent1 = self._tournament_select(population)
                parent2 = self._tournament_select(population)

                child = self._order_crossover(parent1, parent2)
                self._mutate(child)
                new_population.append(child)

            # Сортируем новое поколение по fitness
            new_population = sorted(new_population, key=self._fitness)
            population = new_population

        best_genome = population[0]
        schedule, makespan = self._evaluate(best_genome)
        return schedule, makespan

    # ------------------------------------------------------------------
    # ИНИЦИАЛИЗАЦИЯ ПОПУЛЯЦИИ
    # ------------------------------------------------------------------
    def _init_population(self) -> List[List[int]]:
        """
        Создаёт начальную популяцию.

        Первая особь — это топологически отсортированный порядок задач
        (чтобы SGS гарантированно отработал без переставлений).
        Остальные — случайные перестановки.
        """
        population: List[List[int]] = []

        # Эвристическая начальная особь: задачи, отсортированные по правилу,
        # но с учётом предшественников (топологический порядок)
        heuristic_order = self._topological_priority_order()
        population.append(heuristic_order)

        # Остальные — случайные перестановки
        while len(population) < self.population_size:
            genome = self.task_ids[:]
            random.shuffle(genome)
            population.append(genome)

        return population

    def _topological_priority_order(self) -> List[int]:
        """
        Возвращает перестановку ID задач, которая:
        - уважает частичный порядок (предшественники идут раньше),
        - внутри одного «уровня готовности» сортирует по правилу приоритета.
        """
        from .schedulers import PRIORITY_RULES
        rule_fn = PRIORITY_RULES.get(self.rule.upper())
        if rule_fn is None:
            # fallback: просто все ID подряд
            return self.task_ids[:]

        # Предшественники
        preds: Dict[int, List[int]] = {tid: [] for tid in self.task_ids}
        for tid, deps in self.project.dependencies.items():
            if tid in preds:
                preds[tid] = list(deps)

        # Оставшиеся предшественники
        remaining_preds = {tid: set(preds[tid]) for tid in self.task_ids}
        ready = [tid for tid in self.task_ids if not remaining_preds[tid]]
        order: List[int] = []

        # Для сортировки нужен «пустой» schedule
        empty_schedule: Schedule = {}
        tasks_by_id = {t.id: t for t in self.project.tasks}

        while ready:
            # Сортируем готовые по правилу
            ready.sort(
                key=lambda tid: rule_fn(tasks_by_id[tid], self.project, empty_schedule)
            )
            chosen = ready.pop(0)
            order.append(chosen)

            # Убираем chosen из предшественников других
            for tid in self.task_ids:
                if chosen in remaining_preds[tid]:
                    remaining_preds[tid].discard(chosen)
                    if not remaining_preds[tid] and tid not in order and tid not in ready:
                        ready.append(tid)

        # На случай, если что-то осталось (цикл или ошибка) — допишем в конец
        for tid in self.task_ids:
            if tid not in order:
                order.append(tid)

        return order

    # ------------------------------------------------------------------
    # ОЦЕНКА ОСОБИ
    # ------------------------------------------------------------------
    def _fitness(self, genome: List[int]) -> int:
        """Fitness = makespan (чем меньше — тем лучше)."""
        key = tuple(genome)
        if key in self._fitness_cache:
            return self._fitness_cache[key]
        _, makespan = self._evaluate(genome)
        self._fitness_cache[key] = makespan
        return makespan

    def _evaluate(self, genome: List[int]) -> Tuple[Schedule, int]:
        """Прогон SerialScheduler с заданным порядком задач."""
        return self._evaluator.schedule(order=list(genome))

    # ------------------------------------------------------------------
    # СЕЛЕКЦИЯ
    # ------------------------------------------------------------------
    def _tournament_select(self, population: List[List[int]]) -> List[int]:
        """Турнирная селекция: k случайных, побеждает лучший по fitness."""
        k = min(self.tournament_size, len(population))
        candidates = random.sample(population, k)
        winner = min(candidates, key=self._fitness)
        return winner[:]  # возвращаем копию

    # ------------------------------------------------------------------
    # КРОССОВЕР (Order Crossover OX1)
    # ------------------------------------------------------------------
    def _order_crossover(self, parent1: List[int], parent2: List[int]) -> List[int]:
        """
        OX1: выбираем случайный отрезок из parent1, копируем его в ребёнка,
        остальные гены заполняем в порядке их появления в parent2,
        пропуская уже использованные.
        """
        n = len(parent1)
        if n < 2:
            return parent1[:]

        a, b = sorted(random.sample(range(n), 2))
        child: List[int] = [None] * n  # type: ignore

        # Копируем отрезок из parent1
        for i in range(a, b + 1):
            child[i] = parent1[i]

        # Порядок parent2, пропуская уже использованные гены
        used = set(child[a:b + 1])
        fill_values = [gene for gene in parent2 if gene not in used]

        # Заполняем оставшиеся позиции по кругу, начиная с b+1
        idx = 0
        for i in list(range(b + 1, n)) + list(range(0, a)):
            child[i] = fill_values[idx]
            idx += 1

        return child  # type: ignore

    # ------------------------------------------------------------------
    # МУТАЦИЯ (swap)
    # ------------------------------------------------------------------
    def _mutate(self, genome: List[int]) -> None:
        """Меняет местами два случайных гена с вероятностью mutation_rate."""
        if len(genome) < 2:
            return
        if random.random() < self.mutation_rate:
            i, j = random.sample(range(len(genome)), 2)
            genome[i], genome[j] = genome[j], genome[i]