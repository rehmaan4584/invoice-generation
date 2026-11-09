import sqlite3
import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

from config import DB_PATH, SAVED_DIR


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the SQLite database table for edited PDFs."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS saved_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        filename TEXT NOT NULL,
        file_path TEXT NOT NULL,
        original_filename TEXT NOT NULL,
        page_count INTEGER DEFAULT 1,
        file_size_kb REAL DEFAULT 0.0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()


def save_document(
    title: str,
    filename: str,
    file_path: str,
    original_filename: str,
    page_count: int,
    file_size_kb: float
) -> int:
    """Inserts a new edited document record into the database."""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO saved_documents (
        title, filename, file_path, original_filename, page_count, file_size_kb, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        title.strip(),
        filename.strip(),
        str(file_path),
        original_filename.strip(),
        page_count,
        round(file_size_kb, 2),
        now_str,
        now_str
    ))
    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return doc_id


def list_documents(search_query: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all saved edited PDFs, optionally filtered by title or filename."""
    conn = get_connection()
    cursor = conn.cursor()

    if search_query and search_query.strip():
        term = f"%{search_query.strip()}%"
        cursor.execute("""
        SELECT * FROM saved_documents 
        WHERE title LIKE ? OR filename LIKE ? OR original_filename LIKE ?
        ORDER BY id DESC
        """, (term, term, term))
    else:
        cursor.execute("SELECT * FROM saved_documents ORDER BY id DESC")

    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_document(doc_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a single saved document by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM saved_documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_document(
    doc_id: int,
    title: str,
    file_path: str,
    file_size_kb: float
):
    """Updates an existing document's title or binary file content."""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    UPDATE saved_documents SET
        title = ?,
        file_path = ?,
        file_size_kb = ?,
        updated_at = ?
    WHERE id = ?
    """, (title.strip(), str(file_path), round(file_size_kb, 2), now_str, doc_id))
    conn.commit()
    conn.close()


def delete_document(doc_id: int) -> bool:
    """Deletes the document entry from the database and removes the file from disk."""
    doc = get_document(doc_id)
    if not doc:
        return False

    # Remove file from disk
    file_path = Path(doc["file_path"])
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")

    # Remove record from database
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM saved_documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()
    return True
