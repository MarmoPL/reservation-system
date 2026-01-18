"""
Klient WebSocket dla systemu rezerwacji sal.
Zapewnia synchroniczną komunikację z serwerem w kontekście asynchronicznym.
"""

import asyncio
import json
import websockets
from typing import Optional, Callable
import uuid


class ReservationClient:
    """Klient WebSocket do komunikacji z serwerem rezerwacji."""

    def __init__(self, uri: str = "ws://localhost:8765"):
        self.uri = uri
        self.websocket = None
        self.connected = False
        self.pending_requests: dict = {}
        self.on_update: Optional[Callable] = None  # Callback dla aktualizacji

    async def connect(self) -> bool:
        """Nawiązuje połączenie z serwerem."""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            # Uruchom nasłuchiwanie w tle
            asyncio.create_task(self._listen())
            return True
        except Exception as e:
            print(f"Błąd połączenia: {e}")
            return False

    async def disconnect(self):
        """Zamyka połączenie z serwerem."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False

    async def _listen(self):
        """Nasłuchuje wiadomości od serwera."""
        try:
            async for message in self.websocket:
                data = json.loads(message)

                # Sprawdź czy to odpowiedź na żądanie
                request_id = data.get("request_id")
                if request_id and request_id in self.pending_requests:
                    self.pending_requests[request_id].set_result(data)
                # Albo broadcast od serwera
                elif data.get("type") and self.on_update:
                    await self.on_update(data)
        except websockets.ConnectionClosed:
            self.connected = False

    async def request(self, action: str, data: dict = None) -> dict:
        """Wysyła żądanie do serwera i czeka na odpowiedź."""
        if not self.connected:
            return {"success": False, "error": "Brak połączenia z serwerem"}

        request_id = str(uuid.uuid4())
        message = {
            "action": action,
            "data": data or {},
            "request_id": request_id
        }

        # Utwórz Future dla odpowiedzi
        future = asyncio.Future()
        self.pending_requests[request_id] = future

        try:
            await self.websocket.send(json.dumps(message))
            # Czekaj na odpowiedź z timeoutem
            response = await asyncio.wait_for(future, timeout=10.0)
            return response
        except asyncio.TimeoutError:
            return {"success": False, "error": "Timeout żądania"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            self.pending_requests.pop(request_id, None)

    # ============ METODY POMOCNICZE ============

    async def login(self, username: str, password: str) -> dict:
        """Loguje użytkownika."""
        return await self.request("login", {"username": username, "password": password})

    async def register(self, username: str, password: str) -> dict:
        """Rejestruje nowego użytkownika."""
        return await self.request("register", {"username": username, "password": password})

    async def get_rooms(self) -> dict:
        """Pobiera listę sal."""
        return await self.request("get_rooms")

    async def add_room(self, name: str, capacity: int, description: str = "") -> dict:
        """Dodaje nową salę (admin)."""
        return await self.request("add_room", {
            "name": name, "capacity": capacity, "description": description
        })

    async def delete_room(self, room_id: int) -> dict:
        """Usuwa salę (admin)."""
        return await self.request("delete_room", {"room_id": room_id})

    async def get_reservations_for_date(self, date: str, room_id: int = None) -> dict:
        """Pobiera rezerwacje dla dnia."""
        return await self.request("get_reservations_for_date", {"date": date, "room_id": room_id})

    async def get_week_reservations(self, start_date: str, end_date: str) -> dict:
        """Pobiera rezerwacje dla tygodnia."""
        return await self.request("get_week_reservations", {
            "start_date": start_date, "end_date": end_date
        })

    async def get_user_reservations(self, user_id: int, include_archived: bool = False) -> dict:
        """Pobiera rezerwacje użytkownika."""
        return await self.request("get_user_reservations", {
            "user_id": user_id, "include_archived": include_archived
        })

    async def get_all_reservations(self, include_archived: bool = False) -> dict:
        """Pobiera wszystkie rezerwacje (admin)."""
        return await self.request("get_all_reservations", {"include_archived": include_archived})

    async def create_reservation(self, room_id: int, user_id: int, date: str,
                                  start_time: str, end_time: str, description: str = "") -> dict:
        """Tworzy nową rezerwację."""
        return await self.request("create_reservation", {
            "room_id": room_id,
            "user_id": user_id,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "description": description
        })

    async def update_reservation(self, reservation_id: int, user_id: int, is_admin: bool,
                                  date: str, start_time: str, end_time: str,
                                  description: str = "") -> dict:
        """Aktualizuje rezerwację."""
        return await self.request("update_reservation", {
            "reservation_id": reservation_id,
            "user_id": user_id,
            "is_admin": is_admin,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "description": description
        })

    async def delete_reservation(self, reservation_id: int, user_id: int, is_admin: bool) -> dict:
        """Usuwa rezerwację."""
        return await self.request("delete_reservation", {
            "reservation_id": reservation_id,
            "user_id": user_id,
            "is_admin": is_admin
        })

    async def get_all_users(self) -> dict:
        """Pobiera wszystkich użytkowników (admin)."""
        return await self.request("get_all_users")

    async def delete_user(self, user_id: int) -> dict:
        """Usuwa użytkownika (admin)."""
        return await self.request("delete_user", {"user_id": user_id})

    async def create_user(self, username: str, password: str, is_admin: bool = False) -> dict:
        """Tworzy użytkownika (admin)."""
        return await self.request("create_user", {
            "username": username,
            "password": password,
            "is_admin": is_admin
        })
