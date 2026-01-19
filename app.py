import streamlit as st
import pandas as pd

from inventory import calcular_credito_carbono
from valuation import valorar_creditos

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================

st.set_page_config(
    page_title="Simulador de Créditos de Carbono – Compostagem",
    layout="wide"
)

st.title("🌱 Simulador de Créditos de Carbono")
st.markdown("""
Avaliação **técnica e econômica** do desvio de resíduos orgânicos
do aterro sanitário para compostagem.
""")

# =========================================================
# SIDEBAR – PARÂMETROS
# =========================================================

st.sidebar.header("⚙️ Parâmetros do Projeto")

massa = st.sidebar.number_input(
    "Massa anual de resíduos (t/ano)",
    min_value=100.0,
    max_value=1_000_000.0,
    value=12_000.0,
    step=500.0
)

tipo_residuo = st.sidebar.selectbox(
    "Tipo de resíduo",
    ["podas", "organico_domiciliar", "feira"]
)

executar = st.sidebar.button("🚀 Calcular")

# =========================================================
# EXECUÇÃO
# =========================================================

if executar:
    baseline, projeto, reducao = calcular_credito_carbono(
        massa_t=massa,
        tipo_residuo=tipo_residuo
    )

    valores = valorar_creditos(reducao)

    # =====================================================
    # RESULTADOS
    # =====================================================

    st.header("📊 Resultados Ambientais")

    col1, col2, col3 = st.columns(3)
    col1.metric("Baseline – Aterro", f"{baseline:,.0f} tCO₂e")
    col2.metric("Projeto – Compostagem", f"{projeto:,.0f} tCO₂e")
    col3.metric("Redução Líquida", f"{reducao:,.0f} tCO₂e")

    st.header("💰 Valoração Econômica (referência)")

    col1, col2, col3 = st.columns(3)
    col1.metric("Conservador (€5)", f"€ {valores['conservador']:,.0f}")
    col2.metric("Médio (€12)", f"€ {valores['medio']:,.0f}")
    col3.metric("Otimista (€25)", f"€ {valores['otimista']:,.0f}")

    # =====================================================
    # SAÍDA PARA BI
    # =====================================================

    df = pd.DataFrame({
        "residuo": [tipo_residuo],
        "massa_t_ano": [massa],
        "baseline_tco2e": [baseline],
        "projeto_tco2e": [projeto],
        "reducao_tco2e": [reducao],
        **{f"valor_{k}_eur": [v] for k, v in valores.items()}
    })

    st.download_button(
        "📥 Baixar dados (CSV)",
        df.to_csv(index=False),
        file_name="credito_carbono_compostagem.csv"
    )

else:
    st.info("➡️ Ajuste os parâmetros e clique em **Calcular**.")
