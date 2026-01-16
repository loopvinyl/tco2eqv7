import streamlit as st
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(
    page_title="Potencial de Compostagem de RSU",
    layout="wide"
)

# =========================================================
# FORMATAÇÃO BRASILEIRA
# =========================================================
def formatar_br(valor, casas=2):
    try:
        v = float(valor)
        s = f"{v:,.{casas}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "Não informado"

def formatar_massa(valor):
    try:
        return f"{formatar_br(valor,2)} t"
    except:
        return "Não informado"

# =========================================================
# COTAÇÃO AUTOMÁTICA – CARBONO (tCO2eq)
# =========================================================
def obter_cotacao_carbono_investing():
    try:
        url = "https://www.investing.com/commodities/carbon-emissions"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"
        }
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.content, "html.parser")

        seletores = [
            '[data-test="instrument-price-last"]',
            '.text-2xl',
            '.instrument-price-last'
        ]

        for s in seletores:
            el = soup.select_one(s)
            if el:
                preco = el.text.strip().replace(",", "")
                return float(preco), "€", True, "Investing.com"

        return None, None, False, "Investing.com"
    except:
        return None, None, False, "Erro"

def obter_cotacao_carbono():
    preco, moeda, ok, fonte = obter_cotacao_carbono_investing()
    if ok:
        return preco, moeda, fonte
    return 85.5, "€", "Referência"

def obter_cotacao_euro_real():
    try:
        r = requests.get("https://economia.awesomeapi.com.br/last/EUR-BRL", timeout=10)
        data = r.json()
        return float(data["EURBRL"]["bid"]), True
    except:
        return 5.50, False

# =========================================================
# SIDEBAR – MERCADO DE CARBONO
# =========================================================
def exibir_cotacoes():
    st.sidebar.header("💰 Mercado de Carbono")

    if "preco_carbono" not in st.session_state:
        st.session_state.preco_carbono, st.session_state.moeda, st.session_state.fonte = obter_cotacao_carbono()
        st.session_state.eur_brl, _ = obter_cotacao_euro_real()

    if st.sidebar.button("🔄 Atualizar cotações"):
        st.session_state.preco_carbono, st.session_state.moeda, st.session_state.fonte = obter_cotacao_carbono()
        st.session_state.eur_brl, _ = obter_cotacao_euro_real()
        st.rerun()

    st.sidebar.metric(
        "Preço do Carbono (tCO₂eq)",
        f"{st.session_state.moeda} {formatar_br(st.session_state.preco_carbono)}",
        help=f"Fonte: {st.session_state.fonte}"
    )

    st.sidebar.metric(
        "Euro (EUR/BRL)",
        f"R$ {formatar_br(st.session_state.eur_brl)}"
    )

    st.sidebar.metric(
        "Carbono em Reais",
        f"R$ {formatar_br(st.session_state.preco_carbono * st.session_state.eur_brl)}"
    )

exibir_cotacoes()

# =========================================================
# TÍTULO
# =========================================================
st.title("🌱 Potencial de Compostagem e Vermicompostagem por Município")
st.markdown(
    "Avaliação técnica, ambiental e econômica do desvio de **podas e galhadas** "
    "de aterros sanitários para **compostagem e vermicompostagem**."
)

# =========================================================
# CARGA DOS DADOS
# =========================================================
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/loopvinyl/tco2eqv7/main/rsuBrasil.xlsx"
    df = pd.read_excel(
        url,
        sheet_name="Manejo_Coleta_e_Destinação",
        header=13
    )
    df = df.dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]
    return df

df = load_data()

# =========================================================
# COLUNAS
# =========================================================
COL_MUN = df.columns[2]
COL_TIPO = df.columns[17]
COL_MASSA = df.columns[24]
COL_DESTINO = df.columns[28]  # AC

# =========================================================
# FILTRO BRASIL
# =========================================================
df["MASSA_FLOAT"] = pd.to_numeric(df[COL_MASSA], errors="coerce").fillna(0)

df_brasil = df.copy()

# =========================================================
# PODAS E GALHADAS
# =========================================================
df_podas = df_brasil[
    df_brasil[COL_TIPO]
    .astype(str)
    .str.contains("podas|galhadas|áreas verdes", case=False, na=False)
]

massa_total_podas = df_podas["MASSA_FLOAT"].sum()

st.subheader("🌳 Destinação das podas e galhadas de áreas verdes públicas")
st.metric("Massa total de podas e galhadas", formatar_massa(massa_total_podas))

dist = (
    df_podas
    .groupby(COL_DESTINO, dropna=False)["MASSA_FLOAT"]
    .sum()
    .reset_index()
)

dist["Percentual (%)"] = dist["MASSA_FLOAT"] / massa_total_podas * 100
dist = dist.sort_values("Percentual (%)", ascending=False)

dist["Massa (t)"] = dist["MASSA_FLOAT"].apply(formatar_br)
dist["Percentual (%)"] = dist["Percentual (%)"].apply(lambda x: formatar_br(x,2))

st.dataframe(
    dist[[COL_DESTINO, "Massa (t)", "Percentual (%)"]],
    use_container_width=True
)

# =========================================================
# METANO – ATERRO SANITÁRIO
# =========================================================
df_aterro = df_podas[
    df_podas[COL_DESTINO].astype(str).str.lower().str.contains("aterro sanit")
]

massa_aterro = df_aterro["MASSA_FLOAT"].sum()

# Fatores (modelo técnico)
FATOR_CH4 = 0.062      # tCH4 / t resíduo
GWP_CH4 = 28           # IPCC AR5

ch4_gerado = massa_aterro * FATOR_CH4
co2eq_aterro = ch4_gerado * GWP_CH4

st.subheader("🔥 Potencial de geração de metano (CH₄) – Aterro Sanitário")
st.metric("Massa no aterro", formatar_massa(massa_aterro))
st.metric("CH₄ potencial", f"{formatar_br(ch4_gerado)} t CH₄")
st.metric("Emissões (tCO₂eq)", f"{formatar_br(co2eq_aterro)}")

# =========================================================
# EMISSÕES EVITADAS – COMPOSTAGEM E VERMICOMPOSTAGEM
# =========================================================
RED_COMP = 0.90
RED_VERMI = 0.95

evitado_comp = co2eq_aterro * RED_COMP
evitado_vermi = co2eq_aterro * RED_VERMI

st.subheader("♻️ Emissões Evitadas (desvio do aterro)")

c1, c2 = st.columns(2)
with c1:
    st.metric("Compostagem (tCO₂eq)", formatar_br(evitado_comp))
with c2:
    st.metric("Vermicompostagem (tCO₂eq)", formatar_br(evitado_vermi))

# =========================================================
# VALORAÇÃO ECONÔMICA – 20 ANOS
# =========================================================
anos = 20
preco = st.session_state.preco_carbono
eurbrl = st.session_state.eur_brl

st.subheader("💰 Valor Econômico das Emissões Evitadas (20 anos)")

for nome, valor in {
    "Compostagem": evitado_comp,
    "Vermicompostagem": evitado_vermi
}.items():
    total = valor * anos
    eur = total * preco
    brl = eur * eurbrl

    st.markdown(f"### {nome}")
    st.write(f"**tCO₂eq evitado:** {formatar_br(total)}")
    st.write(f"**Valor (€):** € {formatar_br(eur)}")
    st.write(f"**Valor (R$):** R$ {formatar_br(brl)}")

# =========================================================
# RODAPÉ
# =========================================================
st.markdown("---")
st.caption(
    "Cálculos de metano baseados em fatores médios IPCC. "
    "Preço do carbono e câmbio obtidos automaticamente em tempo real. "
    "Resultados indicativos para planejamento e análise de viabilidade."
)
