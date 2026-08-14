# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This is a graduate research project (Pós-Graduação em IA Aplicada, UniSENAI) analyzing long-term salinity (TDS) trends in wastewater at the Los Angeles–Glendale Water Reclamation Plant (LAGWRP). It is not a software application — there is no build/lint/test tooling yet. The deliverables are: (1) a data-science pipeline (not yet written) and (2) a LaTeX scientific article in `Artigo/`. There is no git repository initialized in this directory yet.

## Governance documents — read before doing any work

Two documents in the repo root define mandatory process rules for this project. Read them before starting any non-trivial task:

- **`Prompt — Manutenção contínua do artigo científico do Projeto Aplicado.md`** — the article (`Artigo/template.tex`) is a "living document." Any time an experiment, analysis, or methodological decision is produced, evaluate whether `Artigo/` needs to be updated *in the same execution*, not deferred to the end. Never invent results, metrics, references, or conclusions — a pending section stays marked pending rather than being filled with fabricated content. Distinguish clearly between (A) proven results, (B) executed methodological decisions, and (C) hypotheses/future work — only (A) and (B) go into the article as fact.
- **`plano_projeto_TDS.md`** — the actual, current execution plan (supersedes `prompt_planejamento_TDS.md`, which was the original prompt that produced it). This is the source of truth for: project objectives, data schema, the methodology battery, script structure, and open decisions. Consult it before writing any pipeline code — do not re-derive the plan from scratch.

`GOVERNANCA_DOCUMENTACAO_TEMPLATE.md` is a generic reusable template for software-project doc governance (SECURITY.md, DECISOES_ARQUITETURA.md, etc.) — it does not describe this repo's actual state and is not currently wired into this project's workflow.

## Data

- Raw data source: `Los_Angeles_Reclamation_Plant_2026_additional_data2.xlsx`, an eSMR (Electronic Self-Monitoring Report) export from the California Water Boards portal, one row per measurement. Expected to be split into `TDS.csv`, `Chloride.csv`, `BOD.csv`, `Ammonia.csv` (not present in the repo yet — check before assuming they exist).
- CSV format when produced: separator `;`, decimal `,` (Excel regional export) — read with `sep=';', decimal=','`.
- Key columns: `Location; Parameter; Analytical Method; Calculated Method; Qual; Result; Units; MDL; ML; RL; Sampling Date; ...; Latitude; Longitude; Receiving Water Body`.
- `Location` values `EFF-001` (pre-2012) and `EFF-001A` (after) are the **same physical point** (plant effluent) — must be unified into one series. `R-4`, `R-7`, `RSW-650`, `RSW-654` are receiving-water monitoring points (LA River), not effluent — context only, not part of the primary analysis.
- Filter to `Units == 'mg/L'` for concentration analysis (`lb/day` is mass loading, secondary). The `Calculated Method == "Monthly Average (Mean)"` rows are the pre-aggregated canonical monthly series to build the pipeline from — raw per-sample rows have wildly uneven frequency across parameters.
- BOD has `Qual == 'ND'` (non-detect, blank `Result`) rows whose treatment is an open, project-significant decision (5 options analyzed in `plano_projeto_TDS.md` §1.3) — do not silently pick one; surface the options with real counts when building the preprocessing script.
- `projeto_aplicado_v1 (1).ipynb` is an old/abandoned notebook — explicitly **not** to be reused or refactored from; the pipeline is being built from scratch per the current plan.

## Planned pipeline structure (from `plano_projeto_TDS.md` §4 — not yet implemented)

```
script_00_preprocessamento.py         # builds the canonical merged monthly dataset from the 4 CSVs
script_01_mann_kendall_theilsen.py    # classical trend stats (Mann-Kendall, Sen's slope, Theil-Sen, OLS)
script_02_arima_sarima.py             # STL decomposition + ARIMA/SARIMA
script_03_random_forest_gridsearch.py # tree-based, CPU
script_04_xgboost_lightgbm.py         # tree-based, GPU-capable (tree_method='hist', device='cuda')
script_05_prophet_bayesiano.py        # Prophet + Bayesian regression (uncertainty-aware for long extrapolation)
```

The methodology scripts are independent (only depend on the script_00 output) and are meant to run in parallel. Each script forecasts TDS at **+10, +15, and +20 years** from the last observed data point, and appends one row (never overwrites others) to `resultados_comparacao.csv`/`.json` with: RMSE/MAE/R² on holdout, trend (mg/L/year) with p-value, and point forecast + 90% CI for each horizon.

GPU (RTX 4060 Ti 16GB, CUDA) is only worth enabling for XGBoost/LightGBM (native CUDA support) and optionally a JAX/Numpyro-backed Bayesian regression — the other methods are lightweight enough that CPU is sufficient given the small dataset (~180 monthly points over ~15 years).

## The article (`Artigo/`)

- `Artigo/template.tex` is the **compilable root file** — the `.tex` files under `Artigo/src/` are `\input`-only fragments and do not compile standalone.
- Fixed include order: `abstract` → `introducao` → `trabalhos-relacionados` → `metodologia` → `resultados` → `conclusao`.
- Compilation cycle: `pdflatex template.tex` → `bibtex template` → `pdflatex template.tex` → `pdflatex template.tex` (run from inside `Artigo/`). Always run the full cycle before considering an article update done, and check the resulting `.log`/PDF for broken refs/citations.
- Bibliography is classic BibTeX (`refs.bib`); currently only 3 placeholder entries (`vaswani2017attention`, `karimi2024employee`, `bai2020industry`) — replace them with real citations the first time a real source is cited, never invent a DOI/author/title.
- `\color{red} ... \color{black}` marks instructional/placeholder text inline in the `.tex` files; remove the red block once a section is filled with real content.
- Content routing (which file a new piece of information belongs in) is tabulated in `plano_projeto_TDS.md` §2.C — e.g. numeric results/figures/tables → `resultados.tex`, data/methods/experimental setup → `metodologia.tex`, new figures go in `Artigo/images/` with ASCII-only filenames (no spaces/accents) and must actually be referenced from `resultados.tex`, not left orphaned (`matrix-de-confusao.png` is a currently-orphaned image, approved for removal once a real figure replaces it).
- 100% of the article is currently placeholder/instructional text — every section is expected to be replaced (not appended to) as real work lands.

## Reference materials in repo root

`AI_Project_Instructions.pdf` (original assignment from the professor), `Salinidade.pdf` (research summary — currently empty/0 bytes), `TreatmentPlant_Brochure-LAGLEN-FINAL.pdf` (LAGWRP institutional context). The Nature Sustainability (2020) article is the professor-mandated anchor reference for interpreting why TDS may be rising; other supporting sources are listed in `plano_projeto_TDS.md` §6.
