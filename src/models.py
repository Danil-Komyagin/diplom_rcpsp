from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from collections import defaultdict, deque


@dataclass
class Task:
    id: int
    name: str
    duration: int
    resources: Dict[str, int]
    start_time: Optional[int] = None
    finish_time: Optional[int] = None


@dataclass
class Project:
    tasks: List[Task]
    dependencies: Dict[int, List[int]]
    resource_limits: Dict[str, int]
    name: str = "Project"

    _predecessors: Dict[int, List[int]] = field(default_factory=dict, repr=False)
    _successors: Dict[int, List[int]] = field(default_factory=dict, repr=False)
    _topological_order: List[int] = field(default_factory=list, repr=False)

    def get_task_by_id(self, task_id: int) -> Task:
        for task in self.tasks:
            if task.id == task_id:
                return task
        raise ValueError(f"Task with id {task_id} not found")

    def get_predecessors(self) -> Dict[int, List[int]]:
        if not self._predecessors:
            self._predecessors = defaultdict(list)
            for task_id, preds in self.dependencies.items():
                for pred in preds:
                    self._predecessors[task_id].append(pred)
            self._predecessors = dict(self._predecessors)
        return self._predecessors

    def get_successors(self) -> Dict[int, List[int]]:
        if not self._successors:
            self._successors = defaultdict(list)
            for task_id, preds in self.dependencies.items():
                for pred in preds:
                    self._successors[pred].append(task_id)
            self._successors = dict(self._successors)
        return self._successors

    def get_topological_order(self) -> List[int]:
        if self._topological_order:
            return self._topological_order

        graph = defaultdict(list)
        in_degree = {task.id: 0 for task in self.tasks}

        for task_id, preds in self.dependencies.items():
            for pred in preds:
                graph[pred].append(task_id)
                in_degree[task_id] += 1

        queue = deque([task.id for task in self.tasks if in_degree[task.id] == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for next_node in graph[node]:
                in_degree[next_node] -= 1
                if in_degree[next_node] == 0:
                    queue.append(next_node)

        if len(result) != len(self.tasks):
            raise ValueError("В графе обнаружен цикл! Невозможно построить расписание.")

        self._topological_order = result
        return result