import streamlit as st
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================

st.set_page_config(
    page_title="Créditos de Carbono – Compostagem",
    layout="wide"
)

st.title("🌱 Simulador de Créditos de Carbono por Compostagem")
st.markdown("""
Avaliação **ambiental e econômica** do desvio de resíduos orgânicos  
do **aterro sanitário** para **compostagem**.

Metodologia baseada em **IPCC 2006** e literatura científica.
""")

# =========================================================
# PARÂMETROS CIENTÍFICOS (IPCC / LITERATURA)
# =========================================================

GWP_CH4 = 79.7   # IPCC AR6 (20 anos)
GWP_N2O = 273

MCF = 1.0
DOCF = 0.5
F = 0.5
OX = 0.1

FATOR_CH4_COMPOST = 0.004
FATOR_N2O_COMPOST = 0.0003

RESIDUOS = {
    "Podas e galhadas": 0.20,
    "Orgânico domiciliar": 0.15,
    "Resíduos de feira": 0.18
}

# =========================================================
# FUNÇÕES DE CÁLCULO
# =========================================================

def emissoes_aterro(massa, DOC):
    ch4 = massa * DOC * DOCF * MCF * F * (16/12) * (1 - OX)
    return ch4 * GWP_CH4

def emissoes_compostagem(massa):
    ch4 = massa * FATOR_CH4_COMPOST
    n2o = massa * FATOR_N2O_COMPOST
    return ch4 * GWP_CH4 + n2o * GWP_N2O

# =========================================================
# PREÇO DO CARBONO (REFERÊNCIA INTERNACIONAL)
# =========================================================

@st.cache_data(ttl=3600)
def preco_carbono_eu():
    try:
        url = "https://www.investing.com/commodities/carbon-emissions"
        headers = {"User-Agent": "Mozilla/5.0"}
        html = requests.get(url, headers=headers, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        preco = soup.find("span", {"data-test": "instrument-price-last"}).text
        return float(preco.replace(",", "."))
    except:
        return 85.0  # fallback conservador

@st.cache_data(ttl=3600)
def cambio_eur_brl():
    try:
        r = requests.get("https://economia.awesomeapi.com.br/json/last/EUR-BRL", timeout=10).json()
        return float(r["EURBRL"]["bid"])
    except:
        return 5.40

preco_eur = preco_carbono_eu()
cambio = cambio_eur_brl()

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("⚙️ Parâmetros")

massa = st.sidebar.number_input(
    "Massa de resíduos desviados (t/ano)",
    min_value=100.0,
    max_value=1_000_000.0,
    value=12000.0,
    step=500.0
)

residuo = st.sidebar.selectbox(
    "Tipo de resíduo",
    list(RESIDUOS.keys())
)

fator_preco = st.sidebar.slider(
    "Ajuste de risco de mercado",
    0.3, 1.2, 0.7,
    help="Redução do preço de referência para mercado voluntário"
)

calcular = st.sidebar.button("🚀 Calcular")

# =========================================================
# EXECUÇÃO
# =========================================================

if calcular:
    DOC = RESIDUOS[residuo]

    baseline = emissoes_aterro(massa, DOC)
    projeto = emissoes_compostagem(massa)
    reducao = baseline - projeto

    preco_ajustado = preco_eur * fator_preco
    valor_eur = reducao * preco_ajustado
    valor_brl = valor_eur * cambio

    # =====================================================
    # RESULTADOS
    # =====================================================

    st.header("📊 Resultado Ambiental")

    c1, c2, c3 = st.columns(3)
    c1.metric("Baseline (Aterro)", f"{baseline:,.0f} tCO₂e")
    c2.metric("Projeto (Compostagem)", f"{projeto:,.0f} tCO₂e")
    c3.metric("Redução Líquida", f"{reducao:,.0f} tCO₂e")

    st.header("💰 Resultado Econômico")

    c1, c2 = st.columns(2)
    c1.metric("Preço referência (€)", f"{preco_eur:,.2f}")
    c2.metric("Preço ajustado (€)", f"{preco_ajustado:,.2f}")

    st.metric("Valor potencial anual (R$)", f"R$ {valor_brl:,.0f}")

    # =====================================================
    # SAÍDA PARA BI
    # =====================================================

    df = pd.DataFrame([{
        "residuo": residuo,
        "massa_t_ano": massa,
        "baseline_tco2e": baseline,
        "projeto_tco2e": projeto,
        "reducao_tco2e": reducao,
        "preco_ref_eur": preco_eur,
        "preco_ajustado_eur": preco_ajustado,
        "valor_eur": valor_eur,
        "valor_brl": valor_brl
    }])

    st.download_button(
        "📥 Baixar dados (CSV)",
        df.to_csv(index=False),
        "resultado_credito_carbono.csv"
    )

else:
    st.info("➡️ Ajuste os parâmetros e clique em **Calcular**.")

# =========================================================
# RODAPÉ METODOLÓGICO
# =========================================================

st.markdown("""
---
**Notas metodológicas**
- Inventário: IPCC 2006 – Waste Sector  
- GWP: IPCC AR6 (20 anos)  
- Preço: referência EU ETS (ajustado para mercado voluntário)  
- Resultado representa **potencial econômico estimado**, não preço garantido.
""")
