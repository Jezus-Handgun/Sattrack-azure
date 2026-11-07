# SatTrack

Wewnętrzna aplikacja webowa dla geodetów: pokazuje, ile satelitów GNSS (GPS, Galileo, GLONASS, BeiDou) będzie widocznych w danym miejscu i czasie, oraz mapę satelitów na żywo. Działa w Azure Container Apps z logowaniem przez Microsoft Entra ID.

## Uruchomienie lokalne

Wymagany Python 3.12.

```bash
python -m venv .venv && .venv\Scripts\activate    # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Aplikacja: <http://localhost:8000>, dokumentacja API: <http://localhost:8000/docs>

Testy i lint: `pytest` oraz `ruff check . && ruff format --check .`

## Dokumentacja

Architektura, instrukcja wdrożenia w Azure i log decyzji: katalog [docs/](docs/).
