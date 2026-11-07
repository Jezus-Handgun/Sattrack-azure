# Wdrożenie SatTrack w Azure

Instrukcja krok po kroku. Każdy krok ma dwa warianty: **Azure Portal** (do zrzutów ekranu) i **Azure CLI**. Zrzuty, które warto zrobić, są oznaczone ikoną 📸 z numerem z [SCREENSHOTS.md](SCREENSHOTS.md). Wariant CLI w całości jest też w skrypcie [scripts/deploy.sh](../scripts/deploy.sh).

## Wymagania wstępne

| Wymaganie | Uwagi |
|---|---|
| Subskrypcja Azure | Np. **Azure for Students** (darmowe kredyty) |
| Uprawnienia do tworzenia rejestracji aplikacji w Entra ID | Potrzebne w kroku 6. Na kontach uczelnianych bywa to zablokowane, patrz [Rozwiązywanie problemów](#rozwiązywanie-problemów) |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Do zbudowania obrazu lokalnie |
| [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) 2.60 lub nowsze | Plus rozszerzenie: `az extension add --name containerapp --upgrade` |
| Kod z repozytorium | `git clone ...`, a obraz budujemy z katalogu głównego repo |

**Dwie uwagi dotyczące Azure for Students:**
- **Budowanie w chmurze (`az acr build`, ACR Tasks) jest wstrzymane dla subskrypcji z darmowymi kredytami** ([Microsoft Learn](https://learn.microsoft.com/azure/container-registry/container-registry-tasks-overview)). Dlatego obraz budujemy **lokalnie w Dockerze** i wysyłamy go do rejestru (`docker push`).
- **Subskrypcja może dopuszczać tylko wybrane regiony.** Instrukcja używa `westeurope`. Jeśli tworzenie zasobu skończy się błędem `RequestDisallowedByPolicy` / `RequestDisallowedByAzure`, użyj regionu, w którym masz już działające zasoby. Listę dozwolonych regionów znajdziesz w portalu: **Policy → Assignments → „Allowed resource deployment regions”**.

Nazwy użyte w instrukcji (CLI w Git Bash, WSL albo Cloud Shell):

```bash
RG=rg-sattrack
LOCATION=westeurope
ACR=acrsattrack<twoj-sufiks>      # globalnie unikalna, tylko małe litery i cyfry
ENV=cae-sattrack
APP=ca-sattrack
IMAGE=$ACR.azurecr.io/sattrack:v1
```

---

## Krok 0. Logowanie i dostawcy zasobów

**CLI**
```bash
az login
az account show --query "{subskrypcja:name, id:id}" -o table   # sprawdź, czy to właściwa subskrypcja
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait
az provider register --namespace Microsoft.ContainerRegistry --wait
```

**Portal:** nic do zrobienia, portal rejestruje dostawców automatycznie przy tworzeniu zasobów.

## Krok 1. Grupa zasobów

Grupa zasobów to logiczny kontener na wszystkie elementy projektu. Po ocenie usuwa się ją jednym poleceniem.

**Portal:** **Resource groups → Create**, potem:
- Subscription: Twoja subskrypcja,
- Resource group: `rg-sattrack`,
- Region: `West Europe`.

Na koniec **Review + create → Create**. 📸 1

**CLI**
```bash
az group create --name $RG --location $LOCATION
```

## Krok 2. Azure Container Registry

Prywatne repozytorium obrazów Dockera.

**Portal:** **Create a resource → Container Registry → Create**, potem:
- Resource group: `rg-sattrack`,
- Registry name: `acrsattrack<sufiks>`,
- Location: `West Europe`,
- Pricing plan: **Basic**.

Na koniec **Review + create → Create**. 📸 2

**CLI**
```bash
az acr create --name $ACR --resource-group $RG --sku Basic --location $LOCATION
```

Konto administratora rejestru (admin user) zostaje **wyłączone**, bo aplikacja pobiera obraz przez tożsamość zarządzaną.

## Krok 3. Budowa i wysłanie obrazu

**CLI (lokalny Docker), ścieżka zalecana dla Azure for Students:**
```bash
az acr login --name $ACR
docker build --platform linux/amd64 -t $IMAGE .
docker push $IMAGE
az acr repository show-tags --name $ACR --repository sattrack -o table   # powinno pokazać v1
```

Wariant w chmurze (działa tylko tam, gdzie ACR Tasks nie są wstrzymane):
```bash
az acr build --registry $ACR --image sattrack:v1 .
```

**Portal (podgląd wyniku):** rejestr `acrsattrack<sufiks>` → **Services → Repositories → sattrack** → widoczny tag `v1`. 📸 3

## Krok 4. Środowisko Container Apps

Środowisko to wspólna granica sieci i logów dla aplikacji. Razem z nim tworzy się obszar roboczy **Log Analytics**.

**Portal:** środowisko tworzy się w kreatorze aplikacji (krok 5), na zakładce **Basics** w sekcji **Container Apps Environment → Create new**:
- Environment name: `cae-sattrack`,
- Plan: **Consumption**,
- zakładka **Monitoring**: Logs destination **Azure Log Analytics** (nowy obszar roboczy).

**CLI**
```bash
az containerapp env create --name $ENV --resource-group $RG --location $LOCATION
```

Bez dodatkowych parametrów polecenie samo tworzy obszar roboczy Log Analytics.

## Krok 5. Container App

**Portal:** **Create a resource → Container App → Create**.

1. Zakładka **Basics**:
   - Resource group: `rg-sattrack`,
   - Container app name: `ca-sattrack`,
   - Region: `West Europe`,
   - Container Apps Environment: `cae-sattrack` (krok 4).

   📸 4a
2. Zakładka **Container**:
   - odznacz **Use quickstart image**,
   - Image source: **Azure Container Registry**,
   - Registry: `acrsattrack<sufiks>`, Image: `sattrack`, Image tag: `v1`,
   - Authentication type: **Managed identity**, Managed identity: **System assigned** (portal sam nada rolę `AcrPull`),
   - CPU and Memory: **0.25 CPU cores, 0.5 Gi memory**.

   📸 4b
3. Zakładka **Ingress**:
   - Ingress: **Enabled**,
   - Ingress traffic: **Accepting traffic from anywhere**,
   - Ingress type: **HTTP**,
   - Target port: **8000**.

   📸 4c
4. **Review + create → Create**. Po wdrożeniu przejdź do zasobu. W **Overview** widać **Application Url**, a po jego otwarciu aplikację. 📸 5

**CLI.** Przy tożsamości przypisanej systemowo Microsoft Learn opisuje trzy kroki: najpierw aplikacja z obrazem testowym, potem podpięcie rejestru, na końcu podmiana obrazu.
```bash
# 1) aplikacja z publicznym obrazem testowym (nasłuchuje na porcie 80)
az containerapp create --name $APP --resource-group $RG --environment $ENV \
  --image mcr.microsoft.com/k8se/quickstart:latest \
  --target-port 80 --ingress external \
  --cpu 0.25 --memory 0.5Gi --min-replicas 0 --max-replicas 2

# 2) tożsamość systemowa + dostęp do rejestru (rola AcrPull)
az containerapp registry set --name $APP --resource-group $RG \
  --server $ACR.azurecr.io --identity system

# 3) docelowy obraz i port aplikacji
az containerapp update --name $APP --resource-group $RG --image $IMAGE
az containerapp ingress update --name $APP --resource-group $RG --target-port 8000

# adres aplikacji
az containerapp show --name $APP --resource-group $RG --query properties.configuration.ingress.fqdn -o tsv
```

Sprawdź, czy rola została nadana: `az role assignment list --scope $(az acr show -n $ACR --query id -o tsv) -o table` powinno pokazać `AcrPull`.

Między krokiem 3a a 3b aplikacja przez chwilę nasłuchuje na innym porcie niż ingress i może być niezdrowa. To normalne.

### Sonda zdrowia na `/healthz`

Domyślnie Container Apps sprawdza tylko, czy port 8000 jest otwarty (sonda TCP). Ustawiamy własną sondę HTTP na endpoint `/healthz`, który odpowiada natychmiast i niczego nie liczy.

**Portal:** Container App → **Application → Containers → Edit and deploy** → zaznacz kontener → **Edit** → zakładka **Health probes**:
- **Liveness probe**: włącz, Transport HTTP, Path `/healthz`, Port `8000`,
- **Readiness probe**: włącz, Transport HTTP, Path `/healthz`, Port `8000`.

Potem **Save → Create** (powstaje nowa rewizja). 📸 14 (opcjonalny)

**CLI:** dla sond nie ma osobnych flag, ustawia się je przez YAML:
```bash
az containerapp show --name $APP --resource-group $RG -o yaml > app.yaml
# w pliku app.yaml, pod properties.template.containers[0], dopisz:
#   probes:
#   - type: Liveness
#     httpGet: { path: /healthz, port: 8000 }
#   - type: Readiness
#     httpGet: { path: /healthz, port: 8000 }
az containerapp update --name $APP --resource-group $RG --yaml app.yaml
```

### Skalowanie (od 0 do 2 replik)

**Portal:** Container App → **Application → Scale** (w nowszym portalu **Scale and replicas**) → Min replicas **0**, Max replicas **2**. Reguła domyślna to skalowanie HTTP. 📸 7

**CLI:** ustawione już w `create` (`--min-replicas 0 --max-replicas 2`). Zmiana później:
```bash
az containerapp update --name $APP --resource-group $RG --min-replicas 0 --max-replicas 2
```

Przy 0 replikach pierwsze żądanie po przerwie trwa kilka sekund (zimny start). Zrzuty ekranu aplikacji rób po rozgrzaniu.

## Krok 6. Logowanie przez Microsoft Entra ID (Easy Auth)

Logowania nie ma w kodzie aplikacji. Zapewnia je platforma: niezalogowane żądanie w ogóle nie dociera do kontenera.

**Portal**, wariant zalecany, bo daje najważniejsze zrzuty:
1. Container App → **Security → Authentication → Add identity provider**.
2. Identity provider: **Microsoft**.
3. App registration type: **Create new app registration**, Name: `sattrack`, Supported account types: **Current tenant – Single tenant** (tylko konta organizacji).
4. Client secret expiration: np. 180 dni.
5. Sekcja **Container App authentication settings** (pojawia się przy pierwszym dostawcy; domyślnie przekierowuje wszystkich do logowania, a etykiety mogą się nieznacznie różnić):
   - Restrict access: **Require authentication**,
   - Unauthenticated requests: **HTTP 302 Found redirect: recommended for websites**,
   - Token store: zaznaczony.
6. **Add**. 📸 6

Sprawdzenie: otwórz adres aplikacji w oknie prywatnym. Powinno pojawić się logowanie Microsoft 📸 9, a po zalogowaniu pasek górny pokaże Twoje imię i nazwisko z linkiem „Wyloguj”.

**CLI** (alternatywa, wymaga utworzenia rejestracji aplikacji ręcznie):
```bash
FQDN=$(az containerapp show -n $APP -g $RG --query properties.configuration.ingress.fqdn -o tsv)
APP_ID=$(az ad app create --display-name sattrack --sign-in-audience AzureADMyOrg \
  --web-redirect-uris "https://$FQDN/.auth/login/aad/callback" \
  --enable-id-token-issuance true --query appId -o tsv)
az ad sp create --id $APP_ID
SECRET=$(az ad app credential reset --id $APP_ID --query password -o tsv)
TENANT=$(az account show --query tenantId -o tsv)

az containerapp auth microsoft update --name $APP --resource-group $RG \
  --client-id $APP_ID --client-secret $SECRET --tenant-id $TENANT --yes
az containerapp auth update --name $APP --resource-group $RG \
  --unauthenticated-client-action RedirectToLoginPage --redirect-provider azureactivedirectory
```

Flag polecenia `az containerapp auth update` nie ma w przewodniku Microsoft Learn. Przed użyciem sprawdź je w `az containerapp auth update --help`.

## Krok 7. Logi w Log Analytics

Wszystko, co aplikacja wypisuje na stdout, trafia do obszaru roboczego Log Analytics z opóźnieniem kilku minut.

**Portal:** Container App → **Monitoring → Logs** (zamknij okno z przykładowymi zapytaniami, przełącz edytor w tryb **KQL**) → wklej zapytanie → **Run**. 📸 8

```kusto
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "ca-sattrack"
| project TimeGenerated, RevisionName_s, Log_s
| order by TimeGenerated desc
| take 100
```

Tylko najważniejsze zdarzenia (start, źródło danych TLE, CelesTrak, czas obliczeń):
```kusto
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "ca-sattrack"
| where Log_s has_any ("SatTrack starting", "TLE", "CelesTrak", "visibility-timeline")
| project TimeGenerated, Log_s
| order by TimeGenerated desc
```

Podgląd na żywo: Container App → **Monitoring → Log stream**, albo w CLI:
```bash
az containerapp logs show --name $APP --resource-group $RG --follow
```

## Krok 8. Aktualizacja do nowej wersji

```bash
docker build --platform linux/amd64 -t $ACR.azurecr.io/sattrack:v2 .
docker push $ACR.azurecr.io/sattrack:v2
az containerapp update --name $APP --resource-group $RG --image $ACR.azurecr.io/sattrack:v2
```

**Portal:** Container App → **Application → Containers → Edit and deploy** → kontener → Image tag `v2` → **Save → Create**. Każda zmiana tworzy nową **rewizję** (Application → Revisions and replicas).

## Sposób dostępu użytkownika końcowego

1. Pracownik otwiera adres `https://ca-sattrack.<...>.azurecontainerapps.io`.
2. Loguje się kontem organizacji Microsoft (Entra ID).
3. Widzi mapę satelitów na żywo, widoczność GNSS w wybranym punkcie (skyplot, tabela, wykres 24 h) i przeloty ISS. 📸 10, 📸 11
4. Wylogowuje się linkiem **Wyloguj** w prawym górnym rogu.

Dla działu IT dostępna jest dokumentacja API pod adresem `/docs`. 📸 12

## Koszty

| Zasób | Koszt |
|---|---|
| Container Apps (plan Consumption) | Miesięczny darmowy limit na subskrypcję: **180 000 vCPU-s, 360 000 GiB-s i 2 mln zapytań**. Przy skalowaniu do zera i ruchu demonstracyjnym koszt jest praktycznie zerowy. |
| Container Registry Basic | Stała opłata, ok. **0,167 USD/dzień (~5 USD/mies.)**. Aktualną cenę sprawdź w [kalkulatorze](https://azure.microsoft.com/pricing/calculator/?service=container-registry). |
| Log Analytics | Opłata za ilość danych, przy kilku MB logów to grosze |
| Entra ID (rejestracja aplikacji) | Bezpłatnie |

Podgląd kosztów: **Cost Management → Cost analysis**, zakres `rg-sattrack`. 📸 13 (opcjonalny)

## Sprzątanie po ocenie projektu

```bash
az group delete --name $RG --yes --no-wait
az ad app delete --id <APP_ID rejestracji "sattrack">   # rejestracja w Entra ID nie należy do grupy zasobów
```

**Portal:**
- **Resource groups → rg-sattrack → Delete resource group**,
- **Microsoft Entra ID → App registrations → sattrack → Delete**.

## Rozwiązywanie problemów

| Objaw | Przyczyna i rozwiązanie |
|---|---|
| `az acr build` kończy się błędem o wstrzymanych zadaniach | ACR Tasks są wstrzymane dla darmowych kredytów. Użyj `docker build` i `docker push` (krok 3). |
| `RequestDisallowedByPolicy` przy tworzeniu zasobu | Region niedozwolony w subskrypcji. Użyj regionu dopuszczonego przez politykę (patrz wymagania wstępne). |
| Rewizja w stanie *Failed*, w logach `unauthorized` przy pobieraniu obrazu | Brak roli `AcrPull` dla tożsamości aplikacji. Nadaj ją w rejestrze: **Access control (IAM) → Add role assignment → AcrPull →** tożsamość zarządzana `ca-sattrack`. Sprawdź też `az acr config authentication-as-arm show -r $ACR` (musi być `enabled`). |
| `exec format error` w logach | Obraz zbudowany na procesorze ARM (np. Mac z Apple Silicon). Buduj z `--platform linux/amd64`. |
| Błąd przy tworzeniu rejestracji aplikacji (*insufficient privileges*) | Uczelnia blokuje rejestrowanie aplikacji w swoim katalogu Entra ID. Poproś dział IT o utworzenie rejestracji i wybierz **Provide the details of an existing app registration**. |
| Pierwsze otwarcie strony trwa kilka sekund | Zimny start po skalowaniu do zera, to normalne. |
| Napis „Dane orbitalne: snapshot…” zamiast „(CelesTrak)” | CelesTrak był niedostępny albo zwrócił 403. Aplikacja ponowi próbę po 2 h. Szczegóły są w logach (`CelesTrak fetch failed`). |
