# Script Manager

Aplikacja konsolowa do zarzadzania harmonogramem uruchamiania skryptow Python.

## Najwazniejsze funkcje

- zapisywanie konfiguracji zadan w bazie SQLite,
- harmonogram w oparciu o wyrazenia cron (APScheduler),
- monitorowanie historii uruchomien wraz z kodami powrotu i logami stdout/stderr,
- jednorazowe uruchamianie wybranych zadan,
- logi przechowywane per zadanie w katalogu `logs`.

## Wymagania

- Python 3.10 lub nowszy,
- system Windows Server 2025 (dziala rowniez na innych systemach wspierajacych Python 3.10).

## Instalacja

```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install --upgrade pip
pip install .
```

## Uzycie

Inicjalnie uruchom komende, aby wyswietlic pomoc oraz sciezke katalogu danych:

```powershell
script-manager --help
```

### Dodawanie zadania

```powershell
script-manager add MojeZadanie C:\\sciezka\\do\\skryptu.py --cron "0 8 * * *"
```

- `--cron` przyjmuje standardowe wyrazenie cron (`min godz dzien miesiac dzienTygodnia`).
- `--python` pozwala wskazac inny interpreter Python.
- `--cwd` ustawia katalog roboczy uruchamianego procesu.

### Lista zadan

```powershell
script-manager list
```

### Uruchomienie serwisu harmonogramu

```powershell
script-manager start --refresh 60
```

Serwis na biezaco synchronizuje zmiany w bazie (dodanie/edycja/usuniecie zadan) co `refresh` sekund.
Aby przerwac dzialanie uzyj `Ctrl+C`.

### Historia uruchomien

```powershell
script-manager runs --limit 20
```

Wyniki uruchomien (stdout/stderr) znajduja sie w katalogu `logs/<nazwa_zadania>/` w katalogu danych aplikacji.

### Jednorazowe uruchomienie zadania

```powershell
script-manager run-once MojeZadanie
```

## Testy

```bash
pytest
```

## Licencja

Projekt powstal w ramach zadania demonstracyjnego.
