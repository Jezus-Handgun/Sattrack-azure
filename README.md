# SatTrack

Wewnętrzna aplikacja webowa dla geodetów: pokazuje, ile satelitów GNSS (GPS, Galileo, GLONASS, BeiDou) będzie widocznych w danym miejscu i czasie, oraz mapę satelitów na żywo. Działa w Azure Container Apps z logowaniem przez Microsoft Entra ID.

## Uruchomienie lokalne

Wymagany [uv](https://docs.astral.sh/uv/) (sam pobierze Pythona 3.12, jeśli go brakuje).

```bash
git clone <adres-repozytorium> && cd sattrack-azure
uv sync
uv run uvicorn app.main:app --reload
```

Aplikacja: <http://localhost:8000>, dokumentacja API: <http://localhost:8000/docs>

Testy i lint: `uv run pytest` oraz `uv run ruff check . && uv run ruff format --check .`

## Uruchomienie w Dockerze

```bash
docker build -t sattrack .
docker run --rm -p 8000:8000 sattrack
```

Aplikacja działa także bez internetu (`--network none`), korzystając z dołączonego snapshotu danych TLE.

## Dokumentacja

Architektura, instrukcja wdrożenia w Azure i log decyzji: katalog [docs/](docs/).
