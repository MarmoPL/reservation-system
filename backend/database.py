"""
Moduł obsługi bazy danych SQLite.
Zawiera wszystkie operacje CRUD dla użytkowników, sal i rezerwacji.
"""

import sqlite3
import hashlib
from datetime import datetime, date
from typing import Optional
from contextlib import contextmanager

DATABASE_PATH = "reservation.db"


@contextmanager
def get_connection():
    """Context manager dla połączenia z bazą danych."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Dostęp do kolumn po nazwie
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_database():
    """Inicjalizuje bazę danych - tworzy tabele jeśli nie istnieją."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Tabela użytkowników
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_md5 TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela sal
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                capacity INTEGER DEFAULT 10,
                description TEXT
            )
        """)

        # Tabela rezerwacji
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                description TEXT,
                is_archived INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES rooms(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Dodaj domyślnego admina jeśli nie istnieje
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            admin_password = hashlib.md5("admin123".encode()).hexdigest()
            cursor.execute(
                "INSERT INTO users (username, password_md5, is_admin) VALUES (?, ?, 1)",
                ("admin", admin_password)
            )

        # Dodaj przykładowe sale jeśli nie istnieją
        cursor.execute("SELECT COUNT(*) FROM rooms")
        if cursor.fetchone()[0] == 0:
            sample_rooms = [
                ("Sala A", 10, "Mała sala konferencyjna"),
                ("Sala B", 20, "Średnia sala konferencyjna"),
                ("Sala C", 50, "Duża sala wykładowa"),
            ]
            cursor.executemany(
                "INSERT INTO rooms (name, capacity, description) VALUES (?, ?, ?)",
                sample_rooms
            )


# ============ UŻYTKOWNICY ============

def hash_password(password: str) -> str:
    """Hashuje hasło algorytmem MD5."""
    return hashlib.md5(password.encode()).hexdigest()


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Uwierzytelnia użytkownika. Zwraca dane użytkownika lub None."""
    with get_connection() as conn:
        cursor = conn.cursor()
        password_hash = hash_password(password)
        cursor.execute(
            "SELECT id, username, is_admin FROM users WHERE username = ? AND password_md5 = ?",
            (username, password_hash)
        )
        row = cursor.fetchone()
        if row:
            return {"id": row["id"], "username": row["username"], "is_admin": bool(row["is_admin"])}
        return None


def register_user(username: str, password: str, is_admin: bool = False) -> tuple[bool, str]:
    """Rejestruje nowego użytkownika. Zwraca (sukces, komunikat)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password_md5, is_admin) VALUES (?, ?, ?)",
                (username, hash_password(password), int(is_admin))
            )
            return True, "Użytkownik zarejestrowany pomyślnie"
        except sqlite3.IntegrityError:
            return False, "Użytkownik o tej nazwie już istnieje"


def get_all_users() -> list[dict]:
    """Zwraca listę wszystkich użytkowników (bez haseł)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, is_admin, created_at FROM users")
        return [dict(row) for row in cursor.fetchall()]


def delete_user(user_id: int) -> tuple[bool, str]:
    """Usuwa użytkownika. Zwraca (sukces, komunikat)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ? AND username != 'admin'", (user_id,))
        if cursor.rowcount > 0:
            return True, "Użytkownik usunięty"
        return False, "Nie można usunąć użytkownika (lub to admin)"


# ============ SALE ============

def get_all_rooms() -> list[dict]:
    """Zwraca listę wszystkich sal."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rooms")
        return [dict(row) for row in cursor.fetchall()]


def add_room(name: str, capacity: int, description: str = "") -> tuple[bool, str]:
    """Dodaje nową salę. Zwraca (sukces, komunikat)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO rooms (name, capacity, description) VALUES (?, ?, ?)",
                (name, capacity, description)
            )
            return True, "Sala dodana pomyślnie"
        except sqlite3.IntegrityError:
            return False, "Sala o tej nazwie już istnieje"


def delete_room(room_id: int) -> tuple[bool, str]:
    """Usuwa salę. Zwraca (sukces, komunikat)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
        if cursor.rowcount > 0:
            return True, "Sala usunięta"
        return False, "Sala nie istnieje"


# ============ REZERWACJE ============

def check_conflict(room_id: int, date_str: str, start_time: str, end_time: str,
                   exclude_id: Optional[int] = None) -> bool:
    """Sprawdza czy istnieje konflikt czasowy dla rezerwacji."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT id FROM reservations
            WHERE room_id = ? AND date = ? AND is_archived = 0
            AND NOT (end_time <= ? OR start_time >= ?)
        """
        params = [room_id, date_str, start_time, end_time]

        if exclude_id:
            query += " AND id != ?"
            params.append(exclude_id)

        cursor.execute(query, params)
        return cursor.fetchone() is not None


def create_reservation(room_id: int, user_id: int, date_str: str,
                       start_time: str, end_time: str, description: str = "") -> tuple[bool, str]:
    """Tworzy nową rezerwację. Automatycznie aktywuje jeśli brak konfliktu."""
    # Walidacja czasu
    if start_time >= end_time:
        return False, "Godzina rozpoczęcia musi być przed godziną zakończenia"

    # Sprawdź konflikt
    if check_conflict(room_id, date_str, start_time, end_time):
        return False, "Konflikt czasowy - sala jest już zarezerwowana w tym terminie"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO reservations
               (room_id, user_id, date, start_time, end_time, description)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (room_id, user_id, date_str, start_time, end_time, description)
        )
        return True, "Rezerwacja utworzona i aktywowana"


def get_reservations_for_date(date_str: str, room_id: Optional[int] = None) -> list[dict]:
    """Pobiera rezerwacje dla danego dnia (opcjonalnie dla konkretnej sali)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT r.*, rooms.name as room_name, users.username
            FROM reservations r
            JOIN rooms ON r.room_id = rooms.id
            JOIN users ON r.user_id = users.id
            WHERE r.date = ? AND r.is_archived = 0
        """
        params = [date_str]

        if room_id:
            query += " AND r.room_id = ?"
            params.append(room_id)

        query += " ORDER BY r.start_time"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_user_reservations(user_id: int, include_archived: bool = False) -> list[dict]:
    """Pobiera rezerwacje użytkownika."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT r.*, rooms.name as room_name
            FROM reservations r
            JOIN rooms ON r.room_id = rooms.id
            WHERE r.user_id = ?
        """
        if not include_archived:
            query += " AND r.is_archived = 0"

        query += " ORDER BY r.date, r.start_time"
        cursor.execute(query, (user_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_all_reservations(include_archived: bool = False) -> list[dict]:
    """Pobiera wszystkie rezerwacje (dla admina)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT r.*, rooms.name as room_name, users.username
            FROM reservations r
            JOIN rooms ON r.room_id = rooms.id
            JOIN users ON r.user_id = users.id
        """
        if not include_archived:
            query += " WHERE r.is_archived = 0"

        query += " ORDER BY r.date, r.start_time"
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]


def update_reservation(reservation_id: int, user_id: int, is_admin: bool,
                       date_str: str, start_time: str, end_time: str,
                       description: str) -> tuple[bool, str]:
    """Aktualizuje rezerwację (właściciel lub admin)."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Sprawdź czy rezerwacja istnieje i należy do użytkownika
        cursor.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,))
        reservation = cursor.fetchone()

        if not reservation:
            return False, "Rezerwacja nie istnieje"

        if reservation["user_id"] != user_id and not is_admin:
            return False, "Brak uprawnień do edycji tej rezerwacji"

        # Walidacja czasu
        if start_time >= end_time:
            return False, "Godzina rozpoczęcia musi być przed godziną zakończenia"

        # Sprawdź konflikt (wykluczając aktualną rezerwację)
        if check_conflict(reservation["room_id"], date_str, start_time, end_time, reservation_id):
            return False, "Konflikt czasowy - sala jest już zarezerwowana"

        cursor.execute(
            """UPDATE reservations
               SET date = ?, start_time = ?, end_time = ?, description = ?
               WHERE id = ?""",
            (date_str, start_time, end_time, description, reservation_id)
        )
        return True, "Rezerwacja zaktualizowana"


def delete_reservation(reservation_id: int, user_id: int, is_admin: bool) -> tuple[bool, str]:
    """Usuwa rezerwację (właściciel lub admin)."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Sprawdź uprawnienia
        cursor.execute("SELECT user_id FROM reservations WHERE id = ?", (reservation_id,))
        reservation = cursor.fetchone()

        if not reservation:
            return False, "Rezerwacja nie istnieje"

        if reservation["user_id"] != user_id and not is_admin:
            return False, "Brak uprawnień do usunięcia tej rezerwacji"

        cursor.execute("DELETE FROM reservations WHERE id = ?", (reservation_id,))
        return True, "Rezerwacja usunięta"


def archive_past_reservations():
    """Archiwizuje przeszłe rezerwacje."""
    today = date.today().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE reservations SET is_archived = 1 WHERE date < ? AND is_archived = 0",
            (today,)
        )


def get_week_reservations(start_date: str, end_date: str) -> list[dict]:
    """Pobiera rezerwacje dla zakresu dat (widok tygodniowy)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT r.*, rooms.name as room_name, users.username
               FROM reservations r
               JOIN rooms ON r.room_id = rooms.id
               JOIN users ON r.user_id = users.id
               WHERE r.date >= ? AND r.date <= ? AND r.is_archived = 0
               ORDER BY r.date, r.start_time""",
            (start_date, end_date)
        )
        return [dict(row) for row in cursor.fetchall()]
