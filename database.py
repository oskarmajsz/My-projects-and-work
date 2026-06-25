"""Warstwa bazy danych dla Planera. SQLite, zero zależności zewnętrznych."""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "planer.db")

# Paleta kolorów do rotacji (gdy użytkownik nie wybierze własnego)
COLOR_PALETTE = [
    "#4285F4",  # niebieski
    "#0F9D58",  # zielony
    "#F4511E",  # pomarańczowy
    "#9C27B0",  # fiolet
    "#F6BF26",  # żółty/musztardowy
    "#E91E63",  # różowy/malinowy
    "#16A2B8",  # turkusowy
]


class Database:
    def __init__(self, path=DB_PATH):
        self.conn = sqlite3.connect(path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                color TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        self.conn.commit()
        self._color_index = self._load_color_index()

    def _load_color_index(self):
        cur = self.conn.execute("SELECT COUNT(*) FROM plans")
        count = cur.fetchone()[0]
        return count % len(COLOR_PALETTE)

    def next_color(self):
        color = COLOR_PALETTE[self._color_index % len(COLOR_PALETTE)]
        self._color_index += 1
        return color

    def add_plan(self, title: str, start_date: str, end_date: str,
                 color: str = None, priority: int = 0):
        if not color:
            color = self.next_color()
        self.conn.execute(
            """INSERT INTO plans (title, start_date, end_date, done, color, priority, created_at)
               VALUES (?, ?, ?, 0, ?, ?, ?)""",
            (title, start_date, end_date, color, priority, datetime.now().isoformat())
        )
        self.conn.commit()

    def update_plan(self, plan_id: int, title: str, start_date: str, end_date: str,
                     color: str, priority: int):
        self.conn.execute(
            """UPDATE plans SET title = ?, start_date = ?, end_date = ?,
               color = ?, priority = ? WHERE id = ?""",
            (title, start_date, end_date, color, priority, plan_id)
        )
        self.conn.commit()

    def set_done(self, plan_id: int, done: bool):
        self.conn.execute("UPDATE plans SET done = ? WHERE id = ?", (1 if done else 0, plan_id))
        self.conn.commit()

    def delete_plan(self, plan_id: int):
        self.conn.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
        self.conn.commit()

    def get_plan(self, plan_id: int):
        cur = self.conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
        return cur.fetchone()

    def plans_for_day(self, day_str: str):
        """Wszystkie plany obejmujące dany dzień (start <= day <= end)."""
        cur = self.conn.execute(
            """SELECT id, title, start_date, end_date, done, color, priority
               FROM plans WHERE start_date <= ? AND end_date >= ?
               ORDER BY priority DESC, start_date ASC""",
            (day_str, day_str)
        )
        return cur.fetchall()

    def plans_in_month(self, year: int, month: int):
        """Wszystkie plany które mają choć jeden dzień w danym miesiącu (dla rysowania belek)."""
        month_start = f"{year:04d}-{month:02d}-01"
        if month == 12:
            next_month_start = f"{year + 1:04d}-01-01"
        else:
            next_month_start = f"{year:04d}-{month + 1:02d}-01"
        cur = self.conn.execute(
            """SELECT id, title, start_date, end_date, done, color, priority
               FROM plans WHERE start_date < ? AND end_date >= ?
               ORDER BY priority DESC, start_date ASC""",
            (next_month_start, month_start)
        )
        return cur.fetchall()

    def search(self, query: str):
        """Szuka planów po tytule (case-insensitive, fragment)."""
        cur = self.conn.execute(
            """SELECT id, title, start_date, end_date, done, color, priority
               FROM plans WHERE title LIKE ? ORDER BY start_date DESC""",
            (f"%{query}%",)
        )
        return cur.fetchall()
