"""
FastAPI-обёртка над core/ RCPSP-планировщика.

Запуск:
    cd backend
    uvicorn main:app --host 0.0.0.0 --port 8000
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Cookie, Response, Body
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from core.models import Task, Project
from core.schedulers import create_scheduler, PRIORITY_RULES
from core.utils import create_test_project
from core import storage
from core.visualizer import plot_gantt, plot_resource_utilization
from core.dashboard import build_dashboard
from core.report import export_resource_table_csv, export_resource_table_txt

from schemas import (
    ProjectIn, ScheduleOut, LoginIn,
)


# ---------- Пути ----------
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="RCPSP Web")

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
app.mount("/results", StaticFiles(directory=str(RESULTS_DIR)), name="results")


# ---------- Хелперы ----------
def project_from_payload(payload: ProjectIn) -> Project:
    tasks = [
        Task(id=t.id, name=t.name, duration=t.duration, resources=t.resources)
        for t in payload.tasks
    ]
    return Project(
        tasks=tasks,
        dependencies=payload.dependencies,
        resource_limits=payload.resource_limits,
        name=payload.name,
    )


def project_to_payload(project: Project) -> dict:
    return project.to_dict()


def current_user(user_id: Optional[str] = Cookie(None)) -> Optional[int]:
    if user_id is None:
        return None
    try:
        return int(user_id)
    except ValueError:
        return None


# ---------- Корень ----------
@app.get("/")
def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


# ---------- Планирование ----------
@app.post("/api/schedule", response_model=ScheduleOut)
def schedule(
    payload: ProjectIn,
    method: str = "parallel",
    rule: str = "LPT",
):
    project = project_from_payload(payload)

    errors = project.validate()
    if errors:
        raise HTTPException(400, detail={"errors": errors})

    if rule not in PRIORITY_RULES:
        raise HTTPException(400, detail=f"Неизвестное правило: {rule}")

    try:
        scheduler = create_scheduler(method, project, rule)
        schedule_dict, makespan = scheduler.schedule()
    except Exception as e:
        raise HTTPException(500, detail=f"Ошибка планирования: {e}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    res_file = RESULTS_DIR / f"resources_{stamp}.png"
    dash_file = RESULTS_DIR / f"dashboard_{stamp}.png"

    try:
        # plot_gantt больше не нужен, так как фронтенд рисует интерактивный SVG
        plot_resource_utilization(project, schedule_dict, save_path=str(res_file))
        img = build_dashboard(project, schedule_dict)
        img.save(dash_file)
    except Exception as e:
        raise HTTPException(500, detail=f"Ошибка визуализации: {e}")

    return ScheduleOut(
        makespan=makespan,
        schedule={tid: [s, e] for tid, (s, e) in schedule_dict.items()},
        gantt_url="", # Оставляем пустым, так как фронтенд больше не использует картинку
        resources_url=f"/results/{res_file.name}",
        dashboard_url=f"/results/{dash_file.name}",
    )


# ---------- Демо ----------
@app.post("/api/demo")
def demo(n_tasks: int = 12, n_resources: int = 3, seed: int = 42):
    try:
        project = create_test_project(
            n_tasks=n_tasks, n_resources=n_resources, seed=seed
        )
    except Exception as e:
        raise HTTPException(500, detail=str(e))
    return project_to_payload(project)


# ---------- JSON save/load ----------
@app.post("/api/project/export")
def export_json(payload: ProjectIn):
    project = project_from_payload(payload)
    data = project.to_dict()
    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f'attachment; filename="{project.name}.json"'
        },
    )


@app.post("/api/project/import")
def import_json(payload: dict):
    try:
        project = Project.from_dict(payload)
        errors = project.validate()
        if errors:
            raise HTTPException(400, detail={"errors": errors})
        return project_to_payload(project)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, detail=f"Некорректный JSON: {e}")


# ---------- Экспорт таблицы ресурсов ----------
@app.post("/api/export/resource-table")
def export_resource_table(
    body: dict = Body(...),
    fmt: str = "csv",
    start_date: Optional[str] = None,
):
    payload_dict = body.get("payload")
    schedule_dict = body.get("schedule")

    if not payload_dict:
        raise HTTPException(400, "В теле отсутствует 'payload'")
    if not schedule_dict:
        raise HTTPException(400, "В теле отсутствует 'schedule' (сначала запустите планирование)")

    try:
        payload = ProjectIn(**payload_dict)
    except Exception as e:
        raise HTTPException(400, f"Некорректный payload: {e}")

    project = project_from_payload(payload)

    try:
        sched = {
            int(k): (int(v[0]), int(v[1]))
            for k, v in schedule_dict.items()
        }
    except Exception as e:
        raise HTTPException(400, f"Некорректный schedule: {e}")

    dt = None
    if start_date:
        try:
            dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(400, "start_date должен быть в формате YYYY-MM-DD")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    ext = ".csv" if fmt == "csv" else ".txt"
    out_file = RESULTS_DIR / f"resource_table_{stamp}{ext}"

    if fmt == "csv":
        ok = export_resource_table_csv(project, sched, str(out_file), dt)
        media_type = "text/csv"
    elif fmt == "txt":
        ok = export_resource_table_txt(project, sched, str(out_file), dt)
        media_type = "text/plain"
    else:
        raise HTTPException(400, f"Неизвестный формат: {fmt}. Используйте 'csv' или 'txt'.")

    if not ok:
        raise HTTPException(500, "Не удалось сформировать отчёт")

    return FileResponse(
        str(out_file),
        filename=f"resource_table_{stamp}{ext}",
        media_type=media_type,
    )


# ---------- Авторизация ----------
@app.post("/api/auth/register")
def register(payload: LoginIn, response: Response):
    uid = storage.register_user(payload.username, payload.password)
    if uid is None:
        raise HTTPException(400, "Логин уже занят")
    response.set_cookie("user_id", str(uid), httponly=True, samesite="lax")
    return {"user_id": uid, "username": payload.username}


@app.post("/api/auth/login")
def login(payload: LoginIn, response: Response):
    uid = storage.authenticate_user(payload.username, payload.password)
    if uid is None:
        raise HTTPException(401, "Неверный логин или пароль")
    response.set_cookie("user_id", str(uid), httponly=True, samesite="lax")
    return {"user_id": uid, "username": payload.username}


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie("user_id")
    return {"ok": True}


# ---------- Проекты в БД ----------
@app.post("/api/projects/save")
def save_project_to_db(payload: ProjectIn, user_id: Optional[str] = Cookie(None)):
    uid = current_user(user_id)
    if uid is None:
        raise HTTPException(401, "Требуется вход")

    project = project_from_payload(payload)
    try:
        pid = storage.save_project(uid, project)
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"project_id": pid}


@app.get("/api/projects/list")
def list_projects(user_id: Optional[str] = Cookie(None)):
    uid = current_user(user_id)
    if uid is None:
        raise HTTPException(401, "Требуется вход")
    return storage.list_projects(uid)


@app.get("/api/projects/{project_id}")
def load_project(project_id: int, user_id: Optional[str] = Cookie(None)):
    uid = current_user(user_id)
    if uid is None:
        raise HTTPException(401, "Требуется вход")
    project = storage.load_project(project_id)
    if project is None:
        raise HTTPException(404, "Проект не найден")
    return project_to_payload(project)


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int, user_id: Optional[str] = Cookie(None)):
    uid = current_user(user_id)
    if uid is None:
        raise HTTPException(401, "Требуется вход")
    ok = storage.delete_project(project_id)
    if not ok:
        raise HTTPException(404, "Проект не найден")
    return {"ok": True}