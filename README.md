Language / Idioma: **English** | [Português](README.pt-br.md)

# TDS Trend & Forecast — LAGWRP

Graduate applied-AI project (Pós-Graduação em IA Aplicada, UniSENAI) analyzing long-term salinity (TDS — Total Dissolved Solids) trends in wastewater at the **Los Angeles–Glendale Water Reclamation Plant (LAGWRP)**, and forecasting TDS 10, 15 and 20 years ahead.

## Motivation

Conventional wastewater treatment relies on microbial communities to remove organic matter (BOD) and convert ammonia to nitrate. High salinity (high TDS) can inhibit these biological processes, reducing treatment efficiency. In regions like Los Angeles, water-conservation measures reduce indoor water use, which can unintentionally raise wastewater salinity — the same mass of salts enters the system in a smaller volume of water.

This project:
1. Determines whether TDS concentrations increased over a ~15-year period, quantifying the rate of change.
2. Builds predictive models forecasting TDS 10, 15 and 20 years ahead from the last observed data point.
3. Investigates the correlation between TDS and two treatment-performance indicators: Ammonia (nitrification) and BOD (organic matter removal).
4. Discusses findings in the context of Los Angeles water-conservation practices and infrastructure/environmental-management implications, anchored on the mandated *Nature Sustainability* (2020) reference on rising wastewater salinity.

## Data

Source: eSMR (Electronic Self-Monitoring Report) export from the California Water Boards portal — one row per measurement, covering TDS, Chloride, Ammonia and BOD at the plant effluent (`EFF-001`/`EFF-001A`, unified into one physical monitoring point) and secondary receiving-water points (contextual only).

Canonical monthly series: `Location ∈ {EFF-001, EFF-001A}`, `Calculated Method == "Monthly Average (Mean)"`, `Units == "mg/L"`. Period: **February 2011 – March 2026 (182 months)**.

**BOD non-detect (ND) handling:** 65% of BOD monthly averages are reported as non-detect by the utility, with a constant detection limit (MDL) of 3.0 mg/L across the whole period. Rather than picking a single ND treatment, three parallel canonical datasets are built and carried through the correlation analysis (the only part of the battery sensitive to this choice — see below):
- `dataset_canonico_bod_mdl2.csv` — ND → MDL/2 (1.5 mg/L)
- `dataset_canonico_bod_zero.csv` — ND → 0
- `dataset_canonico_bod_ros.csv` — ND → ROS/Helsel estimate (2.517 mg/L, data-driven — see `script_00b_analise_censura_bod.py`)

The ROS/Helsel value (Dataset F) is the statistically best-grounded of the three (probability-plot regression r=0.677, p=1.1e-9) but, like A and B, still substitutes a single value across all 118 ND months — the observations are indistinguishable ("< 3.0"), so no method recovers real month-to-month variation within the ND months; this is a data limitation, not an implementation gap. The TDS↔BOD correlation result (null) is the same across all three treatments. See `scripts/script_00b_analise_censura_bod.py` and `results/` for the full rationale, the raw-data checks, and the numbers behind this decision.

## Methodology (battery of methods)

Each method is run independently, in parallel, on both ND-treatment datasets, forecasting TDS at +10, +15 and +20 years from the last observed point:

| Script | Method |
|---|---|
| `script_00_preprocessamento.py` | Builds the canonical monthly datasets from the 4 raw CSVs |
| `script_01_mann_kendall_theilsen.py` | Mann-Kendall + Sen's slope, Theil-Sen, OLS — **implemented** |
| `script_02_arima_sarima.py` | SARIMA — **implemented** |
| `script_03_random_forest_gridsearch.py` | Feature-engineering utilities shared by `script_10`/`script_14`/`script_31` (no longer a standalone method — see D-73) |
| `script_05_prophet_bayesiano.py` | Prophet — **implemented** |
| `script_06_correlacao_tds_amonia_bod.py` | TDS↔Ammonia and TDS↔BOD correlation (raw + detrended + lagged) — **implemented** |
| `script_07_analise_estrutura_serie.py` | Seasonality strength, ADF/KPSS stationarity, Chow/Pettitt/CUSUM structural-break tests — **implemented** |
| `script_08_baselines.py` | Naive baseline — **implemented** |
| `script_10_detrend_arvore.py` | OLS trend + RF on the residual (fixes tree extrapolation saturation) — **implemented** |
| `script_14_diagnostico_residuos.py` | Ljung-Box/Shapiro-Wilk/ARCH residual diagnostics of the 3 strongest candidates — **implemented** |
| `script_15_sintese_final.py` | Consolidated metrics table + forecast figure for all 7 methods (no recommended winner — D-73) — **implemented** |

**Status: project complete.** `script_00` through `script_15` are implemented and validated — **7 forecasting methods** (Mann-Kendall/Sen, Theil-Sen, OLS, SARIMA, Prophet, naive, Detrend+RF), the structural-diagnostics pass, correlation analysis, residual diagnostics, and a literature-grounded final synthesis (all four project objectives addressed). Every forecasting method reports MASE, sMAPE, 5-fold expanding-window CV and rolling-origin backtest (`utils/validacao_utils.py`), not just a single 24-month holdout.

**D-73 (2026-10-15): the battery was reduced from 15 to these 7 methods**, matching exactly the methods an external manuscript review cited with results (it reframed the forecasting models as "auxiliary checks on the difficulty of prediction," not a source of a recommended long-horizon forecast). STL's standalone trend, plain Random Forest, Bayesian regression, seasonal-naive/ETS/Theta, Detrend+XGBoost, and the SARIMA+Prophet hybrid — all part of the original 15-method battery — moved to `scripts/bateria_estendida/` (local only); none of their results changed, they're just no longer the article's reported core. See `docs/adr/0001`–`0003` for the decision trail, including why this also meant dropping the "recommended finalist" framing entirely (a hybrid of two methods was one of the two finalists; without it, a single remaining "finalist" would contradict the project's own "not a single winner" comparison criterion).

A wider screening pass (XGBoost, LightGBM, SVR, Gaussian Process, SARIMAX with Chloride, LSTM, state-space, GAM, quantile regression, intervention analysis, a zero-shot foundation model, and PDSI-covariate retraining) was also tested during development as methodological triage — none of it changed the core conclusions, so it's kept locally in `scripts/bateria_estendida/` (gitignored) rather than in the public article/repo.

**Notable findings:** the **naive baseline has the lowest MASE of the entire 7-method battery** on the 24-month holdout (0.436), with **Detrend+RF a close second** (0.441) — and, unlike plain Random Forest (kept locally — saturates at 704.3 mg/L for all three horizons), Detrend+RF's long-horizon forecast grows monotonically instead of saturating (743.5 → 762.2 → 780.9 mg/L at +10/+15/+20y), directly fixing the tree-extrapolation limitation documented earlier. See `results/resultados_comparacao.csv`, `results/figures/`, and `notebooks/notebook.ipynb` for the full discussion.

**GPU:** confirmed working on this machine's RTX 4060 Ti for the extended-battery XGBoost script (`tree_method="hist", device="cuda"`) — not needed for the core public battery, which is CPU-only.

## How to run

Use a dedicated virtual environment (`.venv/`, git-ignored) to keep this project's dependencies isolated from the rest of the machine:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python scripts/script_00_preprocessamento.py
python scripts/script_01_mann_kendall_theilsen.py
python scripts/script_02_arima_sarima.py
python scripts/script_05_prophet_bayesiano.py
python scripts/script_06_correlacao_tds_amonia_bod.py
python scripts/script_07_analise_estrutura_serie.py
python scripts/script_08_baselines.py
python scripts/script_10_detrend_arvore.py
python scripts/script_14_diagnostico_residuos.py
python scripts/script_15_sintese_final.py

# causal/mechanism investigation (see section below)
python scripts/script_16_reconstrucao_vazao.py
python scripts/script_17_matriz_sensibilidade.py
python scripts/script_18_pdsi_regimes.py
python scripts/script_19_wrtds.py
python scripts/script_20_balanco_massa.py
python scripts/script_21_cenarios.py
python scripts/script_28_ladwp_tds_origem.py
python scripts/script_31_testes_robustez_avancados.py
```

Extended screening battery (local only, gitignored — not part of the public repo): `python scripts/bateria_estendida/script_XX_....py`.

`script_00` generates `dataset_canonico_bod_mdl2.csv`, `dataset_canonico_bod_zero.csv` and `dataset_canonico_bod_ros.csv` in `data/processed/`. `script_01` fits the TDS trend (Mann-Kendall/Sen, Theil-Sen, OLS); `script_02` fits SARIMA (grid search by AIC); `script_03` is now just a feature-engineering utility module (no CLI entry point — `script_10`/`script_14`/`script_31` import its `carregar_serie_tds`/`construir_features`/`FEATURES`); `script_05` fits Prophet; `script_06` computes the TDS↔Ammonia/BOD correlations; `script_07` runs the structural diagnostics (seasonality strength, ADF/KPSS, Chow/Pettitt/CUSUM) that inform whether seasonal terms are worth it; `script_08` fits the naive baseline; `script_10` fits OLS trend + Random Forest on the residual. Every method script also runs `utils/validacao_utils.py`'s 5-fold expanding-window CV and rolling-origin backtest (+3/+5 years), and appends MASE/sMAPE/CV/backtest columns alongside the existing holdout metrics to `results/resultados_comparacao.csv`/`.json`, plus regenerates its figure in `results/figures/`. `script_16` reconstructs effluent flow; `script_17` runs the 9-item data-treatment sensitivity matrix; `script_18` downloads and tests NOAA's PDSI drought index against the TDS cycles; `script_19`/`script_20`/`script_21` are WRTDS, mass balance and climate scenarios — see the "Robust data treatment and expanded battery" section below for each one's results.

## Experiment tracking (MLflow)

Runs are tracked locally with [MLflow](https://mlflow.org/) — no cloud, no account. Tracking metadata lives in a local SQLite file (`mlflow.db`) and artifacts (figures, etc.) in `mlruns/`, both git-ignored. `utils/experiment_tracking.py` provides the shared helpers every script uses: `iniciar_run()` opens a run, logs params/seed/train-holdout window and execution time; `logar_metricas()`/`logar_linha_resultado()` log metrics; `logar_artefatos()` logs files; `exportar_para_resultados_csv()` exports chosen runs back into `results/resultados_comparacao.csv`, replacing only that method's row. `results/resultados_comparacao.csv` stays the lean source used by the notebook and dashboard — MLflow is the fuller experiment history alongside it (including discarded attempts).

All of `script_01`, `script_02`, `script_05`, `script_07`, `script_08` and `script_10` now open one MLflow run per method (or diagnostic pass). To inspect runs:

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

## Project structure

```
├── data/
│   ├── raw/              # eSMR (TDS/Chloride/Ammonia/BOD.csv, xlsx), PDSI raw, comparator plants
│   └── processed/        # canonical datasets, flow series, PDSI series, LADWP extracts
├── scripts/              # script_00 … script_21, script_28, script_31 (+ script_00b) — core/public battery
│   └── bateria_estendida/ # wider screening battery — local only, gitignored
├── utils/
│   ├── paths.py          # canonical paths (raw/processed/result/figure)
│   ├── experiment_tracking.py
│   └── validacao_utils.py
├── results/
│   ├── resultados_comparacao.csv / .json
│   ├── *_resultados.* / tabela_sintese_final.csv / comparacao_pdsi_*
│   └── figures/          # PNGs from the pipeline
├── notebooks/            # didactic notebook.ipynb
├── README.md / README.pt-br.md / CLAUDE.md / requirements.txt
```

Local support material (LaTeX article, execution plan, process prompts, decision logs, PDFs) may exist on disk but is **not** part of the public repository.

## Results

**TDS trend (script_01, classical statistics):** all three methods agree on a statistically significant upward trend of 3.7–3.9 mg/L/year (p < 0.01). See `results/figures/tendencia-tds.png`, `results/resultados_comparacao.csv`, and `notebooks/notebook.ipynb` for the full table, forecast figure, and discussion (including the honest limitation that a simple linear trend underperforms on the 24-month holdout — negative R² — even while correctly identifying the long-term direction).

**SARIMA (script_02):** its best AIC order has no explicit drift term, so its implied trend (10.4 mg/L/year, derived from the forecast path) is notably steeper than the classical methods and its 90% CI already includes negative values by +15 years — the expected, documented fragility of extrapolating SARIMA far beyond the ~15-year training history. STL's own standalone deseasonalized trend (2.9 mg/L/year, consistent with §3.a) is no longer part of the core battery (D-73) — kept locally (`scripts/bateria_estendida/script_33_stl_tendencia.py`). See `results/figures/sarima-tds.png`, `results/resultados_comparacao.csv`, and `notebooks/notebook.ipynb`.

**Prophet (script_05):** correctly detects the historical trend (3.81 mg/L/year, p < 0.0001) via its own trend decomposition, but its extrapolated forecast actually **decreases** with horizon (636.9 → 604.8 mg/L from +10 to +20 years) — its automatic changepoint detection picked up a recent local deceleration and extrapolates that instead of the 15-year average. Reported as a genuine finding, not smoothed over. Plain Random Forest and Bayesian regression — both part of the original battery — are no longer in the core (D-73): Random Forest's forecast saturates at 704.3 mg/L across all three horizons (trees can't extrapolate beyond the training range); Bayesian regression confirmed the classical trend (3.74 mg/L/year, 99.5–99.9% posterior probability of a positive trend) with a smoothly growing 90% CI, but lost significantly against naive in a Diebold-Mariano test (see "Robustness" below) — both kept locally in `scripts/bateria_estendida/`. See `results/tabela_sintese_final.csv`, `results/figures/sintese-final-metodos.png`, and `notebooks/notebook.ipynb` for the full comparison table and discussion.

**Bottom line across the 7-method core battery:** the classical/statistical methods (Mann-Kendall/Sen, Theil-Sen, OLS) converge on a consistent, statistically significant upward TDS trend of 3.7–3.9 mg/L/year (p < 0.01). SARIMA and Prophet diverge in opposite directions when extrapolating. No method achieves positive holdout R² — naive has the single lowest holdout MASE (0.436) of the whole battery. See "Robustness and overfitting battery" below for why none of this is read as a confident long-horizon forecast.

**Structural diagnostics (script_07):** seasonality is weak (Fs=0.25, below the 0.64 literature reference threshold) — not assumed by default, tested. ADF rejects the unit-root null and KPSS fails to reject the stationarity null, both consistent with a trend-stationary process rather than a random walk. Chow (breakpoint ~2012, coinciding with the EFF-001→EFF-001A code switch), Pettitt (change detected 2014-04, inside the 2012-2016 California drought window) and CUSUM all confirm the series is not homogeneous over the full period — reinforcing the existing caution about extrapolating far beyond the training history.

**Honest validation framework + baselines (script_08, `utils/validacao_utils.py`):** every method now reports MASE, sMAPE, 5-fold expanding-window CV, and rolling-origin backtest (+3/+5 years) alongside the original 24-month holdout — not just a single train/test split. The core battery's only mandatory baseline is now naive (D-73 — seasonal-naive/ETS/Holt-Winters/Theta moved to `scripts/bateria_estendida/script_36_baselines_estendidos.py`), and it still has **the lowest holdout MASE of the entire 7-method battery** (0.436). This doesn't undercut the trend-focused methods — naive's forecast is a flat line, capturing no long-term trend at all — but it's a genuine, reported finding: on this series' short-horizon fluctuations, no method (sophisticated or not) reliably beats "nothing changes."

**Residual diagnostics (script_14):** Ljung-Box, Shapiro-Wilk and ARCH tests on the in-sample residuals of the 3 strongest candidates (OLS, Detrend+RF, SARIMA — D-73 dropped Bayesian regression and the SARIMA+Prophet hybrid from this comparison along with the rest of the battery) show that **Detrend+RF is the only candidate with neither detectable residual autocorrelation nor conditional heteroscedasticity** — it only fails the normality test (heavier tails, typical of tree models). OLS and SARIMA, with an explicit linear/stochastic functional form, fail at least 2 of the 3 tests, reinforcing that no single method fully captures the series' short-term dynamics.

**Literature comparison:** Schwabe et al. (2020, 34 Southern California plants, 2013-2017) and Wolfand et al. (2022, same LA River basin the LAGWRP discharges into) both find the same direction of effect — water conservation/reuse increases wastewater/river TDS — as this project found independently. The comparison is deliberately qualitative: neither paper's full text was accessible this session (both paywalled), so no numeric magnitude from either is reproduced without direct verification — only the qualitative direction of the effect, confirmed via genuinely fetched secondary sources (institutional press release, professional-society summary), not invented from a search snippet. See `notebooks/notebook.ipynb` and `results/` for the literature-grounded synthesis.

**Final synthesis (script_15, D-73 — no recommended winner):** the SARIMA+Prophet hybrid was one of two "finalists" recommended by an earlier version of this synthesis, picked for its cautious/conservative 90% CI; it's no longer part of the core battery (see "Status" above). Without it, recommending the one remaining method (Detrend+RF) as a sole "finalist" would contradict the project's own comparison criterion ("not a single winner") — so `script_15` was rewritten to abandon the finalist framing entirely: it now just reports MASE/sMAPE/R²/trend/IC90 for all 7 core methods, sorted by holdout MASE, with naive and Detrend+RF essentially tied at the top (0.436 vs. 0.441) and no method singled out as the recommendation. Bayesian regression, the third candidate considered for a finalist slot before D-73, had already been dropped (D-67) after a dedicated Diebold-Mariano test against naive found it loses significantly (p=0.015) — it's now out of the core battery entirely, not just the finalist label. See `docs/adr/0001`–`0003` for the full decision trail.

The method battery (7 core methods), structural diagnostics, correlation analysis, residual diagnostics, and literature-grounded interpretation are now complete — all four project objectives addressed. `dataset_canonico_bod_ros.csv`, `diagnostico_residuos_resultados.csv/json`, and `tabela_sintese_final.csv` are additional generated outputs from this final phase.

## Robust data treatment and expanded battery (Etapa 3)

Before extending the method battery further, two data-treatment steps were run:

**Flow reconstruction (`script_16_reconstrucao_vazao.py`):** the dataset reports the same parameter in both `mg/L` and `lb/day`, related by `lb/day = mg/L × flow(MGD) × 8.34`. This lets us reconstruct effluent flow, which isn't otherwise in the dataset. Validated two ways: plausibility against the plant's 20 MGD nominal capacity, and cross-parameter consistency (flow derived independently from TDS, Chloride, Ammonia and BOD — measured on the same physical samples — should agree if the pairing is real). **Result: the identity holds** — flow derived from TDS correlates 0.997–0.998 with Chloride/Ammonia (0.87 with BOD, noisier but still strong), averaging ~9.5 MGD (~47% of nominal capacity), all plausible. This unlocked the WRTDS, mass-balance and climate-scenario methods — all implemented, see below.

**9-item data-treatment sensitivity matrix (`script_17_matriz_sensibilidade.py`):** run *before* fixing any treatment as default, each variant logged as its own metric set in MLflow. **Findings that qualify the project's central claim** (statistically significant TDS upward trend): (1) the trend drops from 3.91 mg/L/yr (p=0.0056, full series) to 0.84 mg/L/yr (p=0.59, **not significant**) when restricted to the EFF-001A-only period (2012–2026, 170/182 months) — the 12 early EFF-001 months carry disproportionate weight; (2) 3 of 4 MDL/method-change transitions coincide with a statistically significant level shift in mean TDS; (3) none of 4 annual-aggregation variants (15 points) reach significance (p 0.30–0.44); (4) the p-value flips from significant (0.0056) to **not significant** under 2 of 4 autocorrelation corrections (Hamed-Rao p=0.182; pre-whitening p=0.417), while staying significant under the other two (trend-free pre-whitening p=0.0001; Seasonal Kendall p=0.0038). Counter-balancing: raw-sample reaggregation matches the pre-computed monthly average exactly, the trend is stable with/without outlier removal (3.6–3.9 mg/L/yr, all p<0.01), there are no missing months, and log-scale gives the same p-value as expected (Kendall's tau is invariant to monotonic transforms).

**Follow-up investigation — the EFF-001→EFF-001A "break" is not an artifact; the series is cyclical, not monotonic.** A step-dummy OLS (isolating the location-code transition from a linear trend across the full period) found a large, significant apparent level shift (+137 mg/L, p<0.001) and no significant residual linear trend (0.42 mg/L/yr, p=0.75) — but point-by-point inspection shows the transition itself is continuous (580→598 mg/L month to month, same analytical method, same MDL, same coordinates). The "step" is a modeling artifact of fitting one line + one jump to a series that actually moves in regimes: TDS rises 563→808 mg/L (2011–2015, coinciding with California's 2012–2016 drought), falls to 636 mg/L (2019), rises again to 768 mg/L (2022, second drought), then eases off. Reconstructed flow (`script_16`) correlates with TDS in the expected direction (annual r=−0.55, p=0.027) but doesn't fully track the fine shape of the cycle (flow stayed flat through the 2016–2017 TDS drop) — consistent with independent literature evidence (SCSC/DBS&A 2018) that **source-water TDS, not local conservation, explains ~88% of influent TDS variability** in nearby Southern California plants, a variable this dataset does not contain. Full reasoning and evidence are reflected in `results/matriz_sensibilidade_resultados.csv`, `results/figures/`, and the scripts above (decision IDs D-13, D-14, D-29–D-31).

**Drought-cycle test (`script_18_pdsi_regimes.py`) — the cyclical reframing is now empirically confirmed, not just visually plausible.** Rather than trust the shape of TDS alone, the cyclical pattern was tested against an external, independent variable: NOAA's monthly Palmer Drought Severity Index (PDSI) — the same climate index the SCSC/DBS&A (2018) study used to explain TDS across 26 Southern California plants. Three PDSI series were tested (California statewide; Los Angeles climate division; Sacramento division, the State Water Project's source watershed), with 0–36 month lags and p-values corrected for effective degrees of freedom under serial autocorrelation (Pyper & Peterman, 1998). Four converging results: (1) raw cross-correlation is strong and significant even after the DOF correction (r=−0.53 to −0.65 at 3–4 month lag, n_effective ≈ 22–30 of ~180 nominal); (2) changepoints detected in PDSI alone — blind to the TDS dates — land within months of the four observed regime turns (2012, 2015, 2019, 2022); (3) LMG relative-importance decomposition (`TDS ~ lagged PDSI + reconstructed flow`) attributes 68–79% of importance to PDSI across the three series, the same order of magnitude as SCSC's ~88% source-water benchmark; (4) PDSI's coefficient stays highly significant (p<0.0001) even controlling for regime dummies. **Honest caveat:** the detrended (month-to-month) correlation is much weaker and flips sign (r=+0.15 to +0.19) — drought mainly explains each regime's *level*, not its fine-grained wiggle. Declared outcome (of three pre-specified in the test protocol): **PDSI explains the cycles well** — D-14 is now confirmed, not just proposed. Full evidence in `results/pdsi_regimes_resultados.csv` / `.json` and `data/processed/pdsi_*.csv` (decision ID D-37).

**WRTDS — flow normalization (`script_19_wrtds.py`):** with the cyclical pattern confirmed, the question became "is there a trend *underneath* the cycles, once flow is accounted for?" Own implementation (not the R `EGRET` package, no mature Python equivalent): locally-weighted regression (tricube kernel over time/log-flow/season) + flow-normalization. **Result: the raw trend (+0.58%/yr, p=0.0056) drops to −0.13%/yr (p=0.064, not significant)** once flow is normalized out — almost all of the apparent trend is a flow effect. The mandatory circularity check (flow derived from Chloride, independent of TDS) confirms it: only a 0.024 percentage-point/year difference from the TDS-derived version. See `results/wrtds_resultados.csv` / `.json` and `results/figures/wrtds-*.png` (decision ID D-39).

**Mass balance (`script_20_balanco_massa.py`):** models salt load (lb/day) and flow (MGD) separately and derives `TDS = load ÷ (flow × 8.34)`. **Salt load fell −3.20%/yr and flow fell −3.85%/yr (both p<0.0001) — confirms dilution, not more salt entering the system.** Non-circular historical validation (Chloride-derived flow) has R²=0.94; the tautology check (TDS's own derived flow) gives an exact R²=1.000000, as expected from algebraic identity — reported as a check, not a result. Negative finding on record: linearly extrapolating load and flow 20 years out crosses physically implausible flow (negative by +20y) — the direct motivation for the next method. See `results/balanco_massa_resultados.csv` / `.json` and `results/figures/balanco-massa-*.png` (decision ID D-40).

**Climate scenarios (`script_21_cenarios.py`):** replaces the implausible linear extrapolation with a Monte Carlo conditional projection (AR(1) on 1895–2026 historical PDSI + a TDS~PDSI regression). Four scenarios (dry/normal/wet/climate-worsening), physically plausible ranges at +20 years: dry 718 [588, 846] mg/L; climate-worsening 714 [591, 842]; normal 658 [529, 783]; wet 594 [462, 721]. **There is no single number for 2046** — a climate-conditioned range is the honest answer the data supports. See `results/cenarios_resultados.csv` / `.json` and `results/figures/cenarios-pdsi-*.png` (decision ID D-41).

**A wider screening battery (state-space, GAM, quantile regression, intervention analysis, a zero-shot foundation model, and a 5th climate scenario grounded in real Cal-Adapt/RCP-8.5 projections) was also tested — all of it reinforces, from independent angles, that there's no clear residual trend beyond the flow/regime effect, and none of it changed the core conclusions.** Kept locally in `scripts/bateria_estendida/` (gitignored) rather than in the public repo/article.

**Real source-water TDS via 21 years of LADWP reports (`script_28_ladwp_tds_origem.py`, D-54).** The most critical data gap (D-30 — no source-water TDS series, only the indirect PDSI proxy) is now partially filled with real primary-source data: 21 annual LADWP water-quality reports (2004-2024) each publish average TDS by supply source (LA Aqueduct, local wells, and the MWD's three treatment plants — Weymouth, Diemer, Jensen) plus the yearly supply-mix percentage. A weighted source-TDS series was built from this and compared to LAGWRP's annual effluent TDS (14 overlapping years, 2011-2024): **r=0.912 (p=0.000005)** — stronger than the PDSI correlation (D-37, LMG 67-79%). All 21 years (100%, not a sample) were manually verified cell-by-cell against the source PDFs with zero discrepancies. Declared limitations: MWD weight is a simple average across its 3 plants (the real per-plant blend ratio isn't published in any of the 21 reports); the series is annual, not monthly (the reports don't publish a monthly breakdown); it covers only the Los Angeles (LADWP) side of LAGWRP's service area, not Glendale's.

**PDSI as a covariate, and its fine-tuning (bateria estendida, D-56/D-57).** With PDSI already shown to explain the cyclical *regime* (D-37), the direct question remained: does adding it as a covariate also improve *predictive performance*? Methods that accept an exogenous regressor by design were re-trained with PDSI added. **Result: no consistent improvement** — most methods got worse, and only one (XGBoost) kept a real gain under the stricter honest-CV acceptance bar (not just the fixed 24-month holdout). Full numbers kept locally in `results/bateria_estendida/` (decision IDs D-56/D-57).

**Status:** the core battery and the causal investigation (WRTDS, mass balance, scenarios, flow reconstruction, sensitivity matrix, PDSI regimes, LADWP source water) are complete and public. The wider screening battery confirmed and deepened the D-14/D-37 cyclical reframing without changing it, and is kept locally (see D-45–D-50 for each). Decision logs, glossaries, and the LaTeX article live only on the local disk, under `docs_local/` (gitignored) and are **not** part of this public repository. Full commit history and reproducible source at **https://github.com/igorfnogueira/projeto-aplicado**.

## Robustness and overfitting battery (`script_31`)

Before treating any of the above as final, a dedicated battery stress-tested the 3 candidates of the core battery with an explicit trend (OLS, Detrend+RF, SARIMA — D-73 dropped Bayesian regression and the SARIMA+Prophet hybrid along with the rest of the battery) for overfitting and overconfident uncertainty — own `results/testes_robustez_resultados.csv`/`.json`, not touching `resultados_comparacao.csv`.

**IC90 empirical coverage (`script_31`, item 1):** the 90% confidence interval advertised by each method should contain the true value ~90% of the time under cross-validation/backtest — it doesn't. Mann-Kendall/Sen, Theil-Sen and OLS cover only 37–38% (CV) and 27–27% (36/60-month backtest); Detrend+RF, given a calibrated interval via residual bootstrap (same technique already used for SVR in `script_09`, bateria estendida), covers just 27% (CV) and 13–45% (backtest) — the worst of the candidates. SARIMA fares better (75% CV, 80–91% backtest) but still short of nominal, and its CV interval width (~247 mg/L) is roughly 3× wider than the others' (~87–97 mg/L). **All candidates' stated uncertainty is overconfident relative to the honest validation protocol.**

**Diebold-Mariano (`script_31`, item 2):** pairwise forecast-accuracy comparisons (HLN small-sample correction, n=24 holdout months) among the 3 candidates and the naive baseline — a fixed candidate set, independent of any "finalist" list (ADR-0002/D-73: coupling this item to a list of recommended methods made the exact test that motivated D-67, regressao_bayesiana_vs_naive, irreproducible once that method left the battery) — find Detrend+RF significantly different from SARIMA (p=0.044). Against naive, none of OLS, Detrend+RF or SARIMA is significantly different (p=0.81, p=0.15, and OLS p=0.015 — OLS's in-sample fit is close enough to the old Bayesian-regression construction that this reproduces the same D-67 finding under a different method name).

**Out-of-sample residual diagnostics (`script_31`, item 3):** unlike the in-sample picture in `script_14` (where Detrend+RF was the only candidate passing both autocorrelation and heteroscedasticity tests), **all 3 candidates fail the Ljung-Box test on their 24-month holdout residuals** (p=0.024–0.049) — out-of-sample residual autocorrelation that the in-sample diagnostics didn't surface. Shapiro-Wilk and ARCH both pass for every method at this horizon.

**In-sample × CV × holdout RMSE gap (`script_31`, item 4):** Detrend+RF shows the starkest overfitting signature — in-sample RMSE of 19.4 balloons to 76.7 under CV (vs. holdout's 49.8), a ~4× gap the single train/test split would have hidden entirely. OLS and SARIMA show a smaller but still real gap (e.g. SARIMA: 78.0 in-sample → 90.8 CV → 48.4 holdout).

**Leave-one-year-out and "remove the first N years" sweep (`script_31`, item 5/5b):** removing any single year leaves the Mann-Kendall/Theil-Sen trend positive, usually still significant (1.2–5.4 mg/L/yr), except when 2011 or 2012 alone is dropped (not significant, p=0.29–0.45). Cumulatively removing the first N years is more dramatic: the slope **flips sign and significance** as N grows — from +1.2 mg/L/yr (N=1, p=0.45) to −4.2 (N=3, p=0.017, *significant negative*) and −4.6 (N=4, p=0.027, *significant negative*) before collapsing back to ~0 (N=5, p=0.91). The headline "statistically significant upward trend" is **not robust** to how many of the early (2011–2015) years are included.

A separate diagnostic (`script_32`, bateria estendida, local only) checked nested vs. fixed hyperparameters for the tree/kernel methods of the extended battery — nested CV changed CV-MASE by at most ~3.4% at 3–200× more compute, confirming the fixed-hyperparameter shortcut used throughout this project is a safe simplification, not an optimistic bias.

See `results/testes_robustez_resultados.csv`/`.json` and `results/figures/testes-robustez-avancados.png` for the full numbers; `notebooks/notebook.ipynb` discusses these findings alongside the rest of the analysis.

## References

Primary anchor reference: Schwabe et al., *Nature Sustainability* (2020), on rising wastewater salinity linked to water-conservation practices (professor-mandated). Wolfand et al., *ACS ES&T Water* (2022), on the same LA River basin. Antweiler & Taylor, *Environmental Science & Technology* (2008), for the ROS/Helsel censored-data technique used in `script_00b`.
