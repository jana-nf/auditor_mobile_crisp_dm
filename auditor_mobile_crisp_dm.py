import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", auto_download=["html"])


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    return go, make_subplots, np, pd


@app.cell
def _(mo):
    mo.md("""
    # 📊 Auditoria Mobile e Alocação de Orçamento de Marketing
    ### Projeto Prático sob a Metodologia **CRISP-DM** (Execução Local no Marimo)

    **Resumo com a metodologia STAR:** Durante a definição do orçamento de marketing para o próximo trimestre,
    os números de conversão do *dashboard* não batiam com os dados brutos. Uma atualização no SDK
    *mobile* (ex.: políticas de privacidade/consentimento e mudanças de *payload*) quebrou parte das
    chaves de atribuição e omitiu conversões *mobile*. Em vez de "maquiar" planilhas para entregar
    rápido, o problema foi investigado até a origem, acionando a engenharia de dados e documentando
    a discrepância para proteger a decisão de orçamento.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. Entendimento do Negócio
    """)
    return


@app.cell
def _(mo):
    budget_slider = mo.ui.slider(
        start=50_000,
        stop=500_000,
        step=25_000,
        value=200_000,
        label="Orçamento Total Próximo Trimestre (R$)",
    )
    sdk_break_rate_slider = mo.ui.slider(
        start=0.10,
        stop=0.70,
        step=0.05,
        value=0.40,
        label="Taxa de Quebra do SDK Mobile Pós-Atualização (%)",
    )
    mo.hstack([budget_slider, sdk_break_rate_slider], justify="start", gap=2)
    return budget_slider, sdk_break_rate_slider


@app.cell
def _(budget_slider, mo, sdk_break_rate_slider):
    mo.md(f"""
    * **Objetivo:** Definir como alocar **R$ {budget_slider.value:,.2f}** entre os canais para o próximo trimestre.
    * **Risco identificado:** Uma quebra estimada de **{sdk_break_rate_slider.value * 100:.0f}%** no rastreamento
      *mobile* após a atualização do SDK subestima conversões reais, infla o CPA e derruba o ROAS aparente.
    * **Diretriz de conduta:** Investigar a causa raiz e a engenharia de dados em vez de aplicar
      ajustes manuais isolados no relatório.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## 2. Simulação da Base "Suja" e Diagnóstico
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 2.1: Gerar a base "verdadeira" (o que realmente ocorreu nos eventos e conversões)
    """)
    return


@app.cell
def _(np, pd):
    rng = np.random.default_rng(42)
    n_events = 2_400

    dates = pd.date_range("2026-08-01", "2026-10-29", periods=n_events)
    break_date = pd.Timestamp("2026-09-15")

    channels = rng.choice(
        ["Mobile Paid", "Web Paid", "Organic / Direct", "Email / CRM"],
        size=n_events,
        p=[0.35, 0.30, 0.20, 0.15],
    )
    platforms = np.where(
        channels == "Mobile Paid",
        rng.choice(["iOS", "Android"], size=n_events, p=[0.60, 0.40]),
        np.where(channels == "Web Paid", "Desktop/Mobile Web", "Multi-platform"),
    )

    spend_true = np.select(
        [
            channels == "Mobile Paid",
            channels == "Web Paid",
            channels == "Organic / Direct",
            channels == "Email / CRM",
        ],
        [
            rng.uniform(45, 130, size=n_events),
            rng.uniform(40, 115, size=n_events),
            rng.uniform(5, 25, size=n_events),
            rng.uniform(5, 20, size=n_events),
        ],
    )

    conv_prob_true = np.select(
        [
            channels == "Mobile Paid",
            channels == "Web Paid",
            channels == "Organic / Direct",
            channels == "Email / CRM",
        ],
        [0.24, 0.14, 0.11, 0.16],
    )
    conversions_true = rng.binomial(1, conv_prob_true)
    revenue_true = conversions_true * rng.normal(loc=190.0, scale=45.0, size=n_events).clip(40, 450)
    raw_user_ids = [f"USR-{i:05d}" for i in range(n_events)]

    df_truth = pd.DataFrame(
        {
            "event_id": [f"EVT-{i:06d}" for i in range(n_events)],
            "event_date": dates,
            "channel": channels,
            "platform": platforms,
            "raw_user_id": raw_user_ids,
            "spend_true": spend_true,
            "conversions_true": conversions_true,
            "revenue_true": revenue_true,
        }
    )
    return break_date, df_truth, n_events, rng


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 2.2: Simula a base "suja" do dashboard após a atualização do SDK mobile
    """)
    return


@app.cell
def _(break_date, df_truth, n_events, np, pd, rng, sdk_break_rate_slider):
    conversions_dashboard = df_truth["conversions_true"].to_numpy().copy()
    revenue_dashboard = df_truth["revenue_true"].to_numpy().copy()
    spend_dashboard = df_truth["spend_true"].to_numpy().copy()
    attribution_join_key = df_truth["raw_user_id"].tolist()

    post_update_mobile_mask = (df_truth["event_date"] >= break_date) & (
        df_truth["channel"] == "Mobile Paid"
    )
    broken_indices = np.where(post_update_mobile_mask)[0]

    n_broken = int(len(broken_indices) * sdk_break_rate_slider.value)
    chosen_broken = rng.choice(broken_indices, size=n_broken, replace=False)

    # Perda de conversão e receita no painel por falha de payload/SDK após break_date
    conversions_dashboard[chosen_broken] = 0
    revenue_dashboard[chosen_broken] = 0.0

    # Chaves de join ausentes (NULL) em parte das linhas afetadas
    for idx in chosen_broken[: max(1, n_broken // 2)]:
        attribution_join_key[idx] = None

    # Valores ausentes pontuais de spend fora do canal Mobile Paid
    non_mobile_idx = np.where(df_truth["channel"] != "Mobile Paid")[0]
    null_spend_idx = rng.choice(non_mobile_idx, size=18, replace=False)
    spend_dashboard[null_spend_idx] = np.nan

    df_raw = df_truth.copy()
    df_raw["attribution_key"] = attribution_join_key
    df_raw["spend_dashboard"] = spend_dashboard
    df_raw["conversions_dashboard"] = conversions_dashboard
    df_raw["revenue_dashboard"] = revenue_dashboard
    df_raw["sdk_bug_affected"] = np.isin(np.arange(n_events), chosen_broken)

    # Tabela auxiliar de atribuição (simula chaves ausentes -> joins)
    valid_keys_set = set(df_raw.loc[~df_raw["sdk_bug_affected"], "attribution_key"].dropna())
    df_attribution = pd.DataFrame(
        {
            "attribution_key": list(valid_keys_set),
            "verified_flag": True,
        }
    )
    return df_attribution, df_raw


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 2.3: Tabela de auditoria de nulos, joins e discrepância de conversões
    """)
    return


@app.cell
def _(df_attribution, df_raw, mo, pd):
    total_rows = len(df_raw)
    missing_keys = int(df_raw["attribution_key"].isna().sum())
    missing_spend = int(df_raw["spend_dashboard"].isna().sum())

    joined_check = df_raw.merge(df_attribution, on="attribution_key", how="left")
    unmatched_joins = int(joined_check["verified_flag"].isna().sum())

    dash_conv = int(df_raw["conversions_dashboard"].sum())
    true_conv = int(df_raw["conversions_true"].sum())
    diff_conv = true_conv - dash_conv

    audit_df = pd.DataFrame(
        {
            "Indicador de Qualidade": [
                "Total de eventos",
                "Chaves de join ausentes (NULL)",
                "Joins sem correspondência (LEFT JOIN)",
                "Valores nulos em Spend (Dashboard)",
                "Conversões no Dashboard (suja)",
                "Conversões Reais (verdade)",
                "Conversões omitidas no painel",
            ],
            "Valor": [
                f"{total_rows:,}",
                f"{missing_keys:,} ({missing_keys / total_rows * 100:.2f}%)",
                f"{unmatched_joins:,} ({unmatched_joins / total_rows * 100:.2f}%)",
                f"{missing_spend:,}",
                f"{dash_conv:,}",
                f"{true_conv:,}",
                f"{diff_conv:,} ({diff_conv / max(true_conv, 1) * 100:.1f}%)",
            ],
        }
    )

    mo.vstack([mo.md("### Diagnóstico da Base Suja e Joins"), mo.ui.table(audit_df, selection=None)])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 2.4: Agrega métricas semanais do canal Mobile Paid para o gráfico do problema
    """)
    return


@app.cell
def _(df_raw):
    df_mobile = df_raw[df_raw["channel"] == "Mobile Paid"].copy()
    w_mobile = (
        df_mobile.set_index("event_date")
        .resample("W")
        .agg(
            mobile_dash_conv=("conversions_dashboard", "sum"),
            mobile_true_conv=("conversions_true", "sum"),
            mobile_dash_rev=("revenue_dashboard", "sum"),
            mobile_true_rev=("revenue_true", "sum"),
        )
    )
    return (w_mobile,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 2.5: Gráfico interativo mostrando a queda no painel após atualização do SDK
    """)
    return


@app.cell
def _(break_date, go, make_subplots, mo, w_mobile):
    fig_problem = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            "Conversões Mobile Paid (Dashboard vs. Real)",
            "Receita Mobile Paid (Dashboard vs. Real)",
        ),
    )

    fig_problem.add_trace(
        go.Scatter(
            x=w_mobile.index,
            y=w_mobile["mobile_dash_conv"],
            mode="lines+markers",
            name="Conv. Dashboard (Suja)",
            line=dict(color="#EF4444", width=3, dash="dash"),
        ),
        row=1,
        col=1,
    )
    fig_problem.add_trace(
        go.Scatter(
            x=w_mobile.index,
            y=w_mobile["mobile_true_conv"],
            mode="lines+markers",
            name="Conv. Real",
            line=dict(color="#10B981", width=3),
        ),
        row=1,
        col=1,
    )
    fig_problem.add_trace(
        go.Bar(
            x=w_mobile.index,
            y=w_mobile["mobile_dash_rev"],
            name="Receita Dashboard (R$)",
            marker_color="#FCA5A5",
            showlegend=False,
        ),
        row=1,
        col=2,
    )
    fig_problem.add_trace(
        go.Scatter(
            x=w_mobile.index,
            y=w_mobile["mobile_true_rev"],
            mode="lines+markers",
            name="Receita Real (R$)",
            line=dict(color="#059669", width=3),
            showlegend=False,
        ),
        row=1,
        col=2,
    )

    for col_idx in [1, 2]:
        fig_problem.add_vline(
            x=break_date.timestamp() * 1000,
            line_width=2,
            line_dash="dot",
            line_color="#1D4ED8",
            row=1,
            col=col_idx,
        )

    fig_problem.update_layout(
        height=420,
        template="plotly_white",
        hovermode="x unified",
        title_text="O Problema: Distorção no Canal Mobile Após a Atualização do SDK (Linha Azul)",
    )

    mo.vstack(
        [
            mo.md("### Visualização do Problema: Queda Artificial no Painel"),
            mo.ui.plotly(fig_problem),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## 3. Data Preparation (Tratamento e Reconciliação na Origem)
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 3.1: Trata nulos de spend, classifica status de join e reconcilia dados na origem
    """)
    return


@app.cell
def _(df_attribution, df_raw, pd):
    df_clean = df_raw.copy()

    df_clean["spend_clean"] = df_clean["spend_dashboard"].fillna(
        df_clean.groupby("channel")["spend_dashboard"].transform("median")
    )

    df_clean["join_status"] = pd.Series("OK", index=df_clean.index)
    df_clean.loc[df_clean["attribution_key"].isna(), "join_status"] = "MISSING_KEY (NULL)"
    orphan_mask = df_clean["attribution_key"].notna() & (
        ~df_clean["attribution_key"].isin(df_attribution["attribution_key"])
    )
    df_clean.loc[orphan_mask, "join_status"] = "ORPHAN_JOIN_KEY"

    # Reconciliação após correção do SDK/pipeline junto à Engenharia de Dados
    df_clean["conversions_reconciled"] = df_clean["conversions_true"]
    df_clean["revenue_reconciled"] = df_clean["revenue_true"]
    return (df_clean,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 3.2: Resumo do saneamento e status de join
    """)
    return


@app.cell
def _(df_clean, mo):
    join_summary = (
        df_clean.groupby("join_status", dropna=False)
        .agg(
            registros=("event_id", "count"),
            conv_dashboard=("conversions_dashboard", "sum"),
            conv_reconciliada=("conversions_reconciled", "sum"),
        )
        .reset_index()
    )

    mo.vstack(
        [
            mo.md("### Resumo do Tratamento de Joins e Reconciliação"),
            mo.ui.table(join_summary, selection=None),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ### 3B. Testes Automatizados de Qualidade de Dados (Data Quality Gates)
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 3B.1: Executa checagens formais de integridade antes de liberar métricas/orçamento
    """)
    return


@app.cell
def _(df_clean, pd):
    checks = []

    dup_events = int(df_clean["event_id"].duplicated().sum())
    checks.append(("Unicidade de event_id", dup_events == 0, f"{dup_events} duplicatas"))

    null_spend_clean = int(df_clean["spend_clean"].isna().sum())
    checks.append(("Completude de spend_clean", null_spend_clean == 0, f"{null_spend_clean} nulos"))

    neg_conv = int((df_clean["conversions_reconciled"] < 0).sum())
    checks.append(("Conversões >= 0", neg_conv == 0, f"{neg_conv} inválidos"))

    rev_without_conv = int(
        ((df_clean["conversions_reconciled"] == 0) & (df_clean["revenue_reconciled"] > 0)).sum()
    )
    checks.append(
        ("Coerência Receita x Conversão", rev_without_conv == 0, f"{rev_without_conv} inconsistências")
    )

    df_tests = pd.DataFrame(
        {
            "Regra de Qualidade": [c[0] for c in checks],
            "Status": ["PASSOU ✅" if c[1] else "FALHOU ❌" for c in checks],
            "Detalhe": [c[2] for c in checks],
        }
    )
    return (df_tests,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 3B.2: Exibe o relatório dos testes automatizados
    """)
    return


@app.cell
def _(df_tests, mo):
    mo.vstack(
        [
            mo.md("### Relatório de Validação Automatizada"),
            mo.ui.table(df_tests, selection=None),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## 4. Modeling & Evaluation (Comparação: Base Suja vs. Corrigida)
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 4.1: Calcula ROAS e CPA comparando a leitura suja vs. a leitura corrigida
    """)
    return


@app.cell
def _(df_clean, pd):
    canal_metrics = df_clean.groupby("channel", as_index=False).agg(
        spend_total=("spend_clean", "sum"),
        conv_dirty=("conversions_dashboard", "sum"),
        conv_clean=("conversions_reconciled", "sum"),
        rev_dirty=("revenue_dashboard", "sum"),
        rev_clean=("revenue_reconciled", "sum"),
    )

    canal_metrics["roas_dirty"] = canal_metrics["rev_dirty"] / canal_metrics["spend_total"].replace(
        0, pd.NA
    )
    canal_metrics["roas_clean"] = canal_metrics["rev_clean"] / canal_metrics["spend_total"].replace(
        0, pd.NA
    )
    canal_metrics["cpa_clean"] = canal_metrics["spend_total"] / canal_metrics["conv_clean"].replace(
        0, pd.NA
    )
    return (canal_metrics,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 4.2: Gráfico comparativo de ROAS por canal (Sujo vs. Real)
    """)
    return


@app.cell
def _(canal_metrics, go, mo):
    fig_eval = go.Figure()
    fig_eval.add_trace(
        go.Bar(
            x=canal_metrics["channel"],
            y=canal_metrics["roas_dirty"].astype(float),
            name="ROAS Base Suja (Enviesado)",
            marker_color="#F87171",
        )
    )
    fig_eval.add_trace(
        go.Bar(
            x=canal_metrics["channel"],
            y=canal_metrics["roas_clean"].astype(float),
            name="ROAS Base Corrigida (Real)",
            marker_color="#10B981",
        )
    )
    fig_eval.update_layout(
        barmode="group",
        template="plotly_white",
        height=390,
        title="A Solução: ROAS por Canal Antes e Depois da Reconciliação",
        yaxis_title="ROAS (Receita / Investimento)",
    )

    mo.vstack([mo.md("### Gráfico da Solução: Impacto no ROAS"), mo.ui.plotly(fig_eval)])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 4.3: Tabela consolidada de métricas por canal
    """)
    return


@app.cell
def _(canal_metrics, mo, pd):
    display_metrics = pd.DataFrame(
        {
            "Canal": canal_metrics["channel"],
            "Investimento": canal_metrics["spend_total"].map(lambda x: f"R$ {x:,.2f}"),
            "Conv. Suja": canal_metrics["conv_dirty"],
            "Conv. Corrigida": canal_metrics["conv_clean"],
            "ROAS Sujo": canal_metrics["roas_dirty"].map(lambda x: f"{x:.2f}x"),
            "ROAS Real": canal_metrics["roas_clean"].map(lambda x: f"{x:.2f}x"),
            "CPA Real": canal_metrics["cpa_clean"].map(lambda x: f"R$ {x:,.2f}"),
        }
    )

    mo.vstack([mo.md("### Métricas Consolidadas por Canal"), mo.ui.table(display_metrics, selection=None)])
    return


@app.cell
def _(mo):
    mo.md("""
    ## 5. Deployment (Recomendação de Orçamento & Governança)
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 5.1: Calcula alocação sugerida para o próximo trimestre com base no ROAS real
    """)
    return


@app.cell
def _(budget_slider, canal_metrics, pd):
    total_budget = float(budget_slider.value)
    df_alloc = canal_metrics.copy()

    roas_clean_num = df_alloc["roas_clean"].astype(float)
    weights = roas_clean_num / roas_clean_num.sum()

    roas_dirty_num = df_alloc["roas_dirty"].astype(float)
    weights_dirty = roas_dirty_num / roas_dirty_num.sum()

    df_alloc["orcamento_sujo_r$"] = weights_dirty * total_budget
    df_alloc["orcamento_corrigido_r$"] = weights * total_budget
    df_alloc["diferenca_r$"] = df_alloc["orcamento_corrigido_r$"] - df_alloc["orcamento_sujo_r$"]

    alloc_table = pd.DataFrame(
        {
            "Canal": df_alloc["channel"],
            "Peso Recomendado": (weights * 100).map(lambda x: f"{x:.1f}%"),
            "Alocação (Base Suja)": df_alloc["orcamento_sujo_r$"].map(lambda x: f"R$ {x:,.2f}"),
            "Alocação (Corrigida)": df_alloc["orcamento_corrigido_r$"].map(lambda x: f"R$ {x:,.2f}"),
            "Ajuste de Verba": df_alloc["diferenca_r$"].map(
                lambda x: f"+R$ {x:,.2f}" if x >= 0 else f"-R$ {abs(x):,.2f}"
            ),
        }
    )

    mobile_diff = float(df_alloc.loc[df_alloc["channel"] == "Mobile Paid", "diferenca_r$"].iloc[0])
    return alloc_table, mobile_diff


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 5.2: Relatório executivo final e tabela de alocação
    """)
    return


@app.cell
def _(alloc_table, mo, mobile_diff):
    mo.vstack(
        [
            mo.md(
                f"""
                ### Conclusão Executiva & Documentação (STAR)
                * **Decisão protegida:** A correção na origem evitou subestimar o canal *Mobile Paid* e
                  gerou um ajuste de **{mobile_diff:+,.2f} R$** na alocação em comparação ao cenário enviesado.
                * **Documentação para o time:**
                  1. Registro da falha de rastreamento/chave após atualização do SDK *mobile*.
                  2. Alinhamento com Engenharia de Dados para correção na fonte (sem ajuste manual isolado).
                  3. Inclusão de testes automatizados de qualidade de dados antes da publicação do painel.
                """
            ),
            mo.ui.table(alloc_table, selection=None),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
 
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ### Bônus

    Mesmo com um pequeno atraso na entrega, a investigação até a causa raiz e a correção na origem
    evitaram um erro estratégico grave. Em vez de apenas "maquiar" os números na planilha
    para cumprir o prazo rapidamente, o diagnóstico de *joins*, o tratamento de valores ausentes, o
    trabalho conjunto com a engenharia de dados e a documentação da discrepância revelaram que as
    campanhas para celular tinham um retorno muito maior do que se pensava, então o bônus está em enxergar uma
    oportunidade real de crescimento e não apenas evitar um prejuízo. Com isso, o projeto
    transformou uma falha de rastreamento em uma base confiável e auditável, mudando positivamente a
    forma como a empresa distribuiu o orçamento dali em diante.
    """)
    return


if __name__ == "__main__":
    app.run()