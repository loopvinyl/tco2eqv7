import requests
from bs4 import BeautifulSoup
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
from SALib.sample.sobol import sample
from SALib.analyze.sobol import analyze

np.random.seed(50)  # Garante reprodutibilidade

# Configurações iniciais
st.set_page_config(page_title="Simulador de Emissões CO₂eq", layout="wide")
warnings.filterwarnings("ignore", category=FutureWarning)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
np.seterr(divide='ignore', invalid='ignore')
plt.rcParams['figure.dpi'] = 150
plt.rcParams['font.size'] = 10
sns.set_style("whitegrid")

# =============================================================================
# FUNÇÕES DE COTAÇÃO AUTOMÁTICA DO CARBONO E CÂMBIO
# =============================================================================

def obter_cotacao_carbono_investing():
    """
    Obtém a cotação em tempo real do carbono via web scraping do Investing.com
    """
    try:
        url = "https://www.investing.com/commodities/carbon-emissions"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': 'https://www.investing.com/'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Várias estratégias para encontrar o preço
        selectores = [
            '[data-test="instrument-price-last"]',
            '.text-2xl',
            '.last-price-value',
            '.instrument-price-last',
            '.pid-1062510-last',
            '.float_lang_base_1',
            '.top.bold.inlineblock',
            '#last_last'
        ]
        
        preco = None
        fonte = "Investing.com"
        
        for seletor in selectores:
            try:
                elemento = soup.select_one(seletor)
                if elemento:
                    texto_preco = elemento.text.strip().replace(',', '')
                    # Remover caracteres não numéricos exceto ponto
                    texto_preco = ''.join(c for c in texto_preco if c.isdigit() or c == '.')
                    if texto_preco:
                        preco = float(texto_preco)
                        break
            except (ValueError, AttributeError):
                continue
        
        if preco is not None:
            return preco, "€", "Carbon Emissions Future", True, fonte
        
        # Tentativa alternativa: procurar por padrões numéricos no HTML
        import re
        padroes_preco = [
            r'"last":"([\d,]+)"',
            r'data-last="([\d,]+)"',
            r'last_price["\']?:\s*["\']?([\d,]+)',
            r'value["\']?:\s*["\']?([\d,]+)'
        ]
        
        html_texto = str(soup)
        for padrao in padroes_preco:
            matches = re.findall(padrao, html_texto)
            for match in matches:
                try:
                    preco_texto = match.replace(',', '')
                    preco = float(preco_texto)
                    if 50 < preco < 200:  # Faixa razoável para carbono
                        return preco, "€", "Carbon Emissions Future", True, fonte
                except ValueError:
                    continue
                    
        return None, None, None, False, fonte
        
    except Exception as e:
        return None, None, None, False, f"Investing.com - Erro: {str(e)}"

def obter_cotacao_carbono():
    """
    Obtém a cotação em tempo real do carbono - usa apenas Investing.com
    """
    # Tentar via Investing.com
    preco, moeda, contrato_info, sucesso, fonte = obter_cotacao_carbono_investing()
    
    if sucesso:
        return preco, moeda, f"{contrato_info}", True, fonte
    
    # Fallback para valor padrão
    return 85.50, "€", "Carbon Emissions (Referência)", False, "Referência"

def obter_cotacao_euro_real():
    """
    Obtém a cotação em tempo real do Euro em relação ao Real Brasileiro
    """
    try:
        # API do BCB
        url = "https://economia.awesomeapi.com.br/last/EUR-BRL"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            cotacao = float(data['EURBRL']['bid'])
            return cotacao, "R$", True, "AwesomeAPI"
    except:
        pass
    
    try:
        # Fallback para API alternativa
        url = "https://api.exchangerate-api.com/v4/latest/EUR"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            cotacao = data['rates']['BRL']
            return cotacao, "R$", True, "ExchangeRate-API"
    except:
        pass
    
    # Fallback para valor de referência
    return 5.50, "R$", False, "Referência"

def calcular_valor_creditos(emissoes_evitadas_tco2eq, preco_carbono_por_tonelada, moeda, taxa_cambio=1):
    """
    Calcula o valor financeiro das emissões evitadas baseado no preço do carbono
    """
    valor_total = emissoes_evitadas_tco2eq * preco_carbono_por_tonelada * taxa_cambio
    return valor_total

def exibir_cotacao_carbono():
    """
    Exibe a cotação do carbono com informações - ATUALIZADA AUTOMATICAMENTE
    """
    st.sidebar.header("💰 Mercado de Carbono e Câmbio")
    
    # Atualização automática na primeira execução
    if not st.session_state.get('cotacao_carregada', False):
        st.session_state.mostrar_atualizacao = True
        st.session_state.cotacao_carregada = True
    
    # Botão para atualizar cotações
    col1, col2 = st.sidebar.columns([3, 1])
    with col1:
        if st.button("🔄 Atualizar Cotações", key="atualizar_cotacoes"):
            st.session_state.cotacao_atualizada = True
            st.session_state.mostrar_atualizacao = True
    
    # Mostrar mensagem de atualização se necessário
    if st.session_state.get('mostrar_atualizacao', False):
        st.sidebar.info("🔄 Atualizando cotações...")
        
        # Obter cotação do carbono
        preco_carbono, moeda, contrato_info, sucesso_carbono, fonte_carbono = obter_cotacao_carbono()
        
        # Obter cotação do Euro
        preco_euro, moeda_real, sucesso_euro, fonte_euro = obter_cotacao_euro_real()
        
        # Atualizar session state
        st.session_state.preco_carbono = preco_carbono
        st.session_state.moeda_carbono = moeda
        st.session_state.taxa_cambio = preco_euro
        st.session_state.moeda_real = moeda_real
        st.session_state.fonte_cotacao = fonte_carbono
        
        # Resetar flags
        st.session_state.mostrar_atualizacao = False
        st.session_state.cotacao_atualizada = False
        
        st.rerun()

    # Exibe cotação atual do carbono
    st.sidebar.metric(
        label=f"Preço do Carbono (tCO₂eq)",
        value=f"{st.session_state.moeda_carbono} {st.session_state.preco_carbono:.2f}",
        help=f"Fonte: {st.session_state.fonte_cotacao}"
    )
    
    # Exibe cotação atual do Euro
    st.sidebar.metric(
        label="Euro (EUR/BRL)",
        value=f"{st.session_state.moeda_real} {st.session_state.taxa_cambio:.2f}",
        help="Cotação do Euro em Reais Brasileiros"
    )
    
    # Calcular preço do carbono em Reais
    preco_carbono_reais = st.session_state.preco_carbono * st.session_state.taxa_cambio
    
    st.sidebar.metric(
        label=f"Carbono em Reais (tCO₂eq)",
        value=f"R$ {preco_carbono_reais:.2f}",
        help="Preço do carbono convertido para Reais Brasileiros"
    )
    
    # Informações adicionais
    with st.sidebar.expander("ℹ️ Informações do Mercado de Carbono"):
        st.markdown(f"""
        **📊 Cotações Atuais:**
        - **Fonte do Carbono:** {st.session_state.fonte_cotacao}
        - **Preço Atual:** {st.session_state.moeda_carbono} {st.session_state.preco_carbono:.2f}/tCO₂eq
        - **Câmbio EUR/BRL:** 1 Euro = R$ {st.session_state.taxa_cambio:.2f}
        - **Carbono em Reais:** R$ {preco_carbono_reais:.2f}/tCO₂eq
        
        **🌍 Mercado de Referência:**
        - European Union Allowances (EUA)
        - European Emissions Trading System (EU ETS)
        - Contratos futuros de carbono
        - Preços em tempo real
        
        **🔄 Atualização:**
        - As cotações são carregadas automaticamente ao abrir o aplicativo
        - Clique em **"Atualizar Cotações"** para obter valores mais recentes
        - Em caso de falha na conexão, são utilizados valores de referência atualizados
        
        **💡 Importante:**
        - Os preços são baseados no mercado regulado da UE
        - Valores em tempo real sujeitos a variações de mercado
        - Conversão para Real utilizando câmbio comercial
        """)

# =============================================================================
# INICIALIZAÇÃO DA SESSION STATE
# =============================================================================

# Inicializar todas as variáveis de session state necessárias
def inicializar_session_state():
    if 'preco_carbono' not in st.session_state:
        # Buscar cotação automaticamente na inicialização
        preco_carbono, moeda, contrato_info, sucesso, fonte = obter_cotacao_carbono()
        st.session_state.preco_carbono = preco_carbono
        st.session_state.moeda_carbono = moeda
        st.session_state.fonte_cotacao = fonte
        
    if 'taxa_cambio' not in st.session_state:
        # Buscar cotação do Euro automaticamente
        preco_euro, moeda_real, sucesso_euro, fonte_euro = obter_cotacao_euro_real()
        st.session_state.taxa_cambio = preco_euro
        st.session_state.moeda_real = moeda_real
        
    if 'moeda_real' not in st.session_state:
        st.session_state.moeda_real = "R$"
    if 'cotacao_atualizada' not in st.session_state:
        st.session_state.cotacao_atualizada = False
    if 'run_simulation' not in st.session_state:
        st.session_state.run_simulation = False
    if 'mostrar_atualizacao' not in st.session_state:
        st.session_state.mostrar_atualizacao = False
    if 'cotacao_carregada' not in st.session_state:
        st.session_state.cotacao_carregada = False

# Chamar a inicialização
inicializar_session_state()

# =============================================================================
# FUNÇÕES ORIGINAIS DO SEU SCRIPT
# =============================================================================

# Função para formatar números no padrão brasileiro
def formatar_br(numero):
    """
    Formata números no padrão brasileiro: 1.234,56
    """
    if pd.isna(numero):
        return "N/A"
    
    # Arredonda para 2 casas decimais
    numero = round(numero, 2)
    
    # Formata como string e substitui o ponto pela vírgula
    return f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Função de formatação para os gráficos
def br_format(x, pos):
    """
    Função de formatação para eixos de gráficos (padrão brasileiro)
    """
    if x == 0:
        return "0"
    
    # Para valores muito pequenos, usa notação científica
    if abs(x) < 0.01:
        return f"{x:.1e}".replace(".", ",")
    
    # Para valores grandes, formata com separador de milhar
    if abs(x) >= 1000:
        return f"{x:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    # Para valores menores, mostra duas casas decimais
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def br_format_5_dec(x, pos):
    """
    Função de formatação para eixos de gráficos (padrão brasileiro com 5 decimais)
    """
    return f"{x:,.5f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Título do aplicativo
st.title("Simulador de Emissões de tCO₂eq")
st.markdown("""
Esta ferramenta projeta os Créditos de Carbono ao calcular as emissões de gases de efeito estufa para dois contextos de gestão de resíduos
""")

# =============================================================================
# SIDEBAR COM PARÂMETROS
# =============================================================================

# Seção de cotação do carbono - AGORA ATUALIZADA AUTOMATICAMENTE
exibir_cotacao_carbono()

# Seção original de parâmetros
with st.sidebar:
    st.header("⚙️ Parâmetros de Entrada")
    
    # Entrada principal de resíduos
    residuos_kg_dia = st.slider("Quantidade de resíduos (kg/dia)", 
                               min_value=10, max_value=1000, value=100, step=10,
                               help="Quantidade diária de resíduos orgânicos gerados")
    
    st.subheader("📊 Parâmetros Operacionais")
    
    # Umidade com formatação brasileira (0,85 em vez de 0.85)
    umidade_valor = st.slider("Umidade do resíduo (%)", 50, 95, 85, 1,
                             help="Percentual de umidade dos resíduos orgânicos")
    umidade = umidade_valor / 100.0
    st.write(f"**Umidade selecionada:** {formatar_br(umidade_valor)}%")
    
    massa_exposta_kg = st.slider("Massa exposta na frente de trabalho (kg)", 50, 200, 100, 10,
                                help="Massa de resíduos exposta diariamente para tratamento")
    h_exposta = st.slider("Horas expostas por dia", 4, 24, 8, 1,
                         help="Horas diárias de exposição dos resíduos")
    
    st.subheader("🎯 Configuração de Simulação")
    anos_simulacao = st.slider("Anos de simulação", 5, 50, 20, 5,
                              help="Período total da simulação em anos")
    n_simulations = st.slider("Número de simulações Monte Carlo", 50, 1000, 100, 50,
                             help="Número de iterações para análise de incerteza")
    n_samples = st.slider("Número de amostras Sobol", 32, 256, 64, 16,
                         help="Número de amostras para análise de sensibilidade")
    
    if st.button("🚀 Executar Simulação", type="primary"):
        st.session_state.run_simulation = True

# =============================================================================
# PARÂMETROS FIXOS (DO CÓDIGO ORIGINAL)
# =============================================================================

T = 25  # Temperatura média (ºC)
DOC = 0.15  # Carbono orgânico degradável (fração)
DOCf_val = 0.0147 * T + 0.28
MCF = 1  # Fator de correção de metano
F = 0.5  # Fração de metano no biogás
OX = 0.1  # Fator de oxidação
Ri = 0.0  # Metano recuperado

# Constante de decaimento (fixa como no script anexo)
k_ano = 0.06  # Constante de decaimento anual

# Vermicompostagem (Yang et al. 2017) - valores fixos
TOC_YANG = 0.436  # Fração de carbono orgânico total
TN_YANG = 14.2 / 1000  # Fração de nitrogênio total
CH4_C_FRAC_YANG = 0.13 / 100  # Fração do TOC emitida como CH4-C (fixo)
N2O_N_FRAC_YANG = 0.92 / 100  # Fração do TN emitida como N2O-N (fixo)
DIAS_COMPOSTAGEM = 50  # Período total de compostagem

# Perfil temporal de emissões baseado em Yang et al. (2017)
PERFIL_CH4_VERMI = np.array([
    0.02, 0.02, 0.02, 0.03, 0.03,  # Dias 1-5
    0.04, 0.04, 0.05, 0.05, 0.06,  # Dias 6-10
    0.07, 0.08, 0.09, 0.10, 0.09,  # Dias 11-15
    0.08, 0.07, 0.06, 0.05, 0.04,  # Dias 16-20
    0.03, 0.02, 0.02, 0.01, 0.01,  # Dias 21-25
    0.01, 0.01, 0.01, 0.01, 0.01,  # Dias 26-30
    0.005, 0.005, 0.005, 0.005, 0.005,  # Dias 31-35
    0.005, 0.005, 0.005, 0.005, 0.005,  # Dias 36-40
    0.002, 0.002, 0.002, 0.002, 0.002,  # Dias 41-45
    0.001, 0.001, 0.001, 0.001, 0.001   # Dias 46-50
])
PERFIL_CH4_VERMI /= PERFIL_CH4_VERMI.sum()

PERFIL_N2O_VERMI = np.array([
    0.15, 0.10, 0.20, 0.05, 0.03,  # Dias 1-5 (pico no dia 3)
    0.03, 0.03, 0.04, 0.05, 0.06,  # Dias 6-10
    0.08, 0.09, 0.10, 0.08, 0.07,  # Dias 11-15
    0.06, 0.05, 0.04, 0.03, 0.02,  # Dias 16-20
    0.01, 0.01, 0.005, 0.005, 0.005,  # Dias 21-25
    0.005, 0.005, 0.005, 0.005, 0.005,  # Dias 26-30
    0.002, 0.002, 0.002, 0.002, 0.002,  # Dias 31-35
    0.001, 0.001, 0.001, 0.001, 0.001,  # Dias 36-40
    0.001, 0.001, 0.001, 0.001, 0.001,  # Dias 41-45
    0.001, 0.001, 0.001, 0.001, 0.001   # Dias 46-50
])
PERFIL_N2O_VERMI /= PERFIL_N2O_VERMI.sum()

# Emissões pré-descarte (Feng et al. 2020)
CH4_pre_descarte_ugC_por_kg_h_min = 0.18
CH4_pre_descarte_ugC_por_kg_h_max = 5.38
CH4_pre_descarte_ugC_por_kg_h_media = 2.78

fator_conversao_C_para_CH4 = 16/12
CH4_pre_descarte_ugCH4_por_kg_h_media = CH4_pre_descarte_ugC_por_kg_h_media * fator_conversao_C_para_CH4
CH4_pre_descarte_g_por_kg_dia = CH4_pre_descarte_ugCH4_por_kg_h_media * 24 / 1_000_000

N2O_pre_descarte_mgN_por_kg = 20.26
N2O_pre_descarte_mgN_por_kg_dia = N2O_pre_descarte_mgN_por_kg / 3
N2O_pre_descarte_g_por_kg_dia = N2O_pre_descarte_mgN_por_kg_dia * (44/28) / 1000

PERFIL_N2O_PRE_DESCARTE = {1: 0.8623, 2: 0.10, 3: 0.0377}

# GWP (IPCC AR6)
GWP_CH4_20 = 79.7
GWP_N2O_20 = 273

# Período de Simulação
dias = anos_simulacao * 365
ano_inicio = datetime.now().year
data_inicio = datetime(ano_inicio, 1, 1)
datas = pd.date_range(start=data_inicio, periods=dias, freq='D')

# Perfil temporal N2O (Wang et al. 2017)
PERFIL_N2O = {1: 0.10, 2: 0.30, 3: 0.40, 4: 0.15, 5: 0.05}

# Valores específicos para compostagem termofílica (Yang et al. 2017) - valores fixos
CH4_C_FRAC_THERMO = 0.006  # Fixo
N2O_N_FRAC_THERMO = 0.0196  # Fixo

PERFIL_CH4_THERMO = np.array([
    0.01, 0.02, 0.03, 0.05, 0.08,  # Dias 1-5
    0.12, 0.15, 0.18, 0.20, 0.18,  # Dias 6-10 (pico termofílico)
    0.15, 0.12, 0.10, 0.08, 0.06,  # Dias 11-15
    0.05, 0.04, 0.03, 0.02, 0.02,  # Dias 16-20
    0.01, 0.01, 0.01, 0.01, 0.01,  # Dias 21-25
    0.005, 0.005, 0.005, 0.005, 0.005,  # Dias 26-30
    0.002, 0.002, 0.002, 0.002, 0.002,  # Dias 31-35
    0.001, 0.001, 0.001, 0.001, 0.001,  # Dias 36-40
    0.001, 0.001, 0.001, 0.001, 0.001,  # Dias 41-45
    0.001, 0.001, 0.001, 0.001, 0.001   # Dias 46-50
])
PERFIL_CH4_THERMO /= PERFIL_CH4_THERMO.sum()

PERFIL_N2O_THERMO = np.array([
    0.10, 0.08, 0.15, 0.05, 0.03,  # Dias 1-5
    0.04, 0.05, 0.07, 0.10, 0.12,  # Dias 6-10
    0.15, 0.18, 0.20, 0.18, 0.15,  # Dias 11-15 (pico termofílico)
    0.12, 0.10, 0.08, 0.06, 0.05,  # Dias 16-20
    0.04, 0.03, 0.02, 0.02, 0.01,  # Dias 21-25
    0.01, 0.01, 0.01, 0.01, 0.01,  # Dias 26-30
    0.005, 0.005, 0.005, 0.005, 0.005,  # Dias 31-35
    0.002, 0.002, 0.002, 0.002, 0.002,  # Dias 36-40
    0.001, 0.001, 0.001, 0.001, 0.001,  # Dias 41-45
    0.001, 0.001, 0.001, 0.001, 0.001,   # Dias 46-50
])
PERFIL_N2O_THERMO /= PERFIL_N2O_THERMO.sum()

# =============================================================================
# FUNÇÕES DE CÁLCULO (ADAPTADAS DO SCRIPT ANEXO)
# =============================================================================

def ajustar_emissoes_pre_descarte(O2_concentracao):
    ch4_ajustado = CH4_pre_descarte_g_por_kg_dia

    if O2_concentracao == 21:
        fator_n2o = 1.0
    elif O2_concentracao == 10:
        fator_n2o = 11.11 / 20.26
    elif O2_concentracao == 1:
        fator_n2o = 7.86 / 20.26
    else:
        fator_n2o = 1.0

    n2o_ajustado = N2O_pre_descarte_g_por_kg_dia * fator_n2o
    return ch4_ajustado, n2o_ajustado

def calcular_emissoes_pre_descarte(O2_concentracao, dias_simulacao=dias):
    ch4_ajustado, n2o_ajustado = ajustar_emissoes_pre_descarte(O2_concentracao)

    emissoes_CH4_pre_descarte_kg = np.full(dias_simulacao, residuos_kg_dia * ch4_ajustado / 1000)
    emissoes_N2O_pre_descarte_kg = np.zeros(dias_simulacao)

    for dia_entrada in range(dias_simulacao):
        for dias_apos_descarte, fracao in PERFIL_N2O_PRE_DESCARTE.items():
            dia_emissao = dia_entrada + dias_apos_descarte - 1
            if dia_emissao < dias_simulacao:
                emissoes_N2O_pre_descarte_kg[dia_emissao] += (
                    residuos_kg_dia * n2o_ajustado * fracao / 1000
                )

    return emissoes_CH4_pre_descarte_kg, emissoes_N2O_pre_descarte_kg

def calcular_emissoes_aterro(params, dias_simulacao=dias):
    umidade_val, temp_val, doc_val = params

    fator_umid = (1 - umidade_val) / (1 - 0.55)
    f_aberto = np.clip((massa_exposta_kg / residuos_kg_dia) * (h_exposta / 24), 0.0, 1.0)
    docf_calc = 0.0147 * temp_val + 0.28

    potencial_CH4_por_kg = doc_val * docf_calc * MCF * F * (16/12) * (1 - Ri) * (1 - OX)
    potencial_CH4_lote_diario = residuos_kg_dia * potencial_CH4_por_kg

    t = np.arange(1, dias_simulacao + 1, dtype=float)
    kernel_ch4 = np.exp(-k_ano * (t - 1) / 365.0) - np.exp(-k_ano * t / 365.0)
    entradas_diarias = np.ones(dias_simulacao, dtype=float)
    emissoes_CH4 = fftconvolve(entradas_diarias, kernel_ch4, mode='full')[:dias_simulacao]
    emissoes_CH4 *= potencial_CH4_lote_diario

    E_aberto = 1.91
    E_fechado = 2.15
    E_medio = f_aberto * E_aberto + (1 - f_aberto) * E_fechado
    E_medio_ajust = E_medio * fator_umid
    emissao_diaria_N2O = (E_medio_ajust * (44/28) / 1_000_000) * residuos_kg_dia

    kernel_n2o = np.array([PERFIL_N2O.get(d, 0) for d in range(1, 6)], dtype=float)
    emissoes_N2O = fftconvolve(np.full(dias_simulacao, emissao_diaria_N2O), kernel_n2o, mode='full')[:dias_simulacao]

    O2_concentracao = 21
    emissoes_CH4_pre_descarte_kg, emissoes_N2O_pre_descarte_kg = calcular_emissoes_pre_descarte(O2_concentracao, dias_simulacao)

    total_ch4_aterro_kg = emissoes_CH4 + emissoes_CH4_pre_descarte_kg
    total_n2o_aterro_kg = emissoes_N2O + emissoes_N2O_pre_descarte_kg

    return total_ch4_aterro_kg, total_n2o_aterro_kg

def calcular_emissoes_vermi(params, dias_simulacao=dias):
    umidade_val, temp_val, doc_val = params
    fracao_ms = 1 - umidade_val
    
    # Usando valores fixos para CH4_C_FRAC_YANG e N2O_N_FRAC_YANG
    ch4_total_por_lote = residuos_kg_dia * (TOC_YANG * CH4_C_FRAC_YANG * (16/12) * fracao_ms)
    n2o_total_por_lote = residuos_kg_dia * (TN_YANG * N2O_N_FRAC_YANG * (44/28) * fracao_ms)

    emissoes_CH4 = np.zeros(dias_simulacao)
    emissoes_N2O = np.zeros(dias_simulacao)

    for dia_entrada in range(dias_simulacao):
        for dia_compostagem in range(len(PERFIL_CH4_VERMI)):
            dia_emissao = dia_entrada + dia_compostagem
            if dia_emissao < dias_simulacao:
                emissoes_CH4[dia_emissao] += ch4_total_por_lote * PERFIL_CH4_VERMI[dia_compostagem]
                emissoes_N2O[dia_emissao] += n2o_total_por_lote * PERFIL_N2O_VERMI[dia_compostagem]

    return emissoes_CH4, emissoes_N2O

def calcular_emissoes_compostagem(params, dias_simulacao=dias, dias_compostagem=50):
    umidade, T, DOC = params
    fracao_ms = 1 - umidade
    
    # Usando valores fixos para CH4_C_FRAC_THERMO e N2O_N_FRAC_THERMO
    ch4_total_por_lote = residuos_kg_dia * (TOC_YANG * CH4_C_FRAC_THERMO * (16/12) * fracao_ms)
    n2o_total_por_lote = residuos_kg_dia * (TN_YANG * N2O_N_FRAC_THERMO * (44/28) * fracao_ms)

    emissoes_CH4 = np.zeros(dias_simulacao)
    emissoes_N2O = np.zeros(dias_simulacao)

    for dia_entrada in range(dias_simulacao):
        for dia_compostagem in range(len(PERFIL_CH4_THERMO)):
            dia_emissao = dia_entrada + dia_compostagem
            if dia_emissao < dias_simulacao:
                emissoes_CH4[dia_emissao] += ch4_total_por_lote * PERFIL_CH4_THERMO[dia_compostagem]
                emissoes_N2O[dia_emissao] += n2o_total_por_lote * PERFIL_N2O_THERMO[dia_compostagem]

    return emissoes_CH4, emissoes_N2O

def executar_simulacao_completa(parametros):
    umidade, T, DOC = parametros
    
    ch4_aterro, n2o_aterro = calcular_emissoes_aterro([umidade, T, DOC])
    ch4_vermi, n2o_vermi = calcular_emissoes_vermi([umidade, T, DOC])

    total_aterro_tco2eq = (ch4_aterro * GWP_CH4_20 + n2o_aterro * GWP_N2O_20) / 1000
    total_vermi_tco2eq = (ch4_vermi * GWP_CH4_20 + n2o_vermi * GWP_N2O_20) / 1000

    reducao_tco2eq = total_aterro_tco2eq.sum() - total_vermi_tco2eq.sum()
    return reducao_tco2eq

def executar_simulacao_unfccc(parametros):
    umidade, T, DOC = parametros

    ch4_aterro, n2o_aterro = calcular_emissoes_aterro([umidade, T, DOC])
    total_aterro_tco2eq = (ch4_aterro * GWP_CH4_20 + n2o_aterro * GWP_N2O_20) / 1000

    ch4_compost, n2o_compost = calcular_emissoes_compostagem([umidade, T, DOC], dias_simulacao=dias, dias_compostagem=50)
    total_compost_tco2eq = (ch4_compost * GWP_CH4_20 + n2o_compost * GWP_N2O_20) / 1000

    reducao_tco2eq = total_aterro_tco2eq.sum() - total_compost_tco2eq.sum()
    return reducao_tco2eq

# =============================================================================
# NOVAS FUNÇÕES PARA ANÁLISE FINANCEIRA DE RISCO
# =============================================================================

def analise_financeira_risco(resultados_mc, preco_carbono, taxa_cambio, nome_metodologia):
    """
    Analisa o risco financeiro baseado na simulação Monte Carlo
    """
    # Converter para arrays numpy
    resultados_array = np.array(resultados_mc)
    
    # Estatísticas básicas
    media = np.mean(resultados_array)
    mediana = np.median(resultados_array)
    std = np.std(resultados_array)
    
    # Percentis
    p5 = np.percentile(resultados_array, 5)
    p25 = np.percentile(resultados_array, 25)
    p75 = np.percentile(resultados_array, 75)
    p95 = np.percentile(resultados_array, 95)
    
    # Intervalo de confiança 95%
    ic_inferior = np.percentile(resultados_array, 2.5)
    ic_superior = np.percentile(resultados_array, 97.5)
    
    # Valor em Risco (VaR) - pior cenário em 95% de confiança
    var_95 = np.percentile(resultados_array, 5)
    
    # Conditional VaR (CVaR) - perda esperada nos piores 5%
    cvar_95 = resultados_array[resultados_array <= var_95].mean()
    
    # Cálculos financeiros em Euros
    valor_medio_eur = media * preco_carbono
    valor_var_eur = var_95 * preco_carbono
    valor_cvar_eur = cvar_95 * preco_carbono
    
    # Cálculos financeiros em Reais
    valor_medio_brl = valor_medio_eur * taxa_cambio
    valor_var_brl = valor_var_eur * taxa_cambio
    valor_cvar_brl = valor_cvar_eur * taxa_cambio
    
    # Downside e Upside
    downside = media - ic_inferior  # em tCO₂eq
    upside = ic_superior - media    # em tCO₂eq
    
    downside_brl = downside * preco_carbono * taxa_cambio
    upside_brl = upside * preco_carbono * taxa_cambio
    
    return {
        'nome': nome_metodologia,
        'estatisticas': {
            'media': media,
            'mediana': mediana,
            'std': std,
            'p5': p5,
            'p25': p25,
            'p75': p75,
            'p95': p95,
            'ic_95_inf': ic_inferior,
            'ic_95_sup': ic_superior,
            'var_95': var_95,
            'cvar_95': cvar_95,
            'downside': downside,
            'upside': upside
        },
        'financeiro_eur': {
            'valor_medio': valor_medio_eur,
            'valor_var': valor_var_eur,
            'valor_cvar': valor_cvar_eur
        },
        'financeiro_brl': {
            'valor_medio': valor_medio_brl,
            'valor_var': valor_var_brl,
            'valor_cvar': valor_cvar_brl,
            'downside': downside_brl,
            'upside': upside_brl
        }
    }

def criar_dashboard_financeiro(analise_tese, analise_unfccc, preco_carbono, taxa_cambio, results_array_tese, results_array_unfccc):
    """
    Cria dashboard interativo com métricas financeiras de risco
    """
    st.subheader("💰 Dashboard Financeiro de Risco")
    
    # Abas para diferentes visualizações
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Visão Geral", 
        "🎯 Análise de Risco", 
        "📈 Comparação", 
        "💡 Recomendações"
    ])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"#### {analise_tese['nome']}")
            st.metric(
                "Valor Esperado (R$)", 
                f"R$ {formatar_br(analise_tese['financeiro_brl']['valor_medio'])}",
                delta=f"±R$ {formatar_br(analise_tese['financeiro_brl']['downside'])}",
                delta_color="off"
            )
            
            st.markdown("**Intervalo de Confiança 95%:**")
            st.info(f"""
            **Inferior:** R$ {formatar_br(analise_tese['financeiro_brl']['valor_medio'] - analise_tese['financeiro_brl']['downside'])}
            **Superior:** R$ {formatar_br(analise_tese['financeiro_brl']['valor_medio'] + analise_tese['financeiro_brl']['upside'])}
            """)
        
        with col2:
            st.markdown(f"#### {analise_unfccc['nome']}")
            st.metric(
                "Valor Esperado (R$)", 
                f"R$ {formatar_br(analise_unfccc['financeiro_brl']['valor_medio'])}",
                delta=f"±R$ {formatar_br(analise_unfccc['financeiro_brl']['downside'])}",
                delta_color="off"
            )
            
            st.markdown("**Intervalo de Confiança 95%:**")
            st.info(f"""
            **Inferior:** R$ {formatar_br(analise_unfccc['financeiro_brl']['valor_medio'] - analise_unfccc['financeiro_brl']['downside'])}
            **Superior:** R$ {formatar_br(analise_unfccc['financeiro_brl']['valor_medio'] + analise_unfccc['financeiro_brl']['upside'])}
            """)
    
    with tab2:
        st.markdown("#### 🎯 Medidas de Risco Financeiro")
        
        # VaR e CVaR
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "VaR 95% - Tese (R$)",
                f"R$ {formatar_br(analise_tese['financeiro_brl']['valor_var'])}",
                help="Valor em Risco: máxima perda esperada com 95% de confiança"
            )
        
        with col2:
            st.metric(
                "CVaR 95% - Tese (R$)",
                f"R$ {formatar_br(analise_tese['financeiro_brl']['valor_cvar'])}",
                help="Perda esperada nos piores 5% dos cenários"
            )
        
        with col3:
            st.metric(
                "VaR 95% - UNFCCC (R$)",
                f"R$ {formatar_br(analise_unfccc['financeiro_brl']['valor_var'])}",
                help="Valor em Risco: máxima perda esperada com 95% de confiança"
            )
        
        with col4:
            st.metric(
                "CVaR 95% - UNFCCC (R$)",
                f"R$ {formatar_br(analise_unfccc['financeiro_brl']['valor_cvar'])}",
                help="Perda esperada nos piores 5% dos cenários"
            )
        
        # Gráfico de distribuição de perdas
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Calcular distribuições de valor
        valores_tese_brl = results_array_tese * preco_carbono * taxa_cambio
        valores_unfccc_brl = results_array_unfccc * preco_carbono * taxa_cambio
        
        sns.histplot(valores_tese_brl, kde=True, bins=30, color='skyblue', 
                    label='Tese', alpha=0.6, ax=ax)
        sns.histplot(valores_unfccc_brl, kde=True, bins=30, color='coral', 
                    label='UNFCCC', alpha=0.6, ax=ax)
        
        # Adicionar linhas de VaR
        ax.axvline(analise_tese['financeiro_brl']['valor_var'], color='blue', 
                  linestyle='--', label=f"VaR 95% Tese: R$ {formatar_br(analise_tese['financeiro_brl']['valor_var'])}")
        ax.axvline(analise_unfccc['financeiro_brl']['valor_var'], color='red', 
                  linestyle='--', label=f"VaR 95% UNFCCC: R$ {formatar_br(analise_unfccc['financeiro_brl']['valor_var'])}")
        
        ax.set_title('Distribuição do Valor Financeiro dos Créditos de Carbono')
        ax.set_xlabel('Valor (R$)')
        ax.set_ylabel('Frequência')
        ax.legend()
        ax.grid(alpha=0.3)
        ax.xaxis.set_major_formatter(FuncFormatter(br_format))
        
        st.pyplot(fig)
    
    with tab3:
        st.markdown("#### 📈 Comparação de Retorno vs Risco")
        
        # Dataframe comparativo
        df_comparativo = pd.DataFrame({
            'Métrica': [
                'Valor Esperado (R$)', 
                'Downside (R$)', 
                'Upside (R$)',
                'VaR 95% (R$)',
                'CVaR 95% (R$)',
                'Razão Retorno/Risco'
            ],
            'Proposta da Tese': [
                formatar_br(analise_tese['financeiro_brl']['valor_medio']),
                formatar_br(analise_tese['financeiro_brl']['downside']),
                formatar_br(analise_tese['financeiro_brl']['upside']),
                formatar_br(analise_tese['financeiro_brl']['valor_var']),
                formatar_br(analise_tese['financeiro_brl']['valor_cvar']),
                formatar_br(analise_tese['financeiro_brl']['valor_medio'] / analise_tese['financeiro_brl']['valor_cvar'] if analise_tese['financeiro_brl']['valor_cvar'] > 0 else '∞')
            ],
            'Cenário UNFCCC': [
                formatar_br(analise_unfccc['financeiro_brl']['valor_medio']),
                formatar_br(analise_unfccc['financeiro_brl']['downside']),
                formatar_br(analise_unfccc['financeiro_brl']['upside']),
                formatar_br(analise_unfccc['financeiro_brl']['valor_var']),
                formatar_br(analise_unfccc['financeiro_brl']['valor_cvar']),
                formatar_br(analise_unfccc['financeiro_brl']['valor_medio'] / analise_unfccc['financeiro_brl']['valor_cvar'] if analise_unfccc['financeiro_brl']['valor_cvar'] > 0 else '∞')
            ]
        })
        
        st.dataframe(df_comparativo, use_container_width=True)
        
        # Gráfico de trade-off risco-retorno
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Pontos no gráfico
        ax.scatter(
            analise_tese['financeiro_brl']['valor_cvar'],  # Risco (CVaR)
            analise_tese['financeiro_brl']['valor_medio'], # Retorno
            s=200, color='blue', label='Proposta da Tese',
            edgecolors='black', linewidth=2
        )
        
        ax.scatter(
            analise_unfccc['financeiro_brl']['valor_cvar'],
            analise_unfccc['financeiro_brl']['valor_medio'],
            s=200, color='red', label='Cenário UNFCCC',
            edgecolors='black', linewidth=2
        )
        
        # Linha de eficiência
        ax.plot([0, max(analise_tese['financeiro_brl']['valor_cvar'], 
                       analise_unfccc['financeiro_brl']['valor_cvar'])],
                [0, max(analise_tese['financeiro_brl']['valor_medio'],
                       analise_unfccc['financeiro_brl']['valor_medio'])],
                'k--', alpha=0.3, label='Fronteira de Eficiência')
        
        ax.set_xlabel('Risco (CVaR 95% - R$)')
        ax.set_ylabel('Retorno Esperado (R$)')
        ax.set_title('Trade-off Retorno vs Risco')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(FuncFormatter(br_format))
        ax.yaxis.set_major_formatter(FuncFormatter(br_format))
        
        st.pyplot(fig)
    
    with tab4:
        st.markdown("#### 💡 Recomendações Baseadas em Risco")
        
        # Análise comparativa
        if analise_tese['financeiro_brl']['valor_medio'] > analise_unfccc['financeiro_brl']['valor_medio']:
            diferenca_valor = analise_tese['financeiro_brl']['valor_medio'] - analise_unfccc['financeiro_brl']['valor_medio']
            st.success(f"✅ **A Tese oferece R$ {formatar_br(diferenca_valor)} a mais em valor esperado**")
        else:
            st.warning("⚠️ **O cenário UNFCCC tem maior valor esperado**")
        
        if analise_tese['financeiro_brl']['valor_cvar'] > analise_unfccc['financeiro_brl']['valor_cvar']:
            st.warning(f"⚠️ **A Tese tem maior risco de cauda (CVaR): R$ {formatar_br(analise_tese['financeiro_brl']['valor_cvar'])} vs R$ {formatar_br(analise_unfccc['financeiro_brl']['valor_cvar'])}**")
        else:
            st.success("✅ **A Tese tem menor risco de cauda**")
        
        # Recomendações específicas
        st.markdown("""
