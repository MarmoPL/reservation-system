"""
Serwer WebSocket dla systemu rezerwacji sal.
Obsługuje wszystkie żądania od klientów i rozgłasza aktualizacje.
"""

import asyncio
import json
import websockets
from datetime import date, timedelta

import database as db

# Zbiór podłączonych klientów do rozgłaszania aktualizacji
connected_clients: set = set()


async def broadcast(message: dict, exclude=None):
    """Rozgłasza wiadomość do wszystkich podłączonych klientów."""
    if connected_clients:
        msg = json.dumps(message)
        for client in connected_clients.copy():
            if client != exclude:
                try:
                    await client.send(msg)
                except websockets.ConnectionClosed:
                    connected_clients.discard(client)


async def handle_message(websocket, message: dict) -> dict:
    """Obsługuje pojedyncze żądanie od klienta."""
    action = message.get("action")
    data = message.get("data", {})

    # ============ AUTORYZACJA ============
    if action == "login":
        user = db.authenticate_user(data["username"], data["password"])
        if user:
            return {"success": True, "user": user}
        return {"success": False, "error": "Nieprawidłowy login lub hasło"}

    if action == "register":
        success, msg = db.register_user(data["username"], data["password"])
        return {"success": success, "message": msg}

    # ============ SALE ============
    if action == "get_rooms":
        rooms = db.get_all_rooms()
        return {"success": True, "rooms": rooms}

    if action == "add_room":
        success, msg = db.add_room(data["name"], data["capacity"], data.get("description", ""))
        if success:
            await broadcast({"type": "rooms_updated"})
        return {"success": success, "message": msg}

    if action == "delete_room":
        success, msg = db.delete_room(data["room_id"])
        if success:
            await broadcast({"type": "rooms_updated"})
        return {"success": success, "message": msg}

    # ============ REZERWACJE ============
    if action == "get_reservations_for_date":
        reservations = db.get_reservations_for_date(
            data["date"],
            data.get("room_id")
        )
        return {"success": True, "reservations": reservations}

    if action == "get_week_reservations":
        reservations = db.get_week_reservations(data["start_date"], data["end_date"])
        return {"success": True, "reservations": reservations}

    if action == "get_user_reservations":
        reservations = db.get_user_reservations(data["user_id"], data.get("include_archived", False))
        return {"success": True, "reservations": reservations}

    if action == "get_all_reservations":
        reservations = db.get_all_reservations(data.get("include_archived", False))
        return {"success": True, "reservations": reservations}

    if action == "create_reservation":
        success, msg = db.create_reservation(
            data["room_id"],
            data["user_id"],
            data["date"],
            data["start_time"],
            data["end_time"],
            data.get("description", "")
        )
        if success:
            # Rozgłoś aktualizację do wszystkich klientów
            await broadcast({
                "type": "reservation_created",
                "date": data["date"],
                "room_id": data["room_id"]
            })
        return {"success": success, "message": msg}

    if action == "update_reservation":
        success, msg = db.update_reservation(
            data["reservation_id"],
            data["user_id"],
            data.get("is_admin", False),
            data["date"],
            data["start_time"],
            data["end_time"],
            data.get("description", "")
        )
        if success:
            await broadcast({"type": "reservation_updated", "date": data["date"]})
        return {"success": success, "message": msg}

    if action == "delete_reservation":
        success, msg = db.delete_reservation(
            data["reservation_id"],
            data["user_id"],
            data.get("is_admin", False)
        )
        if success:
            await broadcast({"type": "reservation_deleted"})
        return {"success": success, "message": msg}

    # ============ ADMIN - UŻYTKOWNICY ============
    if action == "get_all_users":
        users = db.get_all_users()
        return {"success": True, "users": users}

    if action == "delete_user":
        success, msg = db.delete_user(data["user_id"])
        return {"success": success, "message": msg}

    if action == "create_user":
        success, msg = db.register_user(
            data["username"],
            data["password"],
            data.get("is_admin", False)
        )
        return {"success": success, "message": msg}

    return {"success": False, "error": "Nieznana akcja"}


async def handler(websocket):
    """Główny handler połączenia WebSocket."""
    connected_clients.add(websocket)
    print(f"Klient podłączony. Łącznie: {len(connected_clients)}")

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                response = await handle_message(websocket, data)
                response["request_id"] = data.get("request_id")
                await websocket.send(json.dumps(response))
            except json.JSONDecodeError:
                await websocket.send(json.dumps({"success": False, "error": "Nieprawidłowy JSON"}))
            except Exception as e:
                await websocket.send(json.dumps({"success": False, "error": str(e)}))
    finally:
        connected_clients.discard(websocket)
        print(f"Klient rozłączony. Łącznie: {len(connected_clients)}")


async def main():
    """Uruchamia serwer WebSocket."""
    # Inicjalizuj bazę danych
    db.init_database()
    db.archive_past_reservations()

    print("=" * 50)
    print("  System Rezerwacji Sal - Serwer Backend")
    print("=" * 50)
    print("Serwer nasłuchuje na ws://localhost:8765")
    print("Domyślne konto admina: admin / admin123")
    print("-" * 50)

    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()  # Działaj w nieskończoność


if __name__ == "__main__":
    asyncio.run(main())
