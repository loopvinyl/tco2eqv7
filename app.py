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

# Configurar tema
custom_css = """
<style>
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    .main-header {
        background: linear-gradient(90deg, #1a2980 0%, #26d0ce 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border-left: 5px solid #26d0ce;
    }
    .tab-content {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #2c3e50 0%, #3498db 100%);
    }
    .stButton>button {
        background: linear-gradient(90deg, #1a2980 0%, #26d0ce 100%);
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(26, 41, 128, 0.3);
    }
</style>
"""

st.markdown(custom_css, unsafe_allow_html=True)

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
GWP_CH4_100 = 29.8  # Em 100 anos (para referência)
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
    if pd.isna(numero):
        return "N/A"
    numero = round(numero, 2)
    return f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_br_dec(numero, decimais=2):
    """Formata números com número específico de casas decimais"""
    if pd.isna(numero):
        return "N/A"
    numero = round(numero, decimais)
    return f"{numero:,.{decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def criar_metric_card(titulo, valor, delta=None, unidade="", cor="normal"):
    """Cria um card de métrica estilizado"""
    cores = {
        "normal": "#26d0ce",
        "positivo": "#2ecc71",
        "negativo": "#e74c3c",
        "neutro": "#3498db"
    }
    
    cor_selecionada = cores.get(cor, cores["normal"])
    
    html = f"""
    <div class="metric-card" style="border-left-color: {cor_selecionada};">
        <div style="font-size: 0.9rem; color: #7f8c8d; margin-bottom: 0.5rem;">{titulo}</div>
        <div style="font-size: 1.8rem; font-weight: bold; color: #2c3e50;">{valor}</div>
        <div style="font-size: 0.9rem; color: #7f8c8d;">{unidade}</div>
    </div>
    """
    return html

# =============================================================================
# FUNÇÕES DE COTAÇÃO EM TEMPO REAL
# =============================================================================

def obter_cotacao_carbono():
    """Obtém cotação do carbono com fallback"""
    try:
        # Tentar Investing.com
        url = "https://www.investing.com/commodities/carbon-emissions"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            elemento = soup.select_one('[data-test="instrument-price-last"]')
            if elemento:
                preco = float(elemento.text.strip().replace(',', ''))
                return preco, "€", "Investing.com", True
    except:
        pass
    
    # Fallback para valor de referência
    return 85.50, "€", "Valor de Referência", False

def obter_cotacao_euro():
    """Obtém cotação EUR/BRL"""
    try:
        url = "https://economia.awesomeapi.com.br/last/EUR-BRL"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return float(data['EURBRL']['bid']), True, "AwesomeAPI"
    except:
        pass
    
    return 5.50, False, "Valor de Referência"

# =============================================================================
# FUNÇÕES DE CÁLCULO CENTRAIS
# =============================================================================

def calcular_potencial_metano_aterro_lote(residuos_kg, umidade, temperatura, anos=20):
    """
    Calcula potencial de metano para UM ÚNICO LOTE ao longo do tempo
    Método IPCC 2006 - Kernel não normalizado
    """
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
    """
    Calcula emissões de aterro para ENTRADA CONTÍNUA diária
    """
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
    """
    Calcula emissões de metano para vermicompostagem (50 dias)
    """
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
# INTERFACE PRINCIPAL
# =============================================================================

# HEADER ELEGANTE
st.markdown("""
<div class="main-header">
    <h1 style="margin: 0; font-size: 2.5rem;">🌿 CARBON SIMULATOR</h1>
    <p style="margin: 0; opacity: 0.9;">Simulador de Potencial de Créditos de Carbono via Gestão de Resíduos Orgânicos</p>
</div>
""", unsafe_allow_html=True)

# BARRA LATERAL - CONFIGURAÇÕES GLOBAIS
with st.sidebar:
    st.markdown("### ⚙️ CONFIGURAÇÕES GLOBAIS")
    
    # Obter cotações
    if 'cotacoes' not in st.session_state:
        with st.spinner("Obtendo cotações..."):
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
    
    cotacoes = st.session_state.cotacoes
    
    # Exibir cotações
    st.markdown("#### 💰 COTAÇÕES ATUAIS")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Carbono (EUA)",
            f"€ {formatar_br(cotacoes['preco_carbono'])}",
            help=f"Fonte: {cotacoes['fonte_carbono']}"
        )
    
    with col2:
        st.metric(
            "EUR/BRL",
            f"R$ {formatar_br(cotacoes['taxa_cambio'])}",
            help=f"Fonte: {cotacoes['fonte_cambio']}"
        )
    
    # Parâmetros ambientais padrão
    st.markdown("#### 🌡️ PARÂMETROS AMBIENTAIS")
    
    temperatura_padrao = st.slider(
        "Temperatura média (°C)",
        15.0, 35.0, 25.0, 0.5,
        help="Temperatura média para cálculo do DOCf"
    )
    
    umidade_padrao = st.slider(
        "Umidade dos resíduos (%)",
        50.0, 95.0, 85.0, 1.0
    ) / 100.0
    
    # GWP selecionado
    st.markdown("#### 📊 FATOR GWP")
    gwp_selecionado = st.selectbox(
        "Período do GWP",
        ["20 anos (GWP-20)", "100 anos (GWP-100)"],
        index=0,
        help="GWP-20 é mais relevante para créditos de carbono de curto prazo"
    )
    
    # Botão para atualizar cotações
    if st.button("🔄 Atualizar Cotações", use_container_width=True):
        with st.spinner("Atualizando..."):
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
            st.rerun()
    
    st.caption(f"🕒 Última atualização: {st.session_state.cotacoes['timestamp'].strftime('%H:%M:%S')}")

# NAVEGAÇÃO POR ABAS
tab1, tab2, tab3 = st.tabs([
    "📦 LOTE ÚNICO (100 kg)", 
    "📈 ENTRADA CONTÍNUA", 
    "🏙️ POTENCIAL MUNICIPAL"
])

# =============================================================================
# ABA 1: LOTE ÚNICO
# =============================================================================
with tab1:
    st.markdown('<div class="tab-content">', unsafe_allow_html=True)
    
    st.header("📦 Análise de Lote Único")
    st.markdown("""
    **Simule o potencial de créditos de carbono para um único lote de resíduos orgânicos**
    
    *Entrada: Resíduos orgânicos puros (frutas, vegetais, restos de comida)*
    """)
    
    # Configurações específicas da Aba 1
    col1, col2, col3 = st.columns(3)
    
    with col1:
        quantidade_lote = st.number_input(
            "Peso do lote (kg)",
            min_value=10.0,
            max_value=10000.0,
            value=100.0,
            step=10.0,
            help="Peso do lote de resíduos orgânicos"
        )
    
    with col2:
        anos_analise = st.select_slider(
            "Período de análise",
            options=[1, 5, 10, 15, 20, 25, 30],
            value=20,
            help="Período para acompanhar as emissões do lote"
        )
    
    with col3:
        st.markdown("### 📊")
        st.markdown(f"**GWP utilizado:** {gwp_selecionado}")
        st.markdown(f"**Temperatura:** {temperatura_padrao}°C")
    
    # Botão de cálculo
    calcular_lote = st.button("🚀 CALCULAR POTENCIAL DO LOTE", type="primary", use_container_width=True)
    
    if calcular_lote:
        with st.spinner("Calculando..."):
            # Obter cotações
            cotacoes = st.session_state.cotacoes
            
            # Calcular emissões do aterro
            emissoes_aterro, potencial_total, docf = calcular_potencial_metano_aterro_lote(
                quantidade_lote, umidade_padrao, temperatura_padrao, anos_analise
            )
            
            # Calcular emissões da vermicompostagem
            emissoes_vermi, total_vermi = calcular_emissoes_vermicompostagem_lote(
                quantidade_lote, umidade_padrao
            )
            
            # Estender emissões da vermicompostagem para o período total
            emissoes_vermi_completa = np.zeros(len(emissoes_aterro))
            dias_vermi = min(50, len(emissoes_vermi))
            emissoes_vermi_completa[:dias_vermi] = emissoes_vermi[:dias_vermi]
            
            # Calcular créditos
            resultados = calcular_creditos_carbono(
                emissoes_aterro, emissoes_vermi_completa,
                cotacoes['preco_carbono'], cotacoes['taxa_cambio'], anos_analise
            )
            
            # ==================== RESULTADOS ====================
            st.markdown("---")
            st.header("📊 RESULTADOS - LOTE ÚNICO")
            
            # Métricas principais
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(criar_metric_card(
                    "Metano Evitado",
                    formatar_br(resultados['emissoes_evitadas_kg_ch4']),
                    unidade="kg CH₄",
                    cor="positivo"
                ), unsafe_allow_html=True)
            
            with col2:
                st.markdown(criar_metric_card(
                    "Créditos de Carbono",
                    formatar_br(resultados['co2eq_evitado_total']),
                    unidade="tCO₂eq",
                    cor="neutro"
                ), unsafe_allow_html=True)
            
            with col3:
                st.markdown(criar_metric_card(
                    "Valor Total",
                    f"R$ {formatar_br(resultados['valor_total_brl'])}",
                    unidade=f"@ €{formatar_br(cotacoes['preco_carbono'])}/tCO₂eq",
                    cor="normal"
                ), unsafe_allow_html=True)
            
            with col4:
                st.markdown(criar_metric_card(
                    "Valor por kg",
                    f"R$ {formatar_br(resultados['valor_total_brl'] / quantidade_lote)}",
                    unidade="por kg de resíduo",
                    cor="neutro"
                ), unsafe_allow_html=True)
            
            # ==================== GRÁFICOS ====================
            st.markdown("---")
            st.header("📈 VISUALIZAÇÕES")
            
            tab_graf1, tab_graf2 = st.tabs(["Emissões ao Longo do Tempo", "Comparação de Cenários"])
            
            with tab_graf1:
                # Criar dataframe para gráfico
                datas = pd.date_range(start=datetime.now(), periods=len(emissoes_aterro), freq='D')
                df_emissoes = pd.DataFrame({
                    'Data': datas,
                    'Aterro (CH₄)': emissoes_aterro,
                    'Vermicompostagem (CH₄)': emissoes_vermi_completa,
                    'Aterro (CO₂eq)': emissoes_aterro * GWP_CH4_20 / 1000,
                    'Vermicompostagem (CO₂eq)': emissoes_vermi_completa * GWP_CH4_20 / 1000
                })
                
                # Gráfico com Plotly
                fig = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=('Emissões de Metano (kg CH₄)', 'Equivalente CO₂ (tCO₂eq)'),
                    vertical_spacing=0.15
                )
                
                # Adicionar traços
                fig.add_trace(
                    go.Scatter(x=df_emissoes['Data'], y=df_emissoes['Aterro (CH₄)'],
                              name='Aterro', line=dict(color='red', width=2)),
                    row=1, col=1
                )
                
                fig.add_trace(
                    go.Scatter(x=df_emissoes['Data'], y=df_emissoes['Vermicompostagem (CH₄)'],
                              name='Vermicompostagem', line=dict(color='green', width=2)),
                    row=1, col=1
                )
                
                fig.add_trace(
                    go.Scatter(x=df_emissoes['Data'], y=df_emissoes['Aterro (CO₂eq)'],
                              name='Aterro (CO₂eq)', line=dict(color='red', width=2, dash='dash')),
                    row=2, col=1
                )
                
                fig.add_trace(
                    go.Scatter(x=df_emissoes['Data'], y=df_emissoes['Vermicompostagem (CO₂eq)'],
                              name='Vermicompostagem (CO₂eq)', line=dict(color='green', width=2, dash='dash')),
                    row=2, col=1
                )
                
                fig.update_layout(
                    height=600,
                    showlegend=True,
                    hovermode='x unified',
                    title=f"Emissões ao Longo de {anos_analise} Anos - Lote de {quantidade_lote} kg"
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with tab_graf2:
                # Gráfico de comparação acumulada
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    name='Aterro',
                    x=['Metano Total', 'CO₂eq Total', 'Valor Financeiro'],
                    y=[emissoes_aterro.sum(), resultados['co2eq_aterro_total'], 0],
                    marker_color='red'
                ))
                
                fig.add_trace(go.Bar(
                    name='Vermicompostagem',
                    x=['Metano Total', 'CO₂eq Total', 'Valor Financeiro'],
                    y=[emissoes_vermi_completa.sum(), resultados['co2eq_vermi_total'], resultados['valor_total_brl']],
                    marker_color='green'
                ))
                
                fig.add_trace(go.Bar(
                    name='Emissões Evitadas',
                    x=['Metano Total', 'CO₂eq Total', 'Valor Financeiro'],
                    y=[resultados['emissoes_evitadas_kg_ch4'], resultados['co2eq_evitado_total'], resultados['valor_total_brl']],
                    marker_color='blue',
                    opacity=0.5
                ))
                
                fig.update_layout(
                    barmode='group',
                    height=400,
                    title="Comparação Total dos Cenários",
                    yaxis_title="Valor"
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # ==================== RESUMO DETALHADO ====================
            with st.expander("📋 RESUMO DETALHADO", expanded=True):
                st.markdown(f"""
                ### 🎯 ANÁLISE COMPLETA - LOTE ÚNICO
                
                **📊 DADOS DE ENTRADA:**
                - Peso do lote: **{formatar_br(quantidade_lote)} kg** de resíduos orgânicos
                - Período de análise: **{anos_analise} anos**
                - Umidade: **{formatar_br(umidade_padrao*100)}%**
                - Temperatura: **{formatar_br(temperatura_padrao)}°C**
                - DOCf calculado: **{formatar_br(docf)}**
                
                **🌿 EMISSÕES DE METANO:**
                - **Aterro:** {formatar_br(emissoes_aterro.sum())} kg CH₄
                - **Vermicompostagem:** {formatar_br(emissoes_vermi_completa.sum())} kg CH₄
                - **Redução:** {formatar_br(resultados['emissoes_evitadas_kg_ch4'])} kg CH₄ ({formatar_br((1 - emissoes_vermi_completa.sum()/emissoes_aterro.sum())*100)}%)
                
                **🌍 CRÉDITOS DE CARBONO (GWP-20):**
                - **Aterro:** {formatar_br(resultados['co2eq_aterro_total'])} tCO₂eq
                - **Vermicompostagem:** {formatar_br(resultados['co2eq_vermi_total'])} tCO₂eq
                - **Créditos gerados:** {formatar_br(resultados['co2eq_evitado_total'])} tCO₂eq
                
                **💰 VALOR FINANCEIRO:**
                - **Preço do carbono:** € {formatar_br(cotacoes['preco_carbono'])}/tCO₂eq
                - **Câmbio:** € 1 = R$ {formatar_br(cotacoes['taxa_cambio'])}
                - **Valor total:** R$ {formatar_br(resultados['valor_total_brl'])}
                - **Valor por kg:** R$ {formatar_br(resultados['valor_total_brl'] / quantidade_lote)}/kg
                - **Valor por tonelada:** R$ {formatar_br(resultados['valor_total_brl'] / (quantidade_lote/1000))}/t
                
                **⏰ DIFERENÇA TEMPORAL:**
                - **Aterro:** Emissões por **{anos_analise} anos** (decaimento exponencial)
                - **Vermicompostagem:** Emissões em **apenas 50 dias** (processo concentrado)
                
                **💡 IMPLICAÇÕES:**
                - O lote evitaria **{formatar_br(resultados['co2eq_evitado_total'])} tCO₂eq** em 20 anos
                - Equivale às emissões de um carro médio por **{formatar_br(resultados['co2eq_evitado_total'] / 2.3)} anos**
                - Potencial de **R$ {formatar_br(resultados['valor_total_brl'])}** em créditos de carbono
                """)
    
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# ABA 2: ENTRADA CONTÍNUA
# =============================================================================
with tab2:
    st.markdown('<div class="tab-content">', unsafe_allow_html=True)
    
    st.header("📈 Análise de Entrada Contínua")
    st.markdown("""
    **Simule o potencial de créditos de carbono para um fluxo contínuo diário de resíduos orgânicos**
    
    *Entrada: Resíduos orgânicos puros processados diariamente*
    """)
    
    # Configurações específicas da Aba 2
    col1, col2, col3 = st.columns(3)
    
    with col1:
        residuos_diarios = st.number_input(
            "Resíduos orgânicos diários",
            min_value=10.0,
            max_value=10000.0,
            value=100.0,
            step=10.0,
            help="Quantidade diária de resíduos orgânicos processados",
            key="diarios_cont"
        )
    
    with col2:
        anos_operacao = st.select_slider(
            "Período de operação",
            options=[1, 5, 10, 15, 20, 25, 30],
            value=20,
            help="Período de operação contínua",
            key="anos_cont"
        )
    
    with col3:
        st.markdown("### 📊")
        st.markdown(f"**Total processado:** {formatar_br(residuos_diarios * 365 * anos_operacao / 1000)} toneladas")
        st.markdown(f"**GWP:** {gwp_selecionado}")
    
    # Botão de cálculo
    calcular_continuo = st.button("🚀 CALCULAR POTENCIAL CONTÍNUO", type="primary", use_container_width=True, key="btn_cont")
    
    if calcular_continuo:
        with st.spinner("Calculando..."):
            # Obter cotações
            cotacoes = st.session_state.cotacoes
            
            # Calcular emissões do aterro (contínuo)
            emissoes_aterro_cont, potencial_diario = calcular_emissoes_aterro_continuo(
                residuos_diarios, umidade_padrao, temperatura_padrao, anos_operacao
            )
            
            # Calcular emissões da vermicompostagem
            dias_totais = anos_operacao * 365
            emissoes_vermi_cont = np.zeros(dias_totais)
            
            # Para cada dia, adicionar emissões da vermicompostagem (50 dias)
            for dia in range(dias_totais):
                emissoes_lote, _ = calcular_emissoes_vermicompostagem_lote(residuos_diarios, umidade_padrao)
                dias_lote = min(50, dias_totais - dia)
                emissoes_vermi_cont[dia:dia+dias_lote] += emissoes_lote[:dias_lote]
            
            # Calcular créditos
            resultados_cont = calcular_creditos_carbono(
                emissoes_aterro_cont, emissoes_vermi_cont,
                cotacoes['preco_carbono'], cotacoes['taxa_cambio'], anos_operacao
            )
            
            # ==================== RESULTADOS ====================
            st.markdown("---")
            st.header("📊 RESULTADOS - ENTRADA CONTÍNUA")
            
            # Métricas principais
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(criar_metric_card(
                    "Resíduos Processados",
                    formatar_br(residuos_diarios * 365 * anos_operacao / 1000),
                    unidade="toneladas totais",
                    cor="neutro"
                ), unsafe_allow_html=True)
            
            with col2:
                st.markdown(criar_metric_card(
                    "Créditos Anuais",
                    formatar_br(resultados_cont['co2eq_evitado_anual']),
                    unidade="tCO₂eq/ano",
                    cor="positivo"
                ), unsafe_allow_html=True)
            
            with col3:
                st.markdown(criar_metric_card(
                    "Valor Anual",
                    f"R$ {formatar_br(resultados_cont['valor_anual_brl'])}",
                    unidade="por ano",
                    cor="normal"
                ), unsafe_allow_html=True)
            
            with col4:
                st.markdown(criar_metric_card(
                    "Valor Total 20 anos",
                    f"R$ {formatar_br(resultados_cont['valor_total_brl'])}",
                    unidade="em 20 anos",
                    cor="positivo"
                ), unsafe_allow_html=True)
            
            # ==================== GRÁFICOS ====================
            st.markdown("---")
            st.header("📈 VISUALIZAÇÕES")
            
            # Gráfico de evolução anual
            anos = list(range(1, anos_operacao + 1))
            valor_acumulado = [resultados_cont['valor_anual_brl'] * ano for ano in anos]
            creditos_acumulados = [resultados_cont['co2eq_evitado_anual'] * ano for ano in anos]
            
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Acumulado de Créditos (tCO₂eq)', 'Valor Financeiro Acumulado (R$)'),
                vertical_spacing=0.15
            )
            
            fig.add_trace(
                go.Scatter(x=anos, y=creditos_acumulados,
                          name='Créditos Acumulados', 
                          line=dict(color='green', width=3),
                          fill='tozeroy', fillcolor='rgba(0,255,0,0.1)'),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(x=anos, y=valor_acumulado,
                          name='Valor Acumulado',
                          line=dict(color='blue', width=3),
                          fill='tozeroy', fillcolor='rgba(0,0,255,0.1)'),
                row=2, col=1
            )
            
            fig.update_layout(
                height=600,
                showlegend=True,
                hovermode='x unified',
                title=f"Projeção para {anos_operacao} Anos - {formatar_br(residuos_diarios)} kg/dia"
            )
            
            fig.update_xaxes(title_text="Anos", row=1, col=1)
            fig.update_xaxes(title_text="Anos", row=2, col=1)
            fig.update_yaxes(title_text="tCO₂eq", row=1, col=1)
            fig.update_yaxes(title_text="R$", row=2, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # ==================== RESUMO DETALHADO ====================
            with st.expander("📋 RESUMO DETALHADO", expanded=True):
                st.markdown(f"""
                ### 🎯 ANÁLISE COMPLETA - ENTRADA CONTÍNUA
                
                **📊 DADOS DE ENTRADA:**
                - Resíduos processados: **{formatar_br(residuos_diarios)} kg/dia** de orgânicos
                - Período de operação: **{anos_operacao} anos**
                - Total processado: **{formatar_br(residuos_diarios * 365 * anos_operacao / 1000)} toneladas**
                
                **🌿 REDUÇÃO ANUAL DE EMISSÕES:**
                - Metano evitado: **{formatar_br(resultados_cont['emissoes_evitadas_kg_ch4'] / anos_operacao)} kg CH₄/ano**
                - Créditos gerados: **{formatar_br(resultados_cont['co2eq_evitado_anual'])} tCO₂eq/ano**
                
                **💰 PROJEÇÃO FINANCEIRA:**
                - **Receita anual:** R$ {formatar_br(resultados_cont['valor_anual_brl'])}/ano
                - **Receita em 20 anos:** R$ {formatar_br(resultados_cont['valor_total_brl'])}
                - **Receita por tonelada:** R$ {formatar_br(resultados_cont['valor_total_brl'] / (residuos_diarios * 365 * anos_operacao / 1000))}/t
                
                **📈 CENÁRIO DE NEGÓCIO:**
                - **Investimento necessário:** Sistema de compostagem/vermicompostagem
                - **Retorno:** {formatar_br(resultados_cont['valor_anual_brl'])}/ano
                - **Payback:** Depende do custo de implantação
                - **Escalabilidade:** Possibilidade de aumentar capacidade
                
                **🌍 IMPACTO AMBIENTAL:**
                - Evita **{formatar_br(resultados_cont['co2eq_evitado_anual'])} tCO₂eq/ano**
                - Equivale a **{formatar_br(resultados_cont['co2eq_evitado_anual'] / 2.3)} carros** fora das ruas por ano
                - Gera **{formatar_br(resultados_cont['co2eq_evitado_anual'] / 0.2)}** créditos de carbono por ano
                """)
    
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# ABA 3: POTENCIAL MUNICIPAL
# =============================================================================
with tab3:
    st.markdown('<div class="tab-content">', unsafe_allow_html=True)
    
    st.header("🏙️ Análise de Potencial Municipal")
    st.markdown("""
    **Calcule o potencial de créditos de carbono para municípios brasileiros**
    
    *Entrada: Dados municipais de resíduos totais, convertidos usando fração orgânica*
    """)
    
    # Carregar dados do Excel (exemplo simplificado)
    st.markdown("### 📁 CARREGAR DADOS MUNICIPAIS")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Upload de arquivo ou usar dados de exemplo
        uploaded_file = st.file_uploader(
            "Carregar planilha Excel com dados municipais",
            type=['xlsx', 'xls'],
            help="Arquivo deve conter coluna com fração orgânica (coluna R)"
        )
    
    with col2:
        st.markdown("#### 📊 OU")
        usar_dados_exemplo = st.checkbox("Usar dados de exemplo", value=True)
    
    # Dados de exemplo (simulando Excel)
    dados_municipais_exemplo = {
        "Cidade": ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Salvador", "Fortaleza"],
        "Estado": ["SP", "RJ", "MG", "BA", "CE"],
        "População": [12300000, 6775000, 2531000, 2903000, 2687000],
        "Resíduos Totais (t/dia)": [12000, 6500, 2500, 2900, 2700],
        "Fração Orgânica": [0.52, 0.48, 0.50, 0.55, 0.53],
        "Taxa de Coleta": [0.95, 0.92, 0.93, 0.85, 0.88]
    }
    
    df_municipios = pd.DataFrame(dados_municipais_exemplo)
    
    if uploaded_file is not None:
        try:
            df_municipios = pd.read_excel(uploaded_file)
            st.success(f"✅ Arquivo carregado com {len(df_municipios)} municípios")
        except Exception as e:
            st.error(f"Erro ao carregar arquivo: {e}")
            st.info("Usando dados de exemplo")
            df_municipios = pd.DataFrame(dados_municipais_exemplo)
    elif usar_dados_exemplo:
        st.info("Usando dados de exemplo (5 principais capitais)")
    
    # Exibir dados
    with st.expander("📋 VISUALIZAR DADOS CARREGADOS"):
        st.dataframe(df_municipios, use_container_width=True)
    
    # Configurações de cálculo
    st.markdown("### ⚙️ CONFIGURAÇÃO DO CÁLCULO")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        anos_municipal = st.select_slider(
            "Período de projeção",
            options=[1, 5, 10, 15, 20],
            value=20,
            help="Período para cálculo do potencial municipal",
            key="anos_mun"
        )
    
    with col2:
        selecionar_todos = st.checkbox("Selecionar todos os municípios", value=True)
    
    with col3:
        if not selecionar_todos:
            municipios_selecionados = st.multiselect(
                "Selecionar municípios",
                options=df_municipios['Cidade'].tolist(),
                default=df_municipios['Cidade'].tolist()[:3]
            )
        else:
            municipios_selecionados = df_municipios['Cidade'].tolist()
    
    # Botão de cálculo
    calcular_municipal = st.button("🚀 CALCULAR POTENCIAL MUNICIPAL", type="primary", use_container_width=True, key="btn_mun")
    
    if calcular_municipal and len(municipios_selecionados) > 0:
        with st.spinner("Calculando potencial para municípios selecionados..."):
            # Filtrar municípios selecionados
            df_selecionados = df_municipios[df_municipios['Cidade'].isin(municipios_selecionados)].copy()
            
            # Obter cotações
            cotacoes = st.session_state.cotacoes
            
            resultados_municipais = []
            
            # Calcular para cada município
            for _, municipio in df_selecionados.iterrows():
                # Converter resíduos totais para orgânicos
                residuos_organicos_dia_ton = municipio['Resíduos Totais (t/dia)'] * municipio['Fração Orgânica'] * municipio['Taxa de Coleta']
                residuos_organicos_dia_kg = residuos_organicos_dia_ton * 1000
                
                # Calcular como entrada contínua (similar à Aba 2)
                emissoes_aterro, _ = calcular_emissoes_aterro_continuo(
                    residuos_organicos_dia_kg, umidade_padrao, temperatura_padrao, anos_municipal
                )
                
                # Calcular vermicompostagem
                dias_totais = anos_municipal * 365
                emissoes_vermi = np.zeros(dias_totais)
                
                for dia in range(dias_totais):
                    emissoes_lote, _ = calcular_emissoes_vermicompostagem_lote(residuos_organicos_dia_kg, umidade_padrao)
                    dias_lote = min(50, dias_totais - dia)
                    emissoes_vermi[dia:dia+dias_lote] += emissoes_lote[:dias_lote]
                
                # Calcular créditos
                resultados = calcular_creditos_carbono(
                    emissoes_aterro, emissoes_vermi,
                    cotacoes['preco_carbono'], cotacoes['taxa_cambio'], anos_municipal
                )
                
                resultados_municipais.append({
                    'Cidade': municipio['Cidade'],
                    'Estado': municipio['Estado'],
                    'População': municipio['População'],
                    'Resíduos Totais (t/dia)': municipio['Resíduos Totais (t/dia)'],
                    'Resíduos Orgânicos (t/dia)': residuos_organicos_dia_ton,
                    'Fração Orgânica': municipio['Fração Orgânica'],
                    'Créditos Anuais (tCO₂eq)': resultados['co2eq_evitado_anual'],
                    'Valor Anual (R$)': resultados['valor_anual_brl'],
                    'Valor 20 Anos (R$)': resultados['valor_total_brl'],
                    'Valor por Habitante (R$)': resultados['valor_anual_brl'] / municipio['População'] * 1000,
                    'Créditos por Habitante (kg CO₂eq)': (resultados['co2eq_evitado_anual'] * 1000) / municipio['População']
                })
            
            df_resultados = pd.DataFrame(resultados_municipais)
            
            # ==================== RESULTADOS ====================
            st.markdown("---")
            st.header("📊 RESULTADOS - POTENCIAL MUNICIPAL")
            
            # Métricas agregadas
            total_populacao = df_resultados['População'].sum()
            total_residuos_organicos = df_resultados['Resíduos Orgânicos (t/dia)'].sum() * 365
            total_creditos_anuais = df_resultados['Créditos Anuais (tCO₂eq)'].sum()
            total_valor_anual = df_resultados['Valor Anual (R$)'].sum()
            total_valor_20anos = df_resultados['Valor 20 Anos (R$)'].sum()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(criar_metric_card(
                    "População Atendida",
                    formatar_br(total_populacao / 1e6),
                    unidade="milhões de habitantes",
                    cor="neutro"
                ), unsafe_allow_html=True)
            
            with col2:
                st.markdown(criar_metric_card(
                    "Resíduos Orgânicos/Ano",
                    formatar_br(total_residuos_organicos),
                    unidade="toneladas/ano",
                    cor="neutro"
                ), unsafe_allow_html=True)
            
            with col3:
                st.markdown(criar_metric_card(
                    "Créditos Anuais",
                    formatar_br(total_creditos_anuais),
                    unidade="tCO₂eq/ano",
                    cor="positivo"
                ), unsafe_allow_html=True)
            
            with col4:
                st.markdown(criar_metric_card(
                    "Receita Anual",
                    f"R$ {formatar_br(total_valor_anual)}",
                    unidade="por ano",
                    cor="normal"
                ), unsafe_allow_html=True)
            
            # ==================== TABELA DETALHADA ====================
            st.markdown("---")
            st.header("🏙️ DETALHAMENTO POR MUNICÍPIO")
            
            # Formatar tabela para exibição
            df_display = df_resultados.copy()
            df_display['População'] = df_display['População'].apply(lambda x: formatar_br(x/1000) + ' mil')
            df_display['Resíduos Orgânicos (t/dia)'] = df_display['Resíduos Orgânicos (t/dia)'].apply(formatar_br)
            df_display['Créditos Anuais (tCO₂eq)'] = df_display['Créditos Anuais (tCO₂eq)'].apply(formatar_br)
            df_display['Valor Anual (R$)'] = df_display['Valor Anual (R$)'].apply(lambda x: f"R$ {formatar_br(x)}")
            df_display['Valor 20 Anos (R$)'] = df_display['Valor 20 Anos (R$)'].apply(lambda x: f"R$ {formatar_br(x)}")
            df_display['Valor por Habitante (R$)'] = df_display['Valor por Habitante (R$)'].apply(lambda x: f"R$ {formatar_br(x)}")
            df_display['Créditos por Habitante (kg CO₂eq)'] = df_display['Créditos por Habitante (kg CO₂eq)'].apply(formatar_br)
            
            st.dataframe(
                df_display[[
                    'Cidade', 'Estado', 'População', 'Resíduos Orgânicos (t/dia)',
                    'Créditos Anuais (tCO₂eq)', 'Valor Anual (R$)', 'Valor por Habitante (R$)'
                ]],
                use_container_width=True,
                height=400
            )
            
            # ==================== GRÁFICOS ====================
            st.markdown("---")
            st.header("📈 VISUALIZAÇÕES COMPARATIVAS")
            
            tab_map, tab_bar, tab_scatter = st.tabs(["Mapa de Calor", "Barras Comparativas", "Dispersão"])
            
            with tab_map:
                # Mapa de calor por estado
                fig = px.treemap(
                    df_resultados,
                    path=['Estado', 'Cidade'],
                    values='Valor Anual (R$)',
                    color='Créditos Anuais (tCO₂eq)',
                    color_continuous_scale='Viridis',
                    title='Potencial de Créditos por Município'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with tab_bar:
                # Gráfico de barras
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    x=df_resultados['Cidade'],
                    y=df_resultados['Créditos Anuais (tCO₂eq)'],
                    name='Créditos Anuais',
                    marker_color='green',
                    text=df_resultados['Créditos Anuais (tCO₂eq)'].apply(formatar_br),
                    textposition='outside'
                ))
                
                fig.add_trace(go.Bar(
                    x=df_resultados['Cidade'],
                    y=df_resultados['Valor Anual (R$)'] / 1000,
                    name='Valor Anual (mil R$)',
                    marker_color='blue',
                    text=(df_resultados['Valor Anual (R$)'] / 1000).apply(lambda x: f"R$ {formatar_br(x)}k"),
                    textposition='outside',
                    yaxis='y2'
                ))
                
                fig.update_layout(
                    barmode='group',
                    title='Comparação entre Municípios',
                    yaxis=dict(title='Créditos Anuais (tCO₂eq)'),
                    yaxis2=dict(
                        title='Valor Anual (mil R$)',
                        overlaying='y',
                        side='right'
                    ),
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with tab_scatter:
                # Gráfico de dispersão
                fig = px.scatter(
                    df_resultados,
                    x='População',
                    y='Valor Anual (R$)',
                    size='Créditos Anuais (tCO₂eq)',
                    color='Estado',
                    hover_name='Cidade',
                    log_x=True,
                    size_max=60,
                    title='Relação entre População e Potencial de Créditos'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # ==================== DOWNLOAD ====================
            st.markdown("---")
            st.header("💾 EXPORTAR RESULTADOS")
            
            # Converter para Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_resultados.to_excel(writer, sheet_name='Resultados_Municipais', index=False)
                df_selecionados.to_excel(writer, sheet_name='Dados_Originais', index=False)
            
            output.seek(0)
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.download_button(
                    label="📥 Baixar Resultados (Excel)",
                    data=output,
                    file_name=f"potencial_municipal_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            with col2:
                st.info("""
                **📋 O arquivo contém:**
                - Resultados detalhados por município
                - Dados originais utilizados
                - Métricas de créditos e valor financeiro
                """)
            
            # ==================== RESUMO EXECUTIVO ====================
            with st.expander("📋 RESUMO EXECUTIVO MUNICIPAL", expanded=True):
                st.markdown(f"""
                ### 🎯 RESUMO DO POTENCIAL MUNICIPAL
                
                **📊 DADOS CONSIDERADOS:**
                - **Municípios analisados:** {len(df_resultados)}
                - **População total:** {formatar_br(total_populacao/1e6)} milhões
                - **Período de análise:** {anos_municipal} anos
                - **GWP utilizado:** {gwp_selecionado}
                
                **🌍 POTENCIAL AMBIENTAL:**
                - **Créditos totais/ano:** {formatar_br(total_creditos_anuais)} tCO₂eq
                - **Créditos em 20 anos:** {formatar_br(total_creditos_anuais * 20)} tCO₂eq
                - **Equivalente em carros:** {formatar_br(total_creditos_anuais / 2.3)} carros fora das ruas por ano
                
                **💰 POTENCIAL FINANCEIRO:**
                - **Receita anual total:** R$ {formatar_br(total_valor_anual)}
                - **Receita em 20 anos:** R$ {formatar_br(total_valor_20anos)}
                - **Média por município:** R$ {formatar_br(total_valor_anual / len(df_resultados))}/ano
                - **Média por habitante:** R$ {formatar_br((total_valor_anual / total_populacao) * 1000)} por mil habitantes
                
                **🏆 MUNICÍPIOS COM MAIOR POTENCIAL:**
                """)
                
                # Top 5 municípios
                top5 = df_resultados.nlargest(5, 'Valor Anual (R$)')
                for idx, row in top5.iterrows():
                    st.markdown(f"- **{row['Cidade']} ({row['Estado']}):** R$ {formatar_br(row['Valor Anual (R$)'])}/ano")
                
                st.markdown(f"""
                **💡 RECOMENDAÇÕES:**
                1. **Priorizar municípios** com maior geração de resíduos orgânicos
                2. **Implementar sistemas** municipais de compostagem/vermicompostagem
                3. **Capturar créditos** através do Mecanismo de Desenvolvimento Limpo
                4. **Parcerias Público-Privadas** para investimento em infraestrutura
                5. **Educação ambiental** para aumentar fração orgânica disponível
                
                **📈 PRÓXIMOS PASSOS:**
                - Análise de viabilidade técnica-econômica
                - Estudo de mercado de créditos de carbono
                - Projeto de engenharia para sistemas de tratamento
                - Busca de financiamento e parcerias
                """)
    
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# RODAPÉ
# =============================================================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #7f8c8d; font-size: 0.9rem;">
    <p><strong>🌿 CARBON SIMULATOR</strong> | Simulador de Potencial de Créditos de Carbono</p>
    <p>📊 Metodologia: IPCC 2006 (Aterro) + Yang et al. 2017 (Compostagem) | GWP-20: {formatar_br(GWP_CH4_20)}</p>
    <p>⚡ Cotações atualizadas em tempo real | 💰 Valores em Euros convertidos para Reais</p>
    <p>📧 Contato: suporte@carbonsimulator.com.br | 🔄 Última atualização: {}</p>
</div>
""".format(datetime.now().strftime("%d/%m/%Y %H:%M")), unsafe_allow_html=True)
