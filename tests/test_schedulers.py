import pytest

from core.models import Task, Project
from core.schedulers import (
    SerialScheduler,
    ParallelScheduler,
    create_scheduler,
    rule_lpt,
    rule_spt,
    rule_mts,
    rule_grpw,
    rule_ms,
)


@pytest.fixture
def independent_project():
    """
    Two independent tasks competing for one resource.
    """
    return Project(
        tasks=[
            Task(1, "Long task", 3, {"developer": 1}),
            Task(2, "Short task", 2, {"developer": 1}),
        ],
        resource_limits={"developer": 1},
        name="Independent Tasks",
    )


@pytest.fixture
def dependency_project():
    return Project(
        tasks=[
            Task(1, "Design", 2, {"developer": 1}),
            Task(2, "Implementation", 4, {"developer": 1}),
            Task(3, "Testing", 3, {"tester": 1}),
        ],
        dependencies={
            2: [1],
            3: [2],
        },
        resource_limits={
            "developer": 1,
            "tester": 1,
        },
        name="Dependency Project",
    )


def assert_schedule_is_valid(project, schedule, makespan):
    tasks_by_id = {task.id: task for task in project.tasks}

    assert set(schedule) == set(tasks_by_id)

    for task_id, (start, end) in schedule.items():
        task = tasks_by_id[task_id]

        assert start >= 0
        assert end > start
        assert end - start == task.duration

    for task_id, dependencies in project.dependencies.items():
        task_start = schedule[task_id][0]

        for dependency_id in dependencies:
            dependency_end = schedule[dependency_id][1]

            assert task_start >= dependency_end

    if schedule:
        last_day = max(end for _, end in schedule.values())

        for day in range(last_day):
            usage = {}

            for task_id, (start, end) in schedule.items():
                if start <= day < end:
                    task = tasks_by_id[task_id]

                    for resource, amount in task.resources.items():
                        usage[resource] = (
                            usage.get(resource, 0) + amount
                        )

            for resource, amount in usage.items():
                assert amount <= project.resource_limits.get(
                    resource, 0
                )
                
    expected_makespan = max(
        (end for _, end in schedule.values()),
        default=0,
    )

    assert makespan == expected_makespan

def test_serial_scheduler_creates_complete_schedule(
    independent_project,
):
    scheduler = SerialScheduler(independent_project)

    schedule, makespan = scheduler.schedule()

    assert_schedule_is_valid(
        independent_project,
        schedule,
        makespan,
    )


def test_serial_scheduler_respects_resource_capacity(
    independent_project,
):
    scheduler = SerialScheduler(independent_project, rule="LPT")

    schedule, makespan = scheduler.schedule()

    assert schedule[1] == (0, 3)
    assert schedule[2] == (3, 5)
    assert makespan == 5


def test_serial_scheduler_respects_dependencies(dependency_project):
    scheduler = SerialScheduler(dependency_project)

    schedule, makespan = scheduler.schedule()

    assert_schedule_is_valid(
        dependency_project,
        schedule,
        makespan,
    )

    assert schedule[2][0] >= schedule[1][1]
    assert schedule[3][0] >= schedule[2][1]


def test_serial_scheduler_accepts_custom_order(independent_project):
    scheduler = SerialScheduler(independent_project, rule="SPT")

    schedule, makespan = scheduler.schedule(order=[1, 2])

    assert_schedule_is_valid(
        independent_project,
        schedule,
        makespan,
    )


def test_serial_scheduler_rejects_unknown_priority_rule(
    independent_project,
):
    with pytest.raises(ValueError):
        SerialScheduler(independent_project, rule="UNKNOWN")

def test_parallel_scheduler_creates_complete_schedule(
    independent_project,
):
    scheduler = ParallelScheduler(independent_project)

    schedule, makespan = scheduler.schedule()

    assert_schedule_is_valid(
        independent_project,
        schedule,
        makespan,
    )


def test_parallel_scheduler_respects_resource_capacity(
    independent_project,
):
    scheduler = ParallelScheduler(independent_project)

    schedule, makespan = scheduler.schedule()

    # Only one task can use the developer resource at a time.
    assert_schedule_is_valid(
        independent_project,
        schedule,
        makespan,
    )

    assert makespan == 5


def test_parallel_scheduler_runs_independent_tasks_concurrently():
    project = Project(
        tasks=[
            Task(1, "Task A", 3, {"developer": 1}),
            Task(2, "Task B", 2, {"developer": 1}),
        ],
        resource_limits={"developer": 2},
    )

    scheduler = ParallelScheduler(project)

    schedule, makespan = scheduler.schedule()

    assert schedule[1] == (0, 3)
    assert schedule[2] == (0, 2)
    assert makespan == 3

    assert_schedule_is_valid(project, schedule, makespan)


def test_parallel_scheduler_respects_dependencies(dependency_project):
    scheduler = ParallelScheduler(dependency_project)

    schedule, makespan = scheduler.schedule()

    assert_schedule_is_valid(
        dependency_project,
        schedule,
        makespan,
    )


def test_parallel_scheduler_rejects_unknown_priority_rule(
    independent_project,
):
    with pytest.raises(ValueError):
        ParallelScheduler(independent_project, rule="UNKNOWN")

@pytest.mark.parametrize(
    ("method", "expected_class"),
    [
        ("serial", SerialScheduler),
        ("parallel", ParallelScheduler),
    ],
)
def test_create_scheduler_returns_correct_class(
    independent_project,
    method,
    expected_class,
):
    scheduler = create_scheduler(
        method,
        independent_project,
        "LPT",
    )

    assert isinstance(scheduler, expected_class)


def test_create_scheduler_is_case_insensitive(independent_project):
    scheduler = create_scheduler(
        "SERIAL",
        independent_project,
        "LPT",
    )

    assert isinstance(scheduler, SerialScheduler)


def test_create_scheduler_rejects_unknown_method(independent_project):
    with pytest.raises(ValueError, match="Неизвестный метод"):
        create_scheduler(
            "unknown",
            independent_project,
        )

def test_lpt_prioritizes_longer_tasks(independent_project):
    long_task, short_task = independent_project.tasks

    assert rule_lpt(long_task, independent_project, {}) < (
        rule_lpt(short_task, independent_project, {})
    )


def test_spt_prioritizes_shorter_tasks(independent_project):
    long_task, short_task = independent_project.tasks

    assert rule_spt(short_task, independent_project, {}) < (
        rule_spt(long_task, independent_project, {})
    )


def test_mts_prioritizes_tasks_with_longer_successor_chains():
    project = Project(
        tasks=[
            Task(1, "Task A", 2),
            Task(2, "Task B", 3),
            Task(3, "Task C", 4),
        ],
        dependencies={
            2: [1],
            3: [2],
        },
    )

    task_a = project.get_task(1)
    task_b = project.get_task(2)

    assert rule_mts(task_a, project, {}) < (
        rule_mts(task_b, project, {})
    )


def test_grpw_accounts_for_task_and_successor_durations():
    project = Project(
        tasks=[
            Task(1, "Task A", 2),
            Task(2, "Task B", 3),
        ],
        dependencies={2: [1]},
    )

    task_a = project.get_task(1)
    task_b = project.get_task(2)

    assert rule_grpw(task_a, project, {}) == -5
    assert rule_grpw(task_b, project, {}) == -3


def test_ms_prioritizes_greater_resource_consumption():
    project = Project(
        tasks=[
            Task(1, "Task A", 2, {"developer": 1}),
            Task(2, "Task B", 2, {"developer": 2}),
        ],
        resource_limits={"developer": 2},
    )

    task_a = project.get_task(1)
    task_b = project.get_task(2)

    assert rule_ms(task_b, project, {}) < (
        rule_ms(task_a, project, {})
    )

def test_scheduler_fails_when_task_exceeds_resource_capacity():
    project = Project(
        tasks=[
            Task(1, "Impossible task", 3, {"developer": 3}),
        ],
        resource_limits={"developer": 2},
    )

    scheduler = SerialScheduler(project)

    with pytest.raises(RuntimeError):
        scheduler.schedule()
