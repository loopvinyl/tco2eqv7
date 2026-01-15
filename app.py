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

# =============================================================================
# CONFIGURAÇÕES INICIAIS
# =============================================================================

st.set_page_config(
    page_title="SINISA + Potencial de Metano e Créditos de Carbono", 
    layout="wide",
    page_icon="🌱"
)

warnings.filterwarnings("ignore")
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
np.seterr(divide='ignore', invalid='ignore')
plt.rcParams['figure.dpi'] = 150
plt.rcParams['font.size'] = 10
sns.set_style("whitegrid")

# =============================================================================
# FUNÇÕES DE FORMATTAÇÃO
# =============================================================================

def formatar_br(numero):
    """Formata números no padrão brasileiro: 1.234,56"""
    if pd.isna(numero):
        return "N/A"
    numero = round(numero, 2)
    return f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_br_dec(numero, decimais=2):
    """Formata números no padrão brasileiro com número específico de casas decimais"""
    if pd.isna(numero):
        return "N/A"
    numero = round(numero, decimais)
    return f"{numero:,.{decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def br_format(x, pos):
    """Função de formatação para eixos de gráficos (padrão brasileiro)"""
    if x == 0:
        return "0"
    if abs(x) < 0.01:
        return f"{x:.1e}".replace(".", ",")
    if abs(x) >= 1000:
        return f"{x:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# =============================================================================
# FUNÇÕES DE COTAÇÃO EM TEMPO REAL
# =============================================================================

def obter_cotacao_carbono_investing():
    """Obtém a cotação em tempo real do carbono via Investing.com"""
    try:
        url = "https://www.investing.com/commodities/carbon-emissions"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Estratégias para encontrar o preço
        selectores = [
            '[data-test="instrument-price-last"]',
            '.text-2xl',
            '.last-price-value',
            '.instrument-price-last',
            '.pid-1062510-last',
            '#last_last'
        ]
        
        preco = None
        fonte = "Investing.com"
        
        for seletor in selectores:
            try:
                elemento = soup.select_one(seletor)
                if elemento:
                    texto_preco = elemento.text.strip().replace(',', '')
                    texto_preco = ''.join(c for c in texto_preco if c.isdigit() or c == '.')
                    if texto_preco:
                        preco = float(texto_preco)
                        break
            except:
                continue
        
        if preco is not None:
            return preco, "€", "Carbon Emissions Future", True, fonte
        
        # Tentativa alternativa com regex
        import re
        padroes_preco = [
            r'"last":"([\d,]+)"',
            r'data-last="([\d,]+)"',
            r'last_price["\']?:\s*["\']?([\d,]+)',
        ]
        
        html_texto = str(soup)
        for padrao in padroes_preco:
            matches = re.findall(padrao, html_texto)
            for match in matches:
                try:
                    preco_texto = match.replace(',', '')
                    preco = float(preco_texto)
                    if 50 < preco < 200:
                        return preco, "€", "Carbon Emissions Future", True, fonte
                except:
                    continue
        
        return 85.50, "€", "Carbon Emissions (Referência)", False, "Valor de referência"
        
    except Exception as e:
        return 85.50, "€", "Carbon Emissions (Referência)", False, f"Erro: {str(e)[:50]}"

def obter_cotacao_euro_real():
    """Obtém a cotação em tempo real do Euro em Reais"""
    try:
        # API do AwesomeAPI
        url = "https://economia.awesomeapi.com.br/last/EUR-BRL"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            cotacao = float(data['EURBRL']['bid'])
            return cotacao, "R$", True, "AwesomeAPI"
    except:
        pass
    
    try:
        # API do BCB
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.21619/dados/ultimos/1?formato=json"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            cotacao = float(data[0]['valor'])
            return cotacao, "R$", True, "BCB"
    except:
        pass
    
    # Fallback
    return 5.50, "R$", False, "Valor de referência"

def obter_cotacoes_tempo_real():
    """Obtém todas as cotações necessárias"""
    # Cotação do carbono
    preco_carbono, moeda_carbono, info_carbono, sucesso_carbono, fonte_carbono = obter_cotacao_carbono_investing()
    
    # Cotação do Euro
    preco_euro, moeda_real, sucesso_euro, fonte_euro = obter_cotacao_euro_real()
    
    # Calcular preço do carbono em Reais
    preco_carbono_reais = preco_carbono * preco_euro
    
    return {
        'preco_carbono_eur': preco_carbono,
        'moeda_carbono': moeda_carbono,
        'info_carbono': info_carbono,
        'fonte_carbono': fonte_carbono,
        'taxa_cambio': preco_euro,
        'moeda_real': moeda_real,
        'fonte_euro': fonte_euro,
        'preco_carbono_reais': preco_carbono_reais,
        'timestamp': datetime.now()
    }

# =============================================================================
# FUNÇÕES DE CÁLCULO DE POTENCIAL DE METANO (PARA ABA 1)
# =============================================================================

def calcular_potencial_metano_aterro(residuos_kg, umidade, temperatura, dias=365):
    """Calcula o potencial de geração de metano de um lote de resíduos no aterro (IPCC 2006)"""
    # Parâmetros fixos (IPCC 2006)
    DOC = 0.15  # Carbono orgânico degradável
    MCF = 1.0   # Fator de correção de metano
    F = 0.5     # Fração de metano no biogás
    OX = 0.1    # Fator de oxidação
    Ri = 0.0    # Metano recuperado
    
    # DOCf calculado pela temperatura
    DOCf = 0.0147 * temperatura + 0.28
    
    # Cálculo do potencial de metano por kg de resíduo
    potencial_CH4_por_kg = DOC * DOCf * MCF * F * (16/12) * (1 - Ri) * (1 - OX)
    
    # Potencial total do lote
    potencial_CH4_total = residuos_kg * potencial_CH4_por_kg
    
    # Taxa de decaimento anual (6% ao ano)
    k_ano = 0.06
    k_dia = k_ano / 365.0
    
    # Gerar emissões ao longo do tempo
    t = np.arange(1, dias + 1, dtype=float)
    kernel_ch4 = np.exp(-k_dia * (t - 1)) - np.exp(-k_dia * t)
    kernel_ch4 = np.maximum(kernel_ch4, 0)
    
    # Distribuir o potencial total
    emissoes_CH4 = potencial_CH4_total * kernel_ch4
    
    # Calcular fração total emitida
    fracao_total_emitida = kernel_ch4.sum()
    
    return emissoes_CH4, potencial_CH4_total, DOCf, fracao_total_emitida

def calcular_emissoes_vermicompostagem_lote(residuos_kg, umidade, dias=50):
    """Calcula emissões de metano na vermicompostagem (Yang et al. 2017)"""
    # Parâmetros fixos
    TOC = 0.436  # Fração de carbono orgânico total
    CH4_C_FRAC = 0.13 / 100  # Fração do TOC emitida como CH4-C
    fracao_ms = 1 - umidade
    
    # Metano total por lote
    ch4_total_por_lote = residuos_kg * (TOC * CH4_C_FRAC * (16/12) * fracao_ms)
    
    # Perfil temporal
    perfil_ch4 = np.array([
        0.02, 0.02, 0.02, 0.03, 0.03, 0.04, 0.04, 0.05, 0.05, 0.06,
        0.07, 0.08, 0.09, 0.10, 0.09, 0.08, 0.07, 0.06, 0.05, 0.04,
        0.03, 0.02, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01,
        0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 0.005,
        0.002, 0.002, 0.002, 0.002, 0.002, 0.001, 0.001, 0.001, 0.001, 0.001
    ])
    
    # Normalizar perfil
    perfil_ch4 = perfil_ch4 / perfil_ch4.sum()
    
    # Distribuir emissões
    emissoes_CH4 = ch4_total_por_lote * perfil_ch4
    
    return emissoes_CH4, ch4_total_por_lote

def calcular_emissoes_compostagem_lote(residuos_kg, umidade, dias=50):
    """Calcula emissões de metano na compostagem termofílica"""
    # Parâmetros fixos
    TOC = 0.436
    CH4_C_FRAC = 0.006  # Fração do TOC emitida como CH4-C
    fracao_ms = 1 - umidade
    
    # Metano total por lote
    ch4_total_por_lote = residuos_kg * (TOC * CH4_C_FRAC * (16/12) * fracao_ms)
    
    # Perfil temporal
    perfil_ch4 = np.array([
        0.01, 0.02, 0.03, 0.05, 0.08, 0.12, 0.15, 0.18, 0.20, 0.18,
        0.15, 0.12, 0.10, 0.08, 0.06, 0.05, 0.04, 0.03, 0.02, 0.02,
        0.01, 0.01, 0.01, 0.01, 0.01, 0.005, 0.005, 0.005, 0.005, 0.005,
        0.002, 0.002, 0.002, 0.002, 0.002, 0.001, 0.001, 0.001, 0.001, 0.001,
        0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001
    ])
    
    # Normalizar perfil
    perfil_ch4 = perfil_ch4 / perfil_ch4.sum()
    
    # Distribuir emissões
    emissoes_CH4 = ch4_total_por_lote * perfil_ch4
    
    return emissoes_CH4, ch4_total_por_lote

# =============================================================================
# FUNÇÕES DE CÁLCULO PARA ABA 2 (ENTRADA CONTÍNUA) - DO CÓDIGO ORIGINAL
# =============================================================================

# Parâmetros fixos (DO CÓDIGO ORIGINAL)
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

# GWP (IPCC AR6)
GWP_CH4_20 = 79.7
GWP_N2O_20 = 273

# Perfil temporal N2O (Wang et al. 2017)
PERFIL_N2O = {1: 0.10, 2: 0.30, 3: 0.40, 4: 0.15, 5: 0.05}

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

def calcular_emissoes_pre_descarte(O2_concentracao, dias_simulacao, residuos_kg_dia):
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

def calcular_emissoes_aterro(params, dias_simulacao, residuos_kg_dia, massa_exposta_kg, h_exposta):
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
    emissoes_CH4_pre_descarte_kg, emissoes_N2O_pre_descarte_kg = calcular_emissoes_pre_descarte(O2_concentracao, dias_simulacao, residuos_kg_dia)

    total_ch4_aterro_kg = emissoes_CH4 + emissoes_CH4_pre_descarte_kg
    total_n2o_aterro_kg = emissoes_N2O + emissoes_N2O_pre_descarte_kg

    return total_ch4_aterro_kg, total_n2o_aterro_kg

def calcular_emissoes_vermi(params, dias_simulacao, residuos_kg_dia):
    umidade_val, temp_val, doc_val = params
    fracao_ms = 1 - umidade_val
    
    # Usando valores fixos para CH4_C_FRAC_YANG e N2O_N_FRAC_YANG
    ch4_total_por_lote = residuos_kg_dia * (TOC_YANG * CH4_C_FRAC_YANG * (16/12) * fracao_ms)
    n2o_total_por_lote = residuos_kg_dia * (TN_YANG * N2O_N_FRAC_YANG * (44/28) * fracao_ms)

    emissoes_CH4 = np.zeros(dias_simulacao)
    emissoes_N2O = np.zeros(dias_simulacao)

    for dia_entrada in range(dias_simulacao):
        for dia_compostagem in range(DIAS_COMPOSTAGEM):
            dia_emissao = dia_entrada + dia_compostagem
            if dia_emissao < dias_simulacao:
                # Distribuição simplificada - usar distribuição uniforme
                emissoes_CH4[dia_emissao] += ch4_total_por_lote * (1/DIAS_COMPOSTAGEM)
                emissoes_N2O[dia_emissao] += n2o_total_por_lote * (1/DIAS_COMPOSTAGEM)

    return emissoes_CH4, emissoes_N2O

# =============================================================================
# DADOS DAS CIDADES BRASILEIRAS (PARA ABA 3)
# =============================================================================

CIDADES_BRASIL = {
    "São Paulo - SP": {
        "populacao": 12300000,
        "residuos_per_capita_kg_dia": 1.2,
        "fracao_organica": 0.52,
        "taxa_coleta": 0.95,
        "regiao": "Sudeste"
    },
    "Rio de Janeiro - RJ": {
        "populacao": 6748000,
        "residuos_per_capita_kg_dia": 1.1,
        "fracao_organica": 0.48,
        "taxa_coleta": 0.92,
        "regiao": "Sudeste"
    },
    "Brasília - DF": {
        "populacao": 3055000,
        "residuos_per_capita_kg_dia": 1.4,
        "fracao_organica": 0.45,
        "taxa_coleta": 0.98,
        "regiao": "Centro-Oeste"
    },
    "Salvador - BA": {
        "populacao": 2903000,
        "residuos_per_capita_kg_dia": 0.9,
        "fracao_organica": 0.55,
        "taxa_coleta": 0.85,
        "regiao": "Nordeste"
    },
    "Fortaleza - CE": {
        "populacao": 2687000,
        "residuos_per_capita_kg_dia": 0.95,
        "fracao_organica": 0.53,
        "taxa_coleta": 0.88,
        "regiao": "Nordeste"
    },
    "Belo Horizonte - MG": {
        "populacao": 2522000,
        "residuos_per_capita_kg_dia": 1.0,
        "fracao_organica": 0.50,
        "taxa_coleta": 0.93,
        "regiao": "Sudeste"
    },
    "Manaus - AM": {
        "populacao": 2218000,
        "residuos_per_capita_kg_dia": 0.85,
        "fracao_organica": 0.58,
        "taxa_coleta": 0.82,
        "regiao": "Norte"
    },
    "Curitiba - PR": {
        "populacao": 1963000,
        "residuos_per_capita_kg_dia": 1.1,
        "fracao_organica": 0.47,
        "taxa_coleta": 0.96,
        "regiao": "Sul"
    },
    "Recife - PE": {
        "populacao": 1653000,
        "residuos_per_capita_kg_dia": 0.88,
        "fracao_organica": 0.54,
        "taxa_coleta": 0.86,
        "regiao": "Nordeste"
    },
    "Goiânia - GO": {
        "populacao": 1536000,
        "residuos_per_capita_kg_dia": 1.2,
        "fracao_organica": 0.49,
        "taxa_coleta": 0.94,
        "regiao": "Centro-Oeste"
    }
}

# =============================================================================
# FUNÇÃO PARA CALCULAR POTENCIAL POR CIDADE (ABA 3)
# =============================================================================

def calcular_potencial_cidade(cidade, dados_cidade, preco_carbono_eur, taxa_cambio, dias_simulacao=365):
    """Calcula o potencial de créditos de carbono para uma cidade"""
    
    # Calcular resíduos orgânicos diários
    residuos_total_dia = dados_cidade["populacao"] * dados_cidade["residuos_per_capita_kg_dia"]
    residuos_organicos_dia = residuos_total_dia * dados_cidade["fracao_organica"] * dados_cidade["taxa_coleta"]
    
    # Calcular para um ano (em kg)
    residuos_organicos_ano = residuos_organicos_dia * 365
    
    # Calcular potencial de metano no aterro
    umidade = 0.85  # 85% de umidade
    temperatura = 25  # 25°C
    
    emissoes_aterro, total_aterro, DOCf, fracao_emitida = calcular_potencial_metano_aterro(
        residuos_organicos_ano, umidade, temperatura, dias_simulacao
    )
    
    # Calcular potencial de metano na vermicompostagem
    dias_vermi = min(50, dias_simulacao)
    emissoes_vermi_temp, total_vermi = calcular_emissoes_vermicompostagem_lote(
        residuos_organicos_ano, umidade, dias_vermi
    )
    emissoes_vermi = np.zeros(dias_simulacao)
    emissoes_vermi[:dias_vermi] = emissoes_vermi_temp
    
    # Calcular potenciais acumulados
    total_aterro_emitido = emissoes_aterro.sum()
    total_vermi_emitido = emissoes_vermi.sum()
    
    # Calcular redução
    reducao_vermi = total_aterro_emitido - total_vermi_emitido
    
    # Converter para CO₂eq (GWP CH₄ = 27.9)
    GWP_CH4 = 27.9
    reducao_vermi_tco2eq = reducao_vermi * GWP_CH4 / 1000
    
    # Calcular valor financeiro
    valor_vermi_eur = reducao_vermi_tco2eq * preco_carbono_eur
    valor_vermi_brl = valor_vermi_eur * taxa_cambio
    
    return {
        "cidade": cidade,
        "regiao": dados_cidade["regiao"],
        "populacao": dados_cidade["populacao"],
        "residuos_organicos_dia_ton": residuos_organicos_dia / 1000,
        "residuos_organicos_ano_ton": residuos_organicos_ano / 1000,
        "total_aterro_emitido_kg": total_aterro_emitido,
        "total_vermi_emitido_kg": total_vermi_emitido,
        "reducao_vermi_tco2eq": reducao_vermi_tco2eq,
        "valor_vermi_eur": valor_vermi_eur,
        "valor_vermi_brl": valor_vermi_brl,
        "valor_por_ton_residuo_eur": valor_vermi_eur / (residuos_organicos_ano / 1000),
        "valor_por_ton_residuo_brl": valor_vermi_brl / (residuos_organicos_ano / 1000)
    }

# =============================================================================
# INICIALIZAÇÃO DA SESSION STATE
# =============================================================================

# Inicializar session state para cotações
if 'cotacoes' not in st.session_state:
    with st.spinner("🔄 Obtendo cotações em tempo real..."):
        st.session_state.cotacoes = obter_cotacoes_tempo_real()
        st.session_state.ultima_atualizacao = datetime.now()

# =============================================================================
# CABEÇALHO PRINCIPAL
# =============================================================================

st.title("🌱 SINISA - Simulador de Potencial de Metano e Créditos de Carbono")
st.markdown("""
**Sistema Integrado de Análise de Potencial de Créditos de Carbono para Gestão de Resíduos Orgânicos**
""")

# =============================================================================
# SEÇÃO DE COTAÇÃO EM TEMPO REAL (COMPARTILHADA)
# =============================================================================

st.header("💰 Cotações em Tempo Real")

# Botão para atualizar cotações
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🔄 Atualizar Cotações", type="primary", use_container_width=True):
        with st.spinner("Atualizando cotações..."):
            st.session_state.cotacoes = obter_cotacoes_tempo_real()
            st.session_state.ultima_atualizacao = datetime.now()
            st.rerun()

# Exibir cotações
cotacoes = st.session_state.cotacoes

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Preço do Carbono (EUA)",
        value=f"€ {formatar_br(cotacoes['preco_carbono_eur'])}",
        help=f"{cotacoes['info_carbono']} - Fonte: {cotacoes['fonte_carbono']}"
    )

with col2:
    st.metric(
        label="Euro (EUR/BRL)",
        value=f"R$ {formatar_br(cotacoes['taxa_cambio'])}",
        help=f"Fonte: {cotacoes['fonte_euro']}"
    )

with col3:
    st.metric(
        label="Carbono em Reais",
        value=f"R$ {formatar_br(cotacoes['preco_carbono_reais'])}",
        help="Preço do carbono convertido para Reais"
    )

st.caption(f"🕒 Última atualização: {st.session_state.ultima_atualizacao.strftime('%d/%m/%Y %H:%M:%S')}")

# =============================================================================
# ABAS PRINCIPAIS
# =============================================================================

tab1, tab2, tab3 = st.tabs([
    "📦 Análise por Lote Único (100 kg)",
    "📈 Entrada Contínua (kg/dia)", 
    "🏙️ Potencial por Cidade"
])

# =============================================================================
# ABA 1: ANÁLISE POR LOTE ÚNICO (100 kg)
# =============================================================================
with tab1:
    st.header("📦 Análise por Lote Único de 100 kg")
    st.markdown("""
    **Análise Comparativa: Aterro vs Vermicompostagem vs Compostagem**

    Este simulador calcula o potencial de geração de metano de um lote de 100 kg de resíduos orgânicos
    em três diferentes cenários de gestão, com análise financeira baseada no mercado de carbono.
    
    **✅ CORREÇÃO APLICADA:** Kernel de decaimento NÃO normalizado para aterro (metodologia IPCC correta)
    """)
    
    # Parâmetros de entrada na sidebar (apenas para aba 1)
    with st.sidebar:
        st.header("⚙️ Parâmetros de Entrada - Lote Único")
        
        # Entrada principal de resíduos (fixo em 100 kg para o lote)
        st.subheader("📦 Lote de Resíduos")
        residuos_kg = st.number_input(
            "Peso do lote (kg)", 
            min_value=10, 
            max_value=1000, 
            value=100, 
            step=10,
            help="Peso do lote de resíduos orgânicos para análise",
            key="lote_residuos"
        )
        
        st.subheader("📊 Parâmetros Ambientais")
        
        umidade_valor = st.slider(
            "Umidade do resíduo (%)", 
            50, 95, 85, 1,
            help="Percentual de umidade dos resíduos orgânicos",
            key="umidade_lote"
        )
        umidade = umidade_valor / 100.0
        
        temperatura = st.slider(
            "Temperatura média (°C)", 
            15, 35, 25, 1,
            help="Temperatura média ambiente (importante para cálculo do DOCf)",
            key="temp_lote"
        )
        
        st.subheader("⏰ Período de Análise")
        dias_simulacao = st.slider(
            "Dias de simulação", 
            50, 3650, 365, 50,
            help="Período total da simulação em dias (até 10 anos)",
            key="dias_lote"
        )
        
        # Adicionar aviso sobre método correto
        with st.expander("ℹ️ Informação sobre Metodologia"):
            st.info("""
            **Método Corrigido (IPCC 2006):**
            - **Aterro:** Kernel NÃO normalizado - respeita a equação diferencial do decaimento
            - **Compostagem/Vermicompostagem:** Kernel normalizado - processos curtos (<50 dias)
            
            **Para 100 kg × 365 dias:**
            - Potencial total CH₄: ~5.83 kg
            - Fração emitida em 365 dias: ~6%
            - CH₄ emitido no período: ~0.35 kg
            """)
        
        if st.button("🚀 Calcular Potencial de Metano", type="primary", key="btn_lote"):
            st.session_state.run_analise_lote = True

    # Execução da simulação para aba 1
    if st.session_state.get('run_analise_lote', False):
        with st.spinner('Calculando potencial de metano para os três cenários...'):
            
            # 1. CÁLCULO DO POTENCIAL DE METANO PARA CADA CENÁRIO
            # Aterro Sanitário (CORRIGIDO)
            emissoes_aterro, total_aterro, DOCf, fracao_emitida = calcular_potencial_metano_aterro(
                residuos_kg, umidade, temperatura, dias_simulacao
            )
            
            # Vermicompostagem (50 dias de processo)
            dias_vermi = min(50, dias_simulacao)
            emissoes_vermi_temp, total_vermi = calcular_emissoes_vermicompostagem_lote(
                residuos_kg, umidade, dias_vermi
            )
            emissoes_vermi = np.zeros(dias_simulacao)
            emissoes_vermi[:dias_vermi] = emissoes_vermi_temp
            
            # Compostagem Termofílica (50 dias de processo)
            dias_compost = min(50, dias_simulacao)
            emissoes_compost_temp, total_compost = calcular_emissoes_compostagem_lote(
                residuos_kg, umidade, dias_compost
            )
            emissoes_compost = np.zeros(dias_simulacao)
            emissoes_compost[:dias_compost] = emissoes_compost_temp
            
            # 2. CRIAR DATAFRAME COM OS RESULTADOS
            datas = pd.date_range(start=datetime.now(), periods=dias_simulacao, freq='D')
            
            df = pd.DataFrame({
                'Data': datas,
                'Aterro_CH4_kg': emissoes_aterro,
                'Vermicompostagem_CH4_kg': emissoes_vermi,
                'Compostagem_CH4_kg': emissoes_compost
            })
            
            # Calcular valores acumulados
            df['Aterro_Acumulado'] = df['Aterro_CH4_kg'].cumsum()
            df['Vermi_Acumulado'] = df['Vermicompostagem_CH4_kg'].cumsum()
            df['Compost_Acumulado'] = df['Compostagem_CH4_kg'].cumsum()
            
            # Calcular reduções (evitadas) em relação ao aterro
            df['Reducao_Vermi'] = df['Aterro_Acumulado'] - df['Vermi_Acumulado']
            df['Reducao_Compost'] = df['Aterro_Acumulado'] - df['Compost_Acumulado']
            
            # 3. EXIBIR RESULTADOS PRINCIPAIS
            st.header("📊 Resultados - Potencial de Metano por Cenário")
            
            # Informação sobre metodologia
            st.info(f"""
            **📈 Método Corrigido (Kernel NÃO normalizado):**
            - Potencial total de CH₄ no aterro: **{formatar_br(total_aterro)} kg**
            - Fração emitida em {dias_simulacao} dias: **{formatar_br(fracao_emitida*100)}%**
            - CH₄ realmente emitido no período: **{formatar_br(df['Aterro_Acumulado'].iloc[-1])} kg**
            """)
            
            # Métricas principais
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Aterro Sanitário",
                    f"{formatar_br(df['Aterro_Acumulado'].iloc[-1])} kg CH₄",
                    f"Potencial: {formatar_br(total_aterro)} kg",
                    help=f"Emitido em {dias_simulacao} dias ({formatar_br(fracao_emitida*100)}% do potencial)"
                )
            
            with col2:
                reducao_vermi_kg = df['Aterro_Acumulado'].iloc[-1] - df['Vermi_Acumulado'].iloc[-1]
                reducao_vermi_perc = (1 - df['Vermi_Acumulado'].iloc[-1]/df['Aterro_Acumulado'].iloc[-1])*100 if df['Aterro_Acumulado'].iloc[-1] > 0 else 0
                st.metric(
                    "Vermicompostagem",
                    f"{formatar_br(df['Vermi_Acumulado'].iloc[-1])} kg CH₄",
                    delta=f"-{formatar_br(reducao_vermi_perc)}%",
                    delta_color="inverse",
                    help=f"Redução de {formatar_br(reducao_vermi_kg)} kg vs aterro"
                )
            
            with col3:
                reducao_compost_kg = df['Aterro_Acumulado'].iloc[-1] - df['Compost_Acumulado'].iloc[-1]
                reducao_compost_perc = (1 - df['Compost_Acumulado'].iloc[-1]/df['Aterro_Acumulado'].iloc[-1])*100 if df['Aterro_Acumulado'].iloc[-1] > 0 else 0
                st.metric(
                    "Compostagem Termofílica",
                    f"{formatar_br(df['Compost_Acumulado'].iloc[-1])} kg CH₄",
                    delta=f"-{formatar_br(reducao_compost_perc)}%",
                    delta_color="inverse",
                    help=f"Redução de {formatar_br(reducao_compost_kg)} kg vs aterro"
                )
            
            # 4. GRÁFICO: REDUÇÃO DE EMISSÕES ACUMULADA
            st.subheader("📉 Redução de Emissões Acumulada (CH₄)")
            
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Configurar formatação
            br_formatter = FuncFormatter(br_format)
            
            # Plotar linhas de acumulado
            ax.plot(df['Data'], df['Aterro_Acumulado'], 'r-', 
                    label='Aterro Sanitário', linewidth=3, alpha=0.7)
            ax.plot(df['Data'], df['Vermi_Acumulado'], 'g-', 
                    label='Vermicompostagem', linewidth=2)
            ax.plot(df['Data'], df['Compost_Acumulado'], 'b-', 
                    label='Compostagem Termofílica', linewidth=2)
            
            # Área de redução (evitadas)
            ax.fill_between(df['Data'], df['Vermi_Acumulado'], df['Aterro_Acumulado'],
                            color='green', alpha=0.3, label='Redução Vermicompostagem')
            ax.fill_between(df['Data'], df['Compost_Acumulado'], df['Aterro_Acumulado'],
                            color='blue', alpha=0.2, label='Redução Compostagem')
            
            # Configurar gráfico
            ax.set_title(f'Acumulado de Metano em {dias_simulacao} Dias - Lote de {residuos_kg} kg (Método Corrigido)', 
                        fontsize=14, fontweight='bold')
            ax.set_xlabel('Data')
            ax.set_ylabel('Metano Acumulado (kg CH₄)')
            ax.legend(title='Cenário de Gestão', loc='upper left')
            ax.grid(True, linestyle='--', alpha=0.5)
            ax.yaxis.set_major_formatter(br_formatter)
            
            # Rotacionar labels do eixo x
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            st.pyplot(fig)
            
            # 5. CÁLCULO DE CO₂eq E VALOR FINANCEIRO
            st.header("💰 Valor Financeiro das Emissões Evitadas")
            
            # Converter metano para CO₂eq (GWP CH₄ = 27.9 para 100 anos - IPCC AR6)
            GWP_CH4 = 27.9  # kg CO₂eq per kg CH₄
            
            total_evitado_vermi_kg = (df['Aterro_Acumulado'].iloc[-1] - df['Vermi_Acumulado'].iloc[-1]) * GWP_CH4
            total_evitado_vermi_tco2eq = total_evitado_vermi_kg / 1000
            
            total_evitado_compost_kg = (df['Aterro_Acumulado'].iloc[-1] - df['Compost_Acumulado'].iloc[-1]) * GWP_CH4
            total_evitado_compost_tco2eq = total_evitado_compost_kg / 1000
            
            # Calcular valor em Reais
            preco_carbono_reais = cotacoes['preco_carbono_reais']
            
            valor_vermi_brl = total_evitado_vermi_tco2eq * preco_carbono_reais
            valor_compost_brl = total_evitado_compost_tco2eq * preco_carbono_reais
            
            # Exibir métricas
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "Vermicompostagem",
                    f"{formatar_br(total_evitado_vermi_tco2eq)} tCO₂eq",
                    f"R$ {formatar_br(valor_vermi_brl)}",
                    delta_color="off"
                )
            
            with col2:
                st.metric(
                    "Compostagem",
                    f"{formatar_br(total_evitado_compost_tco2eq)} tCO₂eq",
                    f"R$ {formatar_br(valor_compost_brl)}",
                    delta_color="off"
                )
            
            # Resumo final
            st.success(f"""
            **🎯 RESUMO FINAL PARA LOTE DE {residuos_kg} kg:**
            
            **Aterro:** Emite **{formatar_br(df['Aterro_Acumulado'].iloc[-1])} kg CH₄** em **{dias_simulacao} dias** ({formatar_br(fracao_emitida*100)}% do potencial total)
            
            **Vermicompostagem:** Emite **{formatar_br(df['Vermi_Acumulado'].iloc[-1])} kg CH₄** em **apenas 50 dias** ({formatar_br((1 - df['Vermi_Acumulado'].iloc[-1]/df['Aterro_Acumulado'].iloc[-1])*100)}% de redução)
            
            **Compostagem:** Emite **{formatar_br(df['Compost_Acumulado'].iloc[-1])} kg CH₄** em **apenas 50 dias** ({formatar_br((1 - df['Compost_Acumulado'].iloc[-1]/df['Aterro_Acumulado'].iloc[-1])*100)}% de redução)
            
            **💰 VALOR FINANCEIRO:** Potencial de **R$ {formatar_br(valor_vermi_brl)}** em créditos de carbono
            """)
    else:
        st.info("💡 Ajuste os parâmetros na barra lateral e clique em 'Calcular Potencial de Metano' para ver os resultados.")

# =============================================================================
# ABA 2: ENTRADA CONTÍNUA (kg/dia) - SEÇÃO ORIGINAL SIMPLIFICADA
# =============================================================================
with tab2:
    # Título da aba 2
    st.header("📈 Análise para Entrada Contínua (kg/dia)")
    st.markdown("""
    **Simulação Completa: Comparação de Emissões em Longo Prazo**
    
    Esta ferramenta projeta os Créditos de Carbono ao calcular as emissões de gases de efeito estufa para dois contextos de gestão de resíduos
    """)
    
    # Seção original de parâmetros
    with st.sidebar:
        st.header("⚙️ Parâmetros de Entrada - Entrada Contínua")
        
        # Entrada principal de resíduos
        residuos_kg_dia = st.slider("Quantidade de resíduos (kg/dia)", 
                                   min_value=10, max_value=1000, value=100, step=10,
                                   help="Quantidade diária de resíduos orgânicos gerados",
                                   key="residuos_cont")
        
        st.subheader("📊 Parâmetros Operacionais")
        
        # Umidade com formatação brasileira
        umidade_valor = st.slider("Umidade do resíduo (%)", 50, 95, 85, 1,
                                 help="Percentual de umidade dos resíduos orgânicos",
                                 key="umidade_cont")
        umidade = umidade_valor / 100.0
        
        # Variáveis operacionais
        massa_exposta_kg = st.slider("Massa exposta na frente de trabalho (kg)", 50, 200, 100, 10,
                                    help="Massa de resíduos exposta diariamente para tratamento",
                                    key="massa_cont")
        h_exposta = st.slider("Horas expostas por dia", 4, 24, 8, 1,
                             help="Horas diárias de exposição dos resíduos",
                             key="horas_cont")
        
        st.subheader("🎯 Configuração de Simulação")
        anos_simulacao = st.slider("Anos de simulação", 1, 50, 20, 1,
                                  help="Período total da simulação em anos",
                                  key="anos_cont")
        
        if st.button("🚀 Executar Simulação", type="primary", key="btn_cont"):
            st.session_state.run_simulation = True

    # Executar simulação quando solicitado
    if st.session_state.get('run_simulation', False):
        with st.spinner('Executando simulação...'):
            # Calcular dias e datas
            dias = anos_simulacao * 365
            data_inicio = datetime.now()
            datas = pd.date_range(start=data_inicio, periods=dias, freq='D')
            
            # Executar modelo base
            params_base = [umidade, T, DOC]

            ch4_aterro_dia, n2o_aterro_dia = calcular_emissoes_aterro(params_base, dias, residuos_kg_dia, massa_exposta_kg, h_exposta)
            ch4_vermi_dia, n2o_vermi_dia = calcular_emissoes_vermi(params_base, dias, residuos_kg_dia)
            
            # Construir DataFrame
            df = pd.DataFrame({
                'Data': datas,
                'CH4_Aterro_kg_dia': ch4_aterro_dia,
                'N2O_Aterro_kg_dia': n2o_aterro_dia,
                'CH4_Vermi_kg_dia': ch4_vermi_dia,
                'N2O_Vermi_kg_dia': n2o_vermi_dia,
            })

            for gas in ['CH4_Aterro', 'N2O_Aterro', 'CH4_Vermi', 'N2O_Vermi']:
                df[f'{gas}_tCO2eq'] = df[f'{gas}_kg_dia'] * (GWP_CH4_20 if 'CH4' in gas else GWP_N2O_20) / 1000

            df['Total_Aterro_tCO2eq_dia'] = df['CH4_Aterro_tCO2eq'] + df['N2O_Aterro_tCO2eq']
            df['Total_Vermi_tCO2eq_dia'] = df['CH4_Vermi_tCO2eq'] + df['N2O_Vermi_tCO2eq']

            df['Total_Aterro_tCO2eq_acum'] = df['Total_Aterro_tCO2eq_dia'].cumsum()
            df['Total_Vermi_tCO2eq_acum'] = df['Total_Vermi_tCO2eq_dia'].cumsum()
            df['Reducao_tCO2eq_acum'] = df['Total_Aterro_tCO2eq_acum'] - df['Total_Vermi_tCO2eq_acum']

            # Resumo anual
            df['Year'] = df['Data'].dt.year
            df_anual = df.groupby('Year').agg({
                'Total_Aterro_tCO2eq_dia': 'sum',
                'Total_Vermi_tCO2eq_dia': 'sum',
            }).reset_index()

            df_anual['Emission reductions (t CO₂eq)'] = df_anual['Total_Aterro_tCO2eq_dia'] - df_anual['Total_Vermi_tCO2eq_dia']
            df_anual['Cumulative reduction (t CO₂eq)'] = df_anual['Emission reductions (t CO₂eq)'].cumsum()

            # =============================================================================
            # EXIBIÇÃO DOS RESULTADOS
            # =============================================================================

            # Obter valores totais
            total_evitado = df['Reducao_tCO2eq_acum'].iloc[-1]
            
            # Calcular valor financeiro
            valor_eur = total_evitado * cotacoes['preco_carbono_eur']
            valor_brl = valor_eur * cotacoes['taxa_cambio']
            
            # Exibir métricas financeiras
            st.subheader("💰 Valor Financeiro das Emissões Evitadas")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Emissões Evitadas",
                    f"{formatar_br(total_evitado)} tCO₂eq",
                    help="Total em toda a simulação"
                )
            with col2:
                st.metric(
                    "Valor em Euros",
                    f"€ {formatar_br(valor_eur)}",
                    help=f"@ €{formatar_br(cotacoes['preco_carbono_eur'])}/tCO₂eq"
                )
            with col3:
                st.metric(
                    "Valor em Reais",
                    f"R$ {formatar_br(valor_brl)}",
                    help=f"@ R${formatar_br(cotacoes['preco_carbono_reais'])}/tCO₂eq"
                )
            
            # Gráfico de redução acumulada
            st.subheader("📉 Redução de Emissões Acumulada")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(df['Data'], df['Total_Aterro_tCO2eq_acum'], 'r-', label='Cenário Base (Aterro)', linewidth=2)
            ax.plot(df['Data'], df['Total_Vermi_tCO2eq_acum'], 'g-', label='Projeto (Vermicompostagem)', linewidth=2)
            ax.fill_between(df['Data'], df['Total_Vermi_tCO2eq_acum'], df['Total_Aterro_tCO2eq_acum'],
                            color='skyblue', alpha=0.5, label='Emissões Evitadas')
            ax.set_title(f'Redução de Emissões em {anos_simulacao} Anos')
            ax.set_xlabel('Ano')
            ax.set_ylabel('tCO₂eq Acumulado')
            ax.legend()
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.yaxis.set_major_formatter(FuncFormatter(br_format))

            st.pyplot(fig)
            
            # Tabela de resultados anuais
            st.subheader("📋 Resultados Anuais")
            
            # Formatar DataFrame para exibição
            df_anual_display = df_anual.copy()
            df_anual_display.columns = ['Ano', 'Emissões Aterro (tCO₂eq)', 'Emissões Vermicompostagem (tCO₂eq)', 
                                       'Redução (tCO₂eq)', 'Redução Acumulada (tCO₂eq)']
            
            for col in df_anual_display.columns[1:]:
                df_anual_display[col] = df_anual_display[col].apply(lambda x: formatar_br(x))
            
            st.dataframe(df_anual_display, use_container_width=True)
            
            # Resumo final
            st.success(f"""
            **📊 RESUMO DA SIMULAÇÃO:**
            
            **Período:** {anos_simulacao} anos ({dias} dias)
            **Resíduos processados:** {formatar_br(residuos_kg_dia)} kg/dia ({formatar_br(residuos_kg_dia * 365 / 1000)} toneladas/ano)
            **Emissões evitadas:** {formatar_br(total_evitado)} tCO₂eq
            **Valor financeiro:** R$ {formatar_br(valor_brl)}
            
            **💰 POTENCIAL ANUAL:** R$ {formatar_br(valor_brl/anos_simulacao)}/ano
            """)
    else:
        st.info("💡 Ajuste os parâmetros na barra lateral e clique em 'Executar Simulação' para ver os resultados.")

# =============================================================================
# ABA 3: POTENCIAL POR CIDADE
# =============================================================================
with tab3:
    st.header("🏙️ Análise de Potencial por Cidade")
    
    st.markdown("""
    **Calcule o potencial de créditos de carbono para cidades brasileiras através do desvio de resíduos orgânicos**
    
    Esta ferramenta estima o valor financeiro que cada cidade poderia gerar ao desviar seus resíduos orgânicos
    de aterros sanitários para sistemas de compostagem ou vermicompostagem.
    """)
    
    # Container para seleção de cidades
    with st.container():
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Seleção de cidades
            cidades_selecionadas = st.multiselect(
                "Selecione as cidades para análise:",
                options=list(CIDADES_BRASIL.keys()),
                default=["São Paulo - SP", "Rio de Janeiro - RJ", "Brasília - DF"],
                help="Selecione uma ou mais cidades para calcular o potencial"
            )
        
        with col2:
            # Período de análise
            dias_simulacao = st.slider(
                "Período (dias):",
                min_value=30,
                max_value=1095,
                value=365,
                step=30,
                help="Período para cálculo do potencial"
            )
    
    # Botão para calcular
    if st.button("📊 Calcular Potencial das Cidades", type="primary", use_container_width=True, key="btn_cidades"):
        if not cidades_selecionadas:
            st.warning("⚠️ Selecione pelo menos uma cidade para análise.")
        else:
            with st.spinner("Calculando potencial para as cidades selecionadas..."):
                # Lista para armazenar resultados
                resultados_cidades = []
                
                # Calcular para cada cidade selecionada
                for cidade in cidades_selecionadas:
                    resultado = calcular_potencial_cidade(
                        cidade, 
                        CIDADES_BRASIL[cidade], 
                        cotacoes['preco_carbono_eur'],
                        cotacoes['taxa_cambio'],
                        dias_simulacao
                    )
                    resultados_cidades.append(resultado)
                
                # Criar DataFrame com resultados
                df_resultados = pd.DataFrame(resultados_cidades)
                
                # =============================================================================
                # EXIBIR RESULTADOS
                # =============================================================================
                
                st.success(f"✅ Análise concluída para {len(resultados_cidades)} cidades!")
                
                # Métricas agregadas
                total_populacao = df_resultados['populacao'].sum()
                total_residuos_ano = df_resultados['residuos_organicos_ano_ton'].sum()
                total_potencial = df_resultados['reducao_vermi_tco2eq'].sum()
                total_valor_brl = df_resultados['valor_vermi_brl'].sum()
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "População Total",
                        f"{formatar_br(total_populacao/1e6)} mi",
                        help="População das cidades selecionadas"
                    )
                
                with col2:
                    st.metric(
                        "Resíduos Orgânicos/Ano",
                        f"{formatar_br(total_residuos_ano)} t",
                        help="Toneladas de resíduos orgânicos por ano"
                    )
                
                with col3:
                    st.metric(
                        "Potencial de Créditos",
                        f"{formatar_br(total_potencial)} tCO₂eq",
                        help="Créditos de carbono anuais"
                    )
                
                with col4:
                    st.metric(
                        "Valor Financeiro (R$)",
                        f"R$ {formatar_br(total_valor_brl)}",
                        help=f"Valor anual @ €{formatar_br(cotacoes['preco_carbono_eur'])}/tCO₂eq"
                    )
                
                # =============================================================================
                # TABELA DETALHADA
                # =============================================================================
                
                st.subheader("📋 Tabela Detalhada por Cidade")
                
                # Preparar DataFrame para exibição
                df_exibir = df_resultados.copy()
                df_exibir = df_exibir[[
                    'cidade', 'regiao', 'populacao', 'residuos_organicos_ano_ton',
                    'reducao_vermi_tco2eq', 'valor_vermi_brl', 'valor_por_ton_residuo_brl'
                ]]
                
                # Renomear colunas
                df_exibir.columns = [
                    'Cidade', 'Região', 'População', 'Resíduos Orgânicos/Ano (t)',
                    'Créditos Potenciais (tCO₂eq)', 'Valor Anual (R$)', 'Valor por t Resíduo (R$)'
                ]
                
                # Formatar números
                for col in ['População', 'Resíduos Orgânicos/Ano (t)', 'Créditos Potenciais (tCO₂eq)',
                           'Valor Anual (R$)', 'Valor por t Resíduo (R$)']:
                    if col == 'População':
                        df_exibir[col] = df_exibir[col].apply(lambda x: formatar_br(x/1000) + ' mil')
                    else:
                        df_exibir[col] = df_exibir[col].apply(lambda x: formatar_br(x))
                
                # Exibir tabela
                st.dataframe(df_exibir, use_container_width=True, height=400)
                
                # =============================================================================
                # GRÁFICOS COMPARATIVOS
                # =============================================================================
                
                st.subheader("📊 Visualizações Comparativas")
                
                tab_graf1, tab_graf2 = st.tabs(["Valor Financeiro", "Potencial de Créditos"])
                
                with tab_graf1:
                    fig, ax = plt.subplots(figsize=(12, 6))
                    bars = ax.bar(df_resultados['cidade'], df_resultados['valor_vermi_brl'] / 1e6, color='green')
                    ax.set_title('Valor Financeiro Anual de Créditos de Carbono (Milhões de R$)', fontsize=14, fontweight='bold')
                    ax.set_xlabel('Cidade')
                    ax.set_ylabel('Valor (Milhões de R$)')
                    ax.tick_params(axis='x', rotation=45)
                    
                    # Adicionar valores nas barras
                    for bar in bars:
                        height = bar.get_height()
                        ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                                f'R$ {formatar_br(height)}M',
                                ha='center', va='bottom', fontsize=9)
                    
                    plt.tight_layout()
                    st.pyplot(fig)
                
                with tab_graf2:
                    fig, ax = plt.subplots(figsize=(12, 6))
                    bars = ax.bar(df_resultados['cidade'], df_resultados['reducao_vermi_tco2eq'], color='blue')
                    ax.set_title('Potencial de Créditos de Carbono (tCO₂eq/ano)', fontsize=14, fontweight='bold')
                    ax.set_xlabel('Cidade')
                    ax.set_ylabel('tCO₂eq/ano')
                    ax.tick_params(axis='x', rotation=45)
                    
                    for bar in bars:
                        height = bar.get_height()
                        ax.text(bar.get_x() + bar.get_width()/2., height + 50,
                                formatar_br(height),
                                ha='center', va='bottom', fontsize=9)
                    
                    plt.tight_layout()
                    st.pyplot(fig)
                
                # =============================================================================
                # ANÁLISE POR REGIÃO
                # =============================================================================
                
                st.subheader("🌍 Análise Agregada por Região")
                
                # Agrupar por região
                df_regiao = df_resultados.groupby('regiao').agg({
                    'populacao': 'sum',
                    'residuos_organicos_ano_ton': 'sum',
                    'reducao_vermi_tco2eq': 'sum',
                    'valor_vermi_brl': 'sum'
                }).reset_index()
                
                # Calcular métricas por região
                df_regiao['valor_por_hab'] = df_regiao['valor_vermi_brl'] / df_regiao['populacao']
                df_regiao['creditos_por_hab'] = df_regiao['reducao_vermi_tco2eq'] / df_regiao['populacao']
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig, ax = plt.subplots(figsize=(10, 6))
                    ax.pie(df_regiao['valor_vermi_brl'], labels=df_regiao['regiao'], autopct='%1.1f%%',
                          colors=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57'])
                    ax.set_title('Distribuição do Valor por Região', fontsize=14, fontweight='bold')
                    st.pyplot(fig)
                
                with col2:
                    fig, ax = plt.subplots(figsize=(10, 6))
                    x = np.arange(len(df_regiao))
                    width = 0.35
                    
                    ax.bar(x - width/2, df_regiao['valor_por_hab'], width, label='R$/hab', color='green')
                    ax.bar(x + width/2, df_regiao['creditos_por_hab'], width, label='tCO₂eq/hab', color='blue')
                    
                    ax.set_xlabel('Região')
                    ax.set_title('Métricas por Habitante', fontsize=14, fontweight='bold')
                    ax.set_xticks(x)
                    ax.set_xticklabels(df_regiao['regiao'])
                    ax.legend()
                    ax.grid(axis='y', alpha=0.3)
                    
                    plt.tight_layout()
                    st.pyplot(fig)
                
                # =============================================================================
                # RESUMO EXECUTIVO
                # =============================================================================
                
                with st.expander("📋 RESUMO EXECUTIVO - POTENCIAL DE MERCADO", expanded=True):
                    st.markdown(f"""
                    ### 🌟 **RESUMO DO POTENCIAL DE CRÉDITOS DE CARBONO**
                    
                    **📊 METRÍCAS CONSIDERANDO {len(resultados_cidades)} CIDADES SELECIONADAS:**
                    
                    | Indicador | Valor Total |
                    |-----------|-------------|
                    | **População atendida** | {formatar_br(total_populacao/1e6)} milhões de habitantes |
                    | **Resíduos orgânicos/ano** | {formatar_br(total_residuos_ano)} toneladas |
                    | **Créditos de carbono potenciais** | {formatar_br(total_potencial)} tCO₂eq/ano |
                    | **Valor financeiro anual** | **R$ {formatar_br(total_valor_brl)}** |
                    
                    **💰 VALORIZAÇÃO POR TONELADA DE RESÍDUO:**
                    - **Média:** R$ {formatar_br(df_resultados['valor_por_ton_residuo_brl'].mean())} por tonelada
                    - **Mínimo:** R$ {formatar_br(df_resultados['valor_por_ton_residuo_brl'].min())}
                    - **Máximo:** R$ {formatar_br(df_resultados['valor_por_ton_residuo_brl'].max())}
                    
                    **🏆 CIDADES COM MAIOR POTENCIAL:**
                    """)
                    
                    # Top 3 cidades por valor
                    top3 = df_resultados.nlargest(3, 'valor_vermi_brl')
                    for idx, row in top3.iterrows():
                        st.markdown(f"- **{row['cidade']}:** R$ {formatar_br(row['valor_vermi_brl'])}/ano")
                    
                    st.markdown(f"""
                    **📈 CONSIDERAÇÕES DE MERCADO:**
                    - **Preço atual do carbono:** € {formatar_br(cotacoes['preco_carbono_eur'])}/tCO₂eq (R$ {formatar_br(cotacoes['preco_carbono_reais'])})
                    - **Taxa de câmbio:** 1 EUR = R$ {formatar_br(cotacoes['taxa_cambio'])}
                    - **Metodologia:** IPCC 2006 + Yang et al. (2017) - Vermicompostagem
                    - **Período de análise:** {dias_simulacao} dias
                    - **GWP CH₄:** 27.9 kg CO₂eq/kg CH₄
                    
                    **💡 RECOMENDAÇÕES:**
                    1. **Priorizar cidades com maior geração de resíduos orgânicos**
                    2. **Implementar programas municipais de compostagem**
                    3. **Capturar créditos de carbono através do Mecanismo de Desenvolvimento Limpo**
                    4. **Considerar parcerias público-privadas para investimento em infraestrutura**
                    """)
                
                # =============================================================================
                # DOWNLOAD DOS RESULTADOS
                # =============================================================================
                
                st.subheader("💾 Download dos Resultados")
                
                # Preparar DataFrame para download
                df_download = df_resultados.copy()
                
                # Converter para Excel
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_download.to_excel(writer, sheet_name='Resultados_Cidades', index=False)
                    df_regiao.to_excel(writer, sheet_name='Agregado_Região', index=False)
                
                output.seek(0)
                
                st.download_button(
                    label="📥 Baixar Resultados Completos (Excel)",
                    data=output,
                    file_name=f"potencial_creditos_carbono_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
    else:
        st.info("💡 Selecione as cidades e clique em 'Calcular Potencial das Cidades' para ver os resultados.")

# =============================================================================
# RODAPÉ
# =============================================================================

st.markdown("---")
st.markdown("""
**📚 Referências Científicas:**

- **Cenário de Baseline (Aterro Sanitário):**
  - Metano: IPCC (2006), UNFCCC (2016) e Wang et al. (2023)
  - Óxido Nitroso: Wang et al. (2017)

- **Cenário de Projeto (Compostagem/Vermicompostagem):**
  - Metano e Óxido Nitroso: Yang et al. (2017)

**🌍 Fontes de Dados:**
- Preço do carbono: Investing.com (mercado regulado da UE)
- Câmbio EUR/BRL: BCB e AwesomeAPI
- Dados populacionais: IBGE (2023)
- Geração de resíduos: ABRELPE (2023)

**🔄 Atualizações:**
- Cotações atualizadas em tempo real
- Dados recalculados automaticamente
""")
