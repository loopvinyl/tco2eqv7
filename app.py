import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import seaborn as sns
from scipy import stats
from scipy.signal import fftconvolve
import warnings
from matplotlib.ticker import FuncFormatter
from io import BytesIO
import requests
import unicodedata
from bs4 import BeautifulSoup
import time
import json
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# =============================================================================
# CONFIGURAÇÕES INICIAIS
# =============================================================================

st.set_page_config(
    page_title="CARBON SIMULATOR PRO | Análise de Créditos de Carbono", 
    layout="wide",
    page_icon="🌱",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/',
        'Report a bug': 'https://github.com/',
        'About': '### Carbon Simulator Pro\nPlataforma completa para análise de créditos de carbono via gestão sustentável de resíduos'
    }
)

# Configurar tema com cores profissionais modernas
st.markdown("""
<style>
    /* ===== TEMA PROFISSIONAL MODERNO ===== */
    :root {
        --primary-dark: #0A2647;
        --primary-blue: #144272;
        --primary-light: #205295;
        --accent-teal: #2C7865;
        --accent-green: #90D26D;
        --neutral-dark: #2D3748;
        --neutral-gray: #4A5568;
        --neutral-light: #EDF2F7;
        --card-white: #FFFFFF;
        --success: #38A169;
        --warning: #D69E2E;
        --error: #E53E3E;
        --info: #3182CE;
        --sidebar-width: 300px;
        --border-radius: 12px;
        --shadow-sm: 0 2px 8px rgba(0,0,0,0.06);
        --shadow-md: 0 4px 16px rgba(0,0,0,0.1);
        --shadow-lg: 0 8px 24px rgba(0,0,0,0.12);
        --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* ===== RESET E BASE ===== */
    .main {
        background: linear-gradient(135deg, #F7FAFC 0%, #EDF2F7 100%);
        min-height: 100vh;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* ===== HEADER PRINCIPAL ===== */
    .main-header {
        background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary-blue) 100%);
        padding: 2.5rem 3rem;
        border-radius: var(--border-radius);
        color: white;
        margin-bottom: 2.5rem;
        box-shadow: var(--shadow-lg);
        position: relative;
        overflow: hidden;
    }
    
    .main-header::after {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 100%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px);
        background-size: 20px 20px;
        opacity: 0.1;
        animation: gridMove 20s linear infinite;
    }
    
    @keyframes gridMove {
        0% { transform: translate(0, 0); }
        100% { transform: translate(20px, 20px); }
    }
    
    /* ===== MENU DE NAVEGAÇÃO VISÍVEL ===== */
    .nav-container {
        background: var(--card-white);
        border-radius: var(--border-radius);
        padding: 1rem;
        margin-bottom: 2rem;
        box-shadow: var(--shadow-sm);
        border: 1px solid rgba(0,0,0,0.05);
    }
    
    /* ===== CARDS MODERNOS ===== */
    .dashboard-card {
        background: var(--card-white);
        border-radius: var(--border-radius);
        padding: 2rem;
        margin-bottom: 1.5rem;
        box-shadow: var(--shadow-md);
        border: 1px solid rgba(0,0,0,0.03);
        transition: var(--transition);
        height: 100%;
    }
    
    .dashboard-card:hover {
        box-shadow: var(--shadow-lg);
        transform: translateY(-2px);
    }
    
    .stat-card {
        background: linear-gradient(135deg, var(--card-white) 0%, #F8FAFC 100%);
        border-radius: var(--border-radius);
        padding: 1.75rem;
        border-left: 4px solid var(--primary-blue);
        box-shadow: var(--shadow-sm);
        height: 100%;
    }
    
    .stat-card.success { border-left-color: var(--success); }
    .stat-card.warning { border-left-color: var(--warning); }
    .stat-card.error { border-left-color: var(--error); }
    .stat-card.info { border-left-color: var(--info); }
    
    /* ===== BOTÕES MODERNOS ===== */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--primary-light) 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.875rem 1.75rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: var(--transition) !important;
        box-shadow: 0 4px 12px rgba(20, 66, 114, 0.2) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(20, 66, 114, 0.3) !important;
        background: linear-gradient(135deg, var(--primary-light) 0%, var(--primary-blue) 100%) !important;
    }
    
    /* ===== SIDEBAR MODERNA ===== */
    [data-testid="stSidebar"] {
        background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary-blue) 100%);
        padding-top: 2rem;
    }
    
    [data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, var(--accent-teal) 0%, #3AA69B 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.875rem 1.5rem !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stSidebar"] .stButton > button:hover {
        background: linear-gradient(135deg, #3AA69B 0%, var(--accent-teal) 100%) !important;
        transform: translateY(-1px) !important;
    }
    
    /* ===== BADGES MODERNOS ===== */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 0.375rem 1rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        gap: 0.5rem;
    }
    
    .badge-success {
        background: linear-gradient(135deg, var(--success) 0%, #48BB78 100%);
        color: white;
    }
    
    .badge-warning {
        background: linear-gradient(135deg, var(--warning) 0%, #ECC94B 100%);
        color: white;
    }
    
    .badge-info {
        background: linear-gradient(135deg, var(--info) 0%, #63B3ED 100%);
        color: white;
    }
    
    .badge-error {
        background: linear-gradient(135deg, var(--error) 0%, #FC8181 100%);
        color: white;
    }
    
    .badge-premium {
        background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary-blue) 100%);
        color: white;
    }
    
    /* ===== TIPOGRAFIA MODERNA ===== */
    h1 {
        font-size: 2.75rem;
        font-weight: 800;
        color: white;
        margin: 0 0 0.5rem 0;
        line-height: 1.2;
    }
    
    h2 {
        font-size: 1.875rem;
        font-weight: 700;
        color: var(--primary-dark);
        margin: 0 0 1.5rem 0;
        position: relative;
        padding-bottom: 0.75rem;
    }
    
    h2::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        width: 60px;
        height: 4px;
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--accent-teal) 100%);
        border-radius: 2px;
    }
    
    h3 {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--neutral-dark);
        margin: 0 0 1rem 0;
    }
    
    /* ===== STATUS INDICATORS ===== */
    .status-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 0.5rem;
        background: var(--success);
    }
    
    .status-active {
        background: var(--success);
    }
    
    /* ===== SCROLLBAR PERSONALIZADA ===== */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f5f9;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--accent-teal) 100%);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, var(--primary-light) 0%, var(--primary-blue) 100%);
    }
</style>
""", unsafe_allow_html=True)

warnings.filterwarnings("ignore")
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
np.seterr(divide='ignore', invalid='ignore')
plt.rcParams['figure.dpi'] = 150
plt.rcParams['font.size'] = 10
sns.set_style("whitegrid")

# =============================================================================
# CONSTANTES GLOBAIS
# =============================================================================

# GWP-20 (IPCC AR6)
GWP_CH4_20 = 82.5
GWP_N2O_20 = 273
GWP_CH4_100 = 29.8
GWP_N2O_100 = 273

# Parâmetros IPCC 2006
DOC = 0.15
MCF = 1.0
F = 0.5
OX = 0.1
Ri = 0.0
k_ano = 0.06

# Parâmetros compostagem (Yang et al. 2017)
TOC_YANG = 0.436
TN_YANG = 14.2 / 1000
CH4_C_FRAC_YANG = 0.13 / 100
N2O_N_FRAC_YANG = 0.92 / 100

# =============================================================================
# FUNÇÕES DE FORMATTAÇÃO E UTILITÁRIAS
# =============================================================================

def formatar_br(numero):
    """Formata números no padrão brasileiro: 1.234,56"""
    if pd.isna(numero) or numero is None:
        return "N/A"
    numero = round(float(numero), 2)
    return f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_br_dec(numero, decimais=2):
    """Formata números com número específico de casas decimais"""
    if pd.isna(numero) or numero is None:
        return "N/A"
    numero = round(float(numero), decimais)
    return f"{numero:,.{decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def criar_metric_card(titulo, valor, subtitulo="", tipo="info", icon=""):
    """Cria um card de métrica estilizado"""
    cores = {
        "info": "#3182CE",
        "success": "#38A169",
        "warning": "#D69E2E",
        "error": "#E53E3E",
        "premium": "#144272"
    }
    
    cor = cores.get(tipo, "#3182CE")
    icon_html = f'<div style="font-size: 2rem; margin-bottom: 1rem; color: {cor};">{icon}</div>' if icon else ""
    
    html = f"""
    <div class="stat-card {tipo}">
        {icon_html}
        <div style="font-size: 0.875rem; color: #4A5568; margin-bottom: 0.5rem; font-weight: 600; letter-spacing: 0.5px;">{titulo}</div>
        <div style="font-size: 2rem; font-weight: 700; color: #2D3748; line-height: 1.2; margin: 0.5rem 0;">{valor}</div>
        <div style="font-size: 0.875rem; color: #718096; margin-top: 0.5rem;">{subtitulo}</div>
    </div>
    """
    return html

def criar_badge(texto, tipo="info"):
    """Cria um badge estilizado"""
    return f'<span class="badge badge-{tipo}">{texto}</span>'

# =============================================================================
# FUNÇÕES DE COTAÇÃO EM TEMPO REAL
# =============================================================================

def obter_cotacao_carbono():
    """Obtém cotação do carbono com fallback seguro"""
    try:
        url = "https://www.investing.com/commodities/carbon-emissions"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Múltiplas estratégias para encontrar o preço
        selectores = [
            '[data-test="instrument-price-last"]',
            '.text-2xl',
            '.last-price-value',
            '.instrument-price-last',
            '.pid-1062510-last',
            '#last_last'
        ]
        
        for seletor in selectores:
            elemento = soup.select_one(seletor)
            if elemento:
                texto = elemento.text.strip().replace(',', '')
                numeros = ''.join(c for c in texto if c.isdigit() or c == '.')
                if numeros:
                    preco = float(numeros)
                    if 50 < preco < 200:
                        return preco, "€", "Investing.com", True
        
        return 85.50, "€", "Referência", False
        
    except Exception as e:
        return 85.50, "€", f"Erro: {str(e)[:30]}", False

def obter_cotacao_euro():
    """Obtém cotação EUR/BRL com múltiplas fontes"""
    fontes = [
        ("https://economia.awesomeapi.com.br/last/EUR-BRL", "AwesomeAPI"),
        ("https://api.bcb.gov.br/dados/serie/bcdata.sgs.21619/dados/ultimos/1?formato=json", "BCB"),
    ]
    
    for url, fonte in fontes:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                if "awesomeapi" in url:
                    data = response.json()
                    return float(data['EURBRL']['bid']), True, fonte
                elif "bcb" in url:
                    data = response.json()
                    return float(data[0]['valor']), True, fonte
        except:
            continue
    
    return 5.50, False, "Referência"

# =============================================================================
# FUNÇÕES DE CÁLCULO CENTRAIS
# =============================================================================

def calcular_potencial_metano_aterro_lote(residuos_kg, umidade, temperatura, anos=20):
    """Calcula potencial de metano para UM ÚNICO LOTE ao longo do tempo"""
    dias = anos * 365
    DOCf = 0.0147 * temperatura + 0.28
    potencial_CH4_total = residuos_kg * DOC * DOCf * MCF * F * (16/12) * (1 - Ri) * (1 - OX)
    k_dia = k_ano / 365.0
    t = np.arange(1, dias + 1, dtype=float)
    kernel = np.exp(-k_dia * (t - 1)) - np.exp(-k_dia * t)
    kernel = np.maximum(kernel, 0)
    emissoes_CH4 = potencial_CH4_total * kernel
    return emissoes_CH4, potencial_CH4_total, DOCf

def calcular_emissoes_aterro_continuo(residuos_kg_dia, umidade, temperatura, anos=20):
    """Calcula emissões de aterro para ENTRADA CONTÍNUA diária"""
    dias = anos * 365
    DOCf = 0.0147 * temperatura + 0.28
    potencial_CH4_por_kg = DOC * DOCf * MCF * F * (16/12) * (1 - Ri) * (1 - OX)
    potencial_CH4_diario = residuos_kg_dia * potencial_CH4_por_kg
    k_dia = k_ano / 365.0
    t = np.arange(1, dias + 1, dtype=float)
    kernel_ch4 = np.exp(-k_dia * (t - 1)) - np.exp(-k_dia * t)
    entradas_diarias = np.ones(dias) * potencial_CH4_diario
    emissoes_CH4 = fftconvolve(entradas_diarias, kernel_ch4, mode='full')[:dias]
    return emissoes_CH4, potencial_CH4_diario

def calcular_emissoes_vermicompostagem_lote(residuos_kg, umidade):
    """Calcula emissões de metano para vermicompostagem (50 dias)"""
    fracao_ms = 1 - umidade
    ch4_total = residuos_kg * (TOC_YANG * CH4_C_FRAC_YANG * (16/12) * fracao_ms)
    dias = 50
    perfil = np.ones(dias) / dias
    return ch4_total * perfil, ch4_total

def calcular_creditos_carbono(emissoes_aterro, emissoes_vermi, preco_carbono_eur, taxa_cambio, 
                            anos=20, usar_gwp_20=True):
    """
    Calcula créditos de carbono usando GWP-20 ou GWP-100
    """
    gwp_ch4 = GWP_CH4_20 if usar_gwp_20 else GWP_CH4_100
    co2eq_aterro = emissoes_aterro * gwp_ch4 / 1000
    co2eq_vermi = emissoes_vermi * gwp_ch4 / 1000
    co2eq_evitado = co2eq_aterro.sum() - co2eq_vermi.sum()
    valor_eur = co2eq_evitado * preco_carbono_eur
    valor_brl = valor_eur * taxa_cambio
    valor_anual_eur = valor_eur / anos
    valor_anual_brl = valor_brl / anos
    
    return {
        'co2eq_aterro_total': co2eq_aterro.sum(),
        'co2eq_vermi_total': co2eq_vermi.sum(),
        'co2eq_evitado_total': co2eq_evitado,
        'co2eq_evitado_anual': co2eq_evitado / anos,
        'valor_total_eur': valor_eur,
        'valor_total_brl': valor_brl,
        'valor_anual_eur': valor_anual_eur,
        'valor_anual_brl': valor_anual_brl,
        'emissoes_evitadas_kg_ch4': (emissoes_aterro.sum() - emissoes_vermi.sum()),
        'gwp_utilizado': '20 anos' if usar_gwp_20 else '100 anos'
    }

# =============================================================================
# INICIALIZAÇÃO DA SESSION STATE
# =============================================================================

if 'cotacoes' not in st.session_state:
    preco_carbono, moeda_carbono, fonte_carbono, sucesso_carbono = obter_cotacao_carbono()
    taxa_cambio, sucesso_cambio, fonte_cambio = obter_cotacao_euro()
    
    st.session_state.cotacoes = {
        'preco_carbono': preco_carbono,
        'moeda_carbono': moeda_carbono,
        'fonte_carbono': fonte_carbono,
        'taxa_cambio': taxa_cambio,
        'fonte_cambio': fonte_cambio,
        'preco_carbono_brl': preco_carbono * taxa_cambio,
        'timestamp': datetime.now()
    }

if 'parametros_globais' not in st.session_state:
    st.session_state.parametros_globais = {
        'temperatura': 25.0,
        'umidade': 0.85,
        'gwp_periodo': '20 anos',
        'usar_gwp_20': True
    }

if 'resultados_lote' not in st.session_state:
    st.session_state.resultados_lote = None

if 'resultados_continuo' not in st.session_state:
    st.session_state.resultados_continuo = None

if 'aba_atual' not in st.session_state:
    st.session_state.aba_atual = "lote_unico"

# =============================================================================
# HEADER PRINCIPAL
# =============================================================================

# Header com design moderno
st.markdown("""
<div class="main-header">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem;">
        <div style="display: flex; align-items: center; gap: 1.5rem;">
            <div style="font-size: 3rem;">🌱</div>
            <div>
                <h1>CARBON SIMULATOR PRO</h1>
                <p style="margin: 0; opacity: 0.9; font-size: 1.1rem; font-weight: 400; max-width: 600px;">
                    Plataforma avançada para análise e gestão de créditos de carbono
                </p>
            </div>
        </div>
        <div style="display: flex; gap: 0.75rem;">
            <span class="badge badge-premium">PROFISSIONAL</span>
            <span class="badge badge-success">IPCC 2021</span>
            <span class="badge badge-info">EM TEMPO REAL</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# BARRA LATERAL MODERNA
# =============================================================================

with st.sidebar:
    st.markdown("""
    <div style="margin-bottom: 2.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
            <div style="font-size: 1.5rem; color: white;">⚙️</div>
            <h3 style="margin: 0; color: white; font-weight: 600;">CONTROLES</h3>
        </div>
        <p style="color: rgba(255,255,255,0.8); font-size: 0.9rem; margin: 0;">
            Configure os parâmetros do sistema e acesse funcionalidades avançadas
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Seção de cotações
    st.markdown('<div style="color: white; font-size: 1rem; font-weight: 600; margin-bottom: 1rem;">💎 COTAÇÕES DO MERCADO</div>', unsafe_allow_html=True)
    
    cotacoes = st.session_state.cotacoes
    preco_carbono = cotacoes.get('preco_carbono', 85.50)
    taxa_cambio = cotacoes.get('taxa_cambio', 5.50)
    preco_carbono_brl = preco_carbono * taxa_cambio
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label="Carbono (EUA)",
            value=f"€ {formatar_br(preco_carbono)}",
            help=f"Fonte: {cotacoes.get('fonte_carbono', 'Referência')}",
            label_visibility="visible"
        )
    
    with col2:
        st.metric(
            label="Câmbio EUR/BRL",
            value=f"R$ {formatar_br(taxa_cambio)}",
            help=f"Fonte: {cotacoes.get('fonte_cambio', 'Referência')}",
            label_visibility="visible"
        )
    
    st.markdown(f"""
    <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px; margin: 1rem 0; border: 1px solid rgba(255,255,255,0.1);">
        <div style="color: white; font-size: 0.875rem; margin-bottom: 0.25rem;">Valor no Brasil</div>
        <div style="color: #90D26D; font-size: 1.25rem; font-weight: 700;">R$ {formatar_br(preco_carbono_brl)}/tCO₂eq</div>
        <div style="color: rgba(255,255,255,0.7); font-size: 0.75rem; margin-top: 0.25rem;">Atualizado: {cotacoes.get('timestamp', datetime.now()).strftime('%H:%M')}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Parâmetros ambientais
    st.markdown('<div style="color: white; font-size: 1rem; font-weight: 600; margin-bottom: 1rem;">🌡️ PARÂMETROS AMBIENTAIS</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        temperatura = st.slider(
            "Temperatura (°C)",
            min_value=15.0,
            max_value=35.0,
            value=25.0,
            step=0.5,
            help="Temperatura média anual local",
            key="sidebar_temp"
        )
    
    with col2:
        umidade_valor = st.slider(
            "Umidade (%)",
            min_value=50.0,
            max_value=95.0,
            value=85.0,
            step=1.0,
            help="Teor de umidade dos resíduos",
            key="sidebar_umid"
        )
    umidade = umidade_valor / 100.0
    
    st.session_state.parametros_globais['temperatura'] = temperatura
    st.session_state.parametros_globais['umidade'] = umidade
    
    # Período do GWP
    st.markdown('<div style="color: white; font-size: 1rem; font-weight: 600; margin: 1.5rem 0 1rem 0;">📊 METODOLOGIA GWP</div>', unsafe_allow_html=True)
    
    gwp_periodo = st.selectbox(
        "Período de Análise",
        options=["20 anos (GWP-20)", "100 anos (GWP-100)"],
        index=0,
        help="GWP-20 é mais conservador para créditos de curto prazo",
        label_visibility="collapsed"
    )
    
    usar_gwp_20 = gwp_periodo == "20 anos (GWP-20)"
    st.session_state.parametros_globais['gwp_periodo'] = gwp_periodo
    st.session_state.parametros_globais['usar_gwp_20'] = usar_gwp_20
    
    with st.expander("ℹ️ Sobre o GWP", expanded=False):
        st.markdown(f"""
        **GWP-20 (20 anos):** 
        - Metano (CH₄): **{GWP_CH4_20}**
        - Óxido Nitroso (N₂O): **{GWP_N2O_20}**
        
        **GWP-100 (100 anos):**
        - Metano (CH₄): **{GWP_CH4_100}**
        - Óxido Nitroso (N₂O): **{GWP_N2O_100}**
        
        *Fonte: IPCC AR6 (2021)*
        
        **Recomendação:** GWP-20 para créditos de curto prazo.
        """)
    
    st.markdown("---")
    
    # Ações
    st.markdown('<div style="color: white; font-size: 1rem; font-weight: 600; margin-bottom: 1rem;">⚡ AÇÕES RÁPIDAS</div>', unsafe_allow_html=True)
    
    if st.button("🔄 Atualizar Cotações", use_container_width=True, type="primary"):
        with st.spinner("Atualizando dados do mercado..."):
            preco_carbono, moeda_carbono, fonte_carbono, sucesso_carbono = obter_cotacao_carbono()
            taxa_cambio, sucesso_cambio, fonte_cambio = obter_cotacao_euro()
            
            st.session_state.cotacoes = {
                'preco_carbono': preco_carbono,
                'moeda_carbono': moeda_carbono,
                'fonte_carbono': fonte_carbono,
                'taxa_cambio': taxa_cambio,
                'fonte_cambio': fonte_cambio,
                'preco_carbono_brl': preco_carbono * taxa_cambio,
                'timestamp': datetime.now()
            }
            st.success("✅ Dados atualizados!")
            st.rerun()
    
    st.markdown("---")
    
    # Informações técnicas
    data_atual = datetime.now().strftime('%d/%m/%Y')
    st.markdown(f"""
    <div style="margin-top: 2rem;">
        <div style="color: white; font-size: 0.875rem; margin-bottom: 0.5rem; opacity: 0.8;">SISTEMA</div>
        <div style="color: white; font-size: 0.75rem; line-height: 1.4; opacity: 0.7;">
            <div style="display: flex; align-items: center; margin-bottom: 0.25rem;">
                <span class="status-dot status-active"></span>
                <span>Status: Online</span>
            </div>
            <div>v2.1.0 • {data_atual}</div>
            <div>IPCC 2006 + Yang 2017</div>
            <div style="margin-top: 0.5rem;">© 2024 Carbon Simulator Pro</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# MENU DE NAVEGAÇÃO PRINCIPAL - SIMPLIFICADO
# =============================================================================

# Criar um container visível para o menu
st.markdown("""
<div class="nav-container">
    <h3 style="margin: 0 0 1rem 0; color: #0A2647; text-align: center;">NAVEGAÇÃO PRINCIPAL</h3>
""", unsafe_allow_html=True)

# Criar 4 botões de navegação usando colunas
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button(
        "📦 LOTE ÚNICO",
        use_container_width=True,
        type="primary" if st.session_state.aba_atual == "lote_unico" else "secondary",
        key="nav_lote"
    ):
        st.session_state.aba_atual = "lote_unico"
        st.rerun()

with col2:
    if st.button(
        "📈 ENTRADA CONTÍNUA",
        use_container_width=True,
        type="primary" if st.session_state.aba_atual == "entrada_continua" else "secondary",
        key="nav_continuo"
    ):
        st.session_state.aba_atual = "entrada_continua"
        st.rerun()

with col3:
    if st.button(
        "🏙️ ANÁLISE MUNICIPAL",
        use_container_width=True,
        type="primary" if st.session_state.aba_atual == "analise_municipal" else "secondary",
        key="nav_municipal"
    ):
        st.session_state.aba_atual = "analise_municipal"
        st.rerun()

with col4:
    if st.button(
        "📊 RELATÓRIOS",
        use_container_width=True,
        type="primary" if st.session_state.aba_atual == "relatorios" else "secondary",
        key="nav_relatorios"
    ):
        st.session_state.aba_atual = "relatorios"
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# =============================================================================
# CONTEÚDO DAS ABAS
# =============================================================================

if st.session_state.aba_atual == "lote_unico":
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    
    st.markdown("### 📦 Análise de Lote Único")
    st.markdown("Calcule o potencial de créditos de carbono para um único lote de resíduos orgânicos")
    
    # Layout principal
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### Configuração do Lote")
        
        col1_1, col1_2 = st.columns(2)
        with col1_1:
            quantidade_lote = st.number_input(
                "Peso do lote (kg)",
                min_value=10.0,
                max_value=10000.0,
                value=100.0,
                step=10.0,
                help="Peso total do lote de resíduos orgânicos",
                key="qtd_lote_main"
            )
        
        with col1_2:
            anos_analise = st.slider(
                "Período de análise (anos)",
                min_value=1,
                max_value=30,
                value=20,
                help="Horizonte temporal para cálculo",
                key="anos_lote_main"
            )
        
        # Botão de cálculo sempre visível
        st.markdown("###")
        calcular_lote = st.button(
            "📊 CALCULAR POTENCIAL", 
            type="primary",
            use_container_width=True,
            key="btn_calc_main"
        )
    
    with col2:
        st.markdown("#### Parâmetros Atuais")
        
        st.markdown(f"""
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem;">
            <div class="stat-card info">
                <div style="font-size: 0.875rem; color: #4A5568; margin-bottom: 0.5rem; font-weight: 600;">TEMPERATURA</div>
                <div style="font-size: 1.5rem; font-weight: 700; color: #2D3748;">{temperatura}°C</div>
            </div>
            <div class="stat-card info">
                <div style="font-size: 0.875rem; color: #4A5568; margin-bottom: 0.5rem; font-weight: 600;">UMIDADE</div>
                <div style="font-size: 1.5rem; font-weight: 700; color: #2D3748;">{umidade_valor}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="stat-card premium">
            <div style="font-size: 0.875rem; color: #4A5568; margin-bottom: 0.5rem; font-weight: 600;">METODOLOGIA</div>
            <div style="font-size: 1.25rem; font-weight: 700; color: #2D3748;">{gwp_periodo.split('(')[0].strip()}</div>
            <div style="font-size: 0.875rem; color: #718096; margin-top: 0.5rem;">IPCC AR6 2021</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Verificar se o botão foi pressionado ou se já existem resultados
    if calcular_lote or st.session_state.resultados_lote is not None:
        if calcular_lote:
            with st.spinner("🔍 Analisando potencial de créditos..."):
                # Obter parâmetros
                cotacoes = st.session_state.cotacoes
                parametros = st.session_state.parametros_globais
                
                # Calcular emissões
                emissoes_aterro, potencial_total, docf = calcular_potencial_metano_aterro_lote(
                    quantidade_lote, umidade, temperatura, anos_analise
                )
                
                emissoes_vermi, total_vermi = calcular_emissoes_vermicompostagem_lote(
                    quantidade_lote, umidade
                )
                
                # Estender emissões da vermicompostagem
                emissoes_vermi_completa = np.zeros(len(emissoes_aterro))
                dias_vermi = min(50, len(emissoes_vermi))
                emissoes_vermi_completa[:dias_vermi] = emissoes_vermi[:dias_vermi]
                
                # Calcular créditos
                resultados = calcular_creditos_carbono(
                    emissoes_aterro, emissoes_vermi_completa,
                    cotacoes.get('preco_carbono', 85.50), 
                    cotacoes.get('taxa_cambio', 5.50), 
                    anos_analise,
                    usar_gwp_20=parametros['usar_gwp_20']
                )
                
                st.session_state.resultados_lote = resultados
        
        # Mostrar resultados se existirem
        if st.session_state.resultados_lote:
            resultados = st.session_state.resultados_lote
            
            # ==================== RESULTADOS ====================
            st.markdown("---")
            st.markdown("### 📈 Resultados da Análise")
            
            # Métricas principais em grid
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(criar_metric_card(
                    "Créditos Gerados",
                    formatar_br(resultados['co2eq_evitado_total']),
                    f"tCO₂eq | {resultados['gwp_utilizado']}",
                    "success",
                    "💰"
                ), unsafe_allow_html=True)
            
            with col2:
                st.markdown(criar_metric_card(
                    "Valor Estimado",
                    f"R$ {formatar_br(resultados['valor_total_brl'])}",
                    f"€ {formatar_br(resultados['valor_total_eur'])}",
                    "premium",
                    "💵"
                ), unsafe_allow_html=True)
            
            with col3:
                valor_por_kg = resultados['valor_total_brl'] / quantidade_lote
                st.markdown(criar_metric_card(
                    "Valor por kg",
                    f"R$ {formatar_br(valor_por_kg)}",
                    "por kg de resíduo",
                    "info",
                    "⚖️"
                ), unsafe_allow_html=True)
            
            with col4:
                st.markdown(criar_metric_card(
                    "Metano Evitado",
                    formatar_br(resultados['emissoes_evitadas_kg_ch4']),
                    "kg CH₄ reduzidos",
                    "warning",
                    "🌿"
                ), unsafe_allow_html=True)
            
            # ==================== GRÁFICOS ====================
            st.markdown("---")
            st.markdown("### 📊 Visualizações")
            
            # Calcular novamente para os gráficos
            emissoes_aterro, potencial_total, docf = calcular_potencial_metano_aterro_lote(
                quantidade_lote, umidade, temperatura, anos_analise
            )
            
            emissoes_vermi, total_vermi = calcular_emissoes_vermicompostagem_lote(
                quantidade_lote, umidade
            )
            
            emissoes_vermi_completa = np.zeros(len(emissoes_aterro))
            dias_vermi = min(50, len(emissoes_vermi))
            emissoes_vermi_completa[:dias_vermi] = emissoes_vermi[:dias_vermi]
            
            # Gráfico 1: Comparação de Emissões
            datas = pd.date_range(start=datetime.now(), periods=len(emissoes_aterro), freq='D')
            df_emissoes = pd.DataFrame({
                'Data': datas,
                'Aterro - CH₄ (kg/dia)': emissoes_aterro,
                'Vermicompostagem - CH₄ (kg/dia)': emissoes_vermi_completa,
            })
            
            fig1 = go.Figure()
            
            fig1.add_trace(go.Scatter(
                x=df_emissoes['Data'],
                y=df_emissoes['Aterro - CH₄ (kg/dia)'],
                name='Aterro Sanitário',
                line=dict(color='#E53E3E', width=2.5),
                fill='tozeroy',
                fillcolor='rgba(229, 62, 62, 0.1)',
                hovertemplate='<b>Aterro</b><br>Data: %{x}<br>CH₄: %{y:.3f} kg/dia<extra></extra>'
            ))
            
            fig1.add_trace(go.Scatter(
                x=df_emissoes['Data'],
                y=df_emissoes['Vermicompostagem - CH₄ (kg/dia)'],
                name='Vermicompostagem',
                line=dict(color='#38A169', width=2.5),
                fill='tozeroy',
                fillcolor='rgba(56, 161, 105, 0.1)',
                hovertemplate='<b>Vermicompostagem</b><br>Data: %{x}<br>CH₄: %{y:.3f} kg/dia<extra></extra>'
            ))
            
            fig1.update_layout(
                title=dict(
                    text='Emissões Diárias de Metano',
                    font=dict(size=16, color='#2D3748')
                ),
                xaxis_title='Data',
                yaxis_title='kg CH₄ por dia',
                hovermode='x unified',
                height=500,
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(color='#4A5568'),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    bgcolor='rgba(255, 255, 255, 0.9)',
                    bordercolor='#E2E8F0',
                    borderwidth=1
                ),
                margin=dict(t=60, l=60, r=60, b=60)
            )
            
            st.plotly_chart(fig1, use_container_width=True)
            
            # ==================== RESUMO DETALHADO ====================
            with st.expander("📋 RELATÓRIO COMPLETO", expanded=False):
                st.markdown(f"""
                ### 📋 Relatório Técnico - Lote Único
                
                **📊 DADOS DE ENTRADA**
                | Parâmetro | Valor | Unidade |
                |-----------|-------|---------|
                | Peso do lote | {formatar_br(quantidade_lote)} | kg |
                | Período de análise | {anos_analise} | anos |
                | Umidade | {formatar_br(umidade_valor)} | % |
                | Temperatura | {formatar_br(temperatura)} | °C |
                | DOCf calculado | {formatar_br(docf)} | - |
                | Fator GWP | {resultados['gwp_utilizado']} | - |
                
                **🌿 ANÁLISE DE EMISSÕES**
                | Cenário | Emissões CH₄ | Equivalente CO₂ |
                |---------|--------------|-----------------|
                | Aterro Sanitário | {formatar_br(emissoes_aterro.sum())} kg | {formatar_br(resultados['co2eq_aterro_total'])} tCO₂eq |
                | Vermicompostagem | {formatar_br(emissoes_vermi_completa.sum())} kg | {formatar_br(resultados['co2eq_vermi_total'])} tCO₂eq |
                | **Redução Total** | **{formatar_br(resultados['emissoes_evitadas_kg_ch4'])} kg** | **{formatar_br(resultados['co2eq_evitado_total'])} tCO₂eq** |
                
                **💰 VIABILIDADE FINANCEIRA**
                | Item | Valor | Detalhes |
                |------|-------|----------|
                | Preço do carbono | € {formatar_br(cotacoes.get('preco_carbono', 85.50))} | /tCO₂eq |
                | Taxa de câmbio | R$ {formatar_br(cotacoes.get('taxa_cambio', 5.50))} | EUR/BRL |
                | Valor total | R$ {formatar_br(resultados['valor_total_brl'])} | € {formatar_br(resultados['valor_total_eur'])} |
                | Valor anual | R$ {formatar_br(resultados['valor_anual_brl'])} | /ano |
                | Valor por kg | R$ {formatar_br(valor_por_kg)} | /kg de resíduo |
                
                **⚡ IMPACTO AMBIENTAL**
                - **Equivalente em carros:** {formatar_br(resultados['co2eq_evitado_total'] / 2.3)} anos de um carro médio
                - **Árvores equivalentes:** {formatar_br(resultados['co2eq_evitado_total'] * 20)} árvores adultas
                - **Eficiência:** {formatar_br((1 - emissoes_vermi_completa.sum()/emissoes_aterro.sum())*100)}% de redução
                """)
    
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.aba_atual == "entrada_continua":
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    
    col_header = st.columns([4, 1])
    with col_header[0]:
        st.markdown("### 📈 Análise de Entrada Contínua")
        st.markdown("Simule o potencial para operações de processamento diário de resíduos")
    with col_header[1]:
        st.markdown('<span class="badge badge-warning">EM BREVE</span>', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%); padding: 2rem; border-radius: 12px; text-align: center; border: 1px solid #F59E0B; margin: 2rem 0;">
        <div style="font-size: 3rem; margin-bottom: 1rem;">🚧</div>
        <h4 style="color: #92400E; margin: 0 0 0.5rem 0;">Funcionalidade em Desenvolvimento</h4>
        <p style="color: #92400E; margin: 0;">Estamos trabalhando na análise contínua. Em breve você poderá calcular créditos para operações 24/7!</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🎯 Funcionalidades Planejadas")
        st.markdown("""
        <div style="background: #F8FAFC; padding: 1.5rem; border-radius: 8px; border: 1px solid #E2E8F0; margin-top: 1rem;">
            <ul style="color: #4A5568; padding-left: 1.5rem; margin: 0;">
                <li style="margin-bottom: 0.5rem;">📊 Simulação de produção contínua</li>
                <li style="margin-bottom: 0.5rem;">💰 Projeção financeira multi-anual</li>
                <li style="margin-bottom: 0.5rem;">📈 Análise de viabilidade econômica</li>
                <li style="margin-bottom: 0.5rem;">⚖️ Sensibilidade a variações de preço</li>
                <li>📋 Relatórios automáticos detalhados</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("#### 🏆 Benefícios")
        st.markdown("""
        <div style="background: #F0F9FF; padding: 1.5rem; border-radius: 8px; border: 1px solid #BAE6FD; margin-top: 1rem;">
            <ul style="color: #075985; padding-left: 1.5rem; margin: 0;">
                <li style="margin-bottom: 0.5rem;">🚀 Otimização de operações</li>
                <li style="margin-bottom: 0.5rem;">📅 Planejamento de capacidade</li>
                <li style="margin-bottom: 0.5rem;">💹 Análise de ROI detalhada</li>
                <li style="margin-bottom: 0.5rem;">🔗 Integração com sistemas ERP</li>
                <li>🏭 Suporte a múltiplas plantas</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.aba_atual == "analise_municipal":
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    
    col_header = st.columns([4, 1])
    with col_header[0]:
        st.markdown("### 🏙️ Análise de Potencial Municipal")
        st.markdown("Avalie o potencial agregado de créditos de carbono para municípios")
    with col_header[1]:
        st.markdown('<span class="badge badge-info">PLUS</span>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        #### Como Funcionará
        
        A análise municipal permitirá avaliar o potencial de créditos de carbono em escala regional, 
        identificando oportunidades de investimento e priorizando ações de gestão de resíduos.
        
        ##### Principais Vantagens:
        - **Análise em larga escala** para municípios brasileiros
        - **Identificação** de áreas com maior potencial
        - **Priorização** de investimentos
        - **Planejamento** regional integrado
        - **Negociação** em bloco de créditos
        """)
        
        col1_1, col1_2 = st.columns(2)
        with col1_1:
            st.markdown(criar_metric_card(
                "MUNICÍPIOS",
                "5.570+",
                "Total no Brasil",
                "info",
                "🏙️"
            ), unsafe_allow_html=True)
        
        with col1_2:
            st.markdown(criar_metric_card(
                "POTENCIAL BR",
                "R$ 15B/ano",
                "Estimativa conservadora",
                "success",
                "💰"
            ), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #EBF8FF 0%, #BEE3F8 100%); padding: 1.5rem; border-radius: 12px; border: 1px solid #90CDF4;">
            <h4 style="color: #2C5282; margin: 0 0 1rem 0;">📋 Formato dos Dados</h4>
            <div style="color: #2C5282; font-size: 0.875rem;">
                <div style="margin-bottom: 0.5rem;">📍 Nome do município</div>
                <div style="margin-bottom: 0.5rem;">👥 População estimada</div>
                <div style="margin-bottom: 0.5rem;">🗑️ Resíduos diários (t)</div>
                <div style="margin-bottom: 0.5rem;">🌿 Fração orgânica</div>
                <div>📊 Taxa de coleta</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("#### 📊 Exemplo de Dados Municipais")
    
    # Criar DataFrame de exemplo
    dados_exemplo = pd.DataFrame({
        'Município': ['São Paulo', 'Rio de Janeiro', 'Belo Horizonte', 'Salvador', 'Fortaleza'],
        'Estado': ['SP', 'RJ', 'MG', 'BA', 'CE'],
        'População': ['12,3 mi', '6,8 mi', '2,5 mi', '2,9 mi', '2,7 mi'],
        'Resíduos (t/dia)': ['12.000', '6.500', '2.500', '2.900', '2.700'],
        '% Orgânico': ['52%', '48%', '50%', '55%', '53%']
    })
    
    # Estilizar a tabela
    st.dataframe(
        dados_exemplo,
        use_container_width=True,
        column_config={
            "Município": st.column_config.TextColumn("Município", width="medium"),
            "Estado": st.column_config.TextColumn("Estado", width="small"),
            "População": st.column_config.TextColumn("População", width="medium"),
            "Resíduos (t/dia)": st.column_config.TextColumn("Resíduos (t/dia)", width="medium"),
            "% Orgânico": st.column_config.ProgressColumn(
                "% Orgânico",
                format="%d%%",
                min_value=0,
                max_value=100,
                width="medium"
            )
        }
    )
    
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.aba_atual == "relatorios":
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    
    col_header = st.columns([4, 1])
    with col_header[0]:
        st.markdown("### 📊 Relatórios e Análises")
        st.markdown("Acesse relatórios detalhados e análises avançadas")
    with col_header[1]:
        st.markdown('<span class="badge badge-premium">PREMIUM</span>', unsafe_allow_html=True)
    
    st.info("""
    **Recursos Premium Disponíveis em Breve:**
    
    - Relatórios personalizados em PDF/Excel
    - Análises comparativas entre cenários
    - Dashboards executivos
    - Exportação de dados brutos
    - API para integração com outros sistemas
    """, icon="🚀")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(criar_metric_card(
            "Relatórios",
            "PDF + Excel",
            "Formatos suportados",
            "info",
            "📄"
        ), unsafe_allow_html=True)
    
    with col2:
        st.markdown(criar_metric_card(
            "Dashboards",
            "Interativos",
            "Tempo real",
            "success",
            "📈"
        ), unsafe_allow_html=True)
    
    with col3:
        st.markdown(criar_metric_card(
            "API",
            "REST API",
            "Integração total",
            "warning",
            "🔗"
        ), unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("#### 📋 Tipos de Relatórios Disponíveis")
    
    tipos_relatorios = {
        "📊 Técnico": "Análise detalhada com metodologia IPCC",
        "💰 Financeiro": "Projeções de ROI e valorização",
        "🌍 Ambiental": "Impacto climático e equivalências",
        "🏭 Operacional": "Otimização de processos e custos",
        "📈 Executivo": "Resumo para tomada de decisão"
    }
    
    for tipo, descricao in tipos_relatorios.items():
        with st.expander(f"{tipo}"):
            st.markdown(f"**Descrição:** {descricao}")
            st.markdown("**Conteúdo:** Metodologia, cálculos, resultados, recomendações")
            st.markdown("**Formato:** PDF detalhado (20-30 páginas)")
    
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# FOOTER
# =============================================================================

ultima_atualizacao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

st.markdown(f"""
<div style="background: white; border-radius: 12px; padding: 2rem; margin-top: 3rem; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border: 1px solid rgba(0,0,0,0.05); text-align: center;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
        <div>
            <div style="font-size: 1.25rem; font-weight: 700; color: #0A2647; margin-bottom: 0.5rem;">Carbon Simulator Pro</div>
            <div style="color: #4A5568; font-size: 0.875rem;">Plataforma avançada para análise de créditos de carbono</div>
        </div>
        <div style="display: flex; gap: 1rem;">
            <span class="badge badge-success">Seguro</span>
            <span class="badge badge-info">Confiável</span>
            <span class="badge badge-premium">Profissional</span>
        </div>
    </div>
    
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 2rem; margin-bottom: 2rem;">
        <div>
            <div style="color: #0A2647; font-weight: 600; margin-bottom: 0.75rem;">Metodologia</div>
            <div style="color: #4A5568; font-size: 0.875rem;">
                IPCC 2006<br>
                IPCC AR6 2021<br>
                Yang et al. 2017<br>
                UNFCCC
            </div>
        </div>
        
        <div>
            <div style="color: #0A2647; font-weight: 600; margin-bottom: 0.75rem;">Dados do Mercado</div>
            <div style="color: #4A5568; font-size: 0.875rem;">
                Investing.com<br>
                BCB - Banco Central<br>
                AwesomeAPI<br>
                Atualização em tempo real
            </div>
        </div>
        
        <div>
            <div style="color: #0A2647; font-weight: 600; margin-bottom: 0.75rem;">Sistema</div>
            <div style="color: #4A5568; font-size: 0.875rem;">
                Versão 2.1.0 Pro<br>
                Python 3.11+<br>
                Streamlit<br>
                Plotly • SciPy • NumPy
            </div>
        </div>
    </div>
    
    <div style="border-top: 1px solid #E2E8F0; padding-top: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="color: #718096; font-size: 0.75rem;">
                © 2024 Carbon Simulator Pro. Todos os direitos reservados.<br>
                Desenvolvido para transição climática sustentável.
            </div>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span class="status-dot status-active"></span>
                <span style="color: #38A169; font-size: 0.875rem; font-weight: 600;">Sistema Online</span>
            </div>
        </div>
        <div style="color: #A0AEC0; font-size: 0.75rem; text-align: center; margin-top: 1rem;">
            Última atualização: {ultima_atualizacao}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
