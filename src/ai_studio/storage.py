from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path


class History:
    def __init__(self, path: Path):
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, title TEXT NOT NULL, path TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS chats(id TEXT PRIMARY KEY, title TEXT NOT NULL, updated TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, chat_id TEXT NOT NULL REFERENCES chats(id), payload TEXT NOT NULL);
        """)
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(chats)")}
        if "project_id" not in columns:
            self.db.execute("ALTER TABLE chats ADD COLUMN project_id TEXT")
            self.db.commit()
        if "pinned" not in columns:
            self.db.execute("ALTER TABLE chats ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")
        self.db.execute("CREATE TABLE IF NOT EXISTS prompts(id TEXT PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL)")
        self.db.commit()

    def create(self, title="Yeni sohbet", project_id=None):
        uid = uuid.uuid4().hex
        with self.db:
            self.db.execute("INSERT INTO chats(id,title,project_id) VALUES(?,?,?)", (uid, title, project_id))
        return uid

    def chats(self):
        return self.db.execute("SELECT id,title FROM chats ORDER BY updated DESC, rowid DESC").fetchall()

    def recent(self):
        return self.db.execute("SELECT id,title FROM chats WHERE project_id IS NULL ORDER BY pinned DESC, updated DESC, rowid DESC").fetchall()

    def search(self, text):
        """Literal, Unicode-aware title/content search; tool payloads aren't chat text."""
        fold = lambda value: value.casefold().replace('i\u0307', 'i')
        query = fold(text.strip())
        rows = self.db.execute("SELECT id,title FROM chats ORDER BY pinned DESC,updated DESC,rowid DESC").fetchall()
        if not query:
            return rows
        matched = {uid for uid, title in rows if query in fold(title)}
        for uid, payload in self.db.execute('SELECT chat_id,payload FROM messages'):
            if uid in matched:
                continue
            message = json.loads(payload)
            if message.get('role') in {'user', 'assistant'} and query in fold(str(message.get('content', ''))):
                matched.add(uid)
        return [(uid, title) for uid, title in rows if uid in matched]

    def pinned(self, uid):
        row = self.db.execute("SELECT pinned FROM chats WHERE id=?", (uid,)).fetchone()
        return bool(row and row[0])

    def pin(self, uid, value):
        with self.db:
            self.db.execute("UPDATE chats SET pinned=? WHERE id=?", (int(bool(value)), uid))

    def export(self, uid):
        row = self.db.execute("SELECT title FROM chats WHERE id=?", (uid,)).fetchone()
        if not row:
            raise ValueError('Sohbet bulunamadı.')
        blocks = ['# ' + row[0]]
        for message in self.messages(uid):
            if message.get('role') not in {'user', 'assistant'}:
                continue
            content = message.get('content', '')
            if content:
                blocks.append('## ' + ('Sen' if message['role'] == 'user' else 'Kayriva') + '\n\n' + content)
        return '\n\n'.join(blocks) + '\n'

    def prompts(self):
        return self.db.execute("SELECT id,title,content FROM prompts ORDER BY rowid DESC").fetchall()

    def save_prompt(self, title, content, uid=None):
        if not title.strip() or not content.strip():
            raise ValueError('Ad ve istem metni gerekli.')
        uid = uid or uuid.uuid4().hex
        with self.db:
            self.db.execute("INSERT INTO prompts VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,content=excluded.content", (uid, title.strip()[:80], content.strip()))
        return uid

    def delete_prompt(self, uid):
        with self.db:
            self.db.execute("DELETE FROM prompts WHERE id=?", (uid,))

    def projects(self):
        return self.db.execute("SELECT id,title,path FROM projects ORDER BY title").fetchall()

    def add_project(self, title, path):
        existing = self.db.execute("SELECT id FROM projects WHERE path=?", (path,)).fetchone()
        if existing:
            return existing[0]
        uid = uuid.uuid4().hex
        with self.db:
            self.db.execute("INSERT INTO projects VALUES(?,?,?)", (uid, title, path))
        return uid

    def project_chats(self, uid):
        return self.db.execute("SELECT id,title FROM chats WHERE project_id=? ORDER BY pinned DESC,updated DESC,rowid DESC", (uid,)).fetchall()

    def project_for(self, chat):
        row = self.db.execute("SELECT project_id FROM chats WHERE id=?", (chat,)).fetchone()
        return row[0] if row else None

    def remove_project(self, uid):
        with self.db:
            self.db.execute("UPDATE chats SET project_id=NULL WHERE project_id=?", (uid,))
            self.db.execute("DELETE FROM projects WHERE id=?", (uid,))

    def rename_project(self, uid, title):
        with self.db:
            self.db.execute("UPDATE projects SET title=? WHERE id=?", (title, uid))

    def messages(self, uid):
        return [json.loads(r[0]) for r in self.db.execute("SELECT payload FROM messages WHERE chat_id=? ORDER BY id", (uid,))]

    def append(self, uid, messages):
        with self.db:
            for message in messages:
                self.db.execute("INSERT INTO messages(chat_id,payload) VALUES(?,?)", (uid, json.dumps(message, ensure_ascii=False)))
            self.db.execute("UPDATE chats SET updated=CURRENT_TIMESTAMP WHERE id=?", (uid,))

    def title(self, uid, text):
        with self.db:
            self.db.execute("UPDATE chats SET title=? WHERE id=?", (text[:48], uid))

    def delete(self, uid):
        with self.db:
            self.db.execute("DELETE FROM messages WHERE chat_id=?", (uid,))
            self.db.execute("DELETE FROM chats WHERE id=?", (uid,))

    def close(self):
        self.db.close()
