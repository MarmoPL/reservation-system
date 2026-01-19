"""
Profesjonalna aplikacja TUI dla systemu rezerwacji sal.
Wykorzystuje framework Textual do pełnego interaktywnego interfejsu.
"""

import asyncio
from datetime import date, timedelta
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, Grid, ScrollableContainer
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    Header, Footer, Static, Button, Input, Label,
    DataTable, TabbedContent, TabPane, Select, TextArea
)
from textual.validation import Length
from textual import on
from rich.text import Text

from client import ReservationClient


# ============================================================================
# EKRAN LOGOWANIA
# ============================================================================

class LoginScreen(Screen):
    """Ekran logowania i rejestracji."""

    CSS = """
    LoginScreen {
        align: center middle;
    }

    #login-container {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #login-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        padding: 1;
    }

    .form-label {
        margin-top: 1;
    }

    Input {
        margin-bottom: 1;
    }

    #login-buttons {
        margin-top: 1;
        height: 3;
    }

    #login-buttons Button {
        width: 1fr;
        margin: 0 1;
    }

    #error-label {
        color: $error;
        text-align: center;
        height: 2;
    }

    #register-link {
        text-align: center;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "quit", "Wyjdź"),
    ]

    def __init__(self, client: ReservationClient):
        super().__init__()
        self.client = client
        self.is_register_mode = False

    def compose(self) -> ComposeResult:
        yield Container(
            Static("SYSTEM REZERWACJI SAL", id="login-title"),
            Label("Login:", classes="form-label"),
            Input(placeholder="Wpisz login...", id="username"),
            Label("Hasło:", classes="form-label"),
            Input(placeholder="Wpisz hasło...", password=True, id="password"),
            Container(id="register-fields"),
            Static("", id="error-label"),
            Horizontal(
                Button("Zaloguj", variant="primary", id="login-btn"),
                Button("Rejestracja", variant="default", id="register-btn"),
                id="login-buttons"
            ),
            id="login-container"
        )

    @on(Button.Pressed, "#login-btn")
    async def handle_login(self) -> None:
        username = self.query_one("#username", Input).value
        password = self.query_one("#password", Input).value
        error_label = self.query_one("#error-label", Static)

        if not username or not password:
            error_label.update("Wypełnij wszystkie pola!")
            return

        if self.is_register_mode:
            result = await self.client.register(username, password)
            if result["success"]:
                error_label.update("")
                self.notify("Zarejestrowano! Możesz się zalogować.", severity="information")
                self.is_register_mode = False
                self.query_one("#login-btn", Button).label = "Zaloguj"
                self.query_one("#register-btn", Button).label = "Rejestracja"
            else:
                error_label.update(result.get("message", "Błąd rejestracji"))
        else:
            result = await self.client.login(username, password)
            if result["success"]:
                self.app.user = result["user"]
                self.app.push_screen(MainScreen(self.client))
            else:
                error_label.update(result.get("error", "Błąd logowania"))

    @on(Button.Pressed, "#register-btn")
    def toggle_register_mode(self) -> None:
        self.is_register_mode = not self.is_register_mode
        login_btn = self.query_one("#login-btn", Button)
        register_btn = self.query_one("#register-btn", Button)

        if self.is_register_mode:
            login_btn.label = "Zarejestruj"
            register_btn.label = "Powrót"
        else:
            login_btn.label = "Zaloguj"
            register_btn.label = "Rejestracja"

    @on(Input.Submitted)
    async def on_submit(self) -> None:
        await self.handle_login()


# ============================================================================
# MODAL NOWEJ REZERWACJI
# ============================================================================

class NewReservationModal(ModalScreen):
    """Modal do tworzenia nowej rezerwacji."""

    CSS = """
    NewReservationModal {
        align: center middle;
    }

    #modal-container {
        width: 70;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #modal-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        padding-bottom: 1;
        border-bottom: solid $primary;
        margin-bottom: 1;
    }

    .modal-row {
        height: 3;
        margin-bottom: 1;
    }

    .modal-row Label {
        width: 15;
        padding-top: 1;
    }

    .modal-row Input, .modal-row Select {
        width: 1fr;
    }

    #modal-buttons {
        margin-top: 1;
        height: 3;
    }

    #modal-buttons Button {
        width: 1fr;
        margin: 0 1;
    }

    #description-area {
        height: 4;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Anuluj"),
    ]

    def __init__(self, client: ReservationClient, user: dict, rooms: list):
        super().__init__()
        self.client = client
        self.user = user
        self.rooms = rooms

    def compose(self) -> ComposeResult:
        room_options = [(r["name"], r["id"]) for r in self.rooms]
        today = date.today().isoformat()

        yield Container(
            Static("NOWA REZERWACJA", id="modal-title"),
            Horizontal(
                Label("Sala:"),
                Select(room_options, id="room-select", value=self.rooms[0]["id"] if self.rooms else None),
                classes="modal-row"
            ),
            Horizontal(
                Label("Data:"),
                Input(value=today, placeholder="RRRR-MM-DD", id="date-input"),
                classes="modal-row"
            ),
            Horizontal(
                Label("Od godziny:"),
                Input(value="09:00", placeholder="HH:MM", id="start-input"),
                classes="modal-row"
            ),
            Horizontal(
                Label("Do godziny:"),
                Input(value="10:00", placeholder="HH:MM", id="end-input"),
                classes="modal-row"
            ),
            Horizontal(
                Label("Opis:"),
                Input(placeholder="Opcjonalny opis...", id="desc-input"),
                classes="modal-row"
            ),
            Horizontal(
                Button("Utwórz", variant="success", id="create-btn"),
                Button("Anuluj", variant="error", id="cancel-btn"),
                id="modal-buttons"
            ),
            id="modal-container"
        )

    @on(Button.Pressed, "#create-btn")
    async def create_reservation(self) -> None:
        room_id = self.query_one("#room-select", Select).value
        date_str = self.query_one("#date-input", Input).value
        start_time = self.query_one("#start-input", Input).value
        end_time = self.query_one("#end-input", Input).value
        description = self.query_one("#desc-input", Input).value

        result = await self.client.create_reservation(
            room_id=room_id,
            user_id=self.user["id"],
            date=date_str,
            start_time=start_time,
            end_time=end_time,
            description=description
        )

        if result["success"]:
            self.dismiss(True)
        else:
            self.notify(result.get("message", "Błąd"), severity="error")

    @on(Button.Pressed, "#cancel-btn")
    def action_cancel(self) -> None:
        self.dismiss(False)


# ============================================================================
# MODAL EDYCJI REZERWACJI
# ============================================================================

class EditReservationModal(ModalScreen):
    """Modal do edycji rezerwacji."""

    CSS = """
    EditReservationModal {
        align: center middle;
    }

    #edit-container {
        width: 70;
        height: auto;
        border: thick $warning;
        background: $surface;
        padding: 1 2;
    }

    #edit-title {
        text-align: center;
        text-style: bold;
        color: $warning;
        padding-bottom: 1;
        border-bottom: solid $warning;
        margin-bottom: 1;
    }

    .edit-row {
        height: 3;
        margin-bottom: 1;
    }

    .edit-row Label {
        width: 15;
        padding-top: 1;
    }

    .edit-row Input {
        width: 1fr;
    }

    #edit-buttons {
        margin-top: 1;
        height: 3;
    }

    #edit-buttons Button {
        width: 1fr;
        margin: 0 1;
    }
    """

    BINDINGS = [Binding("escape", "cancel", "Anuluj")]

    def __init__(self, client: ReservationClient, user: dict, reservation: dict):
        super().__init__()
        self.client = client
        self.user = user
        self.reservation = reservation

    def compose(self) -> ComposeResult:
        r = self.reservation
        yield Container(
            Static(f"EDYCJA REZERWACJI #{r['id']}", id="edit-title"),
            Horizontal(
                Label("Data:"),
                Input(value=r["date"], id="date-input"),
                classes="edit-row"
            ),
            Horizontal(
                Label("Od godziny:"),
                Input(value=r["start_time"][:5], id="start-input"),
                classes="edit-row"
            ),
            Horizontal(
                Label("Do godziny:"),
                Input(value=r["end_time"][:5], id="end-input"),
                classes="edit-row"
            ),
            Horizontal(
                Label("Opis:"),
                Input(value=r.get("description", ""), id="desc-input"),
                classes="edit-row"
            ),
            Horizontal(
                Button("Zapisz", variant="warning", id="save-btn"),
                Button("Usuń", variant="error", id="delete-btn"),
                Button("Anuluj", variant="default", id="cancel-btn"),
                id="edit-buttons"
            ),
            id="edit-container"
        )

    @on(Button.Pressed, "#save-btn")
    async def save_reservation(self) -> None:
        result = await self.client.update_reservation(
            reservation_id=self.reservation["id"],
            user_id=self.user["id"],
            is_admin=self.user.get("is_admin", False),
            date=self.query_one("#date-input", Input).value,
            start_time=self.query_one("#start-input", Input).value,
            end_time=self.query_one("#end-input", Input).value,
            description=self.query_one("#desc-input", Input).value
        )

        if result["success"]:
            self.dismiss("saved")
        else:
            self.notify(result.get("message", "Błąd"), severity="error")

    @on(Button.Pressed, "#delete-btn")
    async def delete_reservation(self) -> None:
        result = await self.client.delete_reservation(
            reservation_id=self.reservation["id"],
            user_id=self.user["id"],
            is_admin=self.user.get("is_admin", False)
        )

        if result["success"]:
            self.dismiss("deleted")
        else:
            self.notify(result.get("message", "Błąd"), severity="error")

    @on(Button.Pressed, "#cancel-btn")
    def action_cancel(self) -> None:
        self.dismiss(None)


# ============================================================================
# MODAL DODAWANIA SALI (ADMIN)
# ============================================================================

class AddRoomModal(ModalScreen):
    """Modal do dodawania nowej sali."""

    CSS = """
    AddRoomModal {
        align: center middle;
    }

    #room-container {
        width: 60;
        height: auto;
        border: thick $success;
        background: $surface;
        padding: 1 2;
    }

    #room-title {
        text-align: center;
        text-style: bold;
        color: $success;
        padding-bottom: 1;
        margin-bottom: 1;
    }

    .room-row {
        height: 3;
        margin-bottom: 1;
    }

    .room-row Label {
        width: 15;
        padding-top: 1;
    }

    .room-row Input {
        width: 1fr;
    }

    #room-buttons {
        margin-top: 1;
        height: 3;
    }

    #room-buttons Button {
        width: 1fr;
        margin: 0 1;
    }
    """

    BINDINGS = [Binding("escape", "cancel", "Anuluj")]

    def __init__(self, client: ReservationClient):
        super().__init__()
        self.client = client

    def compose(self) -> ComposeResult:
        yield Container(
            Static("NOWA SALA", id="room-title"),
            Horizontal(
                Label("Nazwa:"),
                Input(placeholder="Nazwa sali", id="name-input"),
                classes="room-row"
            ),
            Horizontal(
                Label("Pojemność:"),
                Input(value="10", placeholder="Liczba osób", id="capacity-input"),
                classes="room-row"
            ),
            Horizontal(
                Label("Opis:"),
                Input(placeholder="Opcjonalny opis", id="desc-input"),
                classes="room-row"
            ),
            Horizontal(
                Button("Dodaj", variant="success", id="add-btn"),
                Button("Anuluj", variant="default", id="cancel-btn"),
                id="room-buttons"
            ),
            id="room-container"
        )

    @on(Button.Pressed, "#add-btn")
    async def add_room(self) -> None:
        name = self.query_one("#name-input", Input).value
        capacity = self.query_one("#capacity-input", Input).value
        description = self.query_one("#desc-input", Input).value

        if not name:
            self.notify("Podaj nazwę sali!", severity="error")
            return

        result = await self.client.add_room(name, int(capacity), description)

        if result["success"]:
            self.dismiss(True)
        else:
            self.notify(result.get("message", "Błąd"), severity="error")

    @on(Button.Pressed, "#cancel-btn")
    def action_cancel(self) -> None:
        self.dismiss(False)


# ============================================================================
# MODAL DODAWANIA UŻYTKOWNIKA (ADMIN)
# ============================================================================

class AddUserModal(ModalScreen):
    """Modal do dodawania użytkownika."""

    CSS = """
    AddUserModal {
        align: center middle;
    }

    #user-container {
        width: 60;
        height: auto;
        border: thick $success;
        background: $surface;
        padding: 1 2;
    }

    #user-title {
        text-align: center;
        text-style: bold;
        color: $success;
        padding-bottom: 1;
        margin-bottom: 1;
    }

    .user-row {
        height: 3;
        margin-bottom: 1;
    }

    .user-row Label {
        width: 15;
        padding-top: 1;
    }

    .user-row Input, .user-row Select {
        width: 1fr;
    }

    #user-buttons {
        margin-top: 1;
        height: 3;
    }

    #user-buttons Button {
        width: 1fr;
        margin: 0 1;
    }
    """

    BINDINGS = [Binding("escape", "cancel", "Anuluj")]

    def __init__(self, client: ReservationClient):
        super().__init__()
        self.client = client

    def compose(self) -> ComposeResult:
        yield Container(
            Static("NOWY UŻYTKOWNIK", id="user-title"),
            Horizontal(
                Label("Login:"),
                Input(placeholder="Login", id="login-input"),
                classes="user-row"
            ),
            Horizontal(
                Label("Hasło:"),
                Input(placeholder="Hasło", password=True, id="password-input"),
                classes="user-row"
            ),
            Horizontal(
                Label("Typ:"),
                Select([("Użytkownik", False), ("Administrator", True)], id="admin-select", value=False),
                classes="user-row"
            ),
            Horizontal(
                Button("Dodaj", variant="success", id="add-btn"),
                Button("Anuluj", variant="default", id="cancel-btn"),
                id="user-buttons"
            ),
            id="user-container"
        )

    @on(Button.Pressed, "#add-btn")
    async def add_user(self) -> None:
        username = self.query_one("#login-input", Input).value
        password = self.query_one("#password-input", Input).value
        is_admin = self.query_one("#admin-select", Select).value

        if not username or not password:
            self.notify("Wypełnij wszystkie pola!", severity="error")
            return

        result = await self.client.create_user(username, password, is_admin)

        if result["success"]:
            self.dismiss(True)
        else:
            self.notify(result.get("message", "Błąd"), severity="error")

    @on(Button.Pressed, "#cancel-btn")
    def action_cancel(self) -> None:
        self.dismiss(False)


# ============================================================================
# GŁÓWNY EKRAN (DASHBOARD)
# ============================================================================

class MainScreen(Screen):
    """Główny ekran aplikacji z zakładkami."""

    CSS = """
    MainScreen {
        layout: vertical;
    }

    #main-header {
        dock: top;
        height: 3;
        background: $primary;
        color: $text;
        padding: 1;
    }

    #user-info {
        dock: right;
        width: auto;
        padding-right: 2;
    }

    #welcome-text {
        text-style: bold;
    }

    TabbedContent {
        height: 1fr;
    }

    /* Kalendarz */
    #calendar-container {
        padding: 1;
    }

    #calendar-header {
        height: 3;
        margin-bottom: 1;
    }

    #calendar-header Button {
        width: 15;
    }

    #week-label {
        width: 1fr;
        text-align: center;
        padding-top: 1;
        text-style: bold;
    }

    #calendar-grid {
        height: 1fr;
    }

    .day-column {
        width: 1fr;
        border: solid $primary-darken-2;
        margin: 0 1;
    }

    .day-header {
        height: 3;
        background: $primary;
        text-align: center;
        padding: 1;
        text-style: bold;
    }

    .day-header.today {
        background: $success;
    }

    .reservation-item {
        height: auto;
        padding: 1;
        margin: 1;
        background: $primary-darken-1;
        border: solid $primary;
    }

    .reservation-item:hover {
        background: $primary;
    }

    .empty-day {
        color: $text-muted;
        text-align: center;
        padding: 1;
    }

    /* Tabele */
    DataTable {
        height: 1fr;
    }

    /* Panel boczny */
    #action-panel {
        dock: right;
        width: 25;
        background: $surface;
        border-left: solid $primary;
        padding: 1;
    }

    #action-panel Button {
        width: 100%;
        margin-bottom: 1;
    }

    #action-title {
        text-style: bold;
        text-align: center;
        padding-bottom: 1;
        border-bottom: solid $primary;
        margin-bottom: 1;
    }

    /* Moje rezerwacje */
    #my-reservations-container {
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("n", "new_reservation", "Nowa rezerwacja"),
        Binding("r", "refresh", "Odśwież"),
        Binding("q", "logout", "Wyloguj"),
        Binding("left", "prev_week", "Poprzedni tydzień"),
        Binding("right", "next_week", "Następny tydzień"),
    ]

    def __init__(self, client: ReservationClient):
        super().__init__()
        self.client = client
        self.rooms = []
        self.current_week_start = date.today() - timedelta(days=date.today().weekday())
        self.my_reservations = []
        self.all_reservations = []

    def compose(self) -> ComposeResult:
        user = self.app.user
        admin_badge = " [ADMIN]" if user["is_admin"] else ""

        yield Header(show_clock=True)

        with TabbedContent():
            with TabPane("Kalendarz", id="tab-calendar"):
                yield Horizontal(
                    Button("< Poprzedni", id="prev-week-btn", variant="default"),
                    Static("Tydzień", id="week-label"),
                    Button("Następny >", id="next-week-btn", variant="default"),
                    id="calendar-header"
                )
                yield ScrollableContainer(id="calendar-grid")
                yield Vertical(
                    Static("AKCJE", id="action-title"),
                    Button("+ Nowa rezerwacja", variant="success", id="new-reservation-btn"),
                    Button("Odśwież", variant="primary", id="refresh-btn"),
                    Button("Wyloguj", variant="error", id="logout-btn"),
                    id="action-panel"
                )

            with TabPane("Moje rezerwacje", id="tab-my"):
                yield DataTable(id="my-reservations-table")

            with TabPane("Sale", id="tab-rooms"):
                yield DataTable(id="rooms-table")

            if user["is_admin"]:
                with TabPane("Użytkownicy", id="tab-users"):
                    yield Horizontal(
                        Button("+ Dodaj użytkownika", variant="success", id="add-user-btn"),
                        Button("Usuń zaznaczonego", variant="error", id="delete-user-btn"),
                        id="users-header"
                    )
                    yield DataTable(id="users-table")

                with TabPane("Wszystkie rezerwacje", id="tab-all"):
                    yield DataTable(id="all-reservations-table")

                with TabPane("Zarządzaj salami", id="tab-manage-rooms"):
                    yield Horizontal(
                        Button("+ Dodaj salę", variant="success", id="add-room-btn"),
                        Button("Usuń zaznaczoną", variant="error", id="delete-room-btn"),
                        id="rooms-header"
                    )
                    yield DataTable(id="manage-rooms-table")

        yield Footer()

    async def on_mount(self) -> None:
        """Ładuje dane przy montowaniu ekranu."""
        self.client.on_update = self.handle_server_update
        await self.refresh_all_data()

    async def handle_server_update(self, data: dict) -> None:
        """Obsługuje aktualizacje od serwera."""
        self.notify("Dane zaktualizowane!", severity="information")
        await self.refresh_all_data()

    async def refresh_all_data(self) -> None:
        """Odświeża wszystkie dane."""
        # Pobierz sale
        rooms_result = await self.client.get_rooms()
        self.rooms = rooms_result.get("rooms", [])

        # Zaktualizuj widoki
        await self.update_calendar()
        await self.update_rooms_table()
        await self.update_my_reservations()

        if self.app.user["is_admin"]:
            await self.update_users_table()
            await self.update_all_reservations()
            await self.update_manage_rooms_table()

    async def update_calendar(self) -> None:
        """Aktualizuje widok kalendarza."""
        week_end = self.current_week_start + timedelta(days=6)

        # Aktualizuj label
        week_label = self.query_one("#week-label", Static)
        week_label.update(f"{self.current_week_start} — {week_end}")

        # Pobierz rezerwacje
        result = await self.client.get_week_reservations(
            self.current_week_start.isoformat(),
            week_end.isoformat()
        )
        reservations = result.get("reservations", [])

        # Grupuj rezerwacje po dniu
        by_date = {}
        for r in reservations:
            if r["date"] not in by_date:
                by_date[r["date"]] = []
            by_date[r["date"]].append(r)

        # Buduj siatkę kalendarza
        grid = self.query_one("#calendar-grid", ScrollableContainer)
        await grid.remove_children()

        day_names = ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Ndz"]
        today = date.today()

        columns = []
        for i in range(7):
            day = self.current_week_start + timedelta(days=i)
            day_str = day.isoformat()
            day_reservations = by_date.get(day_str, [])

            # Nagłówek dnia
            header_class = "day-header today" if day == today else "day-header"
            header_text = f"{day_names[i]}\n{day.day:02d}.{day.month:02d}"

            column_content = [Static(header_text, classes=header_class)]

            if day_reservations:
                for r in day_reservations:
                    time_str = f"{r['start_time'][:5]}-{r['end_time'][:5]}"
                    res_text = f"{time_str}\n{r['room_name']}\n{r['username']}"
                    column_content.append(Static(res_text, classes="reservation-item"))
            else:
                column_content.append(Static("Brak rezerwacji", classes="empty-day"))

            columns.append(Vertical(*column_content, classes="day-column"))

        await grid.mount(Horizontal(*columns))

    async def update_rooms_table(self) -> None:
        """Aktualizuje tabelę sal."""
        table = self.query_one("#rooms-table", DataTable)
        table.clear(columns=True)

        table.add_column("ID", key="id")
        table.add_column("Nazwa", key="name")
        table.add_column("Pojemność", key="capacity")
        table.add_column("Opis", key="description")

        for room in self.rooms:
            table.add_row(
                str(room["id"]),
                room["name"],
                str(room["capacity"]),
                room.get("description", "")
            )

    async def update_my_reservations(self) -> None:
        """Aktualizuje tabelę moich rezerwacji."""
        result = await self.client.get_user_reservations(self.app.user["id"])
        self.my_reservations = result.get("reservations", [])

        table = self.query_one("#my-reservations-table", DataTable)
        table.clear(columns=True)

        table.add_column("ID", key="id")
        table.add_column("Sala", key="room")
        table.add_column("Data", key="date")
        table.add_column("Godziny", key="time")
        table.add_column("Opis", key="description")

        for r in self.my_reservations:
            table.add_row(
                str(r["id"]),
                r["room_name"],
                r["date"],
                f"{r['start_time'][:5]} - {r['end_time'][:5]}",
                r.get("description", "")[:30],
                key=str(r["id"])
            )

    async def update_users_table(self) -> None:
        """Aktualizuje tabelę użytkowników (admin)."""
        result = await self.client.get_all_users()
        users = result.get("users", [])

        table = self.query_one("#users-table", DataTable)
        table.clear(columns=True)

        table.add_column("ID", key="id")
        table.add_column("Login", key="username")
        table.add_column("Admin", key="admin")
        table.add_column("Utworzony", key="created")

        for u in users:
            table.add_row(
                str(u["id"]),
                u["username"],
                "Tak" if u["is_admin"] else "Nie",
                u["created_at"][:10],
                key=str(u["id"])
            )

    async def update_all_reservations(self) -> None:
        """Aktualizuje tabelę wszystkich rezerwacji (admin)."""
        result = await self.client.get_all_reservations()
        self.all_reservations = result.get("reservations", [])

        table = self.query_one("#all-reservations-table", DataTable)
        table.clear(columns=True)

        table.add_column("ID", key="id")
        table.add_column("Sala", key="room")
        table.add_column("Użytkownik", key="user")
        table.add_column("Data", key="date")
        table.add_column("Godziny", key="time")

        for r in self.all_reservations:
            table.add_row(
                str(r["id"]),
                r["room_name"],
                r["username"],
                r["date"],
                f"{r['start_time'][:5]} - {r['end_time'][:5]}",
                key=str(r["id"])
            )

    async def update_manage_rooms_table(self) -> None:
        """Aktualizuje tabelę zarządzania salami (admin)."""
        table = self.query_one("#manage-rooms-table", DataTable)
        table.clear(columns=True)

        table.add_column("ID", key="id")
        table.add_column("Nazwa", key="name")
        table.add_column("Pojemność", key="capacity")
        table.add_column("Opis", key="description")

        for room in self.rooms:
            table.add_row(
                str(room["id"]),
                room["name"],
                str(room["capacity"]),
                room.get("description", ""),
                key=str(room["id"])
            )

    # ============ OBSŁUGA PRZYCISKÓW ============

    @on(Button.Pressed, "#prev-week-btn")
    async def action_prev_week(self) -> None:
        self.current_week_start -= timedelta(days=7)
        await self.update_calendar()

    @on(Button.Pressed, "#next-week-btn")
    async def action_next_week(self) -> None:
        self.current_week_start += timedelta(days=7)
        await self.update_calendar()

    @on(Button.Pressed, "#new-reservation-btn")
    async def action_new_reservation(self) -> None:
        if not self.rooms:
            self.notify("Brak sal w systemie!", severity="error")
            return

        def handle_result(result: bool) -> None:
            if result:
                self.notify("Rezerwacja utworzona!", severity="information")
                asyncio.create_task(self.refresh_all_data())

        modal = NewReservationModal(self.client, self.app.user, self.rooms)
        self.app.push_screen(modal, handle_result)

    @on(Button.Pressed, "#refresh-btn")
    async def action_refresh(self) -> None:
        await self.refresh_all_data()
        self.notify("Dane odświeżone")

    @on(Button.Pressed, "#logout-btn")
    async def action_logout(self) -> None:
        self.app.user = None
        self.app.pop_screen()

    @on(Button.Pressed, "#add-room-btn")
    async def add_room(self) -> None:
        def handle_result(result: bool) -> None:
            if result:
                self.notify("Sala dodana!", severity="information")
                asyncio.create_task(self.refresh_all_data())

        self.app.push_screen(AddRoomModal(self.client), handle_result)

    @on(Button.Pressed, "#delete-room-btn")
    async def delete_room(self) -> None:
        table = self.query_one("#manage-rooms-table", DataTable)
        if table.cursor_row is not None and self.rooms:
            room_id = self.rooms[table.cursor_row]["id"]
            result = await self.client.delete_room(room_id)
            if result["success"]:
                self.notify("Sala usunięta!", severity="warning")
                await self.refresh_all_data()
            else:
                self.notify(result.get("message", "Błąd"), severity="error")

    @on(Button.Pressed, "#add-user-btn")
    async def add_user(self) -> None:
        def handle_result(result: bool) -> None:
            if result:
                self.notify("Użytkownik dodany!", severity="information")
                asyncio.create_task(self.refresh_all_data())

        self.app.push_screen(AddUserModal(self.client), handle_result)

    @on(Button.Pressed, "#delete-user-btn")
    async def delete_user(self) -> None:
        table = self.query_one("#users-table", DataTable)
        if table.cursor_row is not None:
            row_key = table.get_row_at(table.cursor_row)
            if row_key:
                user_id = int(row_key[0])
                result = await self.client.delete_user(user_id)
                if result["success"]:
                    self.notify("Użytkownik usunięty!", severity="warning")
                    await self.refresh_all_data()
                else:
                    self.notify(result.get("message", "Błąd"), severity="error")

    @on(DataTable.RowSelected, "#my-reservations-table")
    async def on_my_reservation_selected(self, event: DataTable.RowSelected) -> None:
        """Otwiera modal edycji po wybraniu rezerwacji."""
        if event.row_key:
            res_id = int(str(event.row_key.value))
            reservation = next((r for r in self.my_reservations if r["id"] == res_id), None)
            if reservation:
                def handle_result(result) -> None:
                    if result:
                        self.notify(f"Rezerwacja {result}!", severity="information")
                        asyncio.create_task(self.refresh_all_data())

                modal = EditReservationModal(self.client, self.app.user, reservation)
                self.app.push_screen(modal, handle_result)

    @on(DataTable.RowSelected, "#all-reservations-table")
    async def on_all_reservation_selected(self, event: DataTable.RowSelected) -> None:
        """Admin może edytować dowolną rezerwację."""
        if event.row_key:
            res_id = int(str(event.row_key.value))
            reservation = next((r for r in self.all_reservations if r["id"] == res_id), None)
            if reservation:
                def handle_result(result) -> None:
                    if result:
                        self.notify(f"Rezerwacja {result}!", severity="information")
                        asyncio.create_task(self.refresh_all_data())

                modal = EditReservationModal(self.client, self.app.user, reservation)
                self.app.push_screen(modal, handle_result)


# ============================================================================
# GŁÓWNA APLIKACJA
# ============================================================================

class ReservationApp(App):
    """Główna aplikacja systemu rezerwacji."""

    TITLE = "System Rezerwacji Sal"
    CSS = """
    Screen {
        background: $background;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Wyjdź", show=True),
        Binding("ctrl+d", "toggle_dark", "Tryb ciemny/jasny"),
    ]

    def __init__(self):
        super().__init__()
        self.client = ReservationClient()
        self.user = None

    async def on_mount(self) -> None:
        """Uruchamia połączenie z serwerem."""
        if not await self.client.connect():
            self.notify("Nie można połączyć z serwerem!", severity="error", timeout=5)
            self.notify("Uruchom: python backend/server.py", severity="warning", timeout=5)
        else:
            self.push_screen(LoginScreen(self.client))

    def action_toggle_dark(self) -> None:
        """Przełącza tryb ciemny/jasny."""
        self.dark = not self.dark


async def main():
    app = ReservationApp()
    await app.run_async()


if __name__ == "__main__":
    asyncio.run(main())
