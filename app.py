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

# Configurar tema dark/light com CSS moderno
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
# FUNÇÕES DE CÁLCULO CENTRAIS (MANTIDAS)
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
    
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; margin-top: 2rem;">
        <div style="background: rgba(255,255,255,0.15); padding: 1rem; border-radius: 12px; backdrop-filter: blur(10px);">
            <div style="font-size: 0.9rem; opacity: 0.9;">Potencial de Créditos</div>
            <div style="font-size: 1.5rem; font-weight: 700;">R$ 50-150/tCO₂eq</div>
        </div>
        <div style="background: rgba(255,255,255,0.15); padding: 1rem; border-radius: 12px; backdrop-filter: blur(10px);">
            <div style="font-size: 0.9rem; opacity: 0.9;">Redução CH₄</div>
            <div style="font-size: 1.5rem; font-weight: 700;">85-95%</div>
        </div>
        <div style="background: rgba(255,255,255,0.15); padding: 1rem; border-radius: 12px; backdrop-filter: blur(10px);">
            <div style="font-size: 0.9rem; opacity: 0.9;">Payback Típico</div>
            <div style="font-size: 1.5rem; font-weight: 700;">3-5 anos</div>
        </div>
        <div style="background: rgba(255,255,255,0.15); padding: 1rem; border-radius: 12px; backdrop-filter: blur(10px);">
            <div style="font-size: 0.9rem; opacity: 0.9;">Mercado Global</div>
            <div style="font-size: 1.5rem; font-weight: 700;">$ 1T+</div>
        </div>
    </div>
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
            mime="application/json",
            use_container_width=True
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
    st.markdown('<div class="tab-container fade-in">', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
        <div>
            <h2>📦 Análise de Lote Único</h2>
            <p style="color: #64748b; margin-top: -0.5rem;">
            Calcule o potencial de créditos de carbono para um único lote de resíduos orgânicos puros
            </p>
        </div>
        <span class="badge badge-info">Simples e Rápido</span>
    </div>
    """, unsafe_allow_html=True)
    
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
        <div style="background: #f8fafc; padding: 1rem; border-radius: 8px; border-left: 4px solid #667eea;">
            <div style="color: #64748b; font-size: 0.9rem;">🌡️ Temperatura</div>
            <div style="font-size: 1.25rem; font-weight: 600;">{temperatura}°C</div>
            
            <div style="color: #64748b; font-size: 0.9rem; margin-top: 0.75rem;">💧 Umidade</div>
            <div style="font-size: 1.25rem; font-weight: 600;">{umidade_valor}%</div>
            
            <div style="color: #64748b; font-size: 0.9rem; margin-top: 0.75rem;">📅 GWP</div>
            <div style="font-size: 1.25rem; font-weight: 600;">{gwp_periodo}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("#### 📈 Estatísticas")
        st.markdown(f"""
        <div style="background: #f8fafc; padding: 1rem; border-radius: 8px; border-left: 4px solid #10b981;">
            <div style="color: #64748b; font-size: 0.9rem;">📦 Lote</div>
            <div style="font-size: 1.25rem; font-weight: 600;">{formatar_br(quantidade_lote)} kg</div>
            
            <div style="color: #64748b; font-size: 0.9rem; margin-top: 0.75rem;">⏱️ Período</div>
            <div style="font-size: 1.25rem; font-weight: 600;">{anos_analise} anos</div>
            
            <div style="color: #64748b; font-size: 0.9rem; margin-top: 0.75rem;">📊 Dias Totais</div>
            <div style="font-size: 1.25rem; font-weight: 600;">{anos_analise * 365}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Botão de cálculo
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
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
            st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h2>📊 Resultados - Lote Único</h2>
                <span class="badge badge-success">Cálculo Concluído</span>
            </div>
            """, unsafe_allow_html=True)
            
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
            st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h2>📈 Visualizações Detalhadas</h2>
                <span class="badge badge-info">Gráficos Interativos</span>
            </div>
            """, unsafe_allow_html=True)
            
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
                - **Pico de emissão no aterro:** {formatar_br(max(emissoes_aterro))} kg CH₄/dia
                - **Duração das emissões:** {anos_analise} anos vs 50 dias
                
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
                - **Valor por tonelada:** R$ {formatar_br(resultados['valor_total_brl'] / (quantidade_lote/1000))}/t
                
                **⚡ IMPACTO AMBIENTAL EQUIVALENTE**
                - **Carros equivalentes:** {formatar_br(resultados['co2eq_evitado_total'] / 2.3)} anos de um carro médio
                - **Árvores equivalentes:** {formatar_br(resultados['co2eq_evitado_total'] * 20)} árvores adultas
                - **Energia equivalente:** {formatar_br(resultados['co2eq_evitado_total'] * 0.4)} MWh de energia limpa
                
                **💡 RECOMENDAÇÕES PRÁTICAS**
                1. **Escalonabilidade:** Considere processamento em lote contínuo
                2. **Tecnologia:** Avalie sistemas de vermicompostagem automatizados
                3. **Mercado:** Registre projeto em padrões como VERRA ou Gold Standard
                4. **Financiamento:** Utilize linhas de crédito verde para implantação
                5. **Monitoramento:** Implemente sistema de MRV (Medição, Relato e Verificação)
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
# ABA 2: ENTRADA CONTÍNUA
# =============================================================================
with tab2:
    st.markdown('<div class="tab-container fade-in">', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
        <div>
            <h2>📈 Análise de Entrada Contínua</h2>
            <p style="color: #64748b; margin-top: -0.5rem;">
            Calcule o potencial de créditos de carbono para processamento diário constante de resíduos
            </p>
        </div>
        <span class="badge badge-warning">Para Operações Contínuas</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Configurações
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 📊 Configuração do Fluxo Contínuo")
        
        residuos_diarios = st.number_input(
            "Resíduos orgânicos processados diariamente (kg/dia)",
            min_value=10.0,
            max_value=50000.0,
            value=1000.0,
            step=100.0,
            help="Quantidade diária de resíduos orgânicos puros processados",
            key="diarios_continuo"
        )
        
        anos_operacao = st.select_slider(
            "Período de operação contínua (anos)",
            options=[5, 10, 15, 20, 25, 30],
            value=20,
            help="Duração da operação de processamento",
            key="anos_continuo"
        )
    
    with col2:
        st.markdown("#### 📈 Estatísticas do Projeto")
        total_processado = residuos_diarios * 365 * anos_operacao / 1000
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); padding: 1.5rem; border-radius: 12px; border: 1px solid #e2e8f0;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                <div>
                    <div style="color: #64748b; font-size: 0.85rem;">📅 Diário</div>
                    <div style="font-size: 1.5rem; font-weight: 700;">{formatar_br(residuos_diarios)} kg</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.85rem;">🏭 Anual</div>
                    <div style="font-size: 1.5rem; font-weight: 700;">{formatar_br(residuos_diarios * 365 / 1000)} t</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.85rem;">📦 Total</div>
                    <div style="font-size: 1.5rem; font-weight: 700;">{formatar_br(total_processado)} t</div>
                </div>
                <div>
                    <div style="color: #64748b; font-size: 0.85rem;">⏱️ Período</div>
                    <div style="font-size: 1.5rem; font-weight: 700;">{anos_operacao} anos</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Botão de cálculo
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        calcular_continuo = st.button(
            "🚀 CALCULAR POTENCIAL CONTÍNUO", 
            type="primary", 
            use_container_width=True,
            key="btn_continuo_calc"
        )
    
    if calcular_continuo:
        with st.spinner("🔍 Calculando projeção de 20 anos..."):
            # Obter parâmetros
            cotacoes = st.session_state.cotacoes
            parametros = st.session_state.parametros_globais
            
            # Calcular emissões
            emissoes_aterro_cont, potencial_diario = calcular_emissoes_aterro_continuo(
                residuos_diarios, umidade, temperatura, anos_operacao
            )
            
            # Calcular vermicompostagem
            dias_totais = anos_operacao * 365
            emissoes_vermi_cont = np.zeros(dias_totais)
            
            for dia in range(dias_totais):
                emissoes_lote, _ = calcular_emissoes_vermicompostagem_lote(residuos_diarios, umidade)
                dias_lote = min(50, dias_totais - dia)
                emissoes_vermi_cont[dia:dia+dias_lote] += emissoes_lote[:dias_lote]
            
            # Calcular créditos
            resultados_cont = calcular_creditos_carbono(
                emissoes_aterro_cont, emissoes_vermi_cont,
                cotacoes.get('preco_carbono', 85.50),
                cotacoes.get('taxa_cambio', 5.50),
                anos_operacao,
                usar_gwp_20=parametros['usar_gwp_20']
            )
            
            st.session_state.resultados_continuo = resultados_cont
            
            # ==================== RESULTADOS ====================
            st.markdown("---")
            st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h2>📊 Resultados - Operação Contínua</h2>
                <span class="badge badge-success">Projeção {anos_operacao} Anos</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Métricas principais
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(criar_metric_card(
                    "Capacidade Anual",
                    formatar_br(residuos_diarios * 365 / 1000),
                    "toneladas/ano",
                    "info",
                    "🏭"
                ), unsafe_allow_html=True)
            
            with col2:
                st.markdown(criar_metric_card(
                    "Créditos Anuais",
                    formatar_br(resultados_cont['co2eq_evitado_anual']),
                    f"tCO₂eq/ano | GWP-{resultados_cont['gwp_utilizado']}",
                    "primary",
                    "📊"
                ), unsafe_allow_html=True)
            
            with col3:
                st.markdown(criar_metric_card(
                    "Receita Anual",
                    f"R$ {formatar_br(resultados_cont['valor_anual_brl'])}",
                    "por ano de operação",
                    "success",
                    "💰"
                ), unsafe_allow_html=True)
            
            with col4:
                st.markdown(criar_metric_card(
                    "Receita Total",
                    f"R$ {formatar_br(resultados_cont['valor_total_brl'])}",
                    f"em {anos_operacao} anos",
                    "warning",
                    "💵"
                ), unsafe_allow_html=True)
            
            # ==================== PROJEÇÕES ====================
            st.markdown("---")
            st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h2>📈 Projeções Temporais</h2>
                <span class="badge badge-info">Cenário {anos_operacao} Anos</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Calcular projeção anual
            anos = list(range(1, anos_operacao + 1))
            creditos_anuais = [resultados_cont['co2eq_evitado_anual']] * anos_operacao
            valor_anual = [resultados_cont['valor_anual_brl']] * anos_operacao
            creditos_acumulados = [resultados_cont['co2eq_evitado_anual'] * ano for ano in anos]
            valor_acumulado = [resultados_cont['valor_anual_brl'] * ano for ano in anos]
            
            # Gráfico de projeção
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=(
                    f'Créditos Anuais ({resultados_cont["gwp_utilizado"]})',
                    'Receita Anual (R$)',
                    f'Créditos Acumulados ({resultados_cont["gwp_utilizado"]})',
                    'Receita Acumulada (R$)'
                ),
                vertical_spacing=0.15,
                horizontal_spacing=0.15
            )
            
            # Créditos anuais
            fig.add_trace(
                go.Bar(
                    x=anos, 
                    y=creditos_anuais, 
                    name='Créditos/Ano', 
                    marker_color='#10b981',
                    hovertemplate='<b>Ano %{x}</b><br>%{y:.1f} tCO₂eq<extra></extra>'
                ),
                row=1, col=1
            )
            
            # Receita anual
            fig.add_trace(
                go.Bar(
                    x=anos, 
                    y=valor_anual, 
                    name='Receita/Ano', 
                    marker_color='#3b82f6',
                    hovertemplate='<b>Ano %{x}</b><br>R$ %{y:,.0f}<extra></extra>'
                ),
                row=1, col=2
            )
            
            # Créditos acumulados
            fig.add_trace(
                go.Scatter(
                    x=anos, 
                    y=creditos_acumulados, 
                    name='Créditos Acum.', 
                    line=dict(color='#10b981', width=4), 
                    fill='tozeroy',
                    fillcolor='rgba(16, 185, 129, 0.2)',
                    hovertemplate='<b>Ano %{x}</b><br>%{y:.1f} tCO₂eq acumulados<extra></extra>'
                ),
                row=2, col=1
            )
            
            # Receita acumulada
            fig.add_trace(
                go.Scatter(
                    x=anos, 
                    y=valor_acumulado, 
                    name='Receita Acum.', 
                    line=dict(color='#8b5cf6', width=4), 
                    fill='tozeroy',
                    fillcolor='rgba(139, 92, 246, 0.2)',
                    hovertemplate='<b>Ano %{x}</b><br>R$ %{y:,.0f} acumulados<extra></extra>'
                ),
                row=2, col=2
            )
            
            fig.update_layout(
                height=600,
                showlegend=False,
                title=dict(
                    text=f"Projeção para {anos_operacao} Anos - {formatar_br(residuos_diarios)} kg/dia",
                    font=dict(size=20, color='#1e293b')
                ),
                plot_bgcolor='rgba(248, 250, 252, 0.8)',
                paper_bgcolor='rgba(255, 255, 255, 0.9)',
                font=dict(color='#1e293b')
            )
            
            # Atualizar eixos
            fig.update_xaxes(title_text="Ano", row=1, col=1)
            fig.update_xaxes(title_text="Ano", row=1, col=2)
            fig.update_xaxes(title_text="Ano", row=2, col=1)
            fig.update_xaxes(title_text="Ano", row=2, col=2)
            
            fig.update_yaxes(title_text="tCO₂eq", row=1, col=1)
            fig.update_yaxes(title_text="R$", row=1, col=2)
            fig.update_yaxes(title_text="tCO₂eq", row=2, col=1)
            fig.update_yaxes(title_text="R$", row=2, col=2)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # ==================== ANÁLISE DE VIABILIDADE ====================
            with st.expander("📋 ANÁLISE DE VIABILIDADE ECONÔMICA", expanded=False):
                st.markdown(f"""
                ### 🎯 VIABILIDADE DO PROJETO - OPERAÇÃO CONTÍNUA
                
                **📊 DADOS OPERACIONAIS**
                - **Capacidade diária:** {formatar_br(residuos_diarios)} kg/dia de orgânicos
                - **Turnover anual:** {formatar_br(residuos_diarios * 365 / 1000)} t/ano
                - **Total processado ({anos_operacao} anos):** {formatar_br(total_processado)} t
                - **Operação:** {anos_operacao} anos ({dias_totais} dias)
                
                **🌍 IMPACTO AMBIENTAL**
                - **Metano evitado/ano:** {formatar_br(resultados_cont['emissoes_evitadas_kg_ch4'] / anos_operacao)} kg CH₄
                - **Créditos gerados/ano:** {formatar_br(resultados_cont['co2eq_evitado_anual'])} tCO₂eq
                - **Equivalente em carros:** {formatar_br(resultados_cont['co2eq_evitado_anual'] / 2.3)} carros fora das ruas/ano
                - **Árvores equivalentes/ano:** {formatar_br(resultados_cont['co2eq_evitado_anual'] * 20)} árvores
                
                **💰 MODELO DE NEGÓCIO**
                - **Receita anual com créditos:** R$ {formatar_br(resultados_cont['valor_anual_brl'])}
                - **Receita total em {anos_operacao} anos:** R$ {formatar_br(resultados_cont['valor_total_brl'])}
                - **Receita por tonelada:** R$ {formatar_br(resultados_cont['valor_total_brl'] / total_processado)}/t
                - **Receita por kg/dia:** R$ {formatar_br(resultados_cont['valor_anual_brl'] / residuos_diarios)} por kg/dia
                
                **🏗️ INVESTIMENTO NECESSÁRIO (ESTIMATIVAS)**
                - **Sistema de compostagem:** R$ 50.000 - 200.000
                - **Infraestrutura:** R$ 100.000 - 500.000
                - **Equipamentos:** R$ 50.000 - 150.000
                - **Operação mensal:** R$ 5.000 - 20.000
                - **Total investimento:** R$ 200.000 - 850.000
                
                **📈 ANÁLISE DE RETORNO**
                - **Investimento médio:** R$ 500.000
                - **Payback simples:** {formatar_br(500000 / resultados_cont['valor_anual_brl'])} anos
                - **TIR estimada:** {formatar_br((resultados_cont['valor_anual_brl'] / 500000) * 100)}% ao ano
                - **VPL (8% a.a.):** R$ {formatar_br((resultados_cont['valor_anual_brl'] / 0.08) * (1 - (1/1.08)**anos_operacao) - 500000)}
                
                **💡 RECEITAS ADICIONAIS POTENCIAIS**
                1. **Composto orgânico:** R$ 200-500/t
                2. **Húmus de minhoca:** R$ 500-1500/t
                3. **Serviços de consultoria**
                4. **Créditos de biodiversidade**
                5. **Educação ambiental**
                
                **🎯 RECOMENDAÇÕES ESTRATÉGICAS**
                1. **Priorize** tecnologias com menor CAPEX
                2. **Busque** incentivos fiscais e subsídios
                3. **Estabeleça** parcerias com geradores de resíduos
                4. **Registre** projeto em padrões internacionais
                5. **Monitore** com sistema MRV robusto
                6. **Diversifique** fontes de receita
                """)
                
                # Tabela de sensibilidade
                st.markdown("#### 📊 Análise de Sensibilidade - Preço do Carbono")
                
                precos_carbono = [60, 85.5, 100, 120, 150]
                dados_sensibilidade = []
                
                for preco in precos_carbono:
                    resultados_temp = calcular_creditos_carbono(
                        emissoes_aterro_cont, emissoes_vermi_cont,
                        preco, taxa_cambio, anos_operacao, usar_gwp_20=parametros['usar_gwp_20']
                    )
                    dados_sensibilidade.append({
                        'Preço Carbono (€)': preco,
                        'Receita Anual (R$)': resultados_temp['valor_anual_brl'],
                        'Receita Total (R$)': resultados_temp['valor_total_brl'],
                        'Payback (anos)': 500000 / resultados_temp['valor_anual_brl'] if resultados_temp['valor_anual_brl'] > 0 else 999
                    })
                
                df_sensibilidade = pd.DataFrame(dados_sensibilidade)
                st.dataframe(df_sensibilidade.style.format({
                    'Preço Carbono (€)': '{:.1f}',
                    'Receita Anual (R$)': 'R$ {:,.0f}',
                    'Receita Total (R$)': 'R$ {:,.0f}',
                    'Payback (anos)': '{:.1f}'
                }), use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# ABA 3: ANÁLISE MUNICIPAL
# =============================================================================
with tab3:
    st.markdown('<div class="tab-container fade-in">', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
        <div>
            <h2>🏙️ Análise de Potencial Municipal</h2>
            <p style="color: #64748b; margin-top: -0.5rem;">
            Calcule o potencial agregado de créditos de carbono para municípios brasileiros
            </p>
        </div>
        <span class="badge badge-danger">Análise em Larga Escala</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Instruções
    with st.expander("📋 INSTRUÇÕES: Como preparar sua planilha", expanded=True):
        st.markdown("""
        ### 📊 ESTRUTURA DA PLANILHA EXCEL
        
        Sua planilha deve conter as seguintes colunas (obrigatórias):
        
        | Coluna | Descrição | Tipo | Exemplo |
        |--------|-----------|------|---------|
        | **Município** | Nome do município | Texto | "São Paulo" |
        | **Estado** | Sigla do estado | Texto | "SP" |
        | **População** | Número de habitantes | Número | 12300000 |
        | **Resíduos Totais (t/dia)** | Total de RSU coletado | Número | 12000 |
        | **Fração Orgânica** | % orgânica no resíduo (0-1) | Decimal | 0.52 |
        | **Taxa de Coleta** | % de resíduos coletados (0-1) | Decimal | 0.95 |
        
        ### 🔄 PROCESSO DE CÁLCULO
        1. **Resíduos Orgânicos** = Resíduos Totais × Fração Orgânica × Taxa de Coleta
        2. **Conversão** = t/dia → kg/dia (× 1000)
        3. **Cálculo** = Mesmo método da Aba 2 (Entrada Contínua)
        4. **Período**: 20 anos (configurável)
        5. **GWP**: {gwp_periodo}
        
        ### 💾 DADOS DE EXEMPLO DISPONÍVEIS
        Caso não tenha dados próprios, use nossa base com 5 capitais brasileiras.
        """)
    
    # Seção de upload
    st.markdown("### 📁 CARREGUE SUA PLANILHA")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Selecione o arquivo Excel (.xlsx ou .xls)",
            type=['xlsx', 'xls'],
            help="Arquivo deve seguir a estrutura descrita acima"
        )
    
    with col2:
        st.markdown("#### 📊 OU")
        usar_dados_exemplo = st.checkbox("Usar dados de exemplo", value=True, help="Dados de 5 capitais brasileiras")
    
    # Dados de exemplo
    dados_exemplo = {
        "Município": ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Salvador", "Fortaleza"],
        "Estado": ["SP", "RJ", "MG", "BA", "CE"],
        "População": [12300000, 6775000, 2531000, 2903000, 2687000],
        "Resíduos Totais (t/dia)": [12000, 6500, 2500, 2900, 2700],
        "Fração Orgânica": [0.52, 0.48, 0.50, 0.55, 0.53],
        "Taxa de Coleta": [0.95, 0.92, 0.93, 0.85, 0.88]
    }
    
    df_municipios = pd.DataFrame(dados_exemplo)
    
    if uploaded_file is not None:
        try:
            df_municipios = pd.read_excel(uploaded_file)
            st.success(f"✅ Arquivo carregado com sucesso: {len(df_municipios)} municípios")
        except Exception as e:
            st.error(f"❌ Erro ao ler arquivo: {str(e)}")
            st.info("📋 Usando dados de exemplo como fallback")
    elif usar_dados_exemplo:
        st.info("📋 Usando dados de exemplo (5 capitais brasileiras)")
    
    # Mostrar dados carregados
    with st.expander("👁️ VISUALIZAR DADOS CARREGADOS", expanded=False):
        st.dataframe(df_municipios.style.format({
            'População': '{:,.0f}',
            'Resíduos Totais (t/dia)': '{:,.1f}',
            'Fração Orgânica': '{:.2%}',
            'Taxa de Coleta': '{:.1%}'
        }), use_container_width=True, height=300)
        
        # Estatísticas rápidas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Municípios", len(df_municipios))
        with col2:
            st.metric("População Total", f"{df_municipios['População'].sum()/1e6:.1f}M")
        with col3:
            residuos_totais = (df_municipios['Resíduos Totais (t/dia)'] * 
                             df_municipios['Fração Orgânica'] * 
                             df_municipios['Taxa de Coleta']).sum()
            st.metric("Resíduos Orgânicos/dia", f"{residuos_totais:,.0f} t")
    
    # Configurações da análise
    st.markdown("### ⚙️ CONFIGURAÇÃO DA ANÁLISE")
    
    col1, col2 = st.columns(2)
    
    with col1:
        selecionar_todos = st.checkbox("Selecionar todos os municípios", value=True)
        
        if not selecionar_todos:
            municipios_selecionados = st.multiselect(
                "Selecionar municípios para análise",
                options=df_municipios['Município'].tolist(),
                default=df_municipios['Município'].tolist()[:3]
            )
        else:
            municipios_selecionados = df_municipios['Município'].tolist()
    
    with col2:
        st.markdown("#### 📅 PERÍODO DE ANÁLISE")
        anos_municipal = st.select_slider(
            "Anos de projeção",
            options=[10, 15, 20, 25, 30],
            value=20,
            help="Período para cálculo do potencial municipal"
        )
    
    # Botão de cálculo
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        calcular_municipal = st.button(
            "🚀 CALCULAR POTENCIAL MUNICIPAL", 
            type="primary", 
            use_container_width=True,
            key="btn_municipal_calc"
        )
    
    if calcular_municipal and len(municipios_selecionados) > 0:
        with st.spinner(f"🔍 Calculando potencial para {len(municipios_selecionados)} municípios..."):
            # Filtrar municípios selecionados
            df_selecionados = df_municipios[df_municipios['Município'].isin(municipios_selecionados)].copy()
            
            # Obter parâmetros
            cotacoes = st.session_state.cotacoes
            parametros = st.session_state.parametros_globais
            
            resultados_municipais = []
            
            # Calcular para cada município
            progress_bar = st.progress(0)
            status_text = st.empty()
            total_municipios = len(df_selecionados)
            
            for idx, (_, municipio) in enumerate(df_selecionados.iterrows()):
                # Atualizar progresso
                progress_bar.progress((idx + 1) / total_municipios)
                status_text.text(f"Processando: {municipio['Município']} ({idx + 1}/{total_municipios})")
                
                # Converter resíduos totais para orgânicos (em kg/dia)
                residuos_organicos_dia_ton = (municipio['Resíduos Totais (t/dia)'] * 
                                            municipio['Fração Orgânica'] * 
                                            municipio['Taxa de Coleta'])
                residuos_organicos_dia_kg = residuos_organicos_dia_ton * 1000
                
                # Calcular como entrada contínua
                emissoes_aterro, _ = calcular_emissoes_aterro_continuo(
                    residuos_organicos_dia_kg, umidade, temperatura, anos_municipal
                )
                
                # Calcular vermicompostagem
                dias_totais = anos_municipal * 365
                emissoes_vermi = np.zeros(dias_totais)
                
                for dia in range(dias_totais):
                    emissoes_lote, _ = calcular_emissoes_vermicompostagem_lote(residuos_organicos_dia_kg, umidade)
                    dias_lote = min(50, dias_totais - dia)
                    emissoes_vermi[dia:dia+dias_lote] += emissoes_lote[:dias_lote]
                
                # Calcular créditos
                resultados = calcular_creditos_carbono(
                    emissoes_aterro, emissoes_vermi,
                    cotacoes.get('preco_carbono', 85.50),
                    cotacoes.get('taxa_cambio', 5.50),
                    anos_municipal,
                    usar_gwp_20=parametros['usar_gwp_20']
                )
                
                # Armazenar resultados
                resultados_municipais.append({
                    'Município': municipio['Município'],
                    'Estado': municipio['Estado'],
                    'População': municipio['População'],
                    'Resíduos Totais (t/dia)': municipio['Resíduos Totais (t/dia)'],
                    'Resíduos Orgânicos (t/dia)': residuos_organicos_dia_ton,
                    'Fração Orgânica': municipio['Fração Orgânica'],
                    'Taxa de Coleta': municipio['Taxa de Coleta'],
                    'Créditos Anuais (tCO₂eq)': resultados['co2eq_evitado_anual'],
                    'Valor Anual (R$)': resultados['valor_anual_brl'],
                    'Valor Total (R$)': resultados['valor_total_brl'],
                    'Valor por Habitante (R$/ano)': resultados['valor_anual_brl'] / municipio['População'] * 1000,
                    'Créditos por Habitante (kg CO₂eq/ano)': (resultados['co2eq_evitado_anual'] * 1000) / municipio['População']
                })
            
            progress_bar.empty()
            status_text.text("✅ Cálculo concluído!")
            
            # Criar DataFrame de resultados
            df_resultados = pd.DataFrame(resultados_municipais)
            
            # ==================== RESULTADOS AGREGADOS ====================
            st.markdown("---")
            st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h2>📊 Resultados Agregados</h2>
                <span class="badge badge-success">{len(df_resultados)} Municípios</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Calcular totais
            total_populacao = df_resultados['População'].sum()
            total_residuos_organicos_dia = df_resultados['Resíduos Orgânicos (t/dia)'].sum()
            total_residuos_organicos_ano = total_residuos_organicos_dia * 365
            total_creditos_anuais = df_resultados['Créditos Anuais (tCO₂eq)'].sum()
            total_valor_anual = df_resultados['Valor Anual (R$)'].sum()
            total_valor_total = df_resultados['Valor Total (R$)'].sum()
            
            # Métricas principais
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(criar_metric_card(
                    "Municípios",
                    str(len(df_resultados)),
                    "analisados",
                    "primary",
                    "🏙️"
                ), unsafe_allow_html=True)
            
            with col2:
                st.markdown(criar_metric_card(
                    "População",
                    f"{formatar_br(total_populacao / 1e6)}M",
                    "habitantes",
                    "info",
                    "👥"
                ), unsafe_allow_html=True)
            
            with col3:
                st.markdown(criar_metric_card(
                    "Resíduos/dia",
                    formatar_br(total_residuos_organicos_dia),
                    "toneladas orgânicas",
                    "warning",
                    "🗑️"
                ), unsafe_allow_html=True)
            
            with col4:
                st.markdown(criar_metric_card(
                    "Créditos/Ano",
                    formatar_br(total_creditos_anuais),
                    f"tCO₂eq | {gwp_periodo}",
                    "success",
                    "📊"
                ), unsafe_allow_html=True)
            
            # Métricas secundárias
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                valor_por_hab = (total_valor_anual / total_populacao) * 1000
                st.markdown(criar_metric_card(
                    "R$/hab/ano",
                    f"R$ {formatar_br(valor_por_hab)}",
                    "por mil habitantes",
                    "info",
                    "💰"
                ), unsafe_allow_html=True)
            
            with col2:
                st.markdown(criar_metric_card(
                    "Receita/Ano",
                    f"R$ {formatar_br(total_valor_anual)}",
                    "agregada",
                    "success",
                    "💵"
                ), unsafe_allow_html=True)
            
            with col3:
                st.markdown(criar_metric_card(
                    "Receita Total",
                    f"R$ {formatar_br(total_valor_total)}",
                    f"em {anos_municipal} anos",
                    "warning",
                    "🏦"
                ), unsafe_allow_html=True)
            
            with col4:
                carros_equivalentes = total_creditos_anuais / 2.3
                st.markdown(criar_metric_card(
                    "Carros",
                    formatar_br(carros_equivalentes),
                    "equivalentes retirados",
                    "danger",
                    "🚗"
                ), unsafe_allow_html=True)
            
            # ==================== TABELA DETALHADA ====================
            st.markdown("---")
            st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h2>🏙️ Detalhamento por Município</h2>
                <span class="badge badge-info">Ordenável e Filtrável</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Preparar tabela para exibição
            df_display = df_resultados.copy()
            df_display = df_display[[
                'Município', 'Estado', 'População', 'Resíduos Orgânicos (t/dia)',
                'Créditos Anuais (tCO₂eq)', 'Valor Anual (R$)', 'Valor por Habitante (R$/ano)'
            ]]
            
            # Renomear colunas
            df_display.columns = ['Município', 'Estado', 'População', 'Resíduos Orgânicos (t/dia)', 
                                'Créditos/Ano (tCO₂eq)', 'Receita/Ano (R$)', 'Receita/Hab (R$/ano)']
            
            st.dataframe(
                df_display.style.format({
                    'População': '{:,.0f}',
                    'Resíduos Orgânicos (t/dia)': '{:,.1f}',
                    'Créditos/Ano (tCO₂eq)': '{:,.1f}',
                    'Receita/Ano (R$)': 'R$ {:,.0f}',
                    'Receita/Hab (R$/ano)': 'R$ {:,.2f}'
                }),
                use_container_width=True,
                height=400
            )
            
            # ==================== VISUALIZAÇÕES ====================
            st.markdown("---")
            st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h2>📈 Visualizações Comparativas</h2>
                <span class="badge badge-warning">Análise Espacial</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Gráfico 1: Top 10 municípios por receita
            st.markdown("#### 🏆 Top 10 Municípios por Potencial de Receita")
            
            top_10 = df_resultados.nlargest(10, 'Valor Anual (R$)')
            
            fig1 = go.Figure()
            
            fig1.add_trace(go.Bar(
                x=top_10['Município'] + ' (' + top_10['Estado'] + ')',
                y=top_10['Valor Anual (R$)'],
                name='Receita Anual',
                marker_color='#8b5cf6',
                text=top_10['Valor Anual (R$)'].apply(lambda x: f"R$ {formatar_br(x)}"),
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>Receita Anual: R$ %{y:,.0f}<extra></extra>'
            ))
            
            fig1.update_layout(
                title=dict(
                    text='Top 10 Municípios por Potencial de Receita Anual',
                    font=dict(size=18, color='#1e293b')
                ),
                xaxis_title='Município',
                yaxis_title='Receita Anual (R$)',
                height=500,
                xaxis_tickangle=45,
                plot_bgcolor='rgba(248, 250, 252, 0.8)',
                paper_bgcolor='rgba(255, 255, 255, 0.9)',
                font=dict(color='#1e293b')
            )
            
            st.plotly_chart(fig1, use_container_width=True)
            
            # Gráfico 2: Dispersão população vs receita
            st.markdown("#### 📊 Relação: População vs Potencial de Créditos")
            
            fig2 = px.scatter(
                df_resultados,
                x='População',
                y='Valor Anual (R$)',
                size='Créditos Anuais (tCO₂eq)',
                color='Estado',
                hover_name='Município',
                log_x=True,
                size_max=40,
                title='Relação entre População e Potencial de Receita'
            )
            
            fig2.update_traces(
                marker=dict(
                    line=dict(width=1, color='DarkSlateGrey'),
                    opacity=0.8
                )
            )
            
            fig2.update_layout(
                height=500,
                plot_bgcolor='rgba(248, 250, 252, 0.8)',
                paper_bgcolor='rgba(255, 255, 255, 0.9)',
                font=dict(color='#1e293b')
            )
            
            st.plotly_chart(fig2, use_container_width=True)
            
            # ==================== RESUMO EXECUTIVO ====================
            with st.expander("📋 RESUMO EXECUTIVO MUNICIPAL", expanded=False):
                st.markdown(f"""
                ### 🎯 RESUMO DO POTENCIAL DE CRÉDITOS DE CARBONO
                
                **📊 ESCOPO DA ANÁLISE**
                - **Municípios analisados:** {len(df_resultados)}
                - **População total atendida:** {formatar_br(total_populacao/1e6)} milhões
                - **Resíduos orgânicos/dia:** {formatar_br(total_residuos_organicos_dia)} t
                - **Resíduos orgânicos/ano:** {formatar_br(total_residuos_organicos_ano)} t
                - **Período de projeção:** {anos_municipal} anos
                - **GWP utilizado:** {gwp_periodo}
                
                **🌍 IMPACTO AMBIENTAL AGREGADO**
                - **Créditos totais anuais:** {formatar_br(total_creditos_anuais)} tCO₂eq
                - **Créditos em {anos_municipal} anos:** {formatar_br(total_creditos_anuais * anos_municipal)} tCO₂eq
                - **Metano evitado/ano:** {formatar_br((total_creditos_anuais * 1000 / GWP_CH4_20))} t CH₄
                - **Equivalente em carros:** {formatar_br(total_creditos_anuais / 2.3)} carros fora das ruas por ano
                - **Árvores equivalentes:** {formatar_br(total_creditos_anuais * 20)} árvores adultas/ano
                
                **💰 POTENCIAL FINANCEIRO**
                - **Receita anual agregada:** R$ {formatar_br(total_valor_anual)}
                - **Receita em {anos_municipal} anos:** R$ {formatar_br(total_valor_total)}
                - **Média por município:** R$ {formatar_br(total_valor_anual / len(df_resultados))}/ano
                - **Média por habitante:** R$ {formatar_br((total_valor_anual / total_populacao) * 1000)} por mil hab/ano
                - **Receita por tonelada:** R$ {formatar_br(total_valor_anual / total_residuos_organicos_ano)}/t
                
                **🏆 TOP 3 MUNICÍPIOS POR POTENCIAL**
                """)
                
                # Top 3 municípios
                top3 = df_resultados.nlargest(3, 'Valor Anual (R$)')
                for i, (_, row) in enumerate(top3.iterrows(), 1):
                    emoji = ["🥇", "🥈", "🥉"][i-1]
                    st.markdown(f"""
                    {emoji} **{row['Município']} ({row['Estado']})**
                    - População: {formatar_br(row['População']/1000)} mil hab
                    - Resíduos orgânicos: {formatar_br(row['Resíduos Orgânicos (t/dia)'])} t/dia
                    - Créditos/ano: {formatar_br(row['Créditos Anuais (tCO₂eq)'])} tCO₂eq
                    - Receita/ano: **R$ {formatar_br(row['Valor Anual (R$)'])}**
                    """)
                
                st.markdown(f"""
                **💡 RECOMENDAÇÕES ESTRATÉGICAS**
                
                1. **PRIORIZAÇÃO GEOGRÁFICA**
                   - Focar em municípios com > 100k habitantes
                   - Considerar clusters regionais para sinergias
                   - Priorizar estados com políticas ambientais favoráveis
                
                2. **MODELOS DE NEGÓCIO**
                   - PPP (Parcerias Público-Privadas) para infraestrutura
                   - Consórcios intermunicipais para escala
                   - ESCOs (Energy Service Companies) para operação
                
                3. **FINANCIAMENTO**
                   - Linhas de crédito BNDES (Saneamento)
                   - Fundos climáticos internacionais (GCF, GEF)
                   - Green bonds (títulos verdes) municipais
                
                4. **IMPLEMENTAÇÃO ESCALONADA**
                   - **Fase 1 (0-2 anos):** Municípios > 500k habitantes
                   - **Fase 2 (2-5 anos):** Consórcios regionais
                   - **Fase 3 (5+ anos):** Expansão nacional
                
                5. **MONITORAMENTO E RELATO**
                   - Sistema MRV (Medição, Relato e Verificação)
                   - Registro em padrões (VERRA, Gold Standard)
                   - Relatórios anuais de sustentabilidade
                
                **📈 PRÓXIMOS PASSOS**
                1. **Análise de viabilidade** técnica-econômica detalhada
                2. **Estudo de mercado** de créditos de carbono
                3. **Projeto de engenharia** para sistemas de tratamento
                4. **Modelagem financeira** completa (VPL, TIR, payback)
                5. **Busca de parceiros** e financiamento
                6. **Elaboração de projeto** para registro em padrões
                """)
            
            # ==================== DOWNLOAD ====================
            st.markdown("---")
            st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h2>💾 Exportar Resultados</h2>
                <span class="badge badge-info">Formato Excel</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Criar arquivo Excel para download
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Resultados detalhados
                df_resultados.to_excel(writer, sheet_name='Resultados_Detalhados', index=False)
                
                # Resumo executivo
                resumo = pd.DataFrame({
                    'Métrica': [
                        'Municípios Analisados',
                        'População Total',
                        'Resíduos Orgânicos/dia (t)',
                        'Resíduos Orgânicos/ano (t)',
                        'Créditos Anuais (tCO₂eq)',
                        'Receita Anual (R$)',
                        'Receita Total (R$)',
                        'Receita por Habitante (R$/ano/1000hab)',
                        'Período de Análise (anos)',
                        'GWP Utilizado'
                    ],
                    'Valor': [
                        len(df_resultados),
                        f"{formatar_br(total_populacao)}",
                        formatar_br(total_residuos_organicos_dia),
                        formatar_br(total_residuos_organicos_ano),
                        formatar_br(total_creditos_anuais),
                        formatar_br(total_valor_anual),
                        formatar_br(total_valor_total),
                        formatar_br((total_valor_anual / total_populacao) * 1000),
                        anos_municipal,
                        gwp_periodo
                    ]
                })
                resumo.to_excel(writer, sheet_name='Resumo_Executivo', index=False)
                
                # Top 10 municípios
                top10 = df_resultados.nlargest(10, 'Valor Anual (R$)')
                top10.to_excel(writer, sheet_name='Top_10_Municípios', index=False)
            
            output.seek(0)
            
            # Botões de download
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="📥 BAIXAR RELATÓRIO COMPLETO (Excel)",
                    data=output,
                    file_name=f"relatorio_municipal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            with col2:
                st.download_button(
                    label="📋 BAIXAR DADOS CRUS (CSV)",
                    data=df_resultados.to_csv(index=False).encode('utf-8'),
                    file_name=f"dados_municipais_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
    
    elif calcular_municipal and len(municipios_selecionados) == 0:
        st.warning("⚠️ Selecione pelo menos um município para análise.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# RODAPÉ MODERNO
# =============================================================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748b; font-size: 0.9rem; padding: 2rem 0;">
    <div style="display: flex; justify-content: center; align-items: center; gap: 1rem; margin-bottom: 1.5rem;">
        <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px;"></div>
        <div>
            <div style="font-size: 1.2rem; font-weight: 700; color: #1e293b;">🌿 CARBON SIMULATOR PRO</div>
            <div>Solução completa para créditos de carbono via gestão de resíduos</div>
        </div>
    </div>
    
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 2rem; margin: 2rem 0;">
        <div style="text-align: left;">
            <div style="font-weight: 600; color: #475569; margin-bottom: 0.5rem;">📊 Metodologia Científica</div>
            <div style="font-size: 0.85rem;">
                IPCC 2006 (Aterro) + Yang et al. 2017 (Compostagem)<br>
                GWP-20: CH₄ = {formatar_br(GWP_CH4_20)} | N₂O = {formatar_br(GWP_N2O_20)}<br>
                GWP-100: CH₄ = {formatar_br(GWP_CH4_100)} | N₂O = {formatar_br(GWP_N2O_100)}
            </div>
        </div>
        
        <div style="text-align: left;">
            <div style="font-weight: 600; color: #475569; margin-bottom: 0.5rem;">💰 Mercado de Carbono</div>
            <div style="font-size: 0.85rem;">
                Preço atual: € {formatar_br(cotacoes.get('preco_carbono', 85.50))}/tCO₂eq<br>
                Taxa EUR/BRL: R$ {formatar_br(cotacoes.get('taxa_cambio', 5.50))}<br>
                Valor BR: R$ {formatar_br(cotacoes.get('preco_carbono_brl', 85.50 * 5.50))}/tCO₂eq
            </div>
        </div>
        
        <div style="text-align: left;">
            <div style="font-weight: 600; color: #475569; margin-bottom: 0.5rem;">⚡ Performance Técnica</div>
            <div style="font-size: 0.85rem;">
                Cálculos otimizados em NumPy/SciPy<br>
                Interface responsiva e moderna<br>
                Exportação completa em múltiplos formatos<br>
                Atualização em tempo real
            </div>
        </div>
    </div>
    
    <div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid #e2e8f0;">
        <div style="display: flex; justify-content: center; gap: 1.5rem; margin-bottom: 1rem;">
            <a href="#" style="color: #64748b; text-decoration: none;">📚 Documentação</a>
            <a href="#" style="color: #64748b; text-decoration: none;">📞 Suporte</a>
            <a href="#" style="color: #64748b; text-decoration: none;">🔒 Privacidade</a>
            <a href="#" style="color: #64748b; text-decoration: none;">📃 Termos</a>
        </div>
        
        <div style="font-size: 0.8rem; color: #94a3b8;">
            © 2024 Carbon Simulator Pro | Versão 2.0.0 | Desenvolvido para transição climática justa<br>
            Última atualização: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")} | 
            <span class="status-indicator status-active"></span> Sistema Operacional
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
