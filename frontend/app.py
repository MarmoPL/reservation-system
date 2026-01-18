"""
Główna aplikacja TUI dla systemu rezerwacji sal.
Wykorzystuje bibliotekę 'rich' do ładnego interfejsu terminalowego.
"""

import asyncio
from datetime import date, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.text import Text
from rich import box

from client import ReservationClient

console = Console()


class ReservationApp:
    """Główna klasa aplikacji TUI."""

    def __init__(self):
        self.client = ReservationClient()
        self.user = None  # Aktualnie zalogowany użytkownik
        self.running = True

    async def start(self):
        """Uruchamia aplikację."""
        console.clear()
        self.print_header()

        # Połącz z serwerem
        console.print("\n[yellow]Łączenie z serwerem...[/yellow]")
        if not await self.client.connect():
            console.print("[red]Nie można połączyć z serwerem![/red]")
            console.print("Upewnij się, że serwer jest uruchomiony (python backend/server.py)")
            return

        console.print("[green]Połączono z serwerem![/green]\n")

        # Ustaw callback dla aktualizacji
        self.client.on_update = self.handle_update

        # Ekran logowania
        await self.login_screen()

        # Główna pętla aplikacji
        while self.running and self.user:
            await self.main_menu()

        await self.client.disconnect()
        console.print("\n[yellow]Do widzenia![/yellow]\n")

    def print_header(self):
        """Wyświetla nagłówek aplikacji."""
        header = Text()
        header.append("╔══════════════════════════════════════════════════╗\n", style="cyan")
        header.append("║      ", style="cyan")
        header.append("SYSTEM REZERWACJI SAL", style="bold white")
        header.append("                   ║\n", style="cyan")
        header.append("╚══════════════════════════════════════════════════╝", style="cyan")
        console.print(header)

    async def handle_update(self, data):
        """Obsługuje aktualizacje od serwera (broadcast)."""
        update_type = data.get("type")
        if update_type in ["reservation_created", "reservation_updated", "reservation_deleted"]:
            console.print("\n[yellow]📢 Zaktualizowano rezerwacje![/yellow]")

    async def login_screen(self):
        """Ekran logowania/rejestracji."""
        while not self.user:
            console.print("\n[bold]1.[/bold] Zaloguj się")
            console.print("[bold]2.[/bold] Zarejestruj się")
            console.print("[bold]3.[/bold] Wyjście")

            choice = Prompt.ask("\nWybierz opcję", choices=["1", "2", "3"], default="1")

            if choice == "1":
                await self.login()
            elif choice == "2":
                await self.register()
            else:
                self.running = False
                return

    async def login(self):
        """Logowanie użytkownika."""
        console.print("\n[bold cyan]--- Logowanie ---[/bold cyan]")
        username = Prompt.ask("Login")
        password = Prompt.ask("Hasło", password=True)

        result = await self.client.login(username, password)

        if result["success"]:
            self.user = result["user"]
            console.print(f"\n[green]Witaj, {self.user['username']}![/green]")
            if self.user["is_admin"]:
                console.print("[yellow]Jesteś administratorem[/yellow]")
        else:
            console.print(f"\n[red]{result.get('error', 'Błąd logowania')}[/red]")

    async def register(self):
        """Rejestracja nowego użytkownika."""
        console.print("\n[bold cyan]--- Rejestracja ---[/bold cyan]")
        username = Prompt.ask("Login")
        password = Prompt.ask("Hasło", password=True)
        password2 = Prompt.ask("Powtórz hasło", password=True)

        if password != password2:
            console.print("[red]Hasła nie są identyczne![/red]")
            return

        result = await self.client.register(username, password)

        if result["success"]:
            console.print(f"\n[green]{result['message']}[/green]")
            console.print("Możesz teraz się zalogować.")
        else:
            console.print(f"\n[red]{result.get('message', 'Błąd rejestracji')}[/red]")

    async def main_menu(self):
        """Główne menu aplikacji."""
        console.print("\n" + "=" * 50)
        console.print("[bold cyan]MENU GŁÓWNE[/bold cyan]")
        console.print("=" * 50)

        console.print("\n[bold]1.[/bold] 📅 Widok kalendarza (tydzień)")
        console.print("[bold]2.[/bold] 🏠 Lista sal")
        console.print("[bold]3.[/bold] ➕ Nowa rezerwacja")
        console.print("[bold]4.[/bold] 📋 Moje rezerwacje")

        if self.user["is_admin"]:
            console.print("\n[yellow]--- Panel Admina ---[/yellow]")
            console.print("[bold]5.[/bold] 👥 Zarządzanie użytkownikami")
            console.print("[bold]6.[/bold] 🏢 Zarządzanie salami")
            console.print("[bold]7.[/bold] 📊 Wszystkie rezerwacje")

        console.print("\n[bold]0.[/bold] 🚪 Wyloguj")

        choices = ["0", "1", "2", "3", "4"]
        if self.user["is_admin"]:
            choices.extend(["5", "6", "7"])

        choice = Prompt.ask("\nWybierz opcję", choices=choices, default="1")

        actions = {
            "0": self.logout,
            "1": self.show_calendar,
            "2": self.show_rooms,
            "3": self.create_reservation,
            "4": self.show_my_reservations,
            "5": self.manage_users,
            "6": self.manage_rooms,
            "7": self.show_all_reservations,
        }

        action = actions.get(choice)
        if action:
            await action()

    async def logout(self):
        """Wylogowanie użytkownika."""
        self.user = None
        console.print("\n[yellow]Wylogowano[/yellow]")

    async def show_calendar(self):
        """Wyświetla widok kalendarza tygodniowego."""
        console.print("\n[bold cyan]📅 KALENDARZ TYGODNIOWY[/bold cyan]\n")

        # Pobierz dane
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        result = await self.client.get_week_reservations(
            start_of_week.isoformat(),
            end_of_week.isoformat()
        )

        if not result["success"]:
            console.print(f"[red]Błąd: {result.get('error')}[/red]")
            return

        rooms_result = await self.client.get_rooms()
        rooms = {r["id"]: r["name"] for r in rooms_result.get("rooms", [])}

        # Buduj tabelę kalendarza
        table = Table(title=f"Tydzień: {start_of_week} - {end_of_week}", box=box.ROUNDED)

        # Nagłówki - dni tygodnia
        table.add_column("Sala", style="cyan", width=12)
        day_names = ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Ndz"]
        for i, day_name in enumerate(day_names):
            day = start_of_week + timedelta(days=i)
            header = f"{day_name}\n{day.day:02d}.{day.month:02d}"
            style = "green" if day == today else "white"
            table.add_column(header, style=style, width=14)

        # Grupuj rezerwacje
        reservations = result.get("reservations", [])
        res_by_room_day = {}
        for res in reservations:
            key = (res["room_id"], res["date"])
            if key not in res_by_room_day:
                res_by_room_day[key] = []
            res_by_room_day[key].append(res)

        # Wiersze dla każdej sali
        for room_id, room_name in rooms.items():
            row = [room_name]
            for i in range(7):
                day = start_of_week + timedelta(days=i)
                day_str = day.isoformat()
                day_reservations = res_by_room_day.get((room_id, day_str), [])

                if day_reservations:
                    cell = ""
                    for r in day_reservations[:3]:  # Max 3 rezerwacje w komórce
                        cell += f"[yellow]{r['start_time'][:5]}-{r['end_time'][:5]}[/yellow]\n"
                    if len(day_reservations) > 3:
                        cell += f"[dim]+{len(day_reservations)-3} więcej[/dim]"
                    row.append(cell.strip())
                else:
                    row.append("[dim]wolne[/dim]")
            table.add_row(*row)

        console.print(table)

        # Opcja szczegółów
        if Confirm.ask("\nCzy chcesz zobaczyć szczegóły dla konkretnego dnia?", default=False):
            day_offset = IntPrompt.ask("Który dzień (0=Pon, 6=Ndz)", default=0)
            if 0 <= day_offset <= 6:
                selected_date = start_of_week + timedelta(days=day_offset)
                await self.show_day_details(selected_date.isoformat())

    async def show_day_details(self, date_str: str):
        """Pokazuje szczegóły rezerwacji dla konkretnego dnia."""
        console.print(f"\n[bold]Rezerwacje na dzień {date_str}:[/bold]\n")

        result = await self.client.get_reservations_for_date(date_str)

        if not result["success"]:
            console.print(f"[red]Błąd: {result.get('error')}[/red]")
            return

        reservations = result.get("reservations", [])

        if not reservations:
            console.print("[dim]Brak rezerwacji na ten dzień[/dim]")
            return

        table = Table(box=box.SIMPLE)
        table.add_column("Sala", style="cyan")
        table.add_column("Godziny", style="yellow")
        table.add_column("Użytkownik")
        table.add_column("Opis")

        for r in reservations:
            table.add_row(
                r["room_name"],
                f"{r['start_time'][:5]} - {r['end_time'][:5]}",
                r["username"],
                r.get("description", "")[:30]
            )

        console.print(table)

    async def show_rooms(self):
        """Wyświetla listę sal."""
        console.print("\n[bold cyan]🏠 LISTA SAL[/bold cyan]\n")

        result = await self.client.get_rooms()

        if not result["success"]:
            console.print(f"[red]Błąd: {result.get('error')}[/red]")
            return

        rooms = result.get("rooms", [])

        if not rooms:
            console.print("[dim]Brak sal w systemie[/dim]")
            return

        table = Table(box=box.ROUNDED)
        table.add_column("ID", style="dim")
        table.add_column("Nazwa", style="cyan")
        table.add_column("Pojemność", justify="right")
        table.add_column("Opis")

        for room in rooms:
            table.add_row(
                str(room["id"]),
                room["name"],
                str(room["capacity"]),
                room.get("description", "")
            )

        console.print(table)

    async def create_reservation(self):
        """Tworzy nową rezerwację."""
        console.print("\n[bold cyan]➕ NOWA REZERWACJA[/bold cyan]\n")

        # Pobierz sale
        rooms_result = await self.client.get_rooms()
        rooms = rooms_result.get("rooms", [])

        if not rooms:
            console.print("[red]Brak sal w systemie![/red]")
            return

        # Wyświetl sale
        console.print("[bold]Dostępne sale:[/bold]")
        for room in rooms:
            console.print(f"  {room['id']}. {room['name']} (pojemność: {room['capacity']})")

        # Wybierz salę
        room_ids = [str(r["id"]) for r in rooms]
        room_id = IntPrompt.ask("\nID sali", default=int(room_ids[0]))

        if str(room_id) not in room_ids:
            console.print("[red]Nieprawidłowe ID sali![/red]")
            return

        # Data
        today = date.today().isoformat()
        date_str = Prompt.ask("Data (RRRR-MM-DD)", default=today)

        # Godziny
        start_time = Prompt.ask("Godzina rozpoczęcia (HH:MM)", default="09:00")
        end_time = Prompt.ask("Godzina zakończenia (HH:MM)", default="10:00")

        # Opis
        description = Prompt.ask("Opis (opcjonalny)", default="")

        # Utwórz rezerwację
        result = await self.client.create_reservation(
            room_id=room_id,
            user_id=self.user["id"],
            date=date_str,
            start_time=start_time,
            end_time=end_time,
            description=description
        )

        if result["success"]:
            console.print(f"\n[green]✓ {result['message']}[/green]")
        else:
            console.print(f"\n[red]✗ {result.get('message', 'Błąd')}[/red]")

    async def show_my_reservations(self):
        """Wyświetla rezerwacje użytkownika."""
        console.print("\n[bold cyan]📋 MOJE REZERWACJE[/bold cyan]\n")

        result = await self.client.get_user_reservations(self.user["id"])

        if not result["success"]:
            console.print(f"[red]Błąd: {result.get('error')}[/red]")
            return

        reservations = result.get("reservations", [])

        if not reservations:
            console.print("[dim]Nie masz żadnych rezerwacji[/dim]")
            return

        table = Table(box=box.ROUNDED)
        table.add_column("ID", style="dim")
        table.add_column("Sala", style="cyan")
        table.add_column("Data", style="yellow")
        table.add_column("Godziny")
        table.add_column("Opis")

        for r in reservations:
            table.add_row(
                str(r["id"]),
                r["room_name"],
                r["date"],
                f"{r['start_time'][:5]} - {r['end_time'][:5]}",
                r.get("description", "")[:25]
            )

        console.print(table)

        # Opcje zarządzania
        console.print("\n[bold]1.[/bold] Edytuj rezerwację")
        console.print("[bold]2.[/bold] Usuń rezerwację")
        console.print("[bold]0.[/bold] Powrót")

        choice = Prompt.ask("Wybierz opcję", choices=["0", "1", "2"], default="0")

        if choice == "1":
            await self.edit_reservation(reservations)
        elif choice == "2":
            await self.delete_reservation_prompt(reservations)

    async def edit_reservation(self, reservations: list):
        """Edytuje rezerwację."""
        res_ids = [str(r["id"]) for r in reservations]
        res_id = Prompt.ask("ID rezerwacji do edycji", choices=res_ids)

        res = next(r for r in reservations if str(r["id"]) == res_id)

        console.print(f"\nEdycja rezerwacji #{res_id}:")
        date_str = Prompt.ask("Nowa data", default=res["date"])
        start_time = Prompt.ask("Nowa godzina rozpoczęcia", default=res["start_time"][:5])
        end_time = Prompt.ask("Nowa godzina zakończenia", default=res["end_time"][:5])
        description = Prompt.ask("Nowy opis", default=res.get("description", ""))

        result = await self.client.update_reservation(
            reservation_id=int(res_id),
            user_id=self.user["id"],
            is_admin=self.user["is_admin"],
            date=date_str,
            start_time=start_time,
            end_time=end_time,
            description=description
        )

        if result["success"]:
            console.print(f"[green]✓ {result['message']}[/green]")
        else:
            console.print(f"[red]✗ {result.get('message', 'Błąd')}[/red]")

    async def delete_reservation_prompt(self, reservations: list):
        """Usuwa rezerwację."""
        res_ids = [str(r["id"]) for r in reservations]
        res_id = Prompt.ask("ID rezerwacji do usunięcia", choices=res_ids)

        if Confirm.ask(f"Czy na pewno chcesz usunąć rezerwację #{res_id}?"):
            result = await self.client.delete_reservation(
                reservation_id=int(res_id),
                user_id=self.user["id"],
                is_admin=self.user["is_admin"]
            )

            if result["success"]:
                console.print(f"[green]✓ {result['message']}[/green]")
            else:
                console.print(f"[red]✗ {result.get('message', 'Błąd')}[/red]")

    # ============ PANEL ADMINA ============

    async def manage_users(self):
        """Panel zarządzania użytkownikami (admin)."""
        console.print("\n[bold cyan]👥 ZARZĄDZANIE UŻYTKOWNIKAMI[/bold cyan]\n")

        result = await self.client.get_all_users()
        users = result.get("users", [])

        table = Table(box=box.ROUNDED)
        table.add_column("ID", style="dim")
        table.add_column("Login", style="cyan")
        table.add_column("Admin", justify="center")
        table.add_column("Utworzony")

        for u in users:
            admin_badge = "✓" if u["is_admin"] else ""
            table.add_row(str(u["id"]), u["username"], admin_badge, u["created_at"][:10])

        console.print(table)

        console.print("\n[bold]1.[/bold] Dodaj użytkownika")
        console.print("[bold]2.[/bold] Usuń użytkownika")
        console.print("[bold]0.[/bold] Powrót")

        choice = Prompt.ask("Wybierz opcję", choices=["0", "1", "2"], default="0")

        if choice == "1":
            username = Prompt.ask("Login")
            password = Prompt.ask("Hasło", password=True)
            is_admin = Confirm.ask("Czy admin?", default=False)

            result = await self.client.create_user(username, password, is_admin)
            if result["success"]:
                console.print(f"[green]✓ {result['message']}[/green]")
            else:
                console.print(f"[red]✗ {result.get('message', 'Błąd')}[/red]")

        elif choice == "2":
            user_id = IntPrompt.ask("ID użytkownika do usunięcia")
            if Confirm.ask(f"Usunąć użytkownika #{user_id}?"):
                result = await self.client.delete_user(user_id)
                if result["success"]:
                    console.print(f"[green]✓ {result['message']}[/green]")
                else:
                    console.print(f"[red]✗ {result.get('message', 'Błąd')}[/red]")

    async def manage_rooms(self):
        """Panel zarządzania salami (admin)."""
        console.print("\n[bold cyan]🏢 ZARZĄDZANIE SALAMI[/bold cyan]\n")

        await self.show_rooms()

        console.print("\n[bold]1.[/bold] Dodaj salę")
        console.print("[bold]2.[/bold] Usuń salę")
        console.print("[bold]0.[/bold] Powrót")

        choice = Prompt.ask("Wybierz opcję", choices=["0", "1", "2"], default="0")

        if choice == "1":
            name = Prompt.ask("Nazwa sali")
            capacity = IntPrompt.ask("Pojemność", default=10)
            description = Prompt.ask("Opis (opcjonalny)", default="")

            result = await self.client.add_room(name, capacity, description)
            if result["success"]:
                console.print(f"[green]✓ {result['message']}[/green]")
            else:
                console.print(f"[red]✗ {result.get('message', 'Błąd')}[/red]")

        elif choice == "2":
            room_id = IntPrompt.ask("ID sali do usunięcia")
            if Confirm.ask(f"Usunąć salę #{room_id}? (Spowoduje to usunięcie wszystkich rezerwacji!)"):
                result = await self.client.delete_room(room_id)
                if result["success"]:
                    console.print(f"[green]✓ {result['message']}[/green]")
                else:
                    console.print(f"[red]✗ {result.get('message', 'Błąd')}[/red]")

    async def show_all_reservations(self):
        """Wyświetla wszystkie rezerwacje (admin)."""
        console.print("\n[bold cyan]📊 WSZYSTKIE REZERWACJE[/bold cyan]\n")

        include_archived = Confirm.ask("Pokaż archiwalne?", default=False)
        result = await self.client.get_all_reservations(include_archived)

        if not result["success"]:
            console.print(f"[red]Błąd: {result.get('error')}[/red]")
            return

        reservations = result.get("reservations", [])

        if not reservations:
            console.print("[dim]Brak rezerwacji[/dim]")
            return

        table = Table(box=box.ROUNDED)
        table.add_column("ID", style="dim")
        table.add_column("Sala", style="cyan")
        table.add_column("Użytkownik")
        table.add_column("Data", style="yellow")
        table.add_column("Godziny")
        table.add_column("Opis")

        for r in reservations:
            table.add_row(
                str(r["id"]),
                r["room_name"],
                r["username"],
                r["date"],
                f"{r['start_time'][:5]} - {r['end_time'][:5]}",
                r.get("description", "")[:20]
            )

        console.print(table)

        # Opcja usunięcia
        if Confirm.ask("\nCzy chcesz usunąć jakąś rezerwację?", default=False):
            res_id = IntPrompt.ask("ID rezerwacji do usunięcia")
            if Confirm.ask(f"Usunąć rezerwację #{res_id}?"):
                result = await self.client.delete_reservation(res_id, self.user["id"], True)
                if result["success"]:
                    console.print(f"[green]✓ {result['message']}[/green]")
                else:
                    console.print(f"[red]✗ {result.get('message', 'Błąd')}[/red]")


async def main():
    """Punkt wejścia aplikacji."""
    app = ReservationApp()
    await app.start()


if __name__ == "__main__":
    asyncio.run(main())
