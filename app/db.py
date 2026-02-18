from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, Tuple


def get_db_path(data_dir: Path) -> Path:
    return data_dir / "mapping.db"


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_no INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE NOT NULL,
            original_filename_full TEXT NOT NULL,
            original_filename_safe TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            token TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            original_value TEXT NOT NULL,
            UNIQUE(job_id, token)
        );
        """)
        conn.commit()
    finally:
        conn.close()


def create_job(conn: sqlite3.Connection, job_id: str, original_full: str, original_safe: str, created_at: str) -> int:
    cur = conn.execute(
        "INSERT INTO jobs(job_id, original_filename_full, original_filename_safe, created_at) VALUES(?,?,?,?)",
        (job_id, original_full, original_safe, created_at),
    )
    return int(cur.lastrowid)


def insert_mapping(conn: sqlite3.Connection, job_id: str, token: str, entity_type: str, original_value: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO mappings(job_id, token, entity_type, original_value) VALUES(?,?,?,?)",
        (job_id, token, entity_type, original_value),
    )


def load_mapping_dict(conn: sqlite3.Connection, job_id: str) -> dict[str, str]:
    rows = conn.execute(
        "SELECT token, original_value FROM mappings WHERE job_id=?",
        (job_id,),
    ).fetchall()
    return {r["token"]: r["original_value"] for r in rows}
