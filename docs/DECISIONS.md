# Log decyzji

| Data | Decyzja | Uzasadnienie |
|---|---|---|
| 2026-11-07 | Zależności i środowisko zarządzane przez **uv** (`pyproject.toml` + `uv.lock`) | Jedno narzędzie zamiast pip i venv. Plik `uv.lock` gwarantuje identyczne wersje bibliotek lokalnie i w obrazie Dockera. |
| 2026-11-07 | **Snapshot danych TLE w repozytorium** (`data/snapshot/`) jako ostatnie źródło danych | Container Apps skaluje do zera, więc po zimnym starcie pamięć jest pusta. Snapshot pozwala aplikacji zawsze coś pokazać, także bez internetu i przy blokadzie CelesTrak. Testy korzystają tylko ze snapshotu. |
| 2026-11-07 | Pobieranie z CelesTrak **najwyżej raz na 2 h na grupę**, leniwie, bez ponowień | CelesTrak aktualizuje dane co ok. 2 h i zwraca HTTP 403 przy częstszych zapytaniach z tego samego IP. Nieudana próba też czeka pełny TTL. Pobrany plik trafia do katalogu cache, więc restart kontenera nie wymusza ponownego pobrania. |
| 2026-11-07 | **Brak bazy danych** | Dane TLE to kilka małych plików tekstowych odświeżanych co 2 h, a wyniki obliczeń są liczone na żądanie. Baza nie wnosi tu nic poza kosztem i dodatkowym zasobem do zabezpieczenia. |
| 2026-11-07 | Obliczenia orbit **na żądanie, bez cache wyników** | Dzięki wektoryzacji (jedna tablica czasów na satelitę) wykres 24 h dla 144 satelitów GNSS liczy się w ok. 0,05 s, więc cache tylko dodałby złożoności. |
