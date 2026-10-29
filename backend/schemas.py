"""Pydantic-схемы для API."""
from typing import Dict, List
from pydantic import BaseModel, Field


class TaskIn(BaseModel):
    id: int
    name: str
    duration: int = Field(gt=0)
    resources: Dict[str, int] = Field(default_factory=dict)


class ProjectIn(BaseModel):
    name: str = "Мой проект"
    resource_limits: Dict[str, int] = Field(default_factory=dict)
    tasks: List[TaskIn] = Field(default_factory=list)
    dependencies: Dict[int, List[int]] = Field(default_factory=dict)


class ScheduleOut(BaseModel):
    makespan: int
    schedule: Dict[int, List[int]]  # {task_id: [start, end]}
    gantt_url: str
    resources_url: str
    dashboard_url: str


class LoginIn(BaseModel):
    username: str
    password: str


class ProjectListItem(BaseModel):
    id: int
    name: str
    task_count: int
    updated_at: str