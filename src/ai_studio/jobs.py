from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path


class Jobs:
    """Local queue shared by the native desktop and the optional MCP bridge."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=10)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, prompt TEXT NOT NULL, kind TEXT NOT NULL,
          mode TEXT NOT NULL, state TEXT NOT NULL, result TEXT NOT NULL DEFAULT '',
          created REAL NOT NULL, updated REAL NOT NULL, cancelled INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS bridge_meta(key TEXT PRIMARY KEY, value TEXT);
        """)
        columns = {row[1] for row in self.db.execute('PRAGMA table_info(jobs)')}
        for name, definition in [('profile_id', "TEXT NOT NULL DEFAULT 'default'"), ('profile', "TEXT NOT NULL DEFAULT '{}'" )]:
            if name not in columns:
                self.db.execute(f'ALTER TABLE jobs ADD COLUMN {name} {definition}')
        self.db.commit()

    def heartbeat(self, enabled, profiles=None):
        with self.db:
            for key, value in (("heartbeat", str(time.time())), ("enabled", str(int(enabled)))):
                self.db.execute("INSERT INTO bridge_meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
            if profiles is not None:
                self.db.execute("INSERT INTO bridge_meta VALUES('profiles',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (json.dumps(profiles, ensure_ascii=False),))

    def profile(self, profile_id):
        row = self.db.execute("SELECT value FROM bridge_meta WHERE key='profiles'").fetchone()
        if row is None and profile_id == 'default':
            return {}  # Compatibility with older desktops and bridges.
        profiles = json.loads(row[0]) if row else []
        profile = next((p for p in profiles if p['id'] == profile_id), None)
        if profile is None:
            raise ValueError('İş bölümü profili bulunamadı. Bağlantıyı yeniden kopyala.')
        return profile

    def desktop_status(self):
        meta = dict(self.db.execute("SELECT key,value FROM bridge_meta"))
        return {"online": time.time() - float(meta.get("heartbeat", "0")) < 15, "enabled": meta.get("enabled") == "1"}

    def create(self, prompt, kind="research", mode="detailed", external=False, profile_id='default', profile=None):
        if kind not in {"research", "model"} or mode not in {"quick", "detailed", "deep"}:
            raise ValueError("Geçersiz görev türü/modu")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 20_000:
            raise ValueError("Görev metni 1–20000 karakter olmalı")
        if external:
            state = self.desktop_status()
            if not state["online"] or not state["enabled"]:
                raise ValueError("Kayriva’yı aç ve İş bölümü sayfasında MCP köprüsünü etkinleştir.")
            profile = self.profile(profile_id)
            if profile and not profile.get('enabled'):
                raise ValueError('Bu profil için MCP görev kabulünü etkinleştir.')
        elif profile is None:
            profile = self.profile(profile_id)
        pending = self.db.execute("SELECT COUNT(*) FROM jobs WHERE state IN ('queued','running')").fetchone()[0]
        if pending >= 20:
            raise ValueError("Görev kuyruğu dolu")
        uid, now = uuid.uuid4().hex, time.time()
        with self.db:
            self.db.execute("INSERT INTO jobs(id,prompt,kind,mode,state,created,updated,profile_id,profile) VALUES(?,?,?,?,'queued',?,?,?,?)", (uid, prompt, kind, mode, now, now, profile_id, json.dumps(profile or {}, ensure_ascii=False)))
        return uid

    def claim(self):
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            row = self.db.execute("SELECT id FROM jobs WHERE state='queued' AND cancelled=0 ORDER BY created LIMIT 1").fetchone()
            if not row:
                return None
            self.db.execute("UPDATE jobs SET state='running',updated=? WHERE id=?", (time.time(), row[0]))
        return self.get(row[0])

    def get(self, uid):
        cursor = self.db.execute("SELECT * FROM jobs WHERE id=?", (uid,))
        row = cursor.fetchone()
        if not row:
            raise ValueError("Görev bulunamadı")
        return dict(zip([c[0] for c in cursor.description], row))

    def recent(self):
        return [self.get(row[0]) for row in self.db.execute("SELECT id FROM jobs ORDER BY created DESC LIMIT 100").fetchall()]

    def finish(self, uid, state, result):
        with self.db:
            self.db.execute("UPDATE jobs SET state=?,result=?,updated=? WHERE id=?", (state, result, time.time(), uid))

    def cancel(self, uid):
        self.get(uid)
        with self.db:
            self.db.execute("UPDATE jobs SET cancelled=1,state=CASE WHEN state='queued' THEN 'cancelled' ELSE state END,updated=? WHERE id=?", (time.time(), uid))

    def recover(self):
        with self.db:
            self.db.execute("UPDATE jobs SET state='failed',result='Uygulama önceki görev tamamlanmadan kapandı.' WHERE state='running'")

    def close(self):
        self.db.close()
