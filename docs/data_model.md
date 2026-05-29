# Data Model — Star Schema Gold

## Struttura

Il Gold Lakehouse implementa uno **star schema** con 1 fact table e 4 dimension table, tutte in formato Delta Lake.

```
                    ┌────────────────────┐
                    │     dim_date       │
                    ├────────────────────┤
                    │ date_id  (PK) DATE │
                    │ day            INT │
                    │ month          INT │
                    │ quarter        INT │
                    │ year           INT │
                    └────────┬───────────┘
                             │ 1
                             │
┌──────────────────┐      N  │  N  ┌────────────────────┐
│   dim_turbine    │   ┌─────▼─────┴──┐   dim_time       │
├──────────────────┤   │fact_wind_power│  ├────────────────────┤
│ turbine_id (PK)  │◀──│ production_id │  │ time_id  (PK)  STR │
│ turbine_name     │1  │ date_id   (FK)│N │ hour_of_day    INT │
│ capacity         │   │ time_id   (FK)│──▶minute_of_hour INT │
│ location_name    │   │ turbine_id(FK)│  │ second_of_min  INT │
│ latitude         │   │ status_id (FK)│  │ time_period    STR │
│ longitude        │   │ wind_speed    │  └────────────────────┘
│ region           │   │ wind_direction│
└──────────────────┘   │ energy_produc.│  ┌────────────────────┐
                       └──────┬────────┘  │dim_operational_    │
                              │ N         │status              │
                              └──────────▶├────────────────────┤
                                       1  │ status_id  (PK) INT│
                                          │ status         STR │
                                          │ responsible_dept STR│
                                          └────────────────────┘
```

---

## Tabelle

### `fact_wind_power`

- **Granularità:** una riga per rilevazione (ogni 10 minuti per turbina)
- **Cardinalità:** ~6.048 righe nel dataset iniziale, crescita incrementale
- **Misure:** `wind_speed`, `wind_direction`, `energy_produced`

```
production_id  INT      -- PK
date_id        DATE     -- FK → dim_date.date_id
time_id        STRING   -- FK → dim_time.time_id
turbine_id     INT      -- FK → dim_turbine.turbine_id
status_id      INT      -- FK → dim_operational_status.status_id
wind_speed     DOUBLE   -- m/s, arrotondato a 2 decimali
wind_direction STRING   -- N, NE, E, SE, S, SW, W, NW
energy_produced DOUBLE  -- kWh, arrotondato a 2 decimali
```

### `dim_date`

- **Granularità:** un valore per data distinta
- **Utilizzo:** filtri per giorno / mese / trimestre / anno nei report

```
date_id   DATE    -- PK
day       INT
month     INT     -- 1–12
quarter   INT     -- 1–4
year      INT
```

### `dim_time`

- **Granularità:** un valore per slot temporale distinto (HH:MM:SS)
- **Utilizzo:** analisi per fascia oraria (`time_period`) e hour_of_day

```
time_id          STRING  -- PK, formato HH:MM:SS
hour_of_day      INT     -- 0–23
minute_of_hour   INT     -- 0, 10, 20, 30, 40, 50
second_of_minute INT     -- 0 (dataset a granularità 10 min)
time_period      STRING  -- Morning / Afternoon / Evening / Night
```

Definizione fasce:

| time_period | Range ore |
|-------------|-----------|
| Morning | 05:00 – 11:59 |
| Afternoon | 12:00 – 16:59 |
| Evening | 17:00 – 20:59 |
| Night | 21:00 – 04:59 |

### `dim_turbine`

- **Granularità:** una riga per combinazione unica (turbine_name, capacity, location, lat, lon, region)
- **Cardinalità:** 3 record (Turbine A, B, C)
- **Nota:** `turbine_id` è una chiave surrogate generata da `row_number()`

```
turbine_id     INT     -- PK surrogate
turbine_name   STRING  -- Turbine A / B / C
capacity       INT     -- kW: 2200 / 2000 / 2500
location_name  STRING  -- Location 1 / 2 / 3
latitude       DOUBLE
longitude      DOUBLE
region         STRING  -- Region A / B / C
```

Dati di riferimento:

| turbine_name | capacity (kW) | region | location |
|-------------|---------------|--------|----------|
| Turbine A | 2200 | Region A | Location 1 (34.05, -118.24) |
| Turbine B | 2000 | Region B | Location 2 (36.78, -119.42) |
| Turbine C | 2500 | Region C | Location 3 (40.71, -74.01) |

### `dim_operational_status`

- **Granularità:** una riga per combinazione (status, responsible_department)
- **Cardinalità:** stimata 1–3 record

```
status_id              INT    -- PK surrogate
status                 STRING -- Online / Offline / Maintenance
responsible_department STRING -- es. Operations
```

---

## Relazioni nel Semantic Model (Power BI)

| Relazione | Cardinalità | Direzione filtro |
|-----------|-------------|-----------------|
| fact → dim_date | Many-to-One | Singola (dim → fact) |
| fact → dim_time | Many-to-One | Singola (dim → fact) |
| fact → dim_turbine | Many-to-One | Singola (dim → fact) |
| fact → dim_operational_status | Many-to-One | Singola (dim → fact) |

---

## Misure DAX principali

Le misure sono definite nel Semantic Model collegato al Gold Lakehouse.

| Misura | Formula (semplificata) | Scopo |
|--------|------------------------|-------|
| `Total Energy Produced` | `SUM(fact_wind_power[energy_produced])` | KPI principale di produzione |
| `Avg Wind Speed` | `AVERAGE(fact_wind_power[wind_speed])` | Condizione atmosferica media |
| `Energy per Turbine` | `DIVIDE([Total Energy Produced], DISTINCTCOUNT(fact_wind_power[turbine_id]))` | Efficienza per turbina |
| `% Energy by Region` | `DIVIDE([Total Energy Produced], CALCULATE([Total Energy Produced], ALL(dim_turbine[region])))` | Quota regionale |
| `Avg Energy by Time Period` | `AVERAGEX(VALUES(dim_time[time_period]), [Total Energy Produced])` | Produzione media per fascia oraria |

> Le formule esatte sono visibili nel Semantic Model su Fabric. Le precedenti sono semplificazioni a scopo documentativo.
