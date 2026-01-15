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
    page_title="CARBON SIMULATOR PRO | Créditos de Carbono por Gestão de Resíduos", 
    layout="wide",
    page_icon="🌍",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/',
        'Report a bug': 'https://github.com/',
        'About': '### Carbon Simulator Pro\nSolução completa para análise de potencial de créditos de carbono via gestão de resíduos orgânicos'
    }
)

# Configurar tema com CSS moderno
st.markdown("""
<style>
    /* ===== TEMA PRINCIPAL ===== */
    :root {
        --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --secondary-gradient: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        --accent-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        --warning-gradient: linear-gradient(135deg, #f6d365 0%, #fda085 100%);
        --dark-bg: #0f172a;
        --light-bg: #f8fafc;
        --card-bg: rgba(255, 255, 255, 0.95);
        --text-primary: #1e293b;
        --text-secondary: #64748b;
        --shadow-sm: 0 2px 8px rgba(0,0,0,0.05);
        --shadow-md: 0 4px 20px rgba(0,0,0,0.08);
        --shadow-lg: 0 10px 40px rgba(0,0,0,0.12);
        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 20px;
        --border-light: 1px solid #e2e8f0;
    }
    
    /* ===== ESTRUTURA PRINCIPAL ===== */
    .main {
        background: var(--light-bg);
        min-height: 100vh;
    }
    
    /* ===== HEADER ELEGANTE ===== */
    .main-header {
        background: var(--primary-gradient);
        padding: 2.5rem;
        border-radius: var(--radius-lg);
        color: white;
        margin-bottom: 2.5rem;
        box-shadow: var(--shadow-lg);
        position: relative;
        overflow: hidden;
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.1) 50%, transparent 70%);
        animation: shimmer 3s infinite;
    }
    
    @keyframes shimmer {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }
    
    /* ===== CARDS DE MÉTRICAS ===== */
    .metric-card {
        background: var(--card-bg);
        padding: 1.75rem;
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-md);
        border-left: 5px solid #667eea;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        margin-bottom: 1.25rem;
        backdrop-filter: blur(10px);
        border: var(--border-light);
    }
    
    .metric-card:hover {
        transform: translateY(-8px);
        box-shadow: var(--shadow-lg);
        border-left-color: #764ba2;
    }
    
    .metric-card.warning {
        border-left-color: #f59e0b;
    }
    
    .metric-card.success {
        border-left-color: #10b981;
    }
    
    .metric-card.danger {
        border-left-color: #ef4444;
    }
    
    /* ===== BOTÕES MODERNOS ===== */
    .stButton > button {
        background: var(--primary-gradient);
        color: white;
        border: none;
        border-radius: var(--radius-md);
        padding: 0.875rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        width: 100%;
        position: relative;
        overflow: hidden;
    }
    
    .stButton > button::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.2) 50%, transparent 70%);
        transform: translateX(-100%);
    }
    
    .stButton > button:hover::after {
        animation: shimmer 0.8s;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button:active {
        transform: translateY(-1px);
    }
    
    /* ===== ABAS ESTILIZADAS ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        background: transparent;
        padding: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: var(--card-bg);
        border-radius: var(--radius-md) var(--radius-md) 0 0;
        padding: 1rem 2rem;
        border: var(--border-light);
        font-weight: 600;
        color: var(--text-secondary);
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--text-primary);
        border-color: #667eea;
    }
    
    .stTabs [aria-selected="true"] {
        background: var(--primary-gradient) !important;
        color: white !important;
        border-color: #667eea !important;
        box-shadow: var(--shadow-sm);
    }
    
    /* ===== SIDEBAR MODERNA ===== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #334155 100%);
    }
    
    [data-testid="stSidebar"] .sidebar-content {
        padding: 2rem;
    }
    
    /* ===== INPUTS ESTILIZADOS ===== */
    .stNumberInput input, .stTextInput input, .stSelectbox div {
        background: var(--card-bg) !important;
        border-radius: var(--radius-sm) !important;
        border: var(--border-light) !important;
        color: var(--text-primary) !important;
    }
    
    .stSlider [data-baseweb="slider"] {
        background: var(--card-bg);
        padding: 1rem;
        border-radius: var(--radius-md);
        border: var(--border-light);
    }
    
    /* ===== TÍTULOS ===== */
    h1 {
        font-size: 2.75rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 30%, #f093fb 70%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    h2 {
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--text-primary);
        margin-top: 2rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e2e8f0;
    }
    
    h3 {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 1rem;
    }
    
    /* ===== CONTAINERS ===== */
    .tab-container {
        background: var(--card-bg);
        padding: 2.5rem;
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-md);
        margin-top: 1.5rem;
        border: var(--border-light);
        backdrop-filter: blur(10px);
    }
    
    /* ===== BADGES ===== */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 50px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .badge-success {
        background: linear-gradient(135deg, #10b981 0%, #34d399 100%);
        color: white;
    }
    
    .badge-warning {
        background: linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%);
        color: white;
    }
    
    .badge-info {
        background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%);
        color: white;
    }
    
    /* ===== ANIMAÇÕES ===== */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .fade-in {
        animation: fadeIn 0.6s ease-out;
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
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    /* ===== STATUS INDICATORS ===== */
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-active {
        background: #10b981;
        box-shadow: 0 0 10px #10b981;
    }
    
    .status-inactive {
        background: #ef4444;
    }
    
    /* ===== LOADING SPINNER ===== */
    .spinner {
        display: inline-block;
        width: 40px;
        height: 40px;
        border: 4px solid #f1f5f9;
        border-top: 4px solid #667eea;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    /* ===== PROGRESS BAR ===== */
    .stProgress > div > div > div {
        background: var(--primary-gradient) !important;
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

def criar_metric_card(titulo, valor, subtitulo="", tipo="primary", icon=""):
    """Cria um card de métrica estilizado com ícone opcional"""
    cores = {
        "primary": "#667eea",
        "success": "#10b981",
        "warning": "#f59e0b",
        "danger": "#ef4444",
        "info": "#3b82f6"
    }
    
    cor = cores.get(tipo, "#667eea")
    icon_html = f'<div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>' if icon else ""
    
    html = f"""
    <div class="metric-card {tipo} fade-in" style="border-left-color: {cor};">
        {icon_html}
        <div style="font-size: 0.85rem; color: #718096; margin-bottom: 0.5rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">{titulo}</div>
        <div style="font-size: 2.25rem; font-weight: 800; color: #2d3748; line-height: 1.2; margin: 0.5rem 0;">{valor}</div>
        <div style="font-size: 0.85rem; color: #718096; margin-top: 0.5rem; opacity: 0.8;">{subtitulo}</div>
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

# =============================================================================
# HEADER ELEGANTE
# =============================================================================

# Header principal
st.markdown("""
<div class="main-header fade-in">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem;">
        <div style="display: flex; align-items: center; gap: 1.5rem;">
            <div style="font-size: 4rem; filter: drop-shadow(0 4px 6px rgba(0,0,0,0.1));">🌍</div>
            <div>
                <h1 style="margin: 0; font-size: 3rem; font-weight: 900; text-shadow: 0 2px 10px rgba(0,0,0,0.2);">CARBON SIMULATOR PRO</h1>
                <p style="margin: 0; opacity: 0.95; font-size: 1.2rem; font-weight: 400; max-width: 800px;">
                    Solução completa para análise de potencial de créditos de carbono via gestão sustentável de resíduos orgânicos
                </p>
            </div>
        </div>
        <div style="display: flex; gap: 0.5rem;">
            <span class="badge badge-success">IPCC 2006</span>
            <span class="badge badge-info">GWP-20</span>
            <span class="badge badge-warning">Yang et al. 2017</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Cards de métricas do header
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("""
    <div style="background: rgba(102, 126, 234, 0.15); padding: 1rem; border-radius: 12px; backdrop-filter: blur(10px); border: 1px solid rgba(102, 126, 234, 0.3);">
        <div style="font-size: 0.9rem; opacity: 0.9; color: #667eea; font-weight: 600;">Potencial de Créditos</div>
        <div style="font-size: 1.5rem; font-weight: 700; color: #1e293b;">R$ 50-150/tCO₂eq</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style="background: rgba(16, 185, 129, 0.15); padding: 1rem; border-radius: 12px; backdrop-filter: blur(10px); border: 1px solid rgba(16, 185, 129, 0.3);">
        <div style="font-size: 0.9rem; opacity: 0.9; color: #10b981; font-weight: 600;">Redução CH₄</div>
        <div style="font-size: 1.5rem; font-weight: 700; color: #1e293b;">85-95%</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div style="background: rgba(245, 158, 11, 0.15); padding: 1rem; border-radius: 12px; backdrop-filter: blur(10px); border: 1px solid rgba(245, 158, 11, 0.3);">
        <div style="font-size: 0.9rem; opacity: 0.9; color: #f59e0b; font-weight: 600;">Payback Típico</div>
        <div style="font-size: 1.5rem; font-weight: 700; color: #1e293b;">3-5 anos</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div style="background: rgba(139, 92, 246, 0.15); padding: 1rem; border-radius: 12px; backdrop-filter: blur(10px); border: 1px solid rgba(139, 92, 246, 0.3);">
        <div style="font-size: 0.9rem; opacity: 0.9; color: #8b5cf6; font-weight: 600;">Mercado Global</div>
        <div style="font-size: 1.5rem; font-weight: 700; color: #1e293b;">$ 1T+</div>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# BARRA LATERAL MODERNA
# =============================================================================

with st.sidebar:
    st.markdown("""
    <div style="padding: 1.5rem; background: rgba(255,255,255,0.05); border-radius: 12px; margin-bottom: 2rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.5rem;">
            <div style="font-size: 2rem;">⚙️</div>
            <h3 style="margin: 0; color: white;">CONFIGURAÇÕES GLOBAIS</h3>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Seção de cotações
    st.markdown("### 💰 COTAÇÕES EM TEMPO REAL")
    
    cotacoes = st.session_state.cotacoes
    preco_carbono = cotacoes.get('preco_carbono', 85.50)
    taxa_cambio = cotacoes.get('taxa_cambio', 5.50)
    preco_carbono_brl = preco_carbono * taxa_cambio
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label="Preço do Carbono",
            value=f"€ {formatar_br(preco_carbono)}",
            delta=None,
            help=f"Fonte: {cotacoes.get('fonte_carbono', 'Referência')}",
            label_visibility="visible"
        )
    
    with col2:
        st.metric(
            label="Taxa EUR/BRL",
            value=f"R$ {formatar_br(taxa_cambio)}",
            delta=None,
            help=f"Fonte: {cotacoes.get('fonte_cambio', 'Referência')}",
            label_visibility="visible"
        )
    
    st.info(f"""
    **💰 Valor em Reais:** R$ {formatar_br(preco_carbono_brl)}/tCO₂eq
    *Atualizado: {cotacoes.get('timestamp', datetime.now()).strftime('%H:%M')}*
    """)
    
    st.markdown("---")
    
    # Parâmetros ambientais
    st.markdown("### 🌡️ PARÂMETROS AMBIENTAIS")
    
    col1, col2 = st.columns(2)
    with col1:
        temperatura = st.slider(
            "Temperatura (°C)",
            min_value=15.0,
            max_value=35.0,
            value=25.0,
            step=0.5,
            help="Temperatura média anual local"
        )
    
    with col2:
        umidade_valor = st.slider(
            "Umidade (%)",
            min_value=50.0,
            max_value=95.0,
            value=85.0,
            step=1.0,
            help="Teor de umidade dos resíduos"
        )
    umidade = umidade_valor / 100.0
    
    st.session_state.parametros_globais['temperatura'] = temperatura
    st.session_state.parametros_globais['umidade'] = umidade
    
    # Período do GWP
    st.markdown("### 📊 FATOR GWP")
    gwp_periodo = st.selectbox(
        "Período de Análise GWP",
        options=["20 anos (GWP-20)", "100 anos (GWP-100)"],
        index=0,
        help="GWP-20 é mais conservador para créditos de curto prazo"
    )
    
    usar_gwp_20 = gwp_periodo == "20 anos (GWP-20)"
    st.session_state.parametros_globais['gwp_periodo'] = gwp_periodo
    st.session_state.parametros_globais['usar_gwp_20'] = usar_gwp_20
    
    with st.expander("📚 Sobre os Fatores GWP", expanded=False):
        st.markdown(f"""
        **GWP-20 (20 anos):** 
        - Metano (CH₄): **{GWP_CH4_20}**
        - Óxido Nitroso (N₂O): **{GWP_N2O_20}**
        
        **GWP-100 (100 anos):**
        - Metano (CH₄): **{GWP_CH4_100}**
        - Óxido Nitroso (N₂O): **{GWP_N2O_100}**
        
        *Fonte: IPCC AR6 (2021)*
        
        **💡 Recomendação:** Use GWP-20 para projetos de créditos de carbono, pois reflete melhor o impacto de curto prazo do metano.
        """)
    
    st.markdown("---")
    
    # Ações
    st.markdown("### ⚡ AÇÕES")
    
    if st.button("🔄 Atualizar Cotações", use_container_width=True, type="secondary"):
        with st.spinner("Atualizando cotações..."):
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
            st.success("Cotações atualizadas!")
            st.rerun()
    
    if st.button("💾 Exportar Configurações", use_container_width=True, type="secondary"):
        config_data = {
            'parametros': st.session_state.parametros_globais,
            'cotacoes': st.session_state.cotacoes,
            'timestamp': datetime.now().isoformat()
        }
        st.download_button(
            label="📥 Baixar Configurações JSON",
            data=json.dumps(config_data, indent=2),
            file_name=f"config_carbon_simulator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    st.markdown("---")
    
    # Informações técnicas
    st.markdown("### 🔬 INFORMAÇÕES TÉCNICAS")
    st.caption(f"""
    **Metodologia:** IPCC 2006 + Yang et al. 2017  
    **Última atualização:** {datetime.now().strftime('%d/%m/%Y')}  
    **Versão:** 2.0.0 Pro  
    **Status:** <span class="status-indicator status-active"></span> Online
    """, unsafe_allow_html=True)

# =============================================================================
# NAVEGAÇÃO POR ABAS
# =============================================================================

tab1, tab2, tab3 = st.tabs([
    "📦 LOTE ÚNICO", 
    "📈 ENTRADA CONTÍNUA", 
    "🏙️ ANÁLISE MUNICIPAL"
])

# =============================================================================
# ABA 1: LOTE ÚNICO
# =============================================================================
with tab1:
    # Container principal
    st.markdown('<div class="tab-container fade-in">', unsafe_allow_html=True)
    
    # Cabeçalho da aba
    col_header = st.columns([4, 1])
    with col_header[0]:
        st.markdown("### 📦 Análise de Lote Único")
        st.markdown("Calcule o potencial de créditos de carbono para um único lote de resíduos orgânicos puros")
    with col_header[1]:
        st.markdown('<span class="badge badge-info">Simples e Rápido</span>', unsafe_allow_html=True)
    
    # Configurações
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("#### 📊 Configuração do Lote")
        quantidade_lote = st.number_input(
            "Peso do lote de resíduos orgânicos (kg)",
            min_value=10.0,
            max_value=10000.0,
            value=100.0,
            step=10.0,
            help="Peso total do lote de resíduos orgânicos puros",
            key="qtd_lote"
        )
        
        anos_analise = st.select_slider(
            "Período de análise (anos)",
            options=[1, 5, 10, 15, 20, 25, 30],
            value=20,
            help="Tempo que o lote continuará emitindo metano no aterro"
        )
    
    with col2:
        st.markdown("#### ⚙️ Parâmetros Atuais")
        st.markdown(f"""
        <div style="background: #f8fafc; padding: 1rem; border-radius: 8px; border-left: 4px solid #667eea; margin-bottom: 1rem;">
            <div style="color: #64748b; font-size: 0.9rem;">🌡️ Temperatura</div>
            <div style="font-size: 1.25rem; font-weight: 600;">{temperatura}°C</div>
        </div>
        <div style="background: #f8fafc; padding: 1rem; border-radius: 8px; border-left: 4px solid #10b981; margin-bottom: 1rem;">
            <div style="color: #64748b; font-size: 0.9rem;">💧 Umidade</div>
            <div style="font-size: 1.25rem; font-weight: 600;">{umidade_valor}%</div>
        </div>
        <div style="background: #f8fafc; padding: 1rem; border-radius: 8px; border-left: 4px solid #8b5cf6;">
            <div style="color: #64748b; font-size: 0.9rem;">📅 GWP</div>
            <div style="font-size: 1.25rem; font-weight: 600;">{gwp_periodo.split('(')[0].strip()}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("#### 📈 Estatísticas")
        st.markdown(f"""
        <div style="background: #f8fafc; padding: 1rem; border-radius: 8px; border-left: 4px solid #f59e0b; margin-bottom: 1rem;">
            <div style="color: #64748b; font-size: 0.9rem;">📦 Lote</div>
            <div style="font-size: 1.25rem; font-weight: 600;">{formatar_br(quantidade_lote)} kg</div>
        </div>
        <div style="background: #f8fafc; padding: 1rem; border-radius: 8px; border-left: 4px solid #3b82f6; margin-bottom: 1rem;">
            <div style="color: #64748b; font-size: 0.9rem;">⏱️ Período</div>
            <div style="font-size: 1.25rem; font-weight: 600;">{anos_analise} anos</div>
        </div>
        <div style="background: #f8fafc; padding: 1rem; border-radius: 8px; border-left: 4px solid #ef4444;">
            <div style="color: #64748b; font-size: 0.9rem;">📊 Dias Totais</div>
            <div style="font-size: 1.25rem; font-weight: 600;">{anos_analise * 365}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Botão de cálculo
    col_btn = st.columns([1, 2, 1])
    with col_btn[1]:
        calcular_lote = st.button(
            "🚀 CALCULAR POTENCIAL DO LOTE", 
            type="primary", 
            use_container_width=True,
            key="btn_lote_calc"
        )
    
    if calcular_lote:
        with st.spinner("🔍 Calculando potencial de créditos..."):
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
            
            # ==================== RESULTADOS ====================
            st.markdown("---")
            
            col_result_header = st.columns([4, 1])
            with col_result_header[0]:
                st.markdown("### 📊 Resultados - Lote Único")
            with col_result_header[1]:
                st.markdown('<span class="badge badge-success">Cálculo Concluído</span>', unsafe_allow_html=True)
            
            # Métricas principais
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(criar_metric_card(
                    "Metano Evitado",
                    formatar_br(resultados['emissoes_evitadas_kg_ch4']),
                    "kg CH₄ | Redução de 85%+",
                    "success",
                    "🌿"
                ), unsafe_allow_html=True)
            
            with col2:
                st.markdown(criar_metric_card(
                    "Créditos Gerados",
                    formatar_br(resultados['co2eq_evitado_total']),
                    f"tCO₂eq | GWP-{resultados['gwp_utilizado']}",
                    "primary",
                    "💰"
                ), unsafe_allow_html=True)
            
            with col3:
                st.markdown(criar_metric_card(
                    "Valor Total",
                    f"R$ {formatar_br(resultados['valor_total_brl'])}",
                    f"@ €{formatar_br(cotacoes.get('preco_carbono', 85.50))}/tCO₂eq",
                    "warning",
                    "💵"
                ), unsafe_allow_html=True)
            
            with col4:
                valor_por_kg = resultados['valor_total_brl'] / quantidade_lote
                st.markdown(criar_metric_card(
                    "Valor por kg",
                    f"R$ {formatar_br(valor_por_kg)}",
                    "por kg de resíduo",
                    "info",
                    "⚖️"
                ), unsafe_allow_html=True)
            
            # ==================== VISUALIZAÇÕES ====================
            st.markdown("---")
            st.markdown("### 📈 Visualizações Detalhadas")
            
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
                line=dict(color='#ef4444', width=3),
                fill='tozeroy',
                fillcolor='rgba(239, 68, 68, 0.1)',
                hovertemplate='<b>Aterro</b><br>Data: %{x}<br>CH₄: %{y:.3f} kg/dia<extra></extra>'
            ))
            
            fig1.add_trace(go.Scatter(
                x=df_emissoes['Data'],
                y=df_emissoes['Vermicompostagem - CH₄ (kg/dia)'],
                name='Vermicompostagem',
                line=dict(color='#10b981', width=3),
                fill='tozeroy',
                fillcolor='rgba(16, 185, 129, 0.1)',
                hovertemplate='<b>Vermicompostagem</b><br>Data: %{x}<br>CH₄: %{y:.3f} kg/dia<extra></extra>'
            ))
            
            fig1.update_layout(
                title=dict(
                    text=f'Emissões Diárias de Metano - Lote de {quantidade_lote} kg',
                    font=dict(size=18, color='#1e293b')
                ),
                xaxis_title='Data',
                yaxis_title='kg CH₄ por dia',
                hovermode='x unified',
                height=450,
                plot_bgcolor='rgba(248, 250, 252, 0.8)',
                paper_bgcolor='rgba(255, 255, 255, 0.9)',
                font=dict(color='#1e293b'),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig1, use_container_width=True)
            
            # Gráfico 2: Emissões Acumuladas
            df_emissoes['Aterro - Acumulado'] = df_emissoes['Aterro - CH₄ (kg/dia)'].cumsum()
            df_emissoes['Vermi - Acumulado'] = df_emissoes['Vermicompostagem - CH₄ (kg/dia)'].cumsum()
            
            fig2 = go.Figure()
            
            fig2.add_trace(go.Scatter(
                x=df_emissoes['Data'],
                y=df_emissoes['Aterro - Acumulado'],
                name='Aterro - Acumulado',
                line=dict(color='#ef4444', width=4),
                fill='tozeroy',
                fillcolor='rgba(239, 68, 68, 0.2)',
                hovertemplate='<b>Aterro Acumulado</b><br>Data: %{x}<br>CH₄ Total: %{y:.2f} kg<extra></extra>'
            ))
            
            fig2.add_trace(go.Scatter(
                x=df_emissoes['Data'],
                y=df_emissoes['Vermi - Acumulado'],
                name='Vermicompostagem - Acumulado',
                line=dict(color='#10b981', width=4),
                fill='tozeroy',
                fillcolor='rgba(16, 185, 129, 0.2)',
                hovertemplate='<b>Vermicompostagem Acumulado</b><br>Data: %{x}<br>CH₄ Total: %{y:.2f} kg<extra></extra>'
            ))
            
            fig2.update_layout(
                title=dict(
                    text=f'Emissões Acumuladas de Metano - {anos_analise} Anos',
                    font=dict(size=18, color='#1e293b')
                ),
                xaxis_title='Data',
                yaxis_title='kg CH₄ acumulado',
                hovermode='x unified',
                height=450,
                plot_bgcolor='rgba(248, 250, 252, 0.8)',
                paper_bgcolor='rgba(255, 255, 255, 0.9)',
                font=dict(color='#1e293b'),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig2, use_container_width=True)
            
            # ==================== RESUMO DETALHADO ====================
            with st.expander("📋 RELATÓRIO COMPLETO DA ANÁLISE", expanded=False):
                st.markdown(f"""
                ### 🎯 RELATÓRIO DE ANÁLISE - LOTE ÚNICO
                
                **📊 DADOS DE ENTRADA**
                - **Peso do lote:** {formatar_br(quantidade_lote)} kg de resíduos orgânicos puros
                - **Período de análise:** {anos_analise} anos ({anos_analise * 365} dias)
                - **Umidade:** {formatar_br(umidade_valor)}%
                - **Temperatura:** {formatar_br(temperatura)}°C
                - **DOCf calculado:** {formatar_br(docf)} (fórmula IPCC: 0.0147 × T + 0.28)
                - **Fator GWP utilizado:** {resultados['gwp_utilizado']}
                
                **🌿 ANÁLISE DE EMISSÕES**
                - **Aterro sanitário:** {formatar_br(emissoes_aterro.sum())} kg CH₄ total
                - **Vermicompostagem:** {formatar_br(emissoes_vermi_completa.sum())} kg CH₄ total
                - **Redução absoluta:** {formatar_br(resultados['emissoes_evitadas_kg_ch4'])} kg CH₄
                - **Eficiência de redução:** {formatar_br((1 - emissoes_vermi_completa.sum()/emissoes_aterro.sum())*100)}%
                
                **🌍 POTENCIAL DE CRÉDITOS DE CARBONO**
                - **Emissões do aterro:** {formatar_br(resultados['co2eq_aterro_total'])} tCO₂eq
                - **Emissões da vermicompostagem:** {formatar_br(resultados['co2eq_vermi_total'])} tCO₂eq
                - **Créditos geráveis:** **{formatar_br(resultados['co2eq_evitado_total'])} tCO₂eq**
                - **Créditos anuais médios:** {formatar_br(resultados['co2eq_evitado_anual'])} tCO₂eq/ano
                
                **💰 VALOR FINANCEIRO**
                - **Preço do carbono (EU ETS):** € {formatar_br(cotacoes.get('preco_carbono', 85.50))}/tCO₂eq
                - **Taxa de câmbio:** € 1 = R$ {formatar_br(cotacoes.get('taxa_cambio', 5.50))}
                - **Valor total em créditos:** **R$ {formatar_br(resultados['valor_total_brl'])}**
                - **Valor por kg de resíduo:** R$ {formatar_br(resultados['valor_total_brl'] / quantidade_lote)}/kg
                
                **⚡ IMPACTO AMBIENTAL EQUIVALENTE**
                - **Carros equivalentes:** {formatar_br(resultados['co2eq_evitado_total'] / 2.3)} anos de um carro médio
                - **Árvores equivalentes:** {formatar_br(resultados['co2eq_evitado_total'] * 20)} árvores adultas
                """)
                
                # Botão para exportar resultados
                resultados_export = {
                    'parametros_entrada': {
                        'peso_lote_kg': quantidade_lote,
                        'anos_analise': anos_analise,
                        'temperatura_c': temperatura,
                        'umidade_percent': umidade_valor,
                        'gwp_periodo': resultados['gwp_utilizado']
                    },
                    'resultados': resultados,
                    'timestamp': datetime.now().isoformat()
                }
                
                st.download_button(
                    label="📥 Exportar Relatório (JSON)",
                    data=json.dumps(resultados_export, indent=2),
                    file_name=f"relatorio_lote_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
    
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# ABA 2: ENTRADA CONTÍNUA (SIMPLIFICADA PARA DEMONSTRAÇÃO)
# =============================================================================
with tab2:
    st.markdown('<div class="tab-container fade-in">', unsafe_allow_html=True)
    
    col_header = st.columns([4, 1])
    with col_header[0]:
        st.markdown("### 📈 Análise de Entrada Contínua")
        st.markdown("Calcule o potencial de créditos de carbono para processamento diário constante de resíduos")
    with col_header[1]:
        st.markdown('<span class="badge badge-warning">Para Operações Contínuas</span>', unsafe_allow_html=True)
    
    st.info("🚧 Esta funcionalidade está em desenvolvimento. Em breve você poderá calcular o potencial para operações contínuas!")
    
    # Configuração simplificada
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Configuração do Fluxo")
        residuos_diarios = st.number_input(
            "Resíduos processados diariamente (kg/dia)",
            min_value=10.0,
            max_value=50000.0,
            value=1000.0,
            step=100.0,
            key="diarios_continuo"
        )
    
    with col2:
        st.markdown("#### ⏱️ Período de Operação")
        anos_operacao = st.select_slider(
            "Período de operação (anos)",
            options=[5, 10, 15, 20, 25, 30],
            value=20,
            key="anos_continuo"
        )
    
    st.markdown("""
    ### 💡 Como funciona a análise contínua
    
    A análise de entrada contínua considera:
    
    1. **Processamento diário constante** de resíduos orgânicos
    2. **Acúmulo de créditos** ao longo do tempo
    3. **Projeção financeira** para 20 anos ou mais
    4. **Análise de viabilidade** do projeto
    5. **Sensibilidade** a variações de preço do carbono
    
    *Em breve disponível na versão completa!*
    """)
    
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# ABA 3: ANÁLISE MUNICIPAL (SIMPLIFICADA PARA DEMONSTRAÇÃO)
# =============================================================================
with tab3:
    st.markdown('<div class="tab-container fade-in">', unsafe_allow_html=True)
    
    col_header = st.columns([4, 1])
    with col_header[0]:
        st.markdown("### 🏙️ Análise de Potencial Municipal")
        st.markdown("Calcule o potencial agregado de créditos de carbono para municípios brasileiros")
    with col_header[1]:
        st.markdown('<span class="badge badge-danger">Análise em Larga Escala</span>', unsafe_allow_html=True)
    
    st.info("🚧 Esta funcionalidade está em desenvolvimento. Em breve você poderá analisar o potencial de múltiplos municípios!")
    
    # Instruções
    with st.expander("📋 COMO FUNCIONARÁ A ANÁLISE MUNICIPAL", expanded=True):
        st.markdown("""
        ### 📊 PROCESSO DE ANÁLISE
        
        1. **Upload de dados:** Carregue uma planilha Excel com dados municipais
        2. **Cálculo automático:** O sistema calculará o potencial de cada município
        3. **Agregação:** Resultados consolidados por região/estado
        4. **Visualização:** Mapas e gráficos comparativos
        5. **Exportação:** Relatórios completos em Excel/PDF
        
        ### 📋 ESTRUTURA DA PLANILHA
        
        Sua planilha deve conter:
        
        | Coluna | Descrição | Exemplo |
        |--------|-----------|---------|
        | Município | Nome do município | São Paulo |
        | Estado | Sigla do estado | SP |
        | População | Número de habitantes | 12300000 |
        | Resíduos Totais (t/dia) | Total de RSU coletado | 12000 |
        | Fração Orgânica | % orgânica no resíduo (0-1) | 0.52 |
        | Taxa de Coleta | % de resíduos coletados (0-1) | 0.95 |
        
        ### 🎯 BENEFÍCIOS
        
        - **Identificação** de municípios com maior potencial
        - **Priorização** de investimentos
        - **Planejamento** regional integrado
        - **Negociação** em bloco de créditos
        
        *Em breve disponível na versão completa!*
        """)
    
    # Exemplo de dados
    st.markdown("### 📊 EXEMPLO DE DADOS MUNICIPAIS")
    
    dados_exemplo = {
        "Município": ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Salvador", "Fortaleza"],
        "Estado": ["SP", "RJ", "MG", "BA", "CE"],
        "População": [12300000, 6775000, 2531000, 2903000, 2687000],
        "Resíduos Totais (t/dia)": [12000, 6500, 2500, 2900, 2700],
        "Fração Orgânica": [0.52, 0.48, 0.50, 0.55, 0.53],
        "Taxa de Coleta": [0.95, 0.92, 0.93, 0.85, 0.88]
    }
    
    df_exemplo = pd.DataFrame(dados_exemplo)
    st.dataframe(df_exemplo, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# RODAPÉ
# =============================================================================
st.markdown("---")

# Informações do rodapé
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    **📊 Metodologia Científica**  
    IPCC 2006 (Aterro) + Yang et al. 2017 (Compostagem)  
    GWP-20: CH₄ = 82.5 | N₂O = 273  
    GWP-100: CH₄ = 29.8 | N₂O = 273
    """)

with col2:
    cotacoes = st.session_state.cotacoes
    st.markdown(f"""
    **💰 Mercado de Carbono**  
    Preço atual: € {formatar_br(cotacoes.get('preco_carbono', 85.50))}/tCO₂eq  
    Taxa EUR/BRL: R$ {formatar_br(cotacoes.get('taxa_cambio', 5.50))}  
    Valor BR: R$ {formatar_br(cotacoes.get('preco_carbono_brl', 85.50 * 5.50))}/tCO₂eq
    """)

with col3:
    st.markdown("""
    **⚡ Performance Técnica**  
    Cálculos otimizados em NumPy/SciPy  
    Interface responsiva e moderna  
    Exportação completa em múltiplos formatos
    """)

st.markdown("---")

# Créditos
st.markdown(f"""
<div style="text-align: center; color: #64748b; font-size: 0.9rem; padding: 1rem 0;">
    <div style="margin-bottom: 0.5rem;">
        <strong>🌿 CARBON SIMULATOR PRO</strong> | Solução completa para créditos de carbono via gestão de resíduos
    </div>
    <div style="font-size: 0.8rem; color: #94a3b8;">
        © 2024 Carbon Simulator Pro | Versão 2.0.0 | Desenvolvido para transição climática justa<br>
        Última atualização: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")} | 
        <span class="status-indicator status-active"></span> Sistema Operacional
    </div>
</div>
""", unsafe_allow_html=True)
