# Data Dictionary — Wind Power Analytics

## Tabella raw: `wind_power_data.csv` (Bronze)

Dataset originale di produzione eolica. 6.048 righe, granularità 10 minuti per turbina.

| Colonna | Tipo | Descrizione | Valori esempio |
|---------|------|-------------|----------------|
| `production_id` | INT | Identificatore univoco della misura | 1, 2, 3, … |
| `date` | DATE | Data della rilevazione (formato `YYYY-MM-DD`) | 2024-06-01 |
| `time` | STRING | Ora della rilevazione (formato `HH-MM-SS`, separatore `-`) | 00-00-00, 00-10-00 |
| `turbine_name` | STRING | Nome della turbina | Turbine A, B, C |
| `capacity` | INT | Capacità nominale installata in kW | 2200, 2000, 2500 |
| `location_name` | STRING | Nome del sito di installazione | Location 1, 2, 3 |
| `latitude` | FLOAT | Latitudine geografica del sito | 34.0522 |
| `longitude` | FLOAT | Longitudine geografica del sito | -118.2437 |
| `region` | STRING | Regione di appartenenza | Region A, B, C |
| `status` | STRING | Stato operativo della turbina al momento della rilevazione | Online, Offline, Maintenance |
| `responsible_department` | STRING | Dipartimento responsabile della turbina | Operations |
| `wind_speed` | FLOAT | Velocità del vento in m/s | 18.44936 |
| `wind_direction` | STRING | Direzione del vento (rosa dei venti) | N, NE, E, SE, S, SW, W, NW |
| `energy_produced` | FLOAT | Energia prodotta nell'intervallo in kWh | 1786.91843 |

---

## Tabella Silver: `wind_power` (LH_Wind_Power_Silver)

Estende la tabella Bronze con colonne derivate da data e ora. Tutti i campi raw sono preservati.

| Colonna aggiunta | Tipo | Derivazione |
|-----------------|------|-------------|
| `day` | INT | `DAY(date)` |
| `month` | INT | `MONTH(date)` |
| `quarter` | INT | `QUARTER(date)` |
| `year` | INT | `YEAR(date)` |
| `time` | STRING | Formato corretto: `HH:MM:SS` (il separatore `-` diventa `:`) |
| `hour_of_day` | INT | `SUBSTRING(time, 1, 2)` |
| `minute_of_hour` | INT | `SUBSTRING(time, 4, 2)` |
| `second_of_minute` | INT | `SUBSTRING(time, 7, 2)` |
| `time_period` | STRING | Fascia oraria: Morning (5–11), Afternoon (12–16), Evening (17–20), Night (altrimenti) |

---

## Tabelle Gold — Star Schema (LH_Wind_Power_Gold)

### `fact_wind_power`

Tabella dei fatti. Granularità: una riga per ogni rilevazione di produzione.

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| `production_id` | INT | PK della misura |
| `date_id` | DATE | FK → `dim_date.date_id` |
| `time_id` | STRING | FK → `dim_time.time_id` |
| `turbine_id` | INT | FK → `dim_turbine.turbine_id` |
| `status_id` | INT | FK → `dim_operational_status.status_id` |
| `wind_speed` | FLOAT | Velocità vento in m/s |
| `wind_direction` | STRING | Direzione vento |
| `energy_produced` | FLOAT | Energia prodotta in kWh |

### `dim_date`

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| `date_id` | DATE | PK — data della rilevazione |
| `day` | INT | Giorno del mese |
| `month` | INT | Mese (1–12) |
| `quarter` | INT | Trimestre (1–4) |
| `year` | INT | Anno |

### `dim_time`

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| `time_id` | STRING | PK — ora in formato HH:MM:SS |
| `hour_of_day` | INT | Ora (0–23) |
| `minute_of_hour` | INT | Minuto (0–59) |
| `second_of_minute` | INT | Secondo (0–59) |
| `time_period` | STRING | Fascia: Morning, Afternoon, Evening, Night |

### `dim_turbine`

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| `turbine_id` | INT | PK surrogate (generato da `row_number()`) |
| `turbine_name` | STRING | Nome turbina |
| `capacity` | INT | Capacità nominale in kW |
| `location_name` | STRING | Nome sito |
| `latitude` | FLOAT | Latitudine |
| `longitude` | FLOAT | Longitudine |
| `region` | STRING | Regione geografica |

### `dim_operational_status`

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| `status_id` | INT | PK surrogate (generato da `row_number()`) |
| `status` | STRING | Stato operativo: Online, Offline, Maintenance |
| `responsible_department` | STRING | Dipartimento responsabile |

---

## Note sulla qualità dei dati

- `wind_speed` e `energy_produced` sono arrotondati a 2 decimali nel passaggio Bronze → Silver.
- Il campo `time` nel raw usa `-` come separatore (es. `00-10-00`) e viene normalizzato a `:` (es. `00:10:00`) in Silver.
- Le chiavi surrogate (`turbine_id`, `status_id`) sono generate via `row_number()` su ordinamento deterministico — stabili all'interno di un singolo run ma da non considerare persistenti tra re-elaborazioni complete.
- Dataset fonte: [mikailaltundas/datasets-for-training](https://github.com/mikailaltundas/datasets-for-training/tree/main/wind-power-dataset)
