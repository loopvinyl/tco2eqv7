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
# FUNÇÕES DE CÁLCULO DE POTENCIAL DE METANO
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
# DADOS DAS CIDADES BRASILEIRAS
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
# FUNÇÃO PARA CALCULAR POTENCIAL POR CIDADE
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
    
    # Calcular potencial de metano na compostagem
    dias_compost = min(50, dias_simulacao)
    emissoes_compost_temp, total_compost = calcular_emissoes_compostagem_lote(
        residuos_organicos_ano, umidade, dias_compost
    )
    emissoes_compost = np.zeros(dias_simulacao)
    emissoes_compost[:dias_compost] = emissoes_compost_temp
    
    # Calcular totais acumulados
    total_aterro_emitido = emissoes_aterro.sum()
    total_vermi_emitido = emissoes_vermi.sum()
    total_compost_emitido = emissoes_compost.sum()
    
    # Calcular reduções
    reducao_vermi = total_aterro_emitido - total_vermi_emitido
    reducao_compost = total_aterro_emitido - total_compost_emitido
    
    # Converter para CO₂eq (GWP CH₄ = 27.9)
    GWP_CH4 = 27.9
    
    reducao_vermi_tco2eq = reducao_vermi * GWP_CH4 / 1000
    reducao_compost_tco2eq = reducao_compost * GWP_CH4 / 1000
    
    # Calcular valor financeiro
    valor_vermi_eur = reducao_vermi_tco2eq * preco_carbono_eur
    valor_vermi_brl = valor_vermi_eur * taxa_cambio
    
    valor_compost_eur = reducao_compost_tco2eq * preco_carbono_eur
    valor_compost_brl = valor_compost_eur * taxa_cambio
    
    return {
        "cidade": cidade,
        "regiao": dados_cidade["regiao"],
        "populacao": dados_cidade["populacao"],
        "residuos_organicos_dia_ton": residuos_organicos_dia / 1000,
        "residuos_organicos_ano_ton": residuos_organicos_ano / 1000,
        "total_aterro_emitido_kg": total_aterro_emitido,
        "total_vermi_emitido_kg": total_vermi_emitido,
        "total_compost_emitido_kg": total_compost_emitido,
        "reducao_vermi_tco2eq": reducao_vermi_tco2eq,
        "reducao_compost_tco2eq": reducao_compost_tco2eq,
        "valor_vermi_eur": valor_vermi_eur,
        "valor_vermi_brl": valor_vermi_brl,
        "valor_compost_eur": valor_compost_eur,
        "valor_compost_brl": valor_compost_brl,
        "valor_por_ton_residuo_eur": valor_vermi_eur / (residuos_organicos_ano / 1000),
        "valor_por_ton_residuo_brl": valor_vermi_brl / (residuos_organicos_ano / 1000)
    }

# =============================================================================
# INTERFACE PRINCIPAL
# =============================================================================

# Título do aplicativo
st.title("🌱 SINISA - Simulador de Potencial de Metano e Créditos de Carbono")
st.markdown("""
**Sistema Integrado de Análise de Potencial de Créditos de Carbono para Gestão de Resíduos Orgânicos**

Este aplicativo calcula o potencial de geração de créditos de carbono através do desvio de resíduos orgânicos
de aterros sanitários para processos de compostagem e vermicompostagem.
""")

# =============================================================================
# SEÇÃO DE COTAÇÃO EM TEMPO REAL
# =============================================================================

st.header("💰 Cotações em Tempo Real")

# Inicializar session state para cotações
if 'cotacoes' not in st.session_state:
    with st.spinner("🔄 Obtendo cotações em tempo real..."):
        st.session_state.cotacoes = obter_cotacoes_tempo_real()
        st.session_state.ultima_atualizacao = datetime.now()

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

# Informações adicionais
st.caption(f"🕒 Última atualização: {st.session_state.ultima_atualizacao.strftime('%d/%m/%Y %H:%M:%S')}")

# =============================================================================
# SEÇÃO DE ANÁLISE POR CIDADE
# =============================================================================

st.header("🏙️ Análise de Potencial por Cidade")

st.markdown("""
Selecione uma ou mais cidades para analisar o potencial de créditos de carbono através do desvio
de resíduos orgânicos de aterros para compostagem/vermicompostagem.
""")

# Seleção de cidades
cidades_selecionadas = st.multiselect(
    "Selecione as cidades para análise:",
    options=list(CIDADES_BRASIL.keys()),
    default=["São Paulo - SP", "Rio de Janeiro - RJ", "Brasília - DF"]
)

# Parâmetros de simulação
col1, col2 = st.columns(2)

with col1:
    dias_simulacao = st.slider(
        "Período de análise (dias):",
        min_value=30,
        max_value=1095,  # 3 anos
        value=365,
        step=30,
        help="Período para cálculo do potencial de metano"
    )

with col2:
    umidade_padrao = st.slider(
        "Umidade dos resíduos (%):",
        min_value=50,
        max_value=95,
        value=85,
        step=1
    )

# Botão para calcular
if st.button("📊 Calcular Potencial das Cidades", type="primary", use_container_width=True):
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
            total_potencial_vermi = df_resultados['reducao_vermi_tco2eq'].sum()
            total_valor_vermi_brl = df_resultados['valor_vermi_brl'].sum()
            
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
                    f"{formatar_br(total_potencial_vermi)} tCO₂eq",
                    help="Créditos de carbono anuais"
                )
            
            with col4:
                st.metric(
                    "Valor Financeiro (R$)",
                    f"R$ {formatar_br(total_valor_vermi_brl)}",
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
            
            tab1, tab2, tab3 = st.tabs(["Valor Financeiro", "Potencial de Créditos", "Eficiência por Tonelada"])
            
            with tab1:
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
            
            with tab2:
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
            
            with tab3:
                fig, ax = plt.subplots(figsize=(12, 6))
                bars = ax.bar(df_resultados['cidade'], df_resultados['valor_por_ton_residuo_brl'], color='orange')
                ax.set_title('Valor Gerado por Tonelada de Resíduo Orgânico (R$/t)', fontsize=14, fontweight='bold')
                ax.set_xlabel('Cidade')
                ax.set_ylabel('R$ por tonelada')
                ax.tick_params(axis='x', rotation=45)
                
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                            f'R$ {formatar_br(height)}',
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
                | **Créditos de carbono potenciais** | {formatar_br(total_potencial_vermi)} tCO₂eq/ano |
                | **Valor financeiro anual** | **R$ {formatar_br(total_valor_vermi_brl)}** |
                
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
                **🌍 DISTRIBUIÇÃO REGIONAL:**
                """)
                
                for idx, row in df_regiao.iterrows():
                    st.markdown(f"- **{row['regiao']}:** R$ {formatar_br(row['valor_vermi_brl'])} ({formatar_br(row['valor_por_hab'])} por habitante)")
                
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
                
                **⚠️ LIMITAÇÕES:**
                - Valores baseados em dados médios e parâmetros padrão
                - Não considera custos de implantação e operação
                - Preço do carbono sujeito a variações de mercado
                - Depende da implementação efetiva dos sistemas de compostagem
                """)

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
