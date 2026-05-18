import os
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine

st.set_page_config(page_title="SINISA SP BI", layout="wide")

APP_TITLE = os.getenv("APP_TITLE", "SINISA SP 2019-2024 - Painel BI (Web)")
TABLE_NAME = os.getenv("TABLE_NAME", "saneamento_sp_municipios_selecionados")
DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    st.error("Defina a variável DATABASE_URL para conectar ao Supabase/Postgres.")
    st.stop()


@st.cache_resource
def get_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)


@st.cache_data(ttl=300)
def load_data(table_name: str) -> pd.DataFrame:
    engine = get_engine()
    query = f"""
        SELECT ano_ref, modulo, cod_ibge, municipio, uf, regiao,
               codigo_indicador, descricao_indicador, unidade,
               valor_raw, valor_num, grupo
        FROM {table_name}
    """
    with engine.begin() as conn:
        df = pd.read_sql_query(query, conn)
    df["valor_num"] = pd.to_numeric(df["valor_num"], errors="coerce")
    df["municipio"] = df["municipio"].fillna("(sem municipio)").astype(str)
    df["modulo"] = df["modulo"].fillna("(sem modulo)").astype(str)
    df["codigo_indicador"] = df["codigo_indicador"].fillna("(sem codigo)").astype(str)
    df["descricao_indicador"] = df["descricao_indicador"].fillna("").astype(str)
    df["ano_ref"] = pd.to_numeric(df["ano_ref"], errors="coerce").astype("Int64")
    return df


def fmt_br(v: Optional[float], dec: int = 2) -> str:
    if v is None or pd.isna(v):
        return "-"
    s = f"{float(v):,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def gauge_card(title: str, subtitle: str, pct: Optional[float], abs_value: Optional[float], key: str, value_label: str, max_range: float = 100.0):
    st.markdown(f"### {title}")
    st.caption(subtitle)
    if pct is None or pd.isna(pct):
        st.info("Sem valor numérico para este recorte.")
        return
    pct = max(0.0, min(float(pct), max_range))
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=pct,
            number={"suffix": "%", "valueformat": ".1f"},
            gauge={
                "axis": {"range": [0, max_range]},
                "bar": {"color": "#2f9acb"},
                "bgcolor": "#f1f3f5",
                "steps": [{"range": [0, max_range], "color": "#e9ecef"}],
            },
        )
    )
    fig.update_layout(height=240, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True, key=key)
    st.markdown(f"**{value_label}:** {fmt_br(abs_value, 2)}")


df = load_data(TABLE_NAME)

st.title(APP_TITLE)
st.caption("Versão web pública com Supabase + Render.")

with st.sidebar:
    st.header("Filtros")
    anos_disp = sorted([int(a) for a in df["ano_ref"].dropna().unique().tolist()])
    ano_sel = st.multiselect("Ano", anos_disp, default=anos_disp)

    base_casc = df.copy()
    if ano_sel:
        base_casc = base_casc[base_casc["ano_ref"].isin(ano_sel)]

    all_mods = sorted(base_casc["modulo"].dropna().unique().tolist())
    mod_sel = st.multiselect("Módulos", all_mods, default=all_mods)
    if mod_sel:
        base_casc = base_casc[base_casc["modulo"].isin(mod_sel)]

    agregacao_sel = st.selectbox("Método de agregação", ["Média municipal", "Soma municipal"], index=0)

    labels = (
        base_casc[base_casc["valor_num"].notna()]
        .groupby(["codigo_indicador", "descricao_indicador"], dropna=False)
        .size()
        .reset_index(name="n")
        .sort_values("n", ascending=False)
    )
    labels["label"] = labels["codigo_indicador"] + " - " + labels["descricao_indicador"]
    ind_options = labels["label"].head(400).tolist()
    ind_sel = st.selectbox("Indicador principal", ind_options, index=0 if ind_options else None)

    all_muns = sorted(base_casc["municipio"].dropna().unique().tolist())
    mun_sel = st.multiselect("Municípios", all_muns, default=[])

f = df.copy()
if ano_sel:
    f = f[f["ano_ref"].isin(ano_sel)]
if mod_sel:
    f = f[f["modulo"].isin(mod_sel)]

f_scope = f.copy()
if mun_sel:
    f = f[f["municipio"].isin(mun_sel)]

if ind_sel:
    indicator_code = ind_sel.split(" - ")[0]
    fi = f[f["codigo_indicador"] == indicator_code].copy()
else:
    fi = f.iloc[0:0].copy()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Registros", f"{len(f):,}".replace(",", "."))
k2.metric("Municípios", f"{f['municipio'].nunique():,}".replace(",", "."))
k3.metric("Indicadores", f"{f['codigo_indicador'].nunique():,}".replace(",", "."))
k4.metric("Módulos", f"{f['modulo'].nunique():,}".replace(",", "."))

st.markdown("---")
st.subheader("Cards de comparação")

city_rank_group = fi[fi["valor_num"].notna()].groupby("municipio", dropna=False)["valor_num"]
if agregacao_sel == "Soma municipal":
    city_rank = city_rank_group.sum().reset_index()
    value_label = "Valor soma"
else:
    city_rank = city_rank_group.mean().reset_index()
    value_label = "Valor médio"
city_rank = city_rank.sort_values("valor_num", ascending=False)

sp_total = city_rank["valor_num"].sum() if len(city_rank) else None
sp_pct = 100.0 if sp_total is not None and not pd.isna(sp_total) and sp_total != 0 else None

municipios_para_cards = city_rank.to_dict("records") if not mun_sel else [
    {"municipio": m, "valor_num": city_rank.set_index("municipio").get("valor_num", pd.Series()).get(m)} for m in mun_sel
]
municipios_para_cards = municipios_para_cards[:20]

gauge_card(
    "Total dos municípios filtrados",
    (ind_sel or "Indicador principal") + (" - soma municipal" if agregacao_sel == "Soma municipal" else " - soma das médias municipais"),
    sp_pct,
    sp_total,
    "card_sp",
    value_label,
)

cols_per_row = 4
for i in range(0, len(municipios_para_cards), cols_per_row):
    row_cards = municipios_para_cards[i : i + cols_per_row]
    cols = st.columns(cols_per_row)
    for j, item in enumerate(row_cards):
        with cols[j]:
            pct = (item["valor_num"] / sp_total * 100.0) if sp_total not in (None, 0) and item["valor_num"] is not None else None
            gauge_card(
                item["municipio"],
                (ind_sel or "Indicador principal") + " - % da soma filtrada",
                pct,
                item["valor_num"],
                f"card_city_{i+j}",
                value_label,
            )

st.markdown("---")
left, right = st.columns([1.1, 1])
with left:
    st.subheader("Ranking de municípios")
    st.dataframe(city_rank.head(30), use_container_width=True, hide_index=True)

with right:
    st.subheader("Média por módulo")
    if fi.empty or fi["valor_num"].notna().sum() == 0:
        st.info("Sem dados numéricos para o recorte atual.")
    else:
        by_mod = fi.groupby("modulo", dropna=False)["valor_num"].mean().reset_index().sort_values("valor_num", ascending=False)
        st.bar_chart(by_mod.set_index("modulo")["valor_num"])

st.subheader("Tabela detalhada")
show_cols = ["ano_ref", "modulo", "cod_ibge", "municipio", "uf", "regiao", "codigo_indicador", "descricao_indicador", "unidade", "valor_raw", "valor_num"]
show_cols = [c for c in show_cols if c in f.columns]
st.dataframe(f[show_cols].head(8000), use_container_width=True, hide_index=True)

st.download_button(
    "Baixar recorte filtrado (CSV)",
    f[show_cols].to_csv(index=False).encode("utf-8-sig"),
    file_name="sinisa_sp_recorte_filtrado.csv",
    mime="text/csv",
)
