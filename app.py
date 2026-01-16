import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
from datetime import datetime

# =============================================================================
# CONFIGURAÇÕES DE PÁGINA E TEMA COMERCIAL
# =============================================================================

st.set_page_config(
    page_title="Carbon Simulator Pro | Enterprise",
    layout="wide",
    page_icon="🌍"
)

# CSS Customizado para Mobile-First e Design Profissional
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    :root {
        --primary: #0066cc;
        --secondary: #00cc99;
        --warning: #ffaa00;
        --danger: #ff5555;
        --bg-light: #f8fafc;
        --text-main: #0f172a;
    }

    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }

    /* Padding adaptativo */
    .block-container {
        padding: 2rem 1rem !important;
    }

    /* Header Profissional */
    .main-header {
        background: linear-gradient(135deg, #0066cc 0%, #00cc99 100%);
        padding: 3rem 1.5rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0, 102, 204, 0.15);
        text-align: center;
    }

    .main-header h1 {
        font-weight: 800;
        font-size: clamp(2rem, 6vw, 3.5rem) !important;
        margin-bottom: 0.5rem;
        color: white !important;
        letter-spacing: -1px;
    }

    /* Cards Responsivos */
    .metric-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 1.5rem;
        margin: 1rem 0;
    }

    .custom-card {
        background: white;
        padding: 1.8rem;
        border-radius: 16px;
        border-top: 5px solid var(--primary);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }

    .custom-card:hover { transform: translateY(-5px); box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); }
    .custom-card.success { border-top-color: var(--secondary); }

    .card-label { font-size: 0.85rem; font-weight: 600; color: #64748b; text-transform: uppercase; }
    .card-value { font-size: 2.2rem; font-weight: 800; color: var(--text-main); margin: 0.5rem 0; }

    /* Botão Estilo App Mobile */
    .stButton > button {
        width: 100%;
        background: var(--primary);
        color: white;
        border: none;
        padding: 1rem;
        border-radius: 12px;
        font-weight: 700;
        font-size: 1.1rem;
        margin-top: 1rem;
    }

    @media (max-width: 768px) {
        .card-value { font-size: 1.8rem; }
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# INICIALIZAÇÃO SEGURA (Prevenção de KeyError)
# =============================================================================

if 'cotacoes' not in st.session_state:
    st.session_state.cotacoes = {
        'carbono_eur': 88.42,
        'eur_brl': 6.15,
        'last_update': datetime.now().strftime("%H:%M")
    }

# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown("### 🛠️ Painel de Controle")
    
    # Uso de get() para evitar erros de chave faltante
    c_eur = st.session_state.cotacoes.get('carbono_eur', 85.0)
    e_brl = st.session_state.cotacoes.get('eur_brl', 6.0)

    with st.expander("💰 Mercado Financeiro", expanded=True):
        carbono = st.number_input("Preço Carbono (€)", value=float(c_eur), step=0.1)
        cambio = st.number_input("Câmbio EUR/BRL", value=float(e_brl), step=0.01)
    
    with st.expander("🌱 Parâmetros Técnicos", expanded=False):
        st.slider("Temperatura Local (°C)", 10, 40, 25)
        st.slider("Umidade (%)", 40, 95, 80)

# =============================================================================
# CONTEÚDO PRINCIPAL
# =============================================================================

st.markdown(f"""
<div class="main-header">
    <h1>Carbon Simulator Pro</h1>
    <p>Inteligência de dados para o mercado de carbono</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📊 Simulador", "📈 Projeções"])

with tab1:
    col_in, col_out = st.columns([1, 1.5])
    
    with col_in:
        st.subheader("Configuração do Lote")
        toneladas = st.number_input("Volume de Orgânicos (Toneladas)", min_value=0.0, value=100.0)
        
        # Botão com largura total
        if st.button("CALCULAR RESULTADOS"):
            st.success("Cálculo realizado com sucesso!")

    with col_out:
        # Lógica de cálculo
        total_co2 = toneladas * 1.25 # Fator hipotético IPCC
        receita = total_co2 * carbono * cambio

        st.markdown(f"""
        <div class="metric-container">
            <div class="custom-card">
                <div class="card-label">Créditos Gerados</div>
                <div class="card-value">{total_co2:,.2f}</div>
                <div style="color:var(--primary); font-weight:bold;">tCO₂eq Totais</div>
            </div>
            <div class="custom-card success">
                <div class="card-label">Valor de Mercado</div>
                <div class="card-value">R$ {receita:,.2f}</div>
                <div style="color:var(--secondary); font-weight:bold;">Receita Estimada</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

with tab2:
    st.subheader("Análise Temporal de Ativos")
    df = pd.DataFrame({
        'Ano': [1, 2, 3, 4, 5],
        'Receita': [receita * i for i in range(1, 6)]
    })
    
    fig = px.bar(df, x='Ano', y='Receita', 
                 color_discrete_sequence=['#0066cc'],
                 title="Acúmulo de Créditos em 5 Anos")
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=40, b=0)
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption(f"© 2026 Carbon Simulator Pro | Enterprise Edition")
