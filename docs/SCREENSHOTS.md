# Checklista zrzutów ekranu

Zrzuty do prezentacji i sprawozdania. Kolumna „Krok” odsyła do [DEPLOYMENT.md](DEPLOYMENT.md). Proponowana nazwa pliku: `NN-opis.png`, np. `01-grupa-zasobow.png`.

**Wskazówki:**
- portal po polsku lub angielsku, ale konsekwentnie jeden język,
- przed zrzutem ukryj ID subskrypcji i adresy e-mail, jeśli nie chcesz ich pokazywać,
- zrzuty aplikacji rób po rozgrzaniu (po zimnym starcie) i w pełnym oknie przeglądarki.

| Nr | Co ma być widać | Krok | Część prezentacji |
|---|---|---|---|
| ☐ 1 | Formularz **Create a resource group** z nazwą `rg-sattrack` i regionem albo grupa na liście po utworzeniu | 1 | Etapy instalacji |
| ☐ 2 | Formularz tworzenia **Container Registry**: nazwa `acrsattrack…`, Pricing plan **Basic** | 2 | Etapy instalacji |
| ☐ 3 | Rejestr → **Repositories → sattrack** z tagiem `v1` (opcjonalnie obok terminal z `docker push`) | 3 | Etapy instalacji |
| ☐ 4a | Kreator Container App, zakładka **Basics**: nazwa `ca-sattrack` i środowisko `cae-sattrack` | 5 | Etapy instalacji |
| ☐ 4b | Zakładka **Container**: obraz z ACR, **Managed identity**, 0.25 CPU / 0.5 Gi, zmienna `ALLOWED_USERS` | 5 | Etapy instalacji |
| ☐ 4c | Zakładka **Ingress**: Enabled, ruch z dowolnego miejsca, Target port **8000** | 5 | Etapy instalacji |
| ☐ 5 | **Overview** działającej aplikacji: Status *Running*, widoczny **Application Url** | 5 | Interfejs konfiguracyjny |
| ☐ 6 | **Authentication**: dostawca **GitHub** dodany, **Require authentication**, przekierowanie 302 | 6b | Interfejs konfiguracyjny |
| ☐ 7 | **Scale**: Min replicas **0**, Max replicas **2** | 5 | Interfejs konfiguracyjny |
| ☐ 8 | **Logs**: zapytanie KQL na `ContainerAppConsoleLogs_CL` z wynikami (widoczne „SatTrack starting”, „TLE …”, „CelesTrak fetch OK”) | 7 | Interfejs konfiguracyjny |
| ☐ 9 | Okno logowania **GitHuba** po otwarciu adresu aplikacji w oknie prywatnym | 6c | Widok użytkownika |
| ☐ 10 | **Mapa na żywo** z kliknięciem ISS: panel szczegółów i ślad orbity, w pasku górnym login z GitHuba i „Wyloguj” | – | Widok użytkownika |
| ☐ 11 | **Skyplot, tabela widocznych satelitów i wykres 24 h** dla Chorzowa (przewiń stronę albo zrób dwa zrzuty) | – | Widok użytkownika |
| ☐ 12 | **Dokumentacja API** `/docs` (Swagger UI), najlepiej z rozwiniętym `GET /api/visible` i wykonanym zapytaniem (*Try it out*) | – | Widok użytkownika / IT |
| ☐ 13 | *(opcjonalnie)* **Cost Management → Cost analysis** dla `rg-sattrack` | Koszty | Podsumowanie |
| ☐ 14 | *(opcjonalnie)* **Health probes**: sondy Liveness i Readiness na `/healthz` | 5 | Interfejs konfiguracyjny |
| ☐ 15 | Aplikacja **OAuth na GitHubie** (Settings → Developer settings → OAuth Apps): nazwa, Homepage URL, Authorization callback URL `…/.auth/login/github/callback`. **Zasłoń sekret!** | 6a | Etapy instalacji |
| ☐ 16 | Dowód blokady Entra ID: „Nie masz dostępu” (401) w panelu App registrations albo błąd *Insufficient privileges* z `az ad app create` (uzasadnienie wyboru GitHuba) | 6 | Cel / decyzje |
| ☐ 17 | *(opcjonalnie)* Strona **„Brak dostępu do SatTrack”** (403) po zalogowaniu kontem spoza `ALLOWED_USERS` | 6c | Widok użytkownika |
