"""
Хранилище данных в SQLite: пользователи и проекты.

Схема:
    users        — учётные записи (логин, хэш пароля, дата регистрации),
    projects     — проекты (имя, владелец, JSON с данными проекта),
    schedules    — история расчётов (метод, правило, makespan, дата).

Файл БД создаётся в %LOCALAPPDATA%/RCPSP/data.db (Windows) или
~/.local/share/RCPSP/data.db (Linux/macOS).
"""
import json
import sqlite3
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import Project


# ============================================================================
# ПУТЬ К ФАЙЛУ БД
# ============================================================================
def get_db_path() -> Path:
    """
    Возвращает путь к файлу БД в пользовательской папке.
    На Windows — %LOCALAPPDATA%\\RCPSP\\data.db.
    На Linux/macOS — ~/.local/share/RCPSP/data.db.
    """
    if os.name == 'nt':  # Windows
        base = Path(os.getenv('LOCALAPPDATA', Path.home()))
    else:
        base = Path.home() / '.local' / 'share'

    data_dir = base / 'RCPSP'
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / 'data.db'


# ============================================================================
# ПОДКЛЮЧЕНИЕ
# ============================================================================
def get_connection() -> sqlite3.Connection:
    """Открывает соединение с БД и создаёт схему, если её нет."""
    conn = sqlite3.connect(str(get_db_path()))
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection):
    """Создаёт таблицы, если их нет."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS projects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            owner_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            data        TEXT NOT NULL,       -- JSON с проектом
            task_count  INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS schedules (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            method      TEXT NOT NULL,
            rule        TEXT NOT NULL,
            makespan    INTEGER NOT NULL,
            created_at  TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_id);
        CREATE INDEX IF NOT EXISTS idx_schedules_project ON schedules(project_id);
    """)
    conn.commit()


# ============================================================================
# ПОЛЬЗОВАТЕЛИ
# ============================================================================
def _hash_password(password: str) -> str:
    """Простой SHA-256 хэш пароля."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def register_user(username: str, password: str) -> Optional[int]:
    """
    Регистрирует нового пользователя.
    Возвращает id нового пользователя или None, если логин занят.
    """
    if not username or not password:
        return None

    conn = get_connection()
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, created_at) "
                "VALUES (?, ?, ?)",
                (username, _hash_password(password),
                 datetime.now().isoformat(timespec='seconds')),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> Optional[int]:
    """
    Проверяет логин/пароль.
    Возвращает id пользователя или None, если неверно.
    """
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT id FROM users WHERE username = ? AND password_hash = ?",
            (username, _hash_password(password)),
        )
        row = cur.fetchone()
        return row['id'] if row else None
    finally:
        conn.close()


def get_username(user_id: int) -> Optional[str]:
    """Возвращает имя пользователя по id."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT username FROM users WHERE id = ?", (user_id,)
        )
        row = cur.fetchone()
        return row['username'] if row else None
    finally:
        conn.close()


# ============================================================================
# ПРОЕКТЫ
# ============================================================================
def save_project(owner_id: int, project: Project) -> int:
    """
    Сохраняет проект в БД.
    Если проект с таким именем у этого пользователя уже есть — обновляет,
    иначе создаёт новый.
    Возвращает id проекта.
    """
    now = datetime.now().isoformat(timespec='seconds')
    data = json.dumps(project.to_dict(), ensure_ascii=False)
    task_count = len(project.tasks)

    conn = get_connection()
    try:
        with conn:
            cur = conn.execute(
                "SELECT id FROM projects WHERE owner_id = ? AND name = ?",
                (owner_id, project.name),
            )
            row = cur.fetchone()

            if row:
                project_id = row['id']
                conn.execute(
                    "UPDATE projects SET data = ?, task_count = ?, updated_at = ? "
                    "WHERE id = ?",
                    (data, task_count, now, project_id),
                )
            else:
                cur = conn.execute(
                    "INSERT INTO projects (name, owner_id, data, task_count, "
                    "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (project.name, owner_id, data, task_count, now, now),
                )
                project_id = cur.lastrowid

        return project_id
    finally:
        conn.close()


def list_projects(owner_id: int) -> List[Dict[str, Any]]:
    """
    Возвращает список проектов пользователя:
    [{'id': ..., 'name': ..., 'task_count': ..., 'updated_at': ...}, ...]
    """
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT id, name, task_count, updated_at FROM projects "
            "WHERE owner_id = ? ORDER BY updated_at DESC",
            (owner_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def load_project(project_id: int) -> Optional[Project]:
    """Загружает проект из БД по id."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT data FROM projects WHERE id = ?", (project_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return Project.from_dict(json.loads(row['data']))
    finally:
        conn.close()


def delete_project(project_id: int) -> bool:
    """Удаляет проект по id."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            return cur.rowcount > 0
    finally:
        conn.close()


# ============================================================================
# ИСТОРИЯ РАСЧЁТОВ
# ============================================================================
def save_schedule(project_id: int, method: str, rule: str, makespan: int) -> int:
    """Сохраняет запись о расчёте в историю."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO schedules (project_id, method, rule, makespan, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (project_id, method, rule, makespan,
                 datetime.now().isoformat(timespec='seconds')),
            )
            return cur.lastrowid
    finally:
        conn.close()


def list_schedules(project_id: int) -> List[Dict[str, Any]]:
    """Возвращает историю расчётов проекта."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT method, rule, makespan, created_at FROM schedules "
            "WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()