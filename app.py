import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import seaborn as sns
from scipy import stats
from scipy.signal import fftconvolve
from joblib import Parallel, delayed
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
    page_title="CARBON SIMULATOR | Potencial de Créditos de Carbono", 
    layout="wide",
    page_icon="🌿",
    initial_sidebar_state="expanded"
)

# Configurar tema com CSS moderno
st.markdown("""
<style>
    /* Tema principal */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    
    /* Cards de métricas */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        border-left: 5px solid #667eea;
        transition: transform 0.3s ease;
        margin-bottom: 1rem;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
    }
    
    /* Botões modernos */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 7px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* Abas estilizadas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        background: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: white;
        border-radius: 8px 8px 0 0;
        padding: 1rem 2rem;
        border: 1px solid #e0e0e0;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border-color: #667eea;
    }
    
    /* Sidebar moderna */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #2d3748 0%, #4a5568 100%);
    }
    
    /* Inputs estilizados */
    .stNumberInput, .stSlider, .stSelectbox {
        background: white;
        border-radius: 8px;
        padding: 0.5rem;
    }
    
    /* Títulos */
    h1, h2, h3 {
        color: #2d3748;
        font-weight: 700;
    }
    
    /* Contêineres */
    .tab-container {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        margin-top: 1rem;
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
GWP_CH4_20 = 82.5  # Potencial de aquecimento global do metano em 20 anos
GWP_N2O_20 = 273  # Potencial de aquecimento global do N2O em 20 anos

# Parâmetros IPCC 2006
DOC = 0.15  # Carbono orgânico degradável
MCF = 1.0   # Fator de correção de metano para aterros
F = 0.5     # Fração de metano no biogás
OX = 0.1    # Fator de oxidação
Ri = 0.0    # Metano recuperado
k_ano = 0.06  # Constante de decaimento anual

# Parâmetros compostagem (Yang et al. 2017)
TOC_YANG = 0.436  # Fração de carbono orgânico total
TN_YANG = 14.2 / 1000  # Fração de nitrogênio total
CH4_C_FRAC_YANG = 0.13 / 100  # Fração do TOC emitida como CH4-C
N2O_N_FRAC_YANG = 0.92 / 100  # Fração do TN emitida como N2O-N

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

def criar_metric_card(titulo, valor, subtitulo="", cor_borda="#667eea"):
    """Cria um card de métrica estilizado"""
    html = f"""
    <div class="metric-card" style="border-left-color: {cor_borda};">
        <div style="font-size: 0.9rem; color: #718096; margin-bottom: 0.5rem; font-weight: 600;">{titulo}</div>
        <div style="font-size: 2rem; font-weight: 700; color: #2d3748; line-height: 1.2;">{valor}</div>
        <div style="font-size: 0.9rem; color: #718096; margin-top: 0.5rem;">{subtitulo}</div>
    </div>
    """
    return html

# =============================================================================
# FUNÇÕES DE COTAÇÃO EM TEMPO REAL - CORRIGIDAS
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
                # Extrair apenas números e ponto
                numeros = ''.join(c for c in texto if c.isdigit() or c == '.')
                if numeros:
                    preco = float(numeros)
                    if 50 < preco < 200:  # Faixa razoável
                        return preco, "€", "Investing.com", True
        
        # Fallback para valor padrão
        return 85.50, "€", "Referência", False
        
    except Exception as e:
        # Em caso de erro, retorna valor padrão
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
    
    # Fallback
    return 5.50, False, "Referência"

# =============================================================================
# FUNÇÕES DE CÁLCULO CENTRAIS
# =============================================================================

def calcular_potencial_metano_aterro_lote(residuos_kg, umidade, temperatura, anos=20):
    """Calcula potencial de metano para UM ÚNICO LOTE ao longo do tempo"""
    dias = anos * 365
    
    # Cálculo do DOCf baseado na temperatura
    DOCf = 0.0147 * temperatura + 0.28
    
    # Potencial total de metano do lote
    potencial_CH4_total = residuos_kg * DOC * DOCf * MCF * F * (16/12) * (1 - Ri) * (1 - OX)
    
    # Kernel de decaimento
    k_dia = k_ano / 365.0
    t = np.arange(1, dias + 1, dtype=float)
    kernel = np.exp(-k_dia * (t - 1)) - np.exp(-k_dia * t)
    kernel = np.maximum(kernel, 0)
    
    # Emissões ao longo do tempo
    emissoes_CH4 = potencial_CH4_total * kernel
    
    return emissoes_CH4, potencial_CH4_total, DOCf

def calcular_emissoes_aterro_continuo(residuos_kg_dia, umidade, temperatura, anos=20):
    """Calcula emissões de aterro para ENTRADA CONTÍNUA diária"""
    dias = anos * 365
    
    # Parâmetros para cálculo contínuo
    DOCf = 0.0147 * temperatura + 0.28
    potencial_CH4_por_kg = DOC * DOCf * MCF * F * (16/12) * (1 - Ri) * (1 - OX)
    potencial_CH4_diario = residuos_kg_dia * potencial_CH4_por_kg
    
    # Kernel para convolução
    k_dia = k_ano / 365.0
    t = np.arange(1, dias + 1, dtype=float)
    kernel_ch4 = np.exp(-k_dia * (t - 1)) - np.exp(-k_dia * t)
    
    # Emissões usando convolução
    entradas_diarias = np.ones(dias) * potencial_CH4_diario
    emissoes_CH4 = fftconvolve(entradas_diarias, kernel_ch4, mode='full')[:dias]
    
    return emissoes_CH4, potencial_CH4_diario

def calcular_emissoes_vermicompostagem_lote(residuos_kg, umidade):
    """Calcula emissões de metano para vermicompostagem (50 dias)"""
    fracao_ms = 1 - umidade
    ch4_total = residuos_kg * (TOC_YANG * CH4_C_FRAC_YANG * (16/12) * fracao_ms)
    
    # Perfil de 50 dias (distribuição temporal)
    dias = 50
    perfil = np.ones(dias) / dias  # Distribuição uniforme simplificada
    
    return ch4_total * perfil, ch4_total

def calcular_creditos_carbono(emissoes_aterro, emissoes_vermi, preco_carbono_eur, taxa_cambio, anos=20):
    """
    Calcula créditos de carbono para 20 anos usando GWP-20
    """
    # Converter metano para CO₂eq usando GWP-20
    co2eq_aterro = emissoes_aterro * GWP_CH4_20 / 1000  # tCO₂eq
    co2eq_vermi = emissoes_vermi * GWP_CH4_20 / 1000   # tCO₂eq
    
    # Emissões evitadas
    co2eq_evitado = co2eq_aterro.sum() - co2eq_vermi.sum()
    
    # Valor financeiro
    valor_eur = co2eq_evitado * preco_carbono_eur
    valor_brl = valor_eur * taxa_cambio
    
    # Valor anual médio
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
        'emissoes_evitadas_kg_ch4': (emissoes_aterro.sum() - emissoes_vermi.sum())
    }

# =============================================================================
# INICIALIZAÇÃO DA SESSION STATE
# =============================================================================

# Inicializar todas as variáveis necessárias
if 'cotacoes' not in st.session_state:
    # Obter cotações iniciais
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
        'gwp_periodo': '20 anos'
    }

# =============================================================================
# INTERFACE PRINCIPAL
# =============================================================================

# HEADER ELEGANTE
st.markdown("""
<div class="main-header">
    <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;">
        <div style="font-size: 3rem;">🌿</div>
        <div>
            <h1 style="margin: 0; font-size: 2.5rem; font-weight: 800;">CARBON SIMULATOR</h1>
            <p style="margin: 0; opacity: 0.9; font-size: 1.1rem;">Simulador de Potencial de Créditos de Carbono via Gestão de Resíduos Orgânicos</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# BARRA LATERAL - CONFIGURAÇÕES GLOBAIS
# =============================================================================

with st.sidebar:
    st.markdown("### ⚙️ CONFIGURAÇÕES GLOBAIS")
    
    # Divisor visual
    st.markdown("---")
    
    # Seção de cotações
    st.markdown("#### 💰 COTAÇÕES ATUAIS")
    
    # Obter cotações do session state
    cotacoes = st.session_state.cotacoes
    
    # Exibir métricas de cotações
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label="Preço do Carbono",
            value=f"€ {formatar_br(cotacoes.get('preco_carbono', 85.50))}",
            delta=None,
            help=f"Fonte: {cotacoes.get('fonte_carbono', 'Referência')}"
        )
    
    with col2:
        st.metric(
            label="Taxa EUR/BRL",
            value=f"R$ {formatar_br(cotacoes.get('taxa_cambio', 5.50))}",
            delta=None,
            help=f"Fonte: {cotacoes.get('fonte_cambio', 'Referência')}"
        )
    
    # Valor do carbono em Reais
    preco_carbono_brl = cotacoes.get('preco_carbono_brl', 85.50 * 5.50)
    st.info(f"💰 **Carbono em Reais:** R$ {formatar_br(preco_carbono_brl)}/tCO₂eq")
    
    # Divisor
    st.markdown("---")
    
    # Parâmetros ambientais
    st.markdown("#### 🌡️ PARÂMETROS AMBIENTAIS")
    
    # Temperatura
    temperatura = st.slider(
        "Temperatura média (°C)",
        min_value=15.0,
        max_value=35.0,
        value=25.0,
        step=0.5,
        help="Temperatura média para cálculo do DOCf (IPCC 2006)"
    )
    
    # Umidade
    umidade_valor = st.slider(
        "Umidade dos resíduos (%)",
        min_value=50.0,
        max_value=95.0,
        value=85.0,
        step=1.0,
        help="Percentual de umidade dos resíduos orgânicos"
    )
    umidade = umidade_valor / 100.0
    
    # Atualizar session state
    st.session_state.parametros_globais['temperatura'] = temperatura
    st.session_state.parametros_globais['umidade'] = umidade
    
    # Divisor
    st.markdown("---")
    
    # Período do GWP
    st.markdown("#### 📊 FATOR GWP")
    gwp_periodo = st.selectbox(
        "Período do Potencial de Aquecimento Global",
        options=["20 anos (GWP-20)", "100 anos (GWP-100)"],
        index=0,
        help="GWP-20 é mais relevante para créditos de carbono de curto prazo"
    )
    
    st.session_state.parametros_globais['gwp_periodo'] = gwp_periodo
    
    # Explicação do GWP
    with st.expander("ℹ️ Sobre o GWP"):
        st.markdown("""
        **GWP-20 (20 anos):** 
        - Metano (CH₄): **82.5** 
        - Óxido Nitroso (N₂O): **273**
        
        **GWP-100 (100 anos):**
        - Metano (CH₄): **29.8**
        - Óxido Nitroso (N₂O): **273**
        
        *Fonte: IPCC AR6 (2021)*
        """)
    
    # Divisor
    st.markdown("---")
    
    # Botão para atualizar cotações
    if st.button("🔄 Atualizar Cotações", use_container_width=True):
        with st.spinner("Atualizando cotações..."):
            # Atualizar cotações
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
    
    # Informação de atualização
    timestamp = cotacoes.get('timestamp', datetime.now())
    st.caption(f"🕒 Última atualização: {timestamp.strftime('%H:%M:%S')}")

# =============================================================================
# NAVEGAÇÃO POR ABAS
# =============================================================================

# Criar abas com descrições
tab1, tab2, tab3 = st.tabs([
    "📦 LOTE ÚNICO (100 kg)", 
    "📈 ENTRADA CONTÍNUA", 
    "🏙️ POTENCIAL MUNICIPAL"
])

# =============================================================================
# ABA 1: LOTE ÚNICO (100 kg de resíduos orgânicos puros)
# =============================================================================
with tab1:
    st.markdown('<div class="tab-container">', unsafe_allow_html=True)
    
    st.header("📦 Análise de Lote Único")
    st.markdown("""
    **Calcule o potencial de créditos de carbono para um único lote de resíduos orgânicos puros**
    
    *Cenário: Um lote de resíduos de frutas, vegetais e restos de comida processado uma única vez*
    """)
    
    # Configurações específicas da Aba 1
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Configuração do Lote")
        
        quantidade_lote = st.number_input(
            "Peso do lote de resíduos orgânicos (kg)",
            min_value=10.0,
            max_value=10000.0,
            value=100.0,
            step=10.0,
            help="Peso total do lote de resíduos orgânicos puros"
        )
        
        anos_analise = st.select_slider(
            "Período de acompanhamento das emissões",
            options=[1, 5, 10, 15, 20, 25, 30],
            value=20,
            help="Tempo que o lote continuará emitindo metano no aterro"
        )
    
    with col2:
        st.subheader("⚙️ Parâmetros")
        st.markdown(f"""
        **Temperatura:** {temperatura}°C  
        **Umidade:** {umidade_valor}%  
        **GWP:** {gwp_periodo}  
        **Período:** {anos_analise} anos
        """)
    
    # Botão de cálculo
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        calcular_lote = st.button("🚀 CALCULAR POTENCIAL DO LOTE", 
                                type="primary", 
                                use_container_width=True,
                                key="btn_lote")
    
    if calcular_lote:
        with st.spinner("Calculando potencial de créditos..."):
            # Obter parâmetros
            cotacoes = st.session_state.cotacoes
            parametros = st.session_state.parametros_globais
            
            # Calcular emissões do aterro
            emissoes_aterro, potencial_total, docf = calcular_potencial_metano_aterro_lote(
                quantidade_lote, umidade, temperatura, anos_analise
            )
            
            # Calcular emissões da vermicompostagem
            emissoes_vermi, total_vermi = calcular_emissoes_vermicompostagem_lote(
                quantidade_lote, umidade
            )
            
            # Estender emissões da vermicompostagem para o período total
            emissoes_vermi_completa = np.zeros(len(emissoes_aterro))
            dias_vermi = min(50, len(emissoes_vermi))
            emissoes_vermi_completa[:dias_vermi] = emissoes_vermi[:dias_vermi]
            
            # Calcular créditos de carbono
            resultados = calcular_creditos_carbono(
                emissoes_aterro, emissoes_vermi_completa,
                cotacoes.get('preco_carbono', 85.50), 
                cotacoes.get('taxa_cambio', 5.50), 
                anos_analise
            )
            
            # ==================== RESULTADOS ====================
            st.markdown("---")
            st.header("📊 RESULTADOS - LOTE ÚNICO")
            
            # Métricas principais em 4 colunas
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(criar_metric_card(
                    "Metano Evitado",
                    formatar_br(resultados['emissoes_evitadas_kg_ch4']),
                    "kg CH₄",
                    "#10B981"
                ), unsafe_allow_html=True)
            
            with col2:
                st.markdown(criar_metric_card(
                    "Créditos Gerados",
                    formatar_br(resultados['co2eq_evitado_total']),
                    "tCO₂eq (GWP-20)",
                    "#3B82F6"
                ), unsafe_allow_html=True)
            
            with col3:
                st.markdown(criar_metric_card(
                    "Valor Total",
                    f"R$ {formatar_br(resultados['valor_total_brl'])}",
                    f"@ €{formatar_br(cotacoes.get('preco_carbono', 85.50))}/tCO₂eq",
                    "#8B5CF6"
                ), unsafe_allow_html=True)
            
            with col4:
                st.markdown(criar_metric_card(
                    "Valor por kg",
                    f"R$ {formatar_br(resultados['valor_total_brl'] / quantidade_lote)}",
                    "por kg de resíduo",
                    "#F59E0B"
                ), unsafe_allow_html=True)
            
            # ==================== GRÁFICOS ====================
            st.markdown("---")
            st.header("📈 VISUALIZAÇÕES")
            
            # Criar dataframe para gráficos
            datas = pd.date_range(start=datetime.now(), periods=len(emissoes_aterro), freq='D')
            df_emissoes = pd.DataFrame({
                'Data': datas,
                'Aterro - CH₄ (kg/dia)': emissoes_aterro,
                'Vermicompostagem - CH₄ (kg/dia)': emissoes_vermi_completa,
            })
            
            # Calcular acumulados
            df_emissoes['Aterro - Acumulado'] = df_emissoes['Aterro - CH₄ (kg/dia)'].cumsum()
            df_emissoes['Vermi - Acumulado'] = df_emissoes['Vermicompostagem - CH₄ (kg/dia)'].cumsum()
            
            # Gráfico 1: Emissões diárias
            fig1 = go.Figure()
            
            fig1.add_trace(go.Scatter(
                x=df_emissoes['Data'],
                y=df_emissoes['Aterro - CH₄ (kg/dia)'],
                name='Aterro (kg CH₄/dia)',
                line=dict(color='red', width=2),
                fill='tozeroy',
                fillcolor='rgba(255,0,0,0.1)'
            ))
            
            fig1.add_trace(go.Scatter(
                x=df_emissoes['Data'],
                y=df_emissoes['Vermicompostagem - CH₄ (kg/dia)'],
                name='Vermicompostagem (kg CH₄/dia)',
                line=dict(color='green', width=2),
                fill='tozeroy',
                fillcolor='rgba(0,255,0,0.1)'
            ))
            
            fig1.update_layout(
                title=f'Emissões Diárias de Metano - Lote de {quantidade_lote} kg',
                xaxis_title='Data',
                yaxis_title='kg CH₄ por dia',
                hovermode='x unified',
                height=400
            )
            
            st.plotly_chart(fig1, use_container_width=True)
            
            # Gráfico 2: Emissões acumuladas
            fig2 = go.Figure()
            
            fig2.add_trace(go.Scatter(
                x=df_emissoes['Data'],
                y=df_emissoes['Aterro - Acumulado'],
                name='Aterro - Acumulado',
                line=dict(color='red', width=3),
                fill='tozeroy',
                fillcolor='rgba(255,0,0,0.2)'
            ))
            
            fig2.add_trace(go.Scatter(
                x=df_emissoes['Data'],
                y=df_emissoes['Vermi - Acumulado'],
                name='Vermicompostagem - Acumulado',
                line=dict(color='green', width=3),
                fill='tozeroy',
                fillcolor='rgba(0,255,0,0.2)'
            ))
            
            # Área entre as curvas (emissões evitadas)
            fig2.add_trace(go.Scatter(
                x=df_emissoes['Data'],
                y=df_emissoes['Aterro - Acumulado'],
                mode='lines',
                line=dict(width=0),
                showlegend=False,
                hoverinfo='skip'
            ))
            
            fig2.add_trace(go.Scatter(
                x=df_emissoes['Data'],
                y=df_emissoes['Vermi - Acumulado'],
                mode='lines',
                fill='tonexty',
                fillcolor='rgba(100, 100, 255, 0.3)',
                line=dict(width=0),
                name='Emissões Evitadas',
                showlegend=True
            ))
            
            fig2.update_layout(
                title=f'Emissões Acumuladas de Metano - {anos_analise} Anos',
                xaxis_title='Data',
                yaxis_title='kg CH₄ acumulado',
                hovermode='x unified',
                height=400
            )
            
            st.plotly_chart(fig2, use_container_width=True)
            
            # ==================== RESUMO DETALHADO ====================
            with st.expander("📋 RESUMO DETALHADO DA ANÁLISE", expanded=True):
                st.markdown(f"""
                ### 🎯 ANÁLISE COMPLETA - LOTE ÚNICO
                
                **📊 DADOS DE ENTRADA:**
                - **Peso do lote:** {formatar_br(quantidade_lote)} kg de resíduos orgânicos puros
                - **Período de análise:** {anos_analise} anos ({anos_analise * 365} dias)
                - **Umidade:** {formatar_br(umidade_valor)}%
                - **Temperatura:** {formatar_br(temperatura)}°C
                - **DOCf calculado:** {formatar_br(docf)} (fórmula IPCC: 0.0147 × T + 0.28)
                
                **🌿 EMISSÕES DE METANO:**
                - **Aterro sanitário:** {formatar_br(emissoes_aterro.sum())} kg CH₄ total
                - **Vermicompostagem:** {formatar_br(emissoes_vermi_completa.sum())} kg CH₄ total
                - **Redução absoluta:** {formatar_br(resultados['emissoes_evitadas_kg_ch4'])} kg CH₄
                - **Eficiência de redução:** {formatar_br((1 - emissoes_vermi_completa.sum()/emissoes_aterro.sum())*100)}%
                
                **🌍 CRÉDITOS DE CARBONO (GWP-20):**
                - **Aterro:** {formatar_br(resultados['co2eq_aterro_total'])} tCO₂eq
                - **Vermicompostagem:** {formatar_br(resultados['co2eq_vermi_total'])} tCO₂eq
                - **Créditos geráveis:** **{formatar_br(resultados['co2eq_evitado_total'])} tCO₂eq**
                
                **💰 VALOR FINANCEIRO:**
                - **Preço do carbono:** € {formatar_br(cotacoes.get('preco_carbono', 85.50))}/tCO₂eq
                - **Taxa de câmbio:** € 1 = R$ {formatar_br(cotacoes.get('taxa_cambio', 5.50))}
                - **Valor total:** **R$ {formatar_br(resultados['valor_total_brl'])}**
                - **Valor por kg:** R$ {formatar_br(resultados['valor_total_brl'] / quantidade_lote)}/kg
                - **Valor por tonelada:** R$ {formatar_br(resultados['valor_total_brl'] / (quantidade_lote/1000))}/t
                
                **⏰ DIFERENÇA TEMPORAL CRÍTICA:**
                - **Aterro sanitário:** Emissões por **{anos_analise} anos** (decaimento exponencial)
                - **Vermicompostagem:** Emissões em **apenas 50 dias** (processo concentrado)
                - **Vantagem:** Controle total das emissões em período curtíssimo
                
                **💡 IMPLICAÇÕES PRÁTICAS:**
                - Este lote evitaria emissões equivalentes a **{formatar_br(resultados['co2eq_evitado_total'] / 2.3)} anos** de um carro médio
                - Potencial de **R$ {formatar_br(resultados['valor_total_brl'])}** em créditos de carbono
                - Investimento em compostagem/vermicompostagem pode ter retorno atrelado a créditos
                """)
    
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# ABA 2: ENTRADA CONTÍNUA (kg/dia de resíduos orgânicos puros)
# =============================================================================
with tab2:
    st.markdown('<div class="tab-container">', unsafe_allow_html=True)
    
    st.header("📈 Análise de Entrada Contínua")
    st.markdown("""
    **Calcule o potencial de créditos de carbono para um fluxo contínuo diário de resíduos orgânicos puros**
    
    *Cenário: Processamento diário constante de resíduos orgânicos por 20 anos*
    """)
    
    # Configurações específicas da Aba 2
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Configuração do Fluxo")
        
        residuos_diarios = st.number_input(
            "Resíduos orgânicos processados diariamente (kg/dia)",
            min_value=10.0,
            max_value=50000.0,
            value=100.0,
            step=10.0,
            help="Quantidade diária de resíduos orgânicos puros processados",
            key="diarios_cont"
        )
        
        anos_operacao = st.select_slider(
            "Período de operação contínua",
            options=[5, 10, 15, 20, 25, 30],
            value=20,
            help="Duração da operação de processamento",
            key="anos_cont"
        )
    
    with col2:
        st.subheader("⚙️ Parâmetros")
        total_processado = residuos_diarios * 365 * anos_operacao / 1000
        st.markdown(f"""
        **Processamento diário:** {formatar_br(residuos_diarios)} kg/dia  
        **Total processado:** {formatar_br(total_processado)} t  
        **Período:** {anos_operacao} anos  
        **GWP:** {gwp_periodo}
        """)
    
    # Botão de cálculo
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        calcular_continuo = st.button("🚀 CALCULAR POTENCIAL CONTÍNUO", 
                                    type="primary", 
                                    use_container_width=True,
                                    key="btn_cont")
    
    if calcular_continuo:
        with st.spinner("Calculando projeção de 20 anos..."):
            # Obter parâmetros
            cotacoes = st.session_state.cotacoes
            parametros = st.session_state.parametros_globais
            
            # Calcular emissões do aterro (contínuo)
            emissoes_aterro_cont, potencial_diario = calcular_emissoes_aterro_continuo(
                residuos_diarios, umidade, temperatura, anos_operacao
            )
            
            # Calcular emissões da vermicompostagem (processo contínuo)
            dias_totais = anos_operacao * 365
            emissoes_vermi_cont = np.zeros(dias_totais)
            
            # Para cada dia, adicionar emissões da vermicompostagem (50 dias)
            for dia in range(dias_totais):
                emissoes_lote, _ = calcular_emissoes_vermicompostagem_lote(residuos_diarios, umidade)
                dias_lote = min(50, dias_totais - dia)
                emissoes_vermi_cont[dia:dia+dias_lote] += emissoes_lote[:dias_lote]
            
            # Calcular créditos
            resultados_cont = calcular_creditos_carbono(
                emissoes_aterro_cont, emissoes_vermi_cont,
                cotacoes.get('preco_carbono', 85.50),
                cotacoes.get('taxa_cambio', 5.50),
                anos_operacao
            )
            
            # ==================== RESULTADOS ====================
            st.markdown("---")
            st.header("📊 RESULTADOS - ENTRADA CONTÍNUA")
            
            # Métricas principais
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(criar_metric_card(
                    "Resíduos Totais",
                    formatar_br(total_processado),
                    "toneladas em 20 anos",
                    "#6366F1"
                ), unsafe_allow_html=True)
            
            with col2:
                st.markdown(criar_metric_card(
                    "Créditos Anuais",
                    formatar_br(resultados_cont['co2eq_evitado_anual']),
                    "tCO₂eq/ano (GWP-20)",
                    "#10B981"
                ), unsafe_allow_html=True)
            
            with col3:
                st.markdown(criar_metric_card(
                    "Receita Anual",
                    f"R$ {formatar_br(resultados_cont['valor_anual_brl'])}",
                    "por ano",
                    "#3B82F6"
                ), unsafe_allow_html=True)
            
            with col4:
                st.markdown(criar_metric_card(
                    "Receita Total",
                    f"R$ {formatar_br(resultados_cont['valor_total_brl'])}",
                    f"em {anos_operacao} anos",
                    "#8B5CF6"
                ), unsafe_allow_html=True)
            
            # ==================== GRÁFICOS ====================
            st.markdown("---")
            st.header("📈 PROJEÇÃO TEMPORAL")
            
            # Calcular projeção anual
            anos = list(range(1, anos_operacao + 1))
            creditos_anuais = [resultados_cont['co2eq_evitado_anual']] * anos_operacao
            valor_anual = [resultados_cont['valor_anual_brl']] * anos_operacao
            
            creditos_acumulados = [resultados_cont['co2eq_evitado_anual'] * ano for ano in anos]
            valor_acumulado = [resultados_cont['valor_anual_brl'] * ano for ano in anos]
            
            # Gráfico de projeção
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Créditos Anuais (tCO₂eq)', 'Receita Anual (R$)',
                              'Créditos Acumulados (tCO₂eq)', 'Receita Acumulada (R$)'),
                vertical_spacing=0.15,
                horizontal_spacing=0.15
            )
            
            # Créditos anuais
            fig.add_trace(
                go.Bar(x=anos, y=creditos_anuais, name='Créditos/Ano', marker_color='#10B981'),
                row=1, col=1
            )
            
            # Receita anual
            fig.add_trace(
                go.Bar(x=anos, y=valor_anual, name='Receita/Ano', marker_color='#3B82F6'),
                row=1, col=2
            )
            
            # Créditos acumulados
            fig.add_trace(
                go.Scatter(x=anos, y=creditos_acumulados, name='Créditos Acum.', 
                          line=dict(color='#10B981', width=3), fill='tozeroy'),
                row=2, col=1
            )
            
            # Receita acumulada
            fig.add_trace(
                go.Scatter(x=anos, y=valor_acumulado, name='Receita Acum.', 
                          line=dict(color='#8B5CF6', width=3), fill='tozeroy'),
                row=2, col=2
            )
            
            fig.update_layout(
                height=600,
                showlegend=False,
                title=f"Projeção para {anos_operacao} Anos - {formatar_br(residuos_diarios)} kg/dia"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # ==================== RESUMO DETALHADO ====================
            with st.expander("📋 ANÁLISE DE VIABILIDADE", expanded=True):
                st.markdown(f"""
                ### 🎯 VIABILIDADE DO PROJETO - ENTRADA CONTÍNUA
                
                **📊 DADOS OPERACIONAIS:**
                - **Capacidade diária:** {formatar_br(residuos_diarios)} kg/dia de orgânicos
                - **Período de operação:** {anos_operacao} anos
                - **Total processado:** {formatar_br(total_processado)} toneladas
                - **Turnover:** {formatar_br(residuos_diarios * 365 / 1000)} t/ano
                
                **🌍 IMPACTO AMBIENTAL ANUAL:**
                - **Metano evitado:** {formatar_br(resultados_cont['emissoes_evitadas_kg_ch4'] / anos_operacao)} kg CH₄/ano
                - **Créditos gerados:** {formatar_br(resultados_cont['co2eq_evitado_anual'])} tCO₂eq/ano
                - **Equivalente em carros:** {formatar_br(resultados_cont['co2eq_evitado_anual'] / 2.3)} carros fora das ruas
                
                **💰 MODELO DE NEGÓCIO:**
                - **Receita anual com créditos:** R$ {formatar_br(resultados_cont['valor_anual_brl'])}
                - **Receita total em {anos_operacao} anos:** R$ {formatar_br(resultados_cont['valor_total_brl'])}
                - **Receita por tonelada:** R$ {formatar_br(resultados_cont['valor_total_brl'] / total_processado)}/t
                - **Receita por kg/dia:** R$ {formatar_br(resultados_cont['valor_anual_brl'] / residuos_diarios)} por kg/dia
                
                **🏗️ INVESTIMENTO NECESSÁRIO:**
                - **Sistema de compostagem:** R$ XX.XXX (estimativa)
                - **Sistema de vermicompostagem:** R$ XX.XXX (estimativa)
                - **Infraestrutura:** R$ XX.XXX (estimativa)
                - **Operação:** R$ X.XXX/mês (estimativa)
                
                **📈 ANÁLISE DE RETORNO:**
                - **Payback simples:** {formatar_br(1000000 / resultados_cont['valor_anual_brl'])} anos para investimento de R$ 1 milhão
                - **TIR (Taxa Interna de Retorno):** XX% (a ser calculada)
                - **VPL (Valor Presente Líquido):** R$ XX.XXX (a 8% ao ano)
                
                **🎯 RECOMENDAÇÕES:**
                1. **Priorize tecnologias** com menor custo de implantação
                2. **Busque incentivos** governamentais para compostagem
                3. **Considere receitas adicionais** com venda de composto
                4. **Monte um projeto de créditos** de carbono registrado
                5. **Estabeleça parcerias** com geradores de resíduos
                """)
    
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# ABA 3: POTENCIAL MUNICIPAL (Excel → fração orgânica → cálculo)
# =============================================================================
with tab3:
    st.markdown('<div class="tab-container">', unsafe_allow_html=True)
    
    st.header("🏙️ Análise de Potencial Municipal")
    st.markdown("""
    **Calcule o potencial de créditos de carbono para municípios brasileiros**
    
    *Processo: Dados de resíduos totais (Excel) → Aplica fração orgânica → Calcula como entrada contínua*
    """)
    
    # Instruções
    with st.expander("📋 INSTRUÇÕES: Como preparar sua planilha", expanded=True):
        st.markdown("""
        ### ESTRUTURA DA PLANILHA EXCEL:
        
        Sua planilha deve conter as seguintes colunas:
        
        | Coluna | Descrição | Exemplo |
        |--------|-----------|---------|
        | **Município** | Nome do município | "São Paulo" |
        | **Estado** | Sigla do estado | "SP" |
        | **População** | Número de habitantes | 12300000 |
        | **Resíduos Totais (t/dia)** | Total de RSU coletado | 12000 |
        | **Fração Orgânica** | Fração orgânica no resíduo (0-1) | 0.52 |
        | **Taxa de Coleta** | % de resíduos coletados (0-1) | 0.95 |
        
        ### CÁLCULO AUTOMÁTICO:
        1. **Resíduos Orgânicos** = Resíduos Totais × Fração Orgânica × Taxa de Coleta
        2. **Cálculo** = Mesmo método da Aba 2 (Entrada Contínua)
        3. **Período**: 20 anos
        4. **GWP**: 20 anos
        """)
    
    # Seção de upload
    st.subheader("📁 CARREGUE SUA PLANILHA")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Selecione o arquivo Excel com dados municipais",
            type=['xlsx', 'xls'],
            help="Arquivo deve seguir a estrutura descrita acima"
        )
    
    with col2:
        st.markdown("#### 📊 OU")
        usar_dados_exemplo = st.checkbox("Usar dados de exemplo", value=True)
    
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
            st.success(f"✅ Arquivo carregado: {len(df_municipios)} municípios")
        except Exception as e:
            st.error(f"❌ Erro ao ler arquivo: {str(e)}")
            st.info("Usando dados de exemplo")
    elif usar_dados_exemplo:
        st.info("📋 Usando dados de exemplo (5 capitais)")
    
    # Mostrar dados carregados
    with st.expander("👁️ VISUALIZAR DADOS CARREGADOS", expanded=False):
        st.dataframe(df_municipios, use_container_width=True, height=300)
    
    # Configurações da análise
    st.subheader("⚙️ CONFIGURAÇÃO DA ANÁLISE")
    
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
        st.markdown("#### 📅 PERÍODO")
        anos_municipal = st.select_slider(
            "Anos de projeção",
            options=[10, 15, 20, 25, 30],
            value=20,
            help="Período para cálculo do potencial municipal"
        )
    
    # Botão de cálculo
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        calcular_municipal = st.button("🚀 CALCULAR POTENCIAL MUNICIPAL", 
                                     type="primary", 
                                     use_container_width=True,
                                     key="btn_mun")
    
    if calcular_municipal and len(municipios_selecionados) > 0:
        with st.spinner(f"Calculando potencial para {len(municipios_selecionados)} municípios..."):
            # Filtrar municípios selecionados
            df_selecionados = df_municipios[df_municipios['Município'].isin(municipios_selecionados)].copy()
            
            # Obter parâmetros
            cotacoes = st.session_state.cotacoes
            parametros = st.session_state.parametros_globais
            
            resultados_municipais = []
            
            # Calcular para cada município
            progress_bar = st.progress(0)
            total_municipios = len(df_selecionados)
            
            for idx, (_, municipio) in enumerate(df_selecionados.iterrows()):
                # Atualizar progresso
                progress_bar.progress((idx + 1) / total_municipios)
                
                # Converter resíduos totais para orgânicos (em kg/dia)
                residuos_organicos_dia_ton = (municipio['Resíduos Totais (t/dia)'] * 
                                            municipio['Fração Orgânica'] * 
                                            municipio['Taxa de Coleta'])
                residuos_organicos_dia_kg = residuos_organicos_dia_ton * 1000
                
                # Calcular como entrada contínua (igual Aba 2)
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
                    anos_municipal
                )
                
                # Armazenar resultados
                resultados_municipais.append({
                    'Município': municipio['Município'],
                    'Estado': municipio['Estado'],
                    'População': municipio['População'],
                    'Resíduos Totais (t/dia)': municipio['Resíduos Totais (t/dia)'],
                    'Resíduos Orgânicos (t/dia)': residuos_organicos_dia_ton,
                    'Fração Orgânica': municipio['Fração Orgânica'],
                    'Créditos Anuais (tCO₂eq)': resultados['co2eq_evitado_anual'],
                    'Valor Anual (R$)': resultados['valor_anual_brl'],
                    'Valor 20 Anos (R$)': resultados['valor_total_brl'],
                    'Valor por Habitante (R$/ano)': resultados['valor_anual_brl'] / municipio['População'] * 1000,
                    'Créditos por Habitante (kg CO₂eq/ano)': (resultados['co2eq_evitado_anual'] * 1000) / municipio['População']
                })
            
            progress_bar.empty()
            
            # Criar DataFrame de resultados
            df_resultados = pd.DataFrame(resultados_municipais)
            
            # ==================== RESULTADOS AGREGADOS ====================
            st.markdown("---")
            st.header("📊 RESULTADOS AGREGADOS")
            
            # Calcular totais
            total_populacao = df_resultados['População'].sum()
            total_residuos_organicos = df_resultados['Resíduos Orgânicos (t/dia)'].sum() * 365
            total_creditos_anuais = df_resultados['Créditos Anuais (tCO₂eq)'].sum()
            total_valor_anual = df_resultados['Valor Anual (R$)'].sum()
            total_valor_20anos = df_resultados['Valor 20 Anos (R$)'].sum()
            
            # Métricas principais
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(criar_metric_card(
                    "Municípios",
                    str(len(df_resultados)),
                    "analisados",
                    "#6366F1"
                ), unsafe_allow_html=True)
            
            with col2:
                st.markdown(criar_metric_card(
                    "População",
                    formatar_br(total_populacao / 1e6),
                    "milhões de habitantes",
                    "#10B981"
                ), unsafe_allow_html=True)
            
            with col3:
                st.markdown(criar_metric_card(
                    "Créditos/Ano",
                    formatar_br(total_creditos_anuais),
                    "tCO₂eq por ano",
                    "#3B82F6"
                ), unsafe_allow_html=True)
            
            with col4:
                st.markdown(criar_metric_card(
                    "Receita/Ano",
                    f"R$ {formatar_br(total_valor_anual)}",
                    "por ano",
                    "#8B5CF6"
                ), unsafe_allow_html=True)
            
            # ==================== TABELA DETALHADA ====================
            st.markdown("---")
            st.header("🏙️ DETALHAMENTO POR MUNICÍPIO")
            
            # Preparar tabela para exibição
            df_display = df_resultados.copy()
            df_display = df_display[[
                'Município', 'Estado', 'População', 'Resíduos Orgânicos (t/dia)',
                'Créditos Anuais (tCO₂eq)', 'Valor Anual (R$)', 'Valor por Habitante (R$/ano)'
            ]]
            
            # Formatar números
            df_display['População'] = df_display['População'].apply(lambda x: f"{formatar_br(x/1000)} mil")
            df_display['Resíduos Orgânicos (t/dia)'] = df_display['Resíduos Orgânicos (t/dia)'].apply(formatar_br)
            df_display['Créditos Anuais (tCO₂eq)'] = df_display['Créditos Anuais (tCO₂eq)'].apply(formatar_br)
            df_display['Valor Anual (R$)'] = df_display['Valor Anual (R$)'].apply(lambda x: f"R$ {formatar_br(x)}")
            df_display['Valor por Habitante (R$/ano)'] = df_display['Valor por Habitante (R$/ano)'].apply(lambda x: f"R$ {formatar_br(x)}")
            
            # Renomear colunas
            df_display.columns = ['Município', 'Estado', 'População', 'Resíduos Orgânicos (t/dia)', 
                                'Créditos/Ano (tCO₂eq)', 'Receita/Ano (R$)', 'Receita/Hab (R$/ano)']
            
            st.dataframe(df_display, use_container_width=True, height=400)
            
            # ==================== VISUALIZAÇÕES ====================
            st.markdown("---")
            st.header("📈 VISUALIZAÇÕES COMPARATIVAS")
            
            # Gráfico 1: Top 10 municípios por receita
            st.subheader("🏆 Top Municípios por Potencial de Receita")
            
            top_10 = df_resultados.nlargest(10, 'Valor Anual (R$)')
            
            fig1 = go.Figure()
            
            fig1.add_trace(go.Bar(
                x=top_10['Município'] + ' (' + top_10['Estado'] + ')',
                y=top_10['Valor Anual (R$)'],
                name='Receita Anual',
                marker_color='#8B5CF6',
                text=top_10['Valor Anual (R$)'].apply(lambda x: f"R$ {formatar_br(x)}"),
                textposition='outside'
            ))
            
            fig1.update_layout(
                title='Top 10 Municípios por Potencial de Receita Anual',
                xaxis_title='Município',
                yaxis_title='Receita Anual (R$)',
                height=500,
                xaxis_tickangle=45
            )
            
            st.plotly_chart(fig1, use_container_width=True)
            
            # Gráfico 2: Dispersão população vs receita
            st.subheader("📊 Relação: População vs Potencial de Créditos")
            
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
            
            fig2.update_traces(marker=dict(line=dict(width=1, color='DarkSlateGrey')))
            
            st.plotly_chart(fig2, use_container_width=True)
            
            # ==================== RESUMO EXECUTIVO ====================
            with st.expander("📋 RESUMO EXECUTIVO MUNICIPAL", expanded=True):
                st.markdown(f"""
                ### 🎯 RESUMO DO POTENCIAL DE CRÉDITOS DE CARBONO
                
                **📊 ESCOPO DA ANÁLISE:**
                - **Municípios analisados:** {len(df_resultados)}
                - **População total atendida:** {formatar_br(total_populacao/1e6)} milhões
                - **Período de projeção:** {anos_municipal} anos
                - **GWP utilizado:** {gwp_periodo}
                
                **🌍 IMPACTO AMBIENTAL AGREGADO:**
                - **Créditos totais anuais:** {formatar_br(total_creditos_anuais)} tCO₂eq
                - **Créditos em {anos_municipal} anos:** {formatar_br(total_creditos_anuais * anos_municipal)} tCO₂eq
                - **Equivalente em carros:** {formatar_br(total_creditos_anuais / 2.3)} carros fora das ruas por ano
                - **Metano evitado:** {formatar_br((total_creditos_anuais * 1000 / GWP_CH4_20))} t CH₄ por ano
                
                **💰 POTENCIAL FINANCEIRO:**
                - **Receita anual agregada:** R$ {formatar_br(total_valor_anual)}
                - **Receita em {anos_municipal} anos:** R$ {formatar_br(total_valor_20anos)}
                - **Média por município:** R$ {formatar_br(total_valor_anual / len(df_resultados))}/ano
                - **Média por habitante:** R$ {formatar_br((total_valor_anual / total_populacao) * 1000)} por mil hab/ano
                
                **🏆 TOP 3 MUNICÍPIOS POR POTENCIAL:**
                """)
                
                # Top 3 municípios
                top3 = df_resultados.nlargest(3, 'Valor Anual (R$)')
                for i, (_, row) in enumerate(top3.iterrows(), 1):
                    emoji = ["🥇", "🥈", "🥉"][i-1]
                    st.markdown(f"{emoji} **{row['Município']} ({row['Estado']}):** R$ {formatar_br(row['Valor Anual (R$)'])}/ano")
                
                st.markdown(f"""
                **💡 RECOMENDAÇÕES ESTRATÉGICAS:**
                
                1. **PRIORIZAÇÃO GEOGRÁFICA:**
                   - Focar em municípios com maior geração de resíduos
                   - Considerar clusters regionais para sinergias
                   - Priorizar estados com políticas ambientais favoráveis
                
                2. **MODELOS DE NEGÓCIO:**
                   - PPP (Parcerias Público-Privadas) para infraestrutura
                   - Consórcios intermunicipais para escala
                   - Contratos de longo prazo com geradores
                
                3. **FINANCIAMENTO:**
                   - Linhas de crédito BNDES para saneamento
                   - Fundos climáticos internacionais
                   - Green bonds (títulos verdes)
                
                4. **IMPLEMENTAÇÃO:**
                   - Fase 1: Municípios > 500k habitantes
                   - Fase 2: Consórcios regionais
                   - Fase 3: Expansão nacional
                
                **📈 PRÓXIMOS PASSOS:**
                1. Análise de viabilidade técnica-econômica detalhada
                2. Estudo de mercado de créditos de carbono
                3. Projeto de engenharia para sistemas de tratamento
                4. Modelagem financeira completa
                5. Busca de parceiros e financiamento
                """)
            
            # ==================== DOWNLOAD ====================
            st.markdown("---")
            st.header("💾 EXPORTAR RESULTADOS")
            
            # Criar arquivo Excel para download
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_resultados.to_excel(writer, sheet_name='Resultados_Detalhados', index=False)
                
                # Criar resumo executivo
                resumo = pd.DataFrame({
                    'Métrica': [
                        'Municípios Analisados',
                        'População Total (milhões)',
                        'Resíduos Orgânicos/Ano (t)',
                        'Créditos Anuais (tCO₂eq)',
                        'Receita Anual (R$)',
                        'Receita 20 Anos (R$)',
                        'Receita por Habitante (R$/ano/1000hab)'
                    ],
                    'Valor': [
                        len(df_resultados),
                        formatar_br(total_populacao / 1e6),
                        formatar_br(total_residuos_organicos),
                        formatar_br(total_creditos_anuais),
                        formatar_br(total_valor_anual),
                        formatar_br(total_valor_20anos),
                        formatar_br((total_valor_anual / total_populacao) * 1000)
                    ]
                })
                resumo.to_excel(writer, sheet_name='Resumo_Executivo', index=False)
            
            output.seek(0)
            
            # Botão de download
            st.download_button(
                label="📥 BAIXAR RELATÓRIO COMPLETO (Excel)",
                data=output,
                file_name=f"relatorio_potencial_municipal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    
    elif calcular_municipal and len(municipios_selecionados) == 0:
        st.warning("⚠️ Selecione pelo menos um município para análise.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# RODAPÉ
# =============================================================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #718096; font-size: 0.9rem; padding: 2rem 0;">
    <div style="display: flex; justify-content: center; gap: 2rem; margin-bottom: 1rem;">
        <div>
            <div style="font-size: 1.2rem; font-weight: 700; color: #2d3748;">🌿 CARBON SIMULATOR</div>
            <div>Simulador de Potencial de Créditos de Carbono</div>
        </div>
    </div>
    
    <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e2e8f0;">
        <div style="display: flex; justify-content: center; gap: 3rem; flex-wrap: wrap;">
            <div>
                <div style="font-weight: 600; color: #4a5568;">📊 Metodologia</div>
                <div>IPCC 2006 (Aterro) + Yang et al. 2017 (Compostagem)</div>
                <div>GWP-20: CH₄ = {formatar_br(GWP_CH4_20)} | N₂O = {formatar_br(GWP_N2O_20)}</div>
            </div>
            
            <div>
                <div style="font-weight: 600; color: #4a5568;">💰 Cotações</div>
                <div>Atualizadas em tempo real</div>
                <div>Carbono: € {formatar_br(cotacoes.get('preco_carbono', 85.50))}/tCO₂eq</div>
            </div>
            
            <div>
                <div style="font-weight: 600; color: #4a5568;">⚡ Performance</div>
                <div>Cálculos otimizados em numpy</div>
                <div>Interface responsiva e moderna</div>
            </div>
        </div>
    </div>
    
    <div style="margin-top: 1.5rem; color: #a0aec0; font-size: 0.8rem;">
        © 2024 Carbon Simulator | Desenvolvido para análise de créditos de carbono | 
        Última atualização: {datetime.now().strftime("%d/%m/%Y %H:%M")}
    </div>
</div>
""", unsafe_allow_html=True)
