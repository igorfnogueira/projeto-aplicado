Language / Idioma: **English** | [Português](README.pt-br.md)

# TDS Trend & Forecast — LAGWRP

Graduate applied-AI project (Pós-Graduação em IA Aplicada, UniSENAI) analyzing long-term salinity (TDS — Total Dissolved Solids) trends in wastewater at the **Los Angeles–Glendale Water Reclamation Plant (LAGWRP)**, and forecasting TDS 10, 15 and 20 years ahead.

## Motivation

Conventional wastewater treatment relies on microbial communities to remove organic matter (BOD) and convert ammonia to nitrate. High salinity (high TDS) can inhibit these biological processes, reducing treatment efficiency. In regions like Los Angeles, water-conservation measures reduce indoor water use, which can unintentionally raise wastewater salinity — the same mass of salts enters the system in a smaller volume of water.

This project:
1. Determines whether TDS concentrations increased over a ~15-year period, quantifying the rate of change.
2. Builds predictive models forecasting TDS 10, 15 and 20 years ahead from the last observed data point.
3. Investigates the correlation between TDS and two treatment-performance indicators: Ammonia (nitrification) and BOD (organic matter removal).
4. Discusses findings in the context of Los Angeles water-conservation practices and infrastructure/environmental-management implications, anchored on the mandated *Nature Sustainability* (2020) reference on rising wastewater salinity (full citation to be added to `Artigo/refs.bib` when formally cited in the article).

## Data

Source: eSMR (Electronic Self-Monitoring Report) export from the California Water Boards portal — one row per measurement, covering TDS, Chloride, Ammonia and BOD at the plant effluent (`EFF-001`/`EFF-001A`, unified into one physical monitoring point) and secondary receiving-water points (contextual only).

Canonical monthly series: `Location ∈ {EFF-001, EFF-001A}`, `Calculated Method == "Monthly Average (Mean)"`, `Units == "mg/L"`. Period: **February 2011 – March 2026 (182 months)**.

**BOD non-detect (ND) handling:** 65% of BOD monthly averages are reported as non-detect by the utility, with a constant detection limit (MDL) of 3.0 mg/L across the whole period. Rather than picking a single ND treatment, three parallel canonical datasets are built and carried through the correlation analysis (the only part of the battery sensitive to this choice — see below):
- `dataset_canonico_bod_mdl2.csv` — ND → MDL/2 (1.5 mg/L)
- `dataset_canonico_bod_zero.csv` — ND → 0
- `dataset_canonico_bod_ros.csv` — ND → ROS/Helsel estimate (2.517 mg/L, data-driven — see `script_00b_analise_censura_bod.py`)

The ROS/Helsel value (Dataset F) is the statistically best-grounded of the three (probability-plot regression r=0.677, p=1.1e-9) but, like A and B, still substitutes a single value across all 118 ND months — the observations are indistinguishable ("< 3.0"), so no method recovers real month-to-month variation within the ND months; this is a data limitation, not an implementation gap. The TDS↔BOD correlation result (null) is the same across all three treatments. See `plano_projeto_TDS.md` (§1.3), `script_00b_analise_censura_bod.py`, and `Artigo/src/metodologia.tex` for the full rationale, the raw-data checks, and the real numbers presented before this was decided.

## Methodology (battery of methods)

Each method is run independently, in parallel, on both ND-treatment datasets, forecasting TDS at +10, +15 and +20 years from the last observed point:

| Script | Method |
|---|---|
| `script_00_preprocessamento.py` | Builds the canonical monthly datasets from the 4 raw CSVs |
| `script_01_mann_kendall_theilsen.py` | Mann-Kendall + Sen's slope, Theil-Sen, OLS — **implemented** |
| `script_02_arima_sarima.py` | STL decomposition + ARIMA/SARIMA — **implemented** |
| `script_03_random_forest_gridsearch.py` | Random Forest (CPU) — **implemented** |
| `script_04_xgboost_lightgbm.py` | XGBoost (GPU/CUDA) + LightGBM (CPU) — **implemented** |
| `script_05_prophet_bayesiano.py` | Prophet + Bayesian regression (PyMC/NUTS) — **implemented** |
| `script_06_correlacao_tds_amonia_bod.py` | TDS↔Ammonia and TDS↔BOD correlation (raw + detrended + lagged) — **implemented** |
| `script_07_analise_estrutura_serie.py` | Seasonality strength, ADF/KPSS stationarity, Chow/Pettitt/CUSUM structural-break tests — **implemented** |
| `script_08_baselines.py` | Naive, seasonal naive, ETS/Holt-Winters, Theta baselines — **implemented** |
| `script_09_svr_gp.py` | SVR + Gaussian Process (composite kernel) — **implemented** |
| `script_10_detrend_arvore.py` | OLS trend + RF/XGBoost on the residual (fixes tree extrapolation saturation) — **implemented** |
| `script_11_multivariado_cloreto.py` | SARIMAX(TDS, exog=Chloride) — **implemented** |
| `script_12_hibrido_arima_prophet.py` | SARIMA+Prophet ensemble — **implemented** |
| `script_13_deep_learning.py` | Lightweight LSTM (PyTorch, CPU) — **implemented** |
| `script_14_diagnostico_residuos.py` | Ljung-Box/Shapiro-Wilk/ARCH residual diagnostics of the strongest candidates — **implemented** |
| `script_15_sintese_final.py` | Final consolidated table + finalists forecast figure — **implemented** |

**Status: project complete.** `script_00` through `script_15` are implemented and validated — 21 forecasting methods (10 original + 4 mandatory baselines + 7 additional), the structural-diagnostics pass, correlation analysis, residual diagnostics of the strongest candidates, and a literature-grounded final synthesis (all four project objectives addressed). Every forecasting method reports MASE, sMAPE, 5-fold expanding-window CV and rolling-origin backtest (`validacao_utils.py`), not just a single 24-month holdout.

**Notable findings:** the **naive baseline has the lowest MASE of the entire 21-method battery** on the 24-month holdout (0.44), with **Detrend+RF a close second** (0.44) — and, unlike plain Random Forest, Detrend+RF's long-horizon forecast grows monotonically instead of saturating (743.5 → 762.2 → 780.9 mg/L at +10/+15/+20y), directly fixing the tree-extrapolation limitation documented earlier. **SVR is the first method in the whole battery with positive holdout R²** (0.04). The **Gaussian Process was the worst performer** (MASE 2.03) — its marginal-likelihood fit converged to a short RBF length-scale and reverts to the mean instead of extrapolating, a known GP pitfall, reported as obtained rather than re-tuned to look better. Adding **Chloride as a SARIMAX exogenous regressor** has a significant coefficient but doesn't meaningfully improve holdout RMSE/MASE over the univariate SARIMA. The **SARIMA+Prophet hybrid** beats both individual components on holdout RMSE. The **LSTM did not beat the naive baseline** (MASE 0.69 vs. 0.44), confirming the literature precedent that boosting/classical methods tend to beat lightweight deep learning on short monthly environmental series — tested and reported as a non-winner, not omitted. See `Artigo/src/resultados.tex` for the full discussion.

**GPU:** confirmed working on this machine's RTX 4060 Ti — `xgb.XGBRegressor(tree_method="hist", device="cuda")` fits successfully. LightGBM's pip package, however, is **not** built with GPU support (`device="gpu"` raises "GPU Tree Learner was not enabled in this build"); it runs on CPU as an accepted fallback, exactly as anticipated in the plan.

## How to run

Use a dedicated virtual environment (`.venv/`, git-ignored) to keep this project's dependencies isolated from the rest of the machine:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python script_00_preprocessamento.py
python script_01_mann_kendall_theilsen.py
python script_02_arima_sarima.py
python script_03_random_forest_gridsearch.py
python script_04_xgboost_lightgbm.py
python script_05_prophet_bayesiano.py
python script_06_correlacao_tds_amonia_bod.py
python script_07_analise_estrutura_serie.py
python script_08_baselines.py
python script_09_svr_gp.py
python script_10_detrend_arvore.py
python script_11_multivariado_cloreto.py
python script_12_hibrido_arima_prophet.py
python script_13_deep_learning.py
python script_14_diagnostico_residuos.py
python script_15_sintese_final.py
```

`script_00` generates `dataset_canonico_bod_mdl2.csv`, `dataset_canonico_bod_zero.csv` and `dataset_canonico_bod_ros.csv` in the project root. `script_01` fits the TDS trend (Mann-Kendall/Sen, Theil-Sen, OLS); `script_02` fits STL+trend and SARIMA (grid search by AIC); `script_03` fits a Random Forest (GridSearchCV + TimeSeriesSplit) with recursive multi-step forecasting; `script_04` fits XGBoost and LightGBM the same way, with quantile regression (alpha=0.05/0.95) for the 90% CI; `script_05` fits Prophet and a Bayesian linear regression (PyMC/NUTS — note: this machine has no C++ compiler, so PyTensor falls back to pure Python and sampling takes a few minutes); `script_06` computes the TDS↔Ammonia/BOD correlations; `script_07` runs the structural diagnostics (seasonality strength, ADF/KPSS, Chow/Pettitt/CUSUM) that inform whether seasonal terms are worth it; `script_08` fits the 4 mandatory baselines. Every method script (01-05, 08) also runs `validacao_utils.py`'s 5-fold expanding-window CV and rolling-origin backtest (+3/+5 years), and appends MASE/sMAPE/CV/backtest columns alongside the existing holdout metrics to `resultados_comparacao.csv`/`.json`, plus regenerates its figure in `Artigo/images/`.

## Experiment tracking (MLflow)

Runs are tracked locally with [MLflow](https://mlflow.org/) — no cloud, no account. Tracking metadata lives in a local SQLite file (`mlflow.db`) and artifacts (figures, etc.) in `mlruns/`, both git-ignored. `utils/experiment_tracking.py` provides the shared helpers every script uses: `iniciar_run()` opens a run, logs params/seed/train-holdout window and execution time; `logar_metricas()`/`logar_linha_resultado()` log metrics; `logar_artefatos()` logs files; `exportar_para_resultados_csv()` exports chosen runs back into `resultados_comparacao.csv`, replacing only that method's row. `resultados_comparacao.csv` stays the lean source used by the notebook and article — MLflow is the fuller experiment history alongside it (including discarded attempts), per `plano_projeto_TDS.md` §4.3.

All of `script_01`-`script_05`, `script_07` and `script_08` now open one MLflow run per method (or diagnostic pass). To inspect runs:

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

## Project structure

```
├── TDS.csv / Chloride.csv / Ammonia.csv / BOD.csv   # raw eSMR exports (one sheet per parameter)
├── script_00_preprocessamento.py                     # canonical dataset builder
├── dataset_canonico_bod_mdl2.csv / _bod_zero.csv / _bod_ros.csv  # canonical monthly datasets (generated)
├── validacao_utils.py                                 # MASE/sMAPE/CV/backtest framework, shared by scripts 01-05/08
├── utils/experiment_tracking.py                       # MLflow tracking helpers, shared by all scripts
├── diagnostico_serie_resultados.csv / .json            # script_07 structural-diagnostics output (generated)
├── notebook.ipynb                                     # single project notebook (preprocessing, EDA, methods)
├── Artigo/                                            # LaTeX scientific article (template.tex is the compilable root)
├── plano_projeto_TDS.md                               # source-of-truth execution plan
├── resultados_comparacao.csv / .json                  # method comparison results (21 methods)
├── diagnostico_residuos_resultados.csv / .json         # script_14 residual-diagnostics output (generated)
└── tabela_sintese_final.csv                            # script_15 consolidated table (generated)
```

## Results

**TDS trend (script_01, classical statistics):** all three methods agree on a statistically significant upward trend of 3.7–3.9 mg/L/year (p < 0.01). See `Artigo/src/resultados.tex` and `notebook.ipynb` §3.a for the full table, forecast figure, and discussion (including the honest limitation that a simple linear trend underperforms on the 24-month holdout — negative R² — even while correctly identifying the long-term direction).

**STL + SARIMA (script_02):** STL's deseasonalized trend (2.9 mg/L/year) is consistent with §3.a. SARIMA's best AIC order has no explicit drift term, so its implied trend (10.4 mg/L/year, derived from the forecast path) is notably steeper and its 90% CI already includes negative values by +15 years — the expected, documented fragility of extrapolating SARIMA far beyond the ~15-year training history. See `Artigo/src/resultados.tex` and `notebook.ipynb` §3.b.

**Random Forest (script_03):** best holdout RMSE so far (41.0, vs. 49–51 for the classical methods), but its long-horizon forecast **saturates** exactly as the plan anticipated: +10, +15 and +20 years all converge to the same value (704.3 mg/L), and the implied trend over the first 10 years is even slightly negative — trees cannot extrapolate beyond the value range seen in training. Reported explicitly, not hidden. See `Artigo/src/resultados.tex` and `notebook.ipynb` §3.c.

**XGBoost + LightGBM (script_04):** same structural limitation as Random Forest — both implied trends are negative (-0.91 and -0.51 mg/L/year), the opposite of the real upward trend. XGBoost additionally shows non-monotonic oscillation across horizons (649.6 → 717.6 → 649.6 mg/L at +10/+15/+20 years), a boosting artifact when features go out of the training range. Together, the three tree-based methods make an empirical (not just theoretical) case against relying on trees alone for long-horizon trend extrapolation in this project. See `Artigo/src/resultados.tex` and `notebook.ipynb` §3.c.

**Prophet + Bayesian regression (script_05):** the Bayesian regression confirms the classical trend (3.74 mg/L/year, 99.88% posterior probability of a positive trend) with a smoothly growing 90% CI — the "honest uncertainty" behavior this method was chosen for. Prophet is more surprising: it correctly detects the same historical trend (3.81 mg/L/year, p < 0.0001) via its own trend decomposition, but its extrapolated forecast actually **decreases** with horizon (636.9 → 604.8 mg/L from +10 to +20 years) — its automatic changepoint detection picked up a recent local deceleration and extrapolates that instead of the 15-year average. Reported as a genuine finding, not smoothed over. See `Artigo/src/resultados.tex` §Síntese comparativa for the full 10-method comparison table and discussion.

**Bottom line across all 10 methods:** the five methods with a global linear/statistical fit (Mann-Kendall/Sen, Theil-Sen, OLS, STL+trend, Bayesian regression) converge on a consistent, statistically significant upward TDS trend of 2.9–3.9 mg/L/year (p < 0.01). The tree-based methods fail to extrapolate it; SARIMA and Prophet diverge in opposite directions when extrapolating. No method achieves positive holdout R² — the strongest evidence from this project is the **convergence** of the statistical/Bayesian methods, not any single model's point forecast.

**Structural diagnostics (script_07):** seasonality is weak (Fs=0.25, below the 0.64 literature reference threshold) — not assumed by default, tested. ADF rejects the unit-root null and KPSS fails to reject the stationarity null, both consistent with a trend-stationary process rather than a random walk. Chow (breakpoint ~2012, coinciding with the EFF-001→EFF-001A code switch), Pettitt (change detected 2014-04, inside the 2012-2016 California drought window) and CUSUM all confirm the series is not homogeneous over the full period — reinforcing the existing caution about extrapolating far beyond the training history.

**Honest validation framework + baselines (script_08, `validacao_utils.py`):** every method (01-05, 08) now reports MASE, sMAPE, 5-fold expanding-window CV, and rolling-origin backtest (+3/+5 years) alongside the original 24-month holdout — not just a single train/test split. Against the 4 mandatory baselines (naive, seasonal naive, ETS/Holt-Winters, Theta), the **naive baseline has the lowest holdout MASE of the entire 14-method battery** (0.44). This doesn't undercut the trend-focused methods — naive's forecast is a flat line, capturing no long-term trend at all — but it's a genuine, reported finding: on this series' short-horizon fluctuations, no method (sophisticated or not) reliably beats "nothing changes."

**Residual diagnostics (script_14):** Ljung-Box, Shapiro-Wilk and ARCH tests on the in-sample residuals of the 5 strongest candidates (OLS, Bayesian regression, Detrend+RF, SARIMA, SARIMA+Prophet hybrid) show that **Detrend+RF is the only candidate with neither detectable residual autocorrelation nor conditional heteroscedasticity** — it only fails the normality test (heavier tails, typical of tree models). The four methods with an explicit linear/stochastic functional form fail at least 2 of the 3 tests, reinforcing that no single method fully captures the series' short-term dynamics.

**Literature comparison:** Schwabe et al. (2020, 34 Southern California plants, 2013-2017) and Wolfand et al. (2022, same LA River basin the LAGWRP discharges into) both find the same direction of effect — water conservation/reuse increases wastewater/river TDS — as this project found independently. The comparison is deliberately qualitative: neither paper's full text was accessible this session (both paywalled), so no numeric magnitude from either is reproduced without direct verification — only the qualitative direction of the effect, confirmed via genuinely fetched secondary sources (institutional press release, professional-society summary), not invented from a search snippet. See `Artigo/src/trabalhos-relacionados.tex` and `Artigo/src/resultados.tex` §Comparação com a literatura.

**Final synthesis (script_15):** three complementary finalists are recommended (not a single winner, per the project's own comparison criteria) — **Bayesian regression** (honest, smoothly growing uncertainty), **Detrend+RF** (best holdout MASE among trend-capturing methods + cleanest residuals) and the **SARIMA+Prophet hybrid** (best holdout RMSE among time-series methods, widest/most cautious 90% CI). All three converge on ~760-800 mg/L at +20 years despite using completely different extrapolation mechanisms — that convergence, not any single model's point forecast, is the strongest evidence this project produces.

The method battery (21 methods), structural diagnostics, correlation analysis, residual diagnostics, and literature-grounded interpretation are now complete — all four project objectives addressed. `dataset_canonico_bod_ros.csv`, `diagnostico_residuos_resultados.csv/json`, and `tabela_sintese_final.csv` are additional generated outputs from this final phase.

## Robust data treatment (in progress — awaiting decision)

Per `prompt_tratamento_e_metodos.md`, before extending the method battery further, two data-treatment steps were run:

**Flow reconstruction (`script_16_reconstrucao_vazao.py`):** the dataset reports the same parameter in both `mg/L` and `lb/day`, related by `lb/day = mg/L × flow(MGD) × 8.34`. This lets us reconstruct effluent flow, which isn't otherwise in the dataset. Validated two ways: plausibility against the plant's 20 MGD nominal capacity, and cross-parameter consistency (flow derived independently from TDS, Chloride, Ammonia and BOD — measured on the same physical samples — should agree if the pairing is real). **Result: the identity holds** — flow derived from TDS correlates 0.997–0.998 with Chloride/Ammonia (0.87 with BOD, noisier but still strong), averaging ~9.5 MGD (~47% of nominal capacity), all plausible. This unlocks WRTDS/mass-balance/scenario methods for a future phase, pending approval.

**9-item data-treatment sensitivity matrix (`script_17_matriz_sensibilidade.py`):** run *before* fixing any treatment as default, each variant logged as its own metric set in MLflow. **Findings that qualify the project's central claim** (statistically significant TDS upward trend): (1) the trend drops from 3.91 mg/L/yr (p=0.0056, full series) to 0.84 mg/L/yr (p=0.59, **not significant**) when restricted to the EFF-001A-only period (2012–2026, 170/182 months) — the 12 early EFF-001 months carry disproportionate weight; (2) 3 of 4 MDL/method-change transitions coincide with a statistically significant level shift in mean TDS; (3) none of 4 annual-aggregation variants (15 points) reach significance (p 0.30–0.44); (4) the p-value flips from significant (0.0056) to **not significant** under 2 of 4 autocorrelation corrections (Hamed-Rao p=0.182; pre-whitening p=0.417), while staying significant under the other two (trend-free pre-whitening p=0.0001; Seasonal Kendall p=0.0038). Counter-balancing: raw-sample reaggregation matches the pre-computed monthly average exactly, the trend is stable with/without outlier removal (3.6–3.9 mg/L/yr, all p<0.01), there are no missing months, and log-scale gives the same p-value as expected (Kendall's tau is invariant to monotonic transforms). **Net read: the upward trend is not an obvious artifact of outliers or reaggregation, but is sensitive to the location-code transition, MDL changes, and autocorrelation correction — three converging signals that the naive monthly p-value may overstate confidence.** See `matriz_sensibilidade_resultados.csv` and `notebook.ipynb` §6 for the full table.

**Status: awaiting the user's decision on which treatments to adopt as defaults before proceeding to the expanded method battery (WRTDS, mass balance, scenarios, state-space, GAM, quantile regression, intervention analysis, foundation models) — per explicit instruction in `prompt_tratamento_e_metodos.md`, this is not decided unilaterally.**

## References

Primary anchor reference: Schwabe et al., *Nature Sustainability* (2020), on rising wastewater salinity linked to water-conservation practices (professor-mandated). Wolfand et al., *ACS ES&T Water* (2022), on the same LA River basin. Antweiler & Taylor, *Environmental Science & Technology* (2008), for the ROS/Helsel censored-data technique used in `script_00b`. Full entries in `Artigo/refs.bib`; additional (unverified/inaccessible) sources listed in `plano_projeto_TDS.md` (§6) and `material_apoio_referencias.md`.
