# System Rezerwacji Sal

Profesjonalny system do rezerwowania sal konferencyjnych z interaktywnym interfejsem TUI (Terminal User Interface) i komunikacją przez WebSocket w czasie rzeczywistym.

## Screenshoty

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  System Rezerwacji Sal                                           12:34:56   │
├──────────────────────────────────────────────────────────────────────────────┤
│ Kalendarz │ Moje rezerwacje │ Sale │ Użytkownicy │ Wszystkie rezerwacje │    │
├──────────────────────────────────────────────────────────────────────────────┤
│  < Poprzedni        2025-01-13 — 2025-01-19           Następny >             │
│ ┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐      │
│ │   Pon   │   Wt    │   Śr    │   Czw   │   Pt    │   Sob   │   Ndz   │      │
│ │  13.01  │  14.01  │  15.01  │  16.01  │  17.01  │  18.01  │  19.01  │      │
│ ├─────────┼─────────┼─────────┼─────────┼─────────┼─────────┼─────────┤      │
│ │09:00-10 │  Brak   │10:00-12 │  Brak   │  Brak   │  Brak   │  Brak   │      │
│ │Sala A   │rezerwac │Sala B   │rezerwac │rezerwac │rezerwac │rezerwac │      │
│ │jan      │   ji    │admin    │   ji    │   ji    │   ji    │   ji    │      │
│ └─────────┴─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘      │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ ^Q Wyjdź │ ^D Tryb ciemny/jasny │ N Nowa rezerwacja │ R Odśwież             │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Architektura

```
reservation-system/
├── backend/
│   ├── database.py     # Obsługa SQLite (CRUD)
│   └── server.py       # Serwer WebSocket
├── frontend/
│   ├── client.py       # Klient WebSocket (async)
│   └── app.py          # Aplikacja TUI (Textual)
└── requirements.txt
```

## Wymagania

- Python 3.10+
- Biblioteki: `websockets`, `rich`, `textual`

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

### Interfejs TUI

- **Pełna obsługa myszy** - klikaj przyciski, wybieraj z list
- **Zakładki** - nawigacja między widokami
- **Modale** - okna dialogowe do tworzenia/edycji
- **Skróty klawiszowe** - szybka nawigacja
- **Tryb ciemny/jasny** - Ctrl+D
- **Powiadomienia** - informacje o akcjach

### Użytkownik

- Logowanie i rejestracja
- Interaktywny kalendarz tygodniowy (strzałki lewo/prawo)
- Lista sal z pojemnością
- Tworzenie rezerwacji przez modal
- Edycja i usuwanie własnych rezerwacji (kliknij w wierszu tabeli)
- Automatyczna walidacja konfliktów czasowych

### Administrator

- Wszystkie funkcje użytkownika
- Zakładka "Użytkownicy" - dodawanie, usuwanie użytkowników
- Zakładka "Zarządzaj salami" - dodawanie, usuwanie sal
- Zakładka "Wszystkie rezerwacje" - podgląd i edycja wszystkich

## Skróty klawiszowe

| Skrót | Akcja |
|-------|-------|
| `Ctrl+Q` | Wyjście z aplikacji |
| `Ctrl+D` | Przełącz tryb ciemny/jasny |
| `N` | Nowa rezerwacja |
| `R` | Odśwież dane |
| `Q` | Wyloguj |
| `←` `→` | Poprzedni/następny tydzień |
| `Tab` | Nawigacja między elementami |
| `Enter` | Wybierz/zatwierdź |
| `Escape` | Anuluj/zamknij modal |

## Komunikacja w czasie rzeczywistym

System wykorzystuje WebSocket do natychmiastowej synchronizacji danych między klientami. Gdy jeden użytkownik utworzy rezerwację, wszyscy inni otrzymują powiadomienie i automatyczne odświeżenie danych.

## Baza danych

Dane przechowywane są w pliku SQLite `reservation.db` z tabelami:
- `users` - użytkownicy (hasła jako MD5)
- `rooms` - sale konferencyjne
- `reservations` - rezerwacje (bieżące i archiwalne)

## Technologie

- **Backend**: Python, SQLite, websockets
- **Frontend**: Python, Textual (TUI framework), Rich
- **Komunikacja**: WebSocket (JSON)
