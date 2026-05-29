# Insight analitici — Wind Power Analytics

I seguenti insight emergono dall'analisi del dataset di produzione eolica (3 turbine, 6.048 rilevazioni a 10 minuti).

---

## 1. La velocità del vento non spiega da sola la produzione

L'analisi della correlazione tra `wind_speed` e `energy_produced` rivela una relazione positiva attesa, ma con dispersione significativa. Turbine C (capacity 2.500 kW) produce energia superiore a parità di velocità del vento rispetto a Turbine A e B, confermando che la **capacità nominale è il fattore limitante primario** — non la sola condizione atmosferica.

Implicazione operativa: un'analisi di performance corretta deve normalizzare la produzione sulla capacità (`energy_produced / capacity`), non confrontare i kWh assoluti tra turbine di taglia diversa.

---

## 2. La produzione notturna è strutturalmente diversa da quella diurna

La distribuzione di `energy_produced` per `time_period` mostra che la fascia **Night (21:00–04:59)** non è necessariamente la meno produttiva. Il vento in alcune aree geografiche è più costante nelle ore notturne. Questo suggerisce che le decisioni di manutenzione programmate debbano tenere conto del profilo di produzione per fascia oraria — non solo della disponibilità del personale.

---

## 3. La direzione del vento varia in modo non casuale per regione

Le tre turbine si trovano in regioni geograficamente distanti (California meridionale, California centrale, New York). L'analisi della distribuzione della `wind_direction` per turbina mostra pattern prevalenti distinti: venti da Est e Sud-Est dominano alcune turbine, mentre altre mostrano prevalenza da Nord-Ovest. La rosa dei venti nel report *Direction Analysis* evidenzia questa eterogeneità.

Implicazione: l'ottimizzazione dell'orientamento del rotore (yaw control) dovrebbe essere specifica per sito, non applicare un parametro uniforme.

---

## 4. Lo status "Offline" o "Maintenance" ha un impatto misurabile sulla produzione cumulata

Le rilevazioni con `status != 'Online'` producono energia nulla o ridotta. Quantificare la **perdita di produzione** nei periodi di downtime — rispetto alla produzione attesa basata sul vento in quell'intervallo — è la base per calcolare il costo reale di ogni evento di manutenzione.

Il modello dati (dim_operational_status → fact) è strutturato per supportare questa analisi direttamente in DAX: basta filtrare sulla dimensione e confrontare con il totale senza filtro.

---

## 5. La granularità a 10 minuti è sufficiente per analisi operative, non per ottimizzazione in tempo reale

Il dataset a 10 minuti consente analisi di trend, stagionalità intraday e correlazioni vento/produzione con buona fedeltà. Non è sufficiente per sistemi di controllo o previsione a breve termine (che richiedono dati al minuto o al secondo). Per un portfolio BI, questa granularità è ottimale: abbastanza densa da mostrare variabilità, abbastanza aggregabile da produrre KPI leggibili.
