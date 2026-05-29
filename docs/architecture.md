# Architettura — Wind Power Analytics

## Overview

Il progetto implementa una pipeline dati completa su **Microsoft Fabric** seguendo il pattern **Medallion Architecture** (Bronze / Silver / Gold).
I dati di produzione eolica vengono ingeriti incrementalmente, trasformati in due stadi e infine strutturati in uno star schema ottimizzato per l'analisi in Power BI.

---

## Fabric Workspace

**Nome:** `WindPowerAnalitics`
**Tenant ID:** `9708968b-0c32-4669-8c58-045c91ee99dd`

Il workspace contiene tutti gli artefatti del progetto:
- 3 Lakehouses (Bronze, Silver, Gold)
- 4 Notebooks Spark
- 1 Semantic Model (Power BI Dataset)
- 2 Report Power BI

---

## Componenti

### Lakehouses

| Lakehouse | Nome | Scopo |
|-----------|------|-------|
| Bronze | `LH_Wind_Power_Bronze` | Dati raw ingeriti senza trasformazioni. Preserva la fonte originale. |
| Silver | `LH_Wind_Power_Silver` | Dati puliti e arricchiti con colonne derivate da data/ora. |
| Gold | `LH_Wind_Power_Gold` | Star schema in Delta format pronto per il Semantic Model. |

Tutti i dati sono in formato **Delta Lake** su **OneLake**, con percorso base:
```
abfss://WindPowerAnalitics@onelake.dfs.fabric.microsoft.com/<lakehouse>.Lakehouse/Tables/dbo/<table>
```

### Notebooks

| Notebook | Runtime | Descrizione |
|----------|---------|-------------|
| `NB_Get_Daily_Data_Python` | PySpark | Ingestione incrementale: scarica il CSV del giorno successivo da GitHub e lo appende alla tabella Bronze via Delta `append`. |
| `NB_Bronze_To_Silver_Transformations_Python` | PySpark | Trasformazione Bronze → Silver con PySpark DataFrame API. |
| `NB_Bronze_To_Silver_Transformations_SQL` | Spark SQL | Trasformazione equivalente in SQL — alternativa didattica e di riferimento. |
| `NB_Silver_To_Gold_Transformations_Python` | PySpark | Creazione star schema: estrae 4 dimension table + 1 fact table da Silver e salva in Gold. |

---

## Flusso dati

```
GitHub raw CSV
     │
     │  HTTP GET (requests)
     ▼
NB_Get_Daily_Data_Python
     │
     │  Delta append
     ▼
LH_Wind_Power_Bronze  ←─── Tabella: wind_power (raw, immutabile)
     │
     │  NB_Bronze_To_Silver (Python o SQL)
     ▼
LH_Wind_Power_Silver  ←─── Tabella: wind_power (enriched)
     │
     │  NB_Silver_To_Gold
     ▼
LH_Wind_Power_Gold
     ├── fact_wind_power
     ├── dim_date
     ├── dim_time
     ├── dim_turbine
     └── dim_operational_status
          │
          │  DirectLake / Import
          ▼
     Semantic Model (Power BI)
          │
          ├── RPT_Wind_Turbine_Power_Analysis
          └── RPT_Wind_Turbine_Direction_Analysis
```

---

## Strategia di aggiornamento

Il notebook `NB_Get_Daily_Data_Python` implementa un aggiornamento **incrementale**:

1. Legge il Bronze Lakehouse e identifica la data più recente presente.
2. Calcola `next_date = most_recent_date + 1 giorno`.
3. Scarica il file `{YYYYMMDD}_wind_power_data.csv` dal repository GitHub di riferimento.
4. Converte in Spark DataFrame mantenendo lo schema originale.
5. Appende al Bronze con `write.format("delta").mode("append")`.

Il passaggio Bronze → Silver usa `mode("overwrite")` sull'intera tabella Silver, quindi va eseguito ogni volta che si aggiorna il Bronze. In un setup produttivo si consiglia di migrare a un aggiornamento incrementale via Delta `MERGE`.

---

## Considerazioni di design

**Perché due notebook per Bronze → Silver?**
Il notebook Python usa la DataFrame API, quello SQL usa Spark SQL. Sono equivalenti nel risultato — il secondo è incluso per documentare l'approccio SQL ed è utile come riferimento per chi lavora principalmente con query.

**Perché le chiavi surrogate in Gold sono generate con `row_number()`?**
Le dimension table derivano da `distinct()` sulla tabella Silver, quindi non hanno un ID naturale. `row_number()` su ordinamento deterministico garantisce la stabilità delle chiavi all'interno di una run. Limite noto: un `overwrite` completo della Gold può cambiare i `turbine_id` se cambiano i dati a monte — da gestire con una SCD Type 1 o con chiavi hash in ambienti produttivi.

**Formato Delta per tutte le tabelle**
Delta garantisce transazioni ACID, time travel e schema enforcement — fondamentale per la consistenza dei join nel Semantic Model Power BI in modalità DirectLake.
