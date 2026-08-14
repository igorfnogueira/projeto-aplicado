"""
Utilitario de rastreamento de experimentos via MLflow (tracking store local,
sem servidor remoto -- plano_projeto_TDS.md secao 4.3).

Cada execucao de um metodo (dentro de um script_0X) abre uma run com
`iniciar_run`, loga hiperparametros/seed/janela de treino como params e tags,
mede o tempo de execucao do bloco automaticamente, e permite logar metricas
(`logar_metricas`/`logar_linha_resultado`) e artefatos (`logar_artefatos`)
dentro do context.

O resultados_comparacao.csv continua sendo a fonte enxuta usada pelo notebook
e pelo artigo -- nao e substituido pelo MLflow, e alimentado por ele via
`exportar_para_resultados_csv`.
"""

from __future__ import annotations

import subprocess
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import mlflow
import pandas as pd

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
MLRUNS_DIR = RAIZ_PROJETO / "mlruns"
MLFLOW_DB = RAIZ_PROJETO / "mlflow.db"
RESULTADOS_CSV_PADRAO = RAIZ_PROJETO / "resultados_comparacao.csv"
RESULTADOS_JSON_PADRAO = RAIZ_PROJETO / "resultados_comparacao.json"
EXPERIMENTO_PADRAO = "tds_lagwrp"

# Backend de tracking local em SQLite (o backend de arquivos puro, "./mlruns",
# entrou em modo de manutencao no MLflow 3.x e passou a recusar novas runs --
# ver mlflow.exceptions.MlflowException ao usar tracking_uri="file:..." direto).
# Artefatos (graficos etc.) continuam salvos localmente em mlruns/, sem
# servidor remoto nem conta -- so o metadado das runs vai para o SQLite.
mlflow.set_tracking_uri(f"sqlite:///{MLFLOW_DB.as_posix()}")

# Campos da `linha` (dict) ja usada pelos scripts que NAO sao metricas
# numericas -- viram tags textuais quando logados/exportados.
CAMPOS_TAG = ("metodo", "script", "tratamento_nd_bod", "data_execucao", "ordem_sarima", "hiperparametros")


def git_commit_hash() -> str:
    """Hash curto do commit atual do Git, ou "sem_git" se nao houver
    repositorio inicializado (o projeto ainda nao tem Git nesta sessao)."""
    try:
        resultado = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=RAIZ_PROJETO, capture_output=True, text=True, timeout=5, check=True,
        )
        return resultado.stdout.strip() or "sem_git"
    except Exception:
        return "sem_git"


def gerar_run_id(metodo: str) -> str:
    """Padrao de run_id definido no plano: timestamp (UTC) + hash do commit + nome do metodo."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}_{git_commit_hash()}_{metodo}"


@contextmanager
def iniciar_run(metodo: str, script: str, params: dict | None = None, seed=None,
                 janela_treino_holdout: dict | None = None, tags: dict | None = None,
                 experiment_name: str = EXPERIMENTO_PADRAO):
    """Abre uma run do MLflow para uma execucao de metodo. Loga automaticamente
    params (incluindo seed e janela treino/holdout), tags padrao (script,
    git_commit, run_id_padrao) e o tempo de execucao do bloco ao sair.

    Uso:
        with iniciar_run("ols", "script_01_...", params={...}) as run:
            ... ajusta o modelo ...
            logar_metricas({"rmse_holdout": rmse, ...})
            logar_artefatos([FIGURA_PATH])
    """
    if mlflow.get_experiment_by_name(experiment_name) is None:
        MLRUNS_DIR.mkdir(exist_ok=True)
        mlflow.create_experiment(experiment_name, artifact_location=f"file:{MLRUNS_DIR.as_posix()}")
    mlflow.set_experiment(experiment_name)
    run_id_padrao = gerar_run_id(metodo)

    inicio = time.perf_counter()
    with mlflow.start_run(run_name=run_id_padrao) as run:
        mlflow.set_tag("run_id_padrao", run_id_padrao)
        mlflow.set_tag("metodo", metodo)
        mlflow.set_tag("script", script)
        mlflow.set_tag("git_commit", git_commit_hash())
        if tags:
            mlflow.set_tags({k: str(v) for k, v in tags.items()})

        params_completos = dict(params or {})
        if seed is not None:
            params_completos["seed"] = seed
        if janela_treino_holdout:
            params_completos.update({f"janela_{k}": v for k, v in janela_treino_holdout.items()})
        if params_completos:
            mlflow.log_params(params_completos)

        try:
            yield run
        finally:
            mlflow.log_metric("tempo_execucao_s", time.perf_counter() - inicio)


def logar_metricas(metricas: dict) -> None:
    """Loga um dict de metricas numericas na run ativa (ignora chaves com
    valor None/NaN/nao-numerico -- MLflow so aceita numeros)."""
    limpo = {}
    for k, v in metricas.items():
        if v is None:
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if fv != fv:  # NaN
            continue
        limpo[k] = fv
    if limpo:
        mlflow.log_metrics(limpo)


def logar_linha_resultado(linha: dict) -> None:
    """Loga um dict no formato ja usado pelos scripts (a mesma `linha` que
    hoje vira uma linha de resultados_comparacao.csv) na run ativa: campos
    numericos viram metricas, campos textuais (CAMPOS_TAG) viram tags."""
    metricas = {k: v for k, v in linha.items() if k not in CAMPOS_TAG}
    tags_extra = {k: str(v) for k, v in linha.items() if k in CAMPOS_TAG and v is not None}
    logar_metricas(metricas)
    if tags_extra:
        mlflow.set_tags(tags_extra)


def logar_artefatos(paths: list[str]) -> None:
    """Loga uma lista de arquivos (graficos, tabelas de residuos, modelos
    serializados) como artefatos da run ativa."""
    for caminho in paths:
        p = Path(caminho)
        if p.exists():
            mlflow.log_artifact(str(p))


def exportar_para_resultados_csv(run_ids_padrao: list[str],
                                  destino: str | Path = RESULTADOS_CSV_PADRAO,
                                  destino_json: str | Path = RESULTADOS_JSON_PADRAO,
                                  experiment_name: str = EXPERIMENTO_PADRAO) -> pd.DataFrame:
    """Busca runs do MLflow pelo run_id padrao (tag `run_id_padrao`) e exporta
    para resultados_comparacao.csv/.json, substituindo apenas a linha do(s)
    metodo(s) exportado(s) -- nunca as demais (mesma regra ja aplicada em
    gravar_resultados() de cada script_0X, reaproveitada aqui em vez de
    duplicada)."""
    linhas = []
    for run_id_padrao in run_ids_padrao:
        runs = mlflow.search_runs(
            experiment_names=[experiment_name],
            filter_string=f"tags.run_id_padrao = '{run_id_padrao}'",
            output_format="list",
        )
        if not runs:
            raise ValueError(f"Nenhuma run encontrada com run_id_padrao={run_id_padrao!r}")
        run = runs[0]
        linha = dict(run.data.metrics)
        for k, v in run.data.tags.items():
            if k.startswith("mlflow.") or k == "run_id_padrao":
                continue
            linha[k] = v
        linhas.append(linha)

    novas = pd.DataFrame(linhas)

    if Path(destino).exists():
        existentes = pd.read_csv(destino)
        existentes = existentes[~existentes["metodo"].isin(novas["metodo"])]
        for col in novas.columns:
            if col not in existentes.columns:
                existentes[col] = pd.NA
        for col in existentes.columns:
            if col not in novas.columns:
                novas[col] = pd.NA
        consolidado = pd.concat([existentes, novas], ignore_index=True)
    else:
        consolidado = novas

    consolidado.to_csv(destino, index=False)
    consolidado.to_json(destino_json, orient="records", indent=2, force_ascii=False)
    return consolidado
