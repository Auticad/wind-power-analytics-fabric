# Power Automate Flows — Wind Power Analytics Fabric

Tre flussi di integrazione tra Microsoft Fabric e Power Automate, in ordine crescente di complessità.
Tutti i flussi usano il connettore **HTTP** con autenticazione **OAuth 2.0 / Managed Identity** per chiamare
le Fabric REST API (non esiste ancora un connettore nativo Fabric per Power Automate; si usa l'endpoint REST).

---

## Pre-requisiti comuni

| Cosa serve | Dove ottenerlo |
|---|---|
| Tenant ID | Azure Portal → Entra ID → Overview |
| Workspace ID | Fabric Portal → URL del workspace (`/groups/<workspaceId>`) |
| Item ID del notebook | Fabric Portal → URL del notebook (`/items/<itemId>`) |
| Service Principal o account con ruolo **Contributor** sul workspace | Azure App Registration |
| Client ID + Client Secret del Service Principal | Azure App Registration → Certificates & Secrets |

**Base URL Fabric REST API:**
```
https://api.fabric.microsoft.com/v1
```

**Token endpoint (OAuth 2.0 Client Credentials):**
```
https://login.microsoftonline.com/{tenantId}/oauth2/v2.0/token
scope: https://api.fabric.microsoft.com/.default
```

---

## Flusso 0 — SharePoint Test (verifica connettività)

**Scopo:** verificare che la connessione SharePoint → Power Automate → Email funzioni prima di toccare Fabric.
Questo flusso è il "ping" — se non passa, qualsiasi flusso più complesso non girerà.

**Scenario:** ogni volta che un nuovo file CSV viene caricato in una SharePoint Document Library, viene inviata una notifica email.

### Architettura

```
SharePoint Library
    [nuovo file CSV caricato]
           │
           ▼
  Condition: nome file
  contiene "wind_power"?
           │
     SÌ ──▶ Send Email (Outlook 365)
           │   Subject: "Nuovo CSV rilevato: {nome file}"
           │   Body:    path + timestamp + uploader
     NO ──▶ Terminate
```

### Step-by-step configurazione

#### Step 1 — Trigger: "When a file is created (properties only)"

```
Connector:  SharePoint
Action:     When a file is created (properties only)
Site:       https://<tenant>.sharepoint.com/sites/<sitename>
Library:    Wind Power Data       ← crea questa library su SharePoint
```

#### Step 2 — Condition

```
Condition:  contains(triggerOutputs()?['body/Name'], 'wind_power')
If yes:     continua
If no:      Terminate (status: Succeeded)
```

#### Step 3 — Send an email (Outlook 365)

```
To:         pcammise@gmail.com
Subject:    [Wind Power] Nuovo CSV: @{triggerOutputs()?['body/Name']}
Body:
  File:      @{triggerOutputs()?['body/Name']}
  Path:      @{triggerOutputs()?['body/Path']}
  Caricato:  @{triggerOutputs()?['body/Created']}
  Da:        @{triggerOutputs()?['body/Author/DisplayName']}
```

### Come testarlo

1. Crea la SharePoint Library **Wind Power Data** nel tuo SharePoint
2. Importa il flusso (o ricrealo a mano)
3. Carica manualmente `wind_power_data.csv` nella library
4. Verifica che arrivi l'email entro 1–2 minuti

> Se l'email arriva: connettività SharePoint → Power Automate → Outlook OK.
> Se non arriva: controlla i permessi del connettore SharePoint (OAuth, non Application-level).

---

## Flusso 1 — Semplice: Schedulazione giornaliera notebook Fabric

**Scenario:** ogni mattina alle 06:00, il flusso esegue il notebook `NB_Get_Daily_Data_Python` su Fabric (ingestione Bronze), aspetta il completamento, e invia un'email con esito + statistiche run.

**Questo rimpiazza il Fabric Data Pipeline scheduler** quando vuoi orchestrazione esterna o notifiche email native.

### Architettura

```
Recurrence (daily 06:00)
        │
        ▼
HTTP POST → Fabric API
"Run Notebook NB_Get_Daily_Data"
        │
        ▼
Do Until: status = "Succeeded" o "Failed"
  └── HTTP GET → Fabric API (check job status)
  └── Delay 30 sec
        │
   ┌────▼────┐
   │Succeeded│──▶ Email: "Pipeline OK — dati Bronze aggiornati"
   └────┬────┘
        │Failed
        ▼
   Email: "ERRORE pipeline — controllare Fabric"
   + corpo: error message da API response
```

### Step-by-step configurazione

#### Step 1 — Recurrence trigger

```
Interval:   1
Frequency:  Day
Time zone:  (UTC+01:00) Rome
Start time: 2025-01-01T06:00:00
```

#### Step 2 — Inizializza variabili

```
Initialize variable "jobId"    — String — ""
Initialize variable "jobStatus"— String — "NotStarted"
Initialize variable "attempts" — Integer — 0
```

#### Step 3 — HTTP: Esegui notebook (Fabric Jobs API)

```json
Method:  POST
URI:     https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items/{notebookItemId}/jobs/instances?jobType=RunNotebook

Authentication:
  Type:          Active Directory OAuth
  Tenant:        {tenantId}
  Audience:      https://api.fabric.microsoft.com
  Client ID:     {clientId}
  Credential Type: Secret
  Secret:        {clientSecret}

Body: {}
```

> La risposta contiene l'header `Location` con l'URL del job. Estrailo con:
> `outputs('HTTP_Run_Notebook')?['headers']?['Location']`

#### Step 4 — Set variable "jobId"

```
Value: last(split(outputs('HTTP_Run_Notebook')?['headers']?['Location'], '/'))
```

#### Step 5 — Do Until: jobStatus ∈ {"Succeeded", "Failed", "Cancelled"}

```
Condition: or(equals(variables('jobStatus'), 'Succeeded'),
              equals(variables('jobStatus'), 'Failed'),
              equals(variables('jobStatus'), 'Cancelled'))
Limit:      Count = 40   (40 × 30 sec = 20 minuti max attesa)
```

**Dentro il loop:**

```
HTTP GET:
  URI: https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/items/{notebookItemId}/jobs/instances/{jobId}
  Authentication: stessa del Step 3

Set variable "jobStatus":
  Value: body('HTTP_Check_Job_Status')?['status']

Set variable "attempts":
  Value: add(variables('attempts'), 1)

Delay: 30 seconds
```

#### Step 6 — Condition: check esito

```
If jobStatus == "Succeeded":
  Send Email:
    Subject: ✅ [Wind Power] Pipeline Bronze OK — @{formatDateTime(utcNow(), 'dd/MM/yyyy')}
    Body:
      Notebook: NB_Get_Daily_Data_Python
      Esito:    Succeeded
      Tentativi polling: @{variables('attempts')}
      Workspace: WindPowerAnalitics

Else:
  Send Email:
    Subject: ❌ [Wind Power] ERRORE pipeline Bronze — @{formatDateTime(utcNow(), 'dd/MM/yyyy')}
    Body:
      Notebook:  NB_Get_Daily_Data_Python
      Esito:     @{variables('jobStatus')}
      Dettaglio: @{body('HTTP_Check_Job_Status')?['failureReason']?['message']}
```

### Note tecniche

- **Notebook Item ID:** si trova nell'URL Fabric del notebook: `.../items/{guid}/...`
- **Workspace ID:** si trova nell'URL del workspace: `.../groups/{guid}/...`
- **Alternativa al polling:** Fabric supporta anche webhook (beta) — non usarli in produzione ancora, la feature è instabile.
- **Permessi minimi richiesti:** Service Principal con ruolo **Contributor** sul workspace Fabric.

---

## Flusso 2 — Complesso: Orchestrazione pipeline + alert operativo

**Scenario:** quando un nuovo CSV `wind_power_data.csv` appare in una SharePoint Library, il flusso:

1. Copia il file su OneLake via Fabric API
2. Esegue la pipeline completa Bronze → Silver → Gold (3 notebook in sequenza)
3. Chiama un'analisi DAX sul Semantic Model per leggere il KPI `Downtime Loss kWh`
4. Aggiorna una SharePoint List "Wind Power KPIs" con i risultati del giorno
5. Se `Downtime Loss kWh > 500`, invia un alert su Microsoft Teams (canale Operations)

### Architettura

```
SharePoint Library: "Wind Power Uploads"
    [file wind_power_YYYY-MM-DD.csv caricato]
             │
             ▼
     ┌── Copy file → OneLake ──┐
     │   (Fabric Files API)    │
     └─────────────────────────┘
             │
             ▼
    Run Notebook: NB_Get_Daily_Data
    (polling fino a Succeeded/Failed)
             │
             ▼
    Run Notebook: NB_Bronze_To_Silver
    (polling)
             │
             ▼
    Run Notebook: NB_Silver_To_Gold
    (polling)
             │
             ▼
    HTTP POST → Power BI / Fabric API
    DAX Query: Downtime Loss kWh, Total Energy Produced
             │
             ▼
    Update SharePoint List "Wind Power KPIs"
    (data, total_energy, downtime_loss, pipeline_status)
             │
    ┌────────▼─────────┐
    │downtime_loss>500?│
    │ SÌ ─▶ Teams Alert│
    │ NO ─▶ fine       │
    └──────────────────┘
```

### Step-by-step configurazione

#### Step 1 — Trigger: SharePoint "When a file is created"

```
Site:    https://<tenant>.sharepoint.com/sites/<sitename>
Library: Wind Power Uploads
Filter:  File name starts with "wind_power_"
```

#### Step 2 — Inizializza variabili

```
runDate        — String  — formatDateTime(utcNow(), 'yyyy-MM-dd')
downtimeLossKwh— Float   — 0
totalEnergy    — Float   — 0
pipelineStatus — String  — "Running"
```

#### Step 3 — HTTP: Upload CSV su OneLake (Fabric Files API)

```json
Method: PUT
URI:    https://onelake.dfs.fabric.microsoft.com/{workspaceId}/{bronzeLakehouseId}/Files/raw/wind_power_@{variables('runDate')}.csv

Headers:
  Content-Type: application/octet-stream

Body: triggerBody()?['$content']   ← contenuto binario del file da SharePoint

Authentication: Active Directory OAuth (stesso Service Principal)
```

> Il file viene scritto nel percorso `/Files/raw/` del Bronze Lakehouse.
> Il notebook `NB_Get_Daily_Data_Python` legge da questo path — assicurati che
> il path nel notebook corrisponda o parametrizza il notebook (vedi note).

#### Step 4–6 — Run notebook in sequenza (stesso pattern del Flusso 1)

Ripeti 3 volte il blocco HTTP POST + Do Until polling per:

```
4. NB_Get_Daily_Data_Python        (itemId: {nbGetDailyDataId})
5. NB_Bronze_To_Silver_Transformations_Python   (itemId: {nbBronzeSilverId})
6. NB_Silver_To_Gold_Transformations_Python     (itemId: {nbSilverGoldId})
```

Per ogni notebook: se il job fallisce → Set pipelineStatus = "Failed" → salta al Step 9 (aggiorna SharePoint con errore).

#### Step 7 — HTTP: Query DAX sul Semantic Model

Usa la **Power BI REST API** (compatibile con Fabric Semantic Models):

```json
Method: POST
URI:    https://api.powerbi.com/v1.0/myorg/groups/{workspaceId}/datasets/{semanticModelId}/executeQueries

Authentication:
  Type:     Active Directory OAuth
  Audience: https://analysis.windows.net/powerbi/api

Body:
{
  "queries": [
    {
      "query": "EVALUATE ROW(\"TotalEnergy\", [Total Energy Produced], \"DowntimeLoss\", [Downtime Loss kWh (est.)])"
    }
  ],
  "serializerSettings": {
    "includeNulls": true
  }
}
```

> Richiede che il Service Principal abbia **Build** permission sul Semantic Model.
> Oppure usa un account utente con licenza Power BI Pro/Fabric.

#### Step 8 — Parse JSON + Set variabili

```
Parse JSON del body response:
  Schema derivato dalla risposta dell'API (usa "Generate from sample" in Power Automate)

Set totalEnergy:
  body('Parse_DAX_Response')?['results']?[0]?['tables']?[0]?['rows']?[0]?['[TotalEnergy]']

Set downtimeLossKwh:
  body('Parse_DAX_Response')?['results']?[0]?['tables']?[0]?['rows']?[0]?['[DowntimeLoss]']
```

#### Step 9 — Update SharePoint List "Wind Power KPIs"

Crea prima la lista SharePoint con queste colonne:

| Colonna | Tipo |
|---|---|
| Title (data run) | Single line of text |
| TotalEnergyKwh | Number |
| DowntimeLossKwh | Number |
| PipelineStatus | Choice (Running / Succeeded / Failed) |
| NotebooksRun | Number |

```
Connector:  SharePoint
Action:     Create item
Site:       https://<tenant>.sharepoint.com/sites/<sitename>
List:       Wind Power KPIs

Title:              @{variables('runDate')}
TotalEnergyKwh:     @{variables('totalEnergy')}
DowntimeLossKwh:    @{variables('downtimeLossKwh')}
PipelineStatus:     Succeeded
NotebooksRun:       3
```

#### Step 10 — Condition: alert se downtime elevato

```
Condition: greater(float(variables('downtimeLossKwh')), 500)
```

**If yes — Post Teams message:**

```
Connector: Microsoft Teams
Action:    Post a message in a chat or channel
Team:      Wind Power Ops
Channel:   #operations-alerts

Message:
⚠️ ALERT — Downtime elevato rilevato
Data:            @{variables('runDate')}
Downtime Loss:   @{variables('downtimeLossKwh')} kWh
Total Energy:    @{variables('totalEnergy')} kWh
Pipeline:        Succeeded (3/3 notebooks)
Azione richiesta: verificare turbine con status ≠ Online in Fabric Report
Link report: https://app.powerbi.com/groups/{workspaceId}/reports/{reportId}
```

**If no:** nessuna azione aggiuntiva.

### Parametrizzazione dei notebook (opzionale ma consigliato)

Per passare la data del run come parametro al notebook invece di hardcodarla:

```json
Body del job POST:
{
  "executionData": {
    "parameters": {
      "run_date": "@{variables('runDate')}"
    }
  }
}
```

Nel notebook Fabric, leggi il parametro con:
```python
run_date = spark.conf.get("spark.fabric.jobrunner.executionData.parameters.run_date", "2024-01-01")
```

---

## Riepilogo comparativo

| | Flusso 0 | Flusso 1 | Flusso 2 |
|---|---|---|---|
| Trigger | Upload SharePoint | Schedulato (06:00) | Upload SharePoint |
| Fabric API | No | Run notebook × 1 | Run notebook × 3 + DAX query |
| Complessità | Bassa | Media | Alta |
| Tempo stimato build | 15 min | 45 min | 3–4 ore |
| Connettori usati | SharePoint, Outlook | HTTP, Outlook | SharePoint, HTTP, Teams |
| Scopo principale | Test connettività | Ingestione automatica | Orchestrazione completa + alerting |

---

## Limitazioni note e alternative

**Polling vs webhook:** il pattern Do Until con polling ogni 30 sec funziona ma consuma run Power Automate.
Per notebook lunghi (>10 min), valuta Fabric Data Pipelines come alternativa: hanno scheduler nativo e notifiche via Alert.

**DAX API e licenze:** `executeQueries` via REST richiede che il dataset non sia in modalità DirectLake con row-level security abilitata per il Service Principal. Se la query fallisce con 403, verifica le Build permissions sul Semantic Model.

**OneLake upload via PUT:** l'endpoint `onelake.dfs.fabric.microsoft.com` usa ADLS Gen2 API. Per file >100MB usa upload chunked (Append + Flush pattern).

---

*Pietro Cammise · Wind Power Analytics · Microsoft Fabric + Power Automate · 2025*
