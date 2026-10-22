import pytest

from core.models import Task, Project


@pytest.fixture
def sample_tasks():
    return [
        Task(1, "Design", 3, {"developer": 1}),
        Task(2, "Implementation", 5, {"developer": 2}),
        Task(3, "Testing", 2, {"tester": 1}),
    ]


@pytest.fixture
def sample_project(sample_tasks):
    return Project(
        tasks=sample_tasks,
        dependencies={
            2: [1],
            3: [2],
        },
        resource_limits={
            "developer": 2,
            "tester": 1,
        },
        name="Test Project",
    )


# =========================
# Task tests
# =========================

def test_task_creation():
    task = Task(
        id=1,
        name="Development",
        duration=5,
        resources={"developer": 2},
    )

    assert task.id == 1
    assert task.name == "Development"
    assert task.duration == 5
    assert task.resources == {"developer": 2}


@pytest.mark.parametrize("duration", [0, -1, -10])
def test_task_rejects_non_positive_duration(duration):
    with pytest.raises(ValueError):
        Task(1, "Invalid task", duration)


def test_task_normalizes_numeric_fields():
    task = Task(
        id="1",
        name="Task",
        duration="3",
        resources={"developer": "2"},
    )

    assert task.id == 1
    assert task.duration == 3
    assert task.resources == {"developer": 2}


def test_task_removes_non_positive_resource_requirements():
    task = Task(
        1,
        "Task",
        3,
        {
            "developer": 2,
            "tester": 0,
            "designer": -1,
        },
    )

    assert task.resources == {"developer": 2}


def test_task_to_dict():
    task = Task(1, "Development", 5, {"developer": 2})

    result = task.to_dict()

    assert result == {
        "id": 1,
        "name": "Development",
        "duration": 5,
        "resources": {"developer": 2},
    }


def test_task_from_dict():
    data = {
        "id": 1,
        "name": "Development",
        "duration": 5,
        "resources": {"developer": 2},
    }

    task = Task.from_dict(data)

    assert task == Task(1, "Development", 5, {"developer": 2})


def test_task_from_dict_without_resources():
    task = Task.from_dict({
        "id": 1,
        "name": "Task",
        "duration": 2,
    })

    assert task.resources == {}


# =========================
# Project tests
# =========================

def test_project_creation(sample_project):
    assert sample_project.name == "Test Project"
    assert sample_project.task_count == 3


def test_get_task(sample_project):
    task = sample_project.get_task(2)

    assert task is not None
    assert task.name == "Implementation"


def test_get_task_returns_none_for_missing_id(sample_project):
    assert sample_project.get_task(999) is None


def test_get_task_by_id(sample_project):
    assert sample_project.get_task_by_id(1).name == "Design"


def test_get_task_ids(sample_project):
    assert sample_project.get_task_ids() == [1, 2, 3]


def test_get_resource_names(sample_project):
    assert sample_project.get_resource_names() == [
        "developer",
        "tester",
    ]


def test_project_validation_passes_for_valid_project(sample_project):
    assert sample_project.validate() == []


def test_project_validation_detects_duplicate_task_ids():
    project = Project(
        tasks=[
            Task(1, "Task A", 2),
            Task(1, "Task B", 3),
        ]
    )

    errors = project.validate()

    assert any("дублирующимися ID" in error for error in errors)


def test_project_validation_detects_missing_dependency():
    project = Project(
        tasks=[Task(1, "Task A", 2)],
        dependencies={1: [999]},
    )

    errors = project.validate()

    assert any("несуществующей ID=999" in error for error in errors)


def test_project_validation_detects_unknown_resource():
    project = Project(
        tasks=[
            Task(1, "Task A", 2, {"unknown_resource": 1}),
        ],
        resource_limits={"developer": 2},
    )

    errors = project.validate()

    assert any("unknown_resource" in error for error in errors)


def test_project_validation_detects_dependency_cycle():
    project = Project(
        tasks=[
            Task(1, "Task A", 2),
            Task(2, "Task B", 3),
        ],
        dependencies={
            1: [2],
            2: [1],
        },
    )

    errors = project.validate()

    assert any("цикл" in error.lower() for error in errors)


def test_get_predecessors(sample_project):
    predecessors = sample_project.get_predecessors()

    assert predecessors == {
        1: [],
        2: [1],
        3: [2],
    }


def test_get_successors(sample_project):
    successors = sample_project.get_successors()

    assert successors == {
        1: [2],
        2: [3],
        3: [],
    }


def test_topological_order_respects_dependencies(sample_project):
    order = sample_project.get_topological_order()

    positions = {
        task_id: index
        for index, task_id in enumerate(order)
    }

    assert set(order) == {1, 2, 3}
    assert positions[1] < positions[2]
    assert positions[2] < positions[3]


def test_topological_order_rejects_cycle():
    project = Project(
        tasks=[
            Task(1, "Task A", 2),
            Task(2, "Task B", 3),
        ],
        dependencies={
            1: [2],
            2: [1],
        },
    )

    with pytest.raises(ValueError, match="цикл"):
        project.get_topological_order()


def test_project_serialization_round_trip(sample_project):
    serialized = sample_project.to_dict()
    restored = Project.from_dict(serialized)

    assert restored.name == sample_project.name
    assert restored.resource_limits == sample_project.resource_limits
    assert restored.dependencies == sample_project.dependencies
    assert restored.task_count == sample_project.task_count

    for original, restored_task in zip(
        sample_project.tasks,
        restored.tasks,
    ):
        assert restored_task == original
