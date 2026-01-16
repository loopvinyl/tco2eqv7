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
    /* Importação de fonte moderna */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    :root {
        --primary: #0066cc;
        --secondary: #00cc99;
        --warning: #ffaa00;
        --danger: #ff5555;
        --bg-light: #f8fafc;
        --text-main: #0f172a;
    }

    /* Ajuste de Fonte Global */
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }

    /* Container Principal - Padding adaptativo para mobile */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }

    /* Header Profissional e Responsivo */
    .main-header {
        background: linear-gradient(135deg, #0066cc 0%, #00cc99 100%);
        padding: 2.5rem 1.5rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px rgba(0, 102, 204, 0.2);
        text-align: center;
    }

    .main-header h1 {
        font-weight: 800;
        font-size: clamp(1.8rem, 5vw, 3rem) !important;
        margin-bottom: 0.5rem;
        color: white !important;
    }

    .main-header p {
        font-size: clamp(0.9rem, 2vw, 1.1rem);
        opacity: 0.9;
    }

    /* Grid de Cards Responsivo */
    .metric-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1.5rem;
        margin-bottom: 2rem;
    }

    .custom-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 6px solid var(--primary);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease;
    }

    .custom-card:hover {
        transform: translateY(-4px);
    }

    .custom-card.success { border-left-color: var(--secondary); }
    .custom-card.warning { border-left-color: var(--warning); }

    .card-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .card-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: var(--text-main);
        margin: 0.5rem 0;
    }

    /* Botões Modernos */
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #0066cc 0%, #004d99 100%);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        opacity: 0.9;
        box-shadow: 0 4px 12px rgba(0, 102, 204, 0.4);
    }

    /* Ajustes para Mobile (Telas < 768px) */
    @media (max-width: 768px) {
        .main-header { padding: 1.5rem 1rem; }
        .stTabs [data-baseweb="tab"] { font-size: 0.8rem; padding: 0.5rem; }
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# LÓGICA DE DADOS
# =============================================================================

if 'cotacoes' not in st.session_state:
    st.session_state.cotacoes = {
        'carbono_eur': 88.42,
        'eur_brl': 6.15,
        'last_update': datetime.now().strftime("%H:%M")
    }

# =============================================================================
# SIDEBAR (Foco em Parâmetros)
# =============================================================================

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1829/1829589.png", width=80)
    st.title("Configurações")
    
    with st.expander("💰 Mercado Financeiro", expanded=True):
        carbono = st.number_input("Preço Carbono (€)", value=st.session_state.cotacoes['carbono_eur'])
        cambio = st.number_input("Câmbio EUR/BRL", value=st.session_state.cotacoes['eur_brl'])
    
    with st.expander("🌱 Parâmetros Técnicos", expanded=False):
        temp = st.slider("Temp. Média Local (°C)", 10, 40, 25)
        umidade = st.slider("Umidade do Resíduo (%)", 40, 95, 80)

# =============================================================================
# LAYOUT PRINCIPAL
# =============================================================================

# Header adaptativo
st.markdown(f"""
<div class="main-header">
    <h1>Carbon Simulator Pro</h1>
    <p>Tecnologia para gestão de ativos ambientais e créditos de carbono</p>
</div>
""", unsafe_allow_html=True)

# Tabs com ícones (Melhor UX)
tab1, tab2 = st.tabs(["📊 Simulador", "📈 Projeção Comercial"])

with tab1:
    # Layout em colunas que se empilham no mobile automaticamente pelo Streamlit
    col_input, col_space, col_output = st.columns([1, 0.1, 1.5])
    
    with col_input:
        st.subheader("Entrada de Volume")
        toneladas = st.number_input("Resíduos Orgânicos (Toneladas)", min_value=0.0, value=100.0, step=10.0)
        st.info(f"Cotação atual: R$ {carbono * cambio:.2f} / tCO2eq")
        
        # O botão agora ocupa 100% da largura da coluna
        calcular = st.button("CALCULAR IMPACTO")

    with col_output:
        # Simulando cálculo IPCC simplificado
        fator_emissao = 1.25 # Exemplo: tCO2eq por tonelada de resíduo evitado
        total_co2 = toneladas * fator_emissao
        receita_estimada = total_co2 * carbono * cambio

        # Grid de Cards Customizados
        st.markdown(f"""
        <div class="metric-container">
            <div class="custom-card">
                <div class="card-label">Créditos Gerados</div>
                <div class="card-value">{total_co2:,.2f}</div>
                <div style="color:var(--primary); font-size:0.8rem; font-weight:bold;">tCO₂eq Estimadas</div>
            </div>
            <div class="custom-card success">
                <div class="card-label">Potencial Financeiro</div>
                <div class="card-value">R$ {receita_estimada:,.20n}</div>
                <div style="color:var(--secondary); font-size:0.8rem; font-weight:bold;">Receita Bruta Estimada</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

with tab2:
    st.subheader("Análise de ROI (Retorno sobre Investimento)")
    
    # Gráfico responsivo do Plotly
    anos = [1, 2, 3, 4, 5]
    receita_acumulada = [receita_estimada * i for i in anos]
    custo_estimado = [receita_estimada * 0.3 * i for i in anos] # 30% custo op

    fig = px.area(
        x=anos, 
        y=[receita_acumulada, custo_estimado],
        labels={'x': 'Anos de Operação', 'value': 'Valor (R$)'},
        color_discrete_sequence=['#00cc99', '#ff5555'],
        title="Projeção Financeira de 5 Anos"
    )
    
    fig.update_layout(
        legend_title_text='Legenda',
        margin=dict(l=20, r=20, t=50, b=20),
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Footer simples
st.markdown("---")
st.caption(f"Dados atualizados às {st.session_state.cotacoes['last_update']} | Carbon Simulator Pro © 2026")
