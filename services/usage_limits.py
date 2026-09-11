"""SQLite iş rezervasyonu: farklı worker'larda da kullanıcı sınırları ortaktır."""
from contextlib import asynccontextmanager
import sqlite3
import time
import uuid
from fastapi import HTTPException


def reserve_job(path: str, owner_id: str) -> str:
    now = time.time()
    token = uuid.uuid4().hex
    with sqlite3.connect(path, timeout=10) as db:
        db.execute('CREATE TABLE IF NOT EXISTS provider_jobs (id TEXT PRIMARY KEY, owner TEXT NOT NULL, started REAL NOT NULL, active_until REAL NOT NULL)')
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM provider_jobs WHERE started < ?', (now - 900,))
        active, recent = db.execute('SELECT SUM(active_until > ?), COUNT(*) FROM provider_jobs WHERE owner = ?', (now, owner_id)).fetchone()
        if (active or 0) >= 2 or recent >= 30:
            raise HTTPException(429, 'İstek sınırına ulaştınız. Devam eden taramayı bekleyin veya daha sonra tekrar deneyin.')
        db.execute('INSERT INTO provider_jobs VALUES (?,?,?,?)', (token, owner_id, now, now + 90))
    return token


def release_job(path: str, token: str):
    with sqlite3.connect(path, timeout=10) as db:
        db.execute('UPDATE provider_jobs SET active_until = 0 WHERE id = ?', (token,))


@asynccontextmanager
async def provider_job(path: str, owner_id: str):
    token = reserve_job(path, owner_id)
    try:
        yield
    finally:
        release_job(path, token)
