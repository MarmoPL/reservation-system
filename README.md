# System Rezerwacji Sal

System do rezerwowania sal konferencyjnych z interfejsem TUI (Terminal User Interface) i komunikacją przez WebSocket.

## Architektura

```
reservation-system/
├── backend/
│   ├── database.py     # Obsługa SQLite (CRUD)
│   └── server.py       # Serwer WebSocket
├── frontend/
│   ├── client.py       # Klient WebSocket
│   └── app.py          # Aplikacja TUI (rich)
└── requirements.txt
```

## Wymagania

- Python 3.10+
- Biblioteki: `websockets`, `rich`

## Instalacja

```bash
pip install -r requirements.txt
```

## Uruchomienie

### 1. Uruchom serwer backend (w osobnym terminalu)

```bash
cd backend
python server.py
```

Serwer uruchomi się na `ws://localhost:8765`.

### 2. Uruchom aplikację frontend (w osobnym terminalu)

```bash
cd frontend
python app.py
```

## Domyślne konto administratora

- Login: `admin`
- Hasło: `admin123`

## Funkcjonalności

### Użytkownik
- Logowanie i rejestracja
- Przeglądanie kalendarza tygodniowego
- Lista sal z pojemnością
- Tworzenie rezerwacji (data, godziny, sala, opis)
- Edycja i usuwanie własnych rezerwacji
- Automatyczna walidacja konfliktów czasowych

### Administrator
- Wszystkie funkcje użytkownika
- Zarządzanie użytkownikami (dodawanie, usuwanie)
- Zarządzanie salami (dodawanie, usuwanie)
- Podgląd i usuwanie wszystkich rezerwacji

## Komunikacja w czasie rzeczywistym

System wykorzystuje WebSocket do natychmiastowej synchronizacji danych między klientami. Gdy jeden użytkownik utworzy rezerwację, wszyscy inni otrzymują powiadomienie o aktualizacji.

## Baza danych

Dane przechowywane są w pliku SQLite `reservation.db` z tabelami:
- `users` - użytkownicy (hasła jako MD5)
- `rooms` - sale konferencyjne
- `reservations` - rezerwacje (bieżące i archiwalne)
