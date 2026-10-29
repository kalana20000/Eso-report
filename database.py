import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

DB_FILE = os.path.join(os.path.dirname(__file__), "rank_tracker.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes and migrates the SQLite database schema."""
    conn = get_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rank_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP NOT NULL,
                keyword TEXT NOT NULL,
                location TEXT NOT NULL,
                country_code TEXT,
                target_website TEXT NOT NULL,
                target_found BOOLEAN NOT NULL,
                rank INTEGER,
                page INTEGER,
                appearances_count INTEGER DEFAULT 0,
                all_appearances_json TEXT,
                matched_url TEXT,
                matched_title TEXT,
                total_extracted INTEGER,
                duration_seconds REAL,
                results_json TEXT
            )
        """)
        
        # Check and add new columns if upgrading from earlier version
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(rank_checks)")
        columns = [row["name"] for row in cursor.fetchall()]
        
        if "appearances_count" not in columns:
            cursor.execute("ALTER TABLE rank_checks ADD COLUMN appearances_count INTEGER DEFAULT 0")
        if "all_appearances_json" not in columns:
            cursor.execute("ALTER TABLE rank_checks ADD COLUMN all_appearances_json TEXT")
            
    conn.close()


def save_check_result(data: Dict) -> int:
    """Saves a check result to the database and returns the record ID."""
    conn = get_connection()
    with conn:
        matched = data.get("matched_item") or {}
        cursor = conn.execute(
            """
            INSERT INTO rank_checks (
                created_at, keyword, location, country_code, target_website,
                target_found, rank, page, appearances_count, all_appearances_json,
                matched_url, matched_title, total_extracted, duration_seconds, results_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                data.get("keyword"),
                data.get("location"),
                data.get("country_code"),
                data.get("target_website"),
                1 if data.get("target_found") else 0,
                data.get("rank"),
                data.get("page"),
                data.get("appearances_count", 0),
                json.dumps(data.get("all_appearances", [])),
                matched.get("url") or "",
                matched.get("title") or "",
                data.get("total_extracted", 0),
                data.get("duration_seconds", 0.0),
                json.dumps(data.get("results", [])),
            ),
        )
        record_id = cursor.lastrowid
    conn.close()
    return record_id


def get_recent_checks(limit: int = 50) -> List[Dict]:
    """Retrieves recent rank checks sorted by date descending."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, created_at, keyword, location, country_code, target_website,
               target_found, rank, page, appearances_count, all_appearances_json,
               matched_url, matched_title, total_extracted, duration_seconds
        FROM rank_checks
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    checks = []
    for row in rows:
        d = dict(row)
        if d.get("all_appearances_json"):
            try:
                d["all_appearances"] = json.loads(d["all_appearances_json"])
            except Exception:
                d["all_appearances"] = []
        else:
            d["all_appearances"] = []
        checks.append(d)
    conn.close()
    return checks


def get_check_by_id(record_id: int) -> Optional[Dict]:
    """Retrieves a single check result including full results JSON."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM rank_checks WHERE id = ?
        """,
        (record_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    
    data = dict(row)
    if data.get("results_json"):
        data["results"] = json.loads(data["results_json"])
    else:
        data["results"] = []
        
    if data.get("all_appearances_json"):
        try:
            data["all_appearances"] = json.loads(data["all_appearances_json"])
        except Exception:
            data["all_appearances"] = []
    else:
        data["all_appearances"] = []
        
    return data


def delete_check_by_id(record_id: int) -> bool:
    """Deletes a check from database."""
    conn = get_connection()
    with conn:
        cursor = conn.execute("DELETE FROM rank_checks WHERE id = ?", (record_id,))
        deleted = cursor.rowcount > 0
    conn.close()
    return deleted
