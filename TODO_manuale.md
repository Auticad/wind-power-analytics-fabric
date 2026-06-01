# TODO manuale — Azioni richieste a te per completare il repository

File e documenti generati automaticamente sono già presenti nella cartella.
Quello che segue è tutto ciò che richiede azioni manuali da parte tua, in ordine di priorità.

---

## FASE 1 — Creazione e struttura del repository GitHub

### 1.1 Crea il repository su GitHub

Vai su [github.com/new](https://github.com/new) e configura:

- **Repository name:** `wind-power-analytics-fabric`
- **Description:** `End-to-end data pipeline on Microsoft Fabric — Medallion Architecture (Bronze/Silver/Gold), PySpark, Delta Lake, Power BI`
- **Visibility:** Public
- **Inizializza con README:** NO (lo abbiamo già)
- Clicca **Create repository**

---

### 1.2 Crea la struttura di cartelle e carica i file

Dalla tua cartella locale, esegui questi comandi nel terminale:

```bash
cd "C:\Users\pietr\OneDrive\Desktop\Claude-Cowork\Progetto_repository_FABRIC"

git init
git remote add origin https://github.com/Auticad/wind-power-analytics-fabric.git

# Crea le sottocartelle necessarie
mkdir notebooks
mkdir reports
mkdir screenshots
mkdir data    # già creata con data_dictionary.md
mkdir docs    # già creata con i file docs

# Sposta i file nelle cartelle corrette
move NB_*.ipynb notebooks\
move RPT_*.pbix reports\
move RPT_*.pdf reports\
move *.png screenshots\
move wind_power_data.csv data\
move Schema_progetto.png screenshots\
move star_schema.png screenshots\

git add .
git commit -m "feat: initial commit — wind power analytics Fabric pipeline"
git push -u origin main
```

---

## FASE 2 — Screenshot aggiuntivi da fare in Fabric

Questi screenshot mancano o vanno integrati nel repository per documentare le funzionalità di Fabric Service.

### 2.1 Screenshot workspace organizzato

1. Apri il workspace `WindPowerAnalitics` su [app.fabric.microsoft.com](https://app.fabric.microsoft.com)
2. Assicurati che siano visibili: i 3 Lakehouses, i 4 Notebook, il Semantic Model e i 2 Report
3. Fai screenshot dell'intera lista artefatti
4. Salva come `screenshots/workspace_full.png`

### 2.2 Screenshot Bronze Lakehouse — tabella dati

1. Apri `LH_Wind_Power_Bronze` → sezione **Tables** → `dbo/wind_power`
2. Clicca sulla tabella per vedere l'anteprima dati
3. Screenshot della preview con almeno 10 righe visibili
4. Salva come `screenshots/LH_bronze_table_preview.png`

### 2.3 Screenshot Gold Lakehouse — tutte le tabelle

1. Apri `LH_Wind_Power_Gold` → sezione **Tables**
2. Deve mostrare le 5 tabelle: `fact_wind_power`, `dim_date`, `dim_time`, `dim_turbine`, `dim_operational_status`
3. Screenshot
4. Salva come `screenshots/LH_gold_tables.png`

### 2.4 Screenshot del Semantic Model (relazioni)

1. Apri il Semantic Model collegato al Gold Lakehouse
2. Vai nella vista **Model** (diagramma relazioni)
3. Screenshot che mostri tutte e 5 le tabelle con le relazioni tracciate
4. Salva come `screenshots/semantic_model_relationships.png`

### 2.5 Screenshot scheduled refresh (opzionale ma consigliato)

1. Apri le impostazioni del Semantic Model su Fabric Service
2. Sezione **Scheduled refresh** — configura una frequenza (es. Daily)
3. Screenshot della configurazione attiva
4. Salva come `screenshots/scheduled_refresh.png`

---

## FASE 3 — Misure DAX da aggiungere + documentazione

### 3.1 Aggiungi queste 4 misure DAX al Semantic Model

Apri il Semantic Model su Fabric (o in Power BI Desktop collegato al Gold Lakehouse) e crea le seguenti misure. Copiale esattamente — sono testate sulla struttura dello star schema di questo progetto.

---

#### Misura 1: `Capacity Factor %`

Il **capacity factor** è il KPI standard nell'energia eolica: misura quanta energia è stata prodotta rispetto al massimo teorico (capacità × ore operative). Valori tipici per eolico onshore: 25–45%.

```dax
Capacity Factor % =
VAR TotalEnergyMWh =
    DIVIDE( SUM( fact_wind_power[energy_produced] ), 1000 )  -- da kWh a MWh
VAR TotalCapacityKW =
    SUMX(
        fact_wind_power,
        RELATED( dim_turbine[capacity] )
    )
VAR IntervalHours = 10 / 60  -- rilevazioni ogni 10 minuti
VAR TheoreticalMaxMWh =
    DIVIDE( TotalCapacityKW, 1000 ) * IntervalHours * COUNTROWS( fact_wind_power ) / DISTINCTCOUNT( fact_wind_power[turbine_id] )
RETURN
    DIVIDE( TotalEnergyMWh, TheoreticalMaxMWh, 0 ) * 100
```

**Dove usarla:** card KPI nella pagina overview, matrice per turbina, confronto tra regioni.
**Filter context:** risponde a qualsiasi filtro su `dim_turbine`, `dim_date`, `dim_time`.

---

#### Misura 2: `Energy MTD`

Produzione cumulata dall'inizio del mese corrente (o del mese selezionato via slicer).

```dax
Energy MTD =
CALCULATE(
    SUM( fact_wind_power[energy_produced] ),
    DATESMTD( dim_date[date_id] )
)
```

**Dove usarla:** card affiancata a `Total Energy Produced` per mostrare l'andamento nel periodo corrente. Usa uno slicer su `dim_date[year]` e `dim_date[month]` per renderla interattiva.
**Filter context:** `DATESMTD` ignora filtri di data attivi e li sostituisce con il range month-to-date.

---

#### Misura 3: `Downtime Loss kWh (est.)`

Stima l'energia persa durante i periodi `Offline` o `Maintenance`, usando la produzione media per turbina nelle ore operative come baseline.

```dax
Downtime Loss kWh (est.) =
VAR AvgProductionOnline =
    CALCULATE(
        AVERAGE( fact_wind_power[energy_produced] ),
        dim_operational_status[status] = "Online"
    )
VAR DowntimeRows =
    CALCULATE(
        COUNTROWS( fact_wind_power ),
        dim_operational_status[status] <> "Online"
    )
RETURN
    DowntimeRows * AvgProductionOnline
```

**Dove usarla:** pagina dedicata all'analisi operativa / downtime. Affiancala a una tabella con `dim_operational_status[status]` per confrontare energia reale vs perdita stimata.
**Limite noto:** la baseline usa la media globale Online, non una previsione basata sul vento nell'intervallo — è una stima conservativa ma corretta per un portfolio.

---

#### Misura 4: `Avg Energy per Interval by Time Period`

Produzione media per singolo intervallo di 10 minuti, raggruppata per fascia oraria. Permette di confrontare Morning vs Night senza distorsioni dovute al numero diverso di rilevazioni per fascia.

```dax
Avg Energy per Interval by Time Period =
AVERAGEX(
    VALUES( dim_time[time_period] ),
    CALCULATE( AVERAGE( fact_wind_power[energy_produced] ) )
)
```

**Dove usarla:** grafico a barre con `dim_time[time_period]` sull'asse X. Evidenzia quale fascia oraria è strutturalmente più produttiva indipendentemente dalla sua durata totale nel dataset.
**Filter context:** risponde a filtri su turbina e data — ottimo con uno slicer per turbina.

---

### 3.2 Crea il file `docs/dax_measures.md`

Dopo aver aggiunto le misure al modello, documenta tutte le misure presenti (incluse quelle già esistenti nei report) usando questa struttura:

```markdown
### Nome misura

**Formula:**
```dax
[formula esatta copiata dal Model view]
```
**Contesto di utilizzo:** [dove è usata nel report]
**Filter context:** [quali filtri modificano il risultato]
```

Misure da documentare (minimo):
- Total Energy Produced
- Average Wind Speed
- Energy by Turbine
- % Production by Region
- Energy by Time Period
- Capacity Factor %  ← nuova
- Energy MTD         ← nuova
- Downtime Loss kWh  ← nuova
- Avg Energy per Interval by Time Period  ← nuova

---

## FASE 3B — Due nuovi report da costruire

### Report 3: `RPT_Capacity_Factor_Analysis`

**Obiettivo:** mostrare l'efficienza reale delle turbine rispetto alla capacità installata — il report più "da ingegnere" dei tre e quello che dimostra la comprensione del dominio eolico.

**Pagine consigliate (2–3):**

**Pagina 1 — Overview Capacity Factor**
- Card KPI: `Capacity Factor %` (globale)
- Grafico a barre orizzontali: `Capacity Factor %` per `dim_turbine[turbine_name]`
- Matrice: righe = `dim_turbine[region]`, colonne = `dim_date[month]`, valori = `Capacity Factor %` (con formattazione condizionale: verde > 35%, arancio 20–35%, rosso < 20%)
- Slicer: `dim_date[year]`, `dim_date[quarter]`

**Pagina 2 — Correlazione vento / efficienza**
- Scatter chart: asse X = `Average Wind Speed`, asse Y = `Capacity Factor %`, legenda = `dim_turbine[turbine_name]`
- Line chart: `wind_speed` vs `energy_produced` per fascia oraria (`dim_time[time_period]`)
- Tooltip personalizzato: mostra `Capacity Factor %` + `energy_produced` al passaggio su ogni punto

**Pagina 3 — Benchmark per turbina**
- Grouped bar chart: `Total Energy Produced` vs `Downtime Loss kWh (est.)` affiancati per turbina
- Card: % ore Online / totale (filtrabile per turbina)
- Tabella: `turbine_name` | `capacity` | `Total Energy Produced` | `Capacity Factor %` | `Downtime Loss kWh`

**Istruzioni di build:**
1. In Power BI Desktop, crea un nuovo report collegato al Semantic Model del Gold Lakehouse
2. Imposta il tema coerente con gli altri due report (`View → Themes`)
3. Costruisci le 3 pagine nell'ordine sopra
4. Salva come `reports/RPT_Capacity_Factor_Analysis.pbix`
5. Esporta PDF: `File → Export → Export to PDF` → `reports/RPT_Capacity_Factor_Analysis.pdf`

---

### Report 4: `RPT_Operational_Status_Analysis`

**Obiettivo:** analisi dei periodi di downtime e impatto sulla produzione — risponde alla domanda "quanto ci è costato ogni evento di manutenzione?". Dimostra comprensione delle dimensioni operative, non solo di quelle temporali.

**Pagine consigliate (2):**

**Pagina 1 — Status Overview**
- Donut chart: distribuzione rilevazioni per `dim_operational_status[status]` (Online / Offline / Maintenance)
- Stacked bar chart: per mese (`dim_date[month]`), barre impilate con percentuale Online vs non-Online
- Card KPI: `Downtime Loss kWh (est.)` — con formato numero grande e etichetta "Energia persa stimata"
- Tabella: `dim_date[year]` | `dim_date[month]` | conteggio rilevazioni Online | conteggio Offline | conteggio Maintenance
- Slicer: `dim_turbine[turbine_name]`, `dim_date[year]`

**Pagina 2 — Analisi per dipartimento e turbina**
- Matrix: righe = `dim_operational_status[responsible_department]`, colonne = `dim_operational_status[status]`, valori = COUNTROWS
- Bar chart: `Downtime Loss kWh (est.)` per `dim_turbine[turbine_name]`
- Line chart: `energy_produced` nel tempo con evidenziazione visiva dei periodi non-Online (usa un misura booleana `Is Online = IF(SELECTEDVALUE(dim_operational_status[status]) = "Online", 1, 0)` per colorare le barre)

**Istruzioni di build:**
1. Stessa procedura del Report 3
2. Salva come `reports/RPT_Operational_Status_Analysis.pbix`
3. Esporta PDF: `reports/RPT_Operational_Status_Analysis.pdf`
4. Aggiungi screenshot rappresentativo in `screenshots/`

---

## FASE 4 — Export e pubblicazione report

### 4.1 Verifica i PDF già presenti

Controlla che `RPT_Wind_Turbine_Power_Analysis.pdf` e `RPT_Wind_Turbine_Direction_Analysis.pdf` siano export completi (tutte le pagine del report). Se sono export parziali, riesporta da Power BI Desktop:
**File → Export → Export to PDF**

### 4.2 Pubblica il report come Public (alto impatto)

Per ottenere un link pubblico visualizzabile senza Power BI installato:

1. In Power BI Service (Fabric), apri uno dei due report
2. Clicca **File → Embed report → Publish to web (public)**
3. Accetta l'avviso di pubblicazione pubblica
4. Copia il link generato (`https://app.powerbi.com/view?r=...`)
5. Inserisci il link nel `README.md` sotto la sezione "Report Power BI"

> ⚠️ Usa solo dataset pubblici (questo dataset è pubblico, provenendo da GitHub). Non pubblicare mai report con dati aziendali o personali tramite Publish to web.

---

## FASE 5 — Miglioramenti opzionali (alto impatto sul portfolio)

### 5.1 Crea `docs/schema_progetto.md`

Hai già `Schema_progetto.png` nella cartella. Aggiungilo in `docs/` e aggiungi nel README una riga che lo referenzia:
```bash
move Schema_progetto.png docs\
```
Poi aggiungi nel README:
```markdown
![Schema progetto](docs/Schema_progetto.png)
```

### 5.2 Crea un tema Power BI personalizzato

Se i report usano un tema custom:
1. In Power BI Desktop: **View → Themes → Save current theme**
2. Salva come `reports/theme_wind_power.json`
3. Committa nel repo — dimostra attenzione al branding visivo

### 5.3 Aggiungi GitHub Topics al repository

Sulla pagina GitHub del repo, clicca l'icona a ingranaggio vicino a "About" e aggiungi questi topics:
```
microsoft-fabric  delta-lake  pyspark  spark-sql  power-bi  
medallion-architecture  data-engineering  onelake  wind-power
```

### 5.4 Aggiungi GitHub Actions per CI (avanzato)

Se vuoi dimostrare maturità devops, aggiungi un workflow `.github/workflows/validate.yml` che esegua un lint dei notebook (es. `nbformat`) ad ogni push.

---

## Checklist finale prima di condividere il link

- [ ] Repository pubblico su GitHub con nome leggibile
- [ ] README con screenshot inline visibili (non solo path locali)
- [ ] Tutti i notebook in `notebooks/`, report in `reports/`, screenshot in `screenshots/`
- [ ] `docs/dax_measures.md` compilato con le misure reali
- [ ] Almeno un PDF export nel repo
- [ ] Link al report pubblico su Power BI Service (o screenshot del workspace)
- [ ] `.gitignore` presente
- [ ] Nessun file con credenziali o tenant ID committato nei notebook (rimuovi o oscura il `ctid` nei path se presenti)
- [ ] GitHub Topics configurati
