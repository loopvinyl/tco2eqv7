import streamlit as st
import pandas as pd
import numpy as np
import unicodedata
import requests
from bs4 import BeautifulSoup
import re
from scipy.signal import fftconvolve
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter

# =========================================================
# Configuração da página
# =========================================================
st.set_page_config(
    page_title="Potencial de Compostagem de RSU",
    layout="wide"
)

st.title("🌱 Potencial de Compostagem e Vermicompostagem por Município")
st.markdown("""
Este aplicativo interpreta os **tipos de coleta executada** informados pelos municípios
e avalia o **potencial técnico para compostagem e vermicompostagem**
de resíduos sólidos urbanos.
""")

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

# Função para formatar números no padrão brasileiro
def formatar_br(numero):
    """
    Formata números no padrão brasileiro: 1.234,56
    """
    if pd.isna(numero) or numero is None:
        return "N/A"
    
    # Arredonda para 2 casas decimais
    numero = round(numero, 2)
    
    # Formata como string e substitui o ponto pela vírgula
    return f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Função de formatação para os gráficos (padrão brasileiro)
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

# =============================================================================
# FUNÇÕES AUXILIARES ORIGINAIS
# =============================================================================

def formatar_numero_br(valor, casas_decimais=2):
    if pd.isna(valor) or valor is None:
        return "Não informado"
    try:
        num = float(valor)
        formato = f"{{:,.{casas_decimais}f}}".format(num)
        partes = formato.split(".")
        milhar = partes[0].replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{milhar},{partes[1]}"
    except:
        return "Não informado"

def formatar_massa_br(valor):
    if pd.isna(valor) or valor is None:
        return "Não informado"
    return f"{formatar_numero_br(valor)} t"

def normalizar_texto(txt):
    if pd.isna(txt):
        return ""
    txt = unicodedata.normalize("NFKD", str(txt))
    txt = txt.encode("ASCII", "ignore").decode("utf-8")
    return txt.upper().strip()

def classificar_tipo_aterro(mcf):
    """
    Classifica o tipo de aterro baseado no valor do MCF.
    """
    if mcf >= 0.95:
        return "Aterro Sanitário Gerenciado"
    elif mcf >= 0.6:
        return "Aterro Sanitário Não Gerenciado"
    elif mcf > 0:
        return "Aterro Controlado/Lixão"
    else:
        return "Não Aterro"

# =========================================================
# PARÂMETROS PARA CÁLCULO COM DECAIMENTO (DO SCRIPT ORIGINAL)
# =========================================================

# Parâmetros fixos (IPCC 2006)
T = 25  # Temperatura média (ºC)
DOC = 0.15  # Carbono orgânico degradável (fração)
MCF = 1  # Fator de correção de metano (será ajustado por destino)
F = 0.5  # Fração de metano no biogás
OX = 0.1  # Fator de oxidação
Ri = 0.0  # Metano recuperado

# Constante de decaimento (fixa como no script anexo)
k_ano = 0.06  # Constante de decaimento anual

# GWP (IPCC AR6)
GWP_CH4_20 = 79.7  # Para comparabilidade com script original
GWP_N2O_20 = 273   # Para comparabilidade com script original

# Período de Simulação (20 anos para projeção de créditos)
ANOS_PROJECAO_CREDITOS = 20
DIAS_PROJECAO = ANOS_PROJECAO_CREDITOS * 365

# =========================================================
# FUNÇÕES DE CÁLCULO COM ENTRADA CONTÍNUA E DECAIMENTO ACUMULADO
# =========================================================

def calcular_emissoes_aterro_entrada_continua(massa_kg_dia, mcf, dias_simulacao=DIAS_PROJECAO):
    """
    Calcula emissões de CH4 do aterro com entrada contínua diária e decaimento acumulado
    Adaptado do script original tco2e - modelo de entrada contínua
    """
    # Parâmetros IPCC 2006
    DOCf = 0.0147 * T + 0.28  # Decomposable fraction of DOC
    
    # Calcular potencial diário de CH4
    potencial_CH4_por_kg = DOC * DOCf * mcf * F * (16/12) * (1 - Ri) * (1 - OX)
    potencial_CH4_diario_kg = massa_kg_dia * potencial_CH4_por_kg
    
    # Kernel de decaimento exponencial (igual ao script original)
    t = np.arange(1, dias_simulacao + 1, dtype=float)
    kernel_ch4 = np.exp(-k_ano * (t - 1) / 365.0) - np.exp(-k_ano * t / 365.0)
    
    # Entradas diárias CONSTANTES (massa_kg_dia todos os dias)
    # Isso simula entrada contínua ao longo dos anos
    entradas_diarias = np.ones(dias_simulacao, dtype=float) * potencial_CH4_diario_kg
    
    # Convolução para obter emissões com decaimento ACUMULADO
    # Cada entrada diária contribui com emissões que decaem ao longo do tempo
    emissoes_CH4 = fftconvolve(entradas_diarias, kernel_ch4, mode='full')[:dias_simulacao]
    
    return emissoes_CH4  # kg CH4 por dia

def calcular_ch4_total_aterro_20anos(massa_t_ano, mcf):
    """
    Calcula o CH4 total gerado no aterro ao longo de 20 anos considerando entrada contínua e decaimento
    Método IDÊNTICO ao do script tco2e original
    """
    if massa_t_ano <= 0 or mcf <= 0:
        return 0.0
    
    # Converter massa anual para diária (kg/dia)
    # Supondo que a massa anual de 2023 se repete todos os anos
    massa_kg_dia = (massa_t_ano * 1000) / 365
    
    # Calcular emissões diárias com entrada contínua
    emissoes_ch4_aterro_dia = calcular_emissoes_aterro_entrada_continua(massa_kg_dia, mcf, DIAS_PROJECAO)
    
    # Somar emissões diárias para obter total
    total_ch4_aterro_kg = emissoes_ch4_aterro_dia.sum()
    total_ch4_aterro_t = total_ch4_aterro_kg / 1000
    
    return total_ch4_aterro_t

def calcular_emissoes_n2o_entrada_continua(massa_kg_dia, dias_simulacao=DIAS_PROJECAO):
    """
    Calcula emissões de N2O do aterro com entrada contínua
    Adaptado do script original tco2e
    """
    # Perfil temporal N2O (Wang et al. 2017) - para decomposição gradual
    PERFIL_N2O = {1: 0.10, 2: 0.30, 3: 0.40, 4: 0.15, 5: 0.05}
    
    # Valores de referência (E_aberto e E_fechado do script original)
    E_aberto = 1.91  # mg N2O-N/kg/dia para aterro aberto
    E_fechado = 2.15  # mg N2O-N/kg/dia para aterro fechado
    
    # Fator de exposição (assumindo 50% aberto, 50% fechado como padrão)
    f_aberto = 0.5  # Pode ser ajustado se necessário
    
    E_medio = f_aberto * E_aberto + (1 - f_aberto) * E_fechado
    
    # Converter para kg N2O/dia
    emissao_diaria_N2O_kg = (E_medio * (44/28) / 1_000_000) * massa_kg_dia
    
    # Kernel N2O (perfil de 5 dias)
    kernel_n2o = np.array([PERFIL_N2O.get(d, 0) for d in range(1, 6)], dtype=float)
    
    # Entradas diárias CONSTANTES
    entradas_diarias = np.full(dias_simulacao, emissao_diaria_N2O_kg)
    
    # Convolução para distribuir emissões ACUMULADAS
    emissoes_N2O = fftconvolve(entradas_diarias, kernel_n2o, mode='full')[:dias_simulacao]
    
    return emissoes_N2O  # kg N2O por dia

def calcular_emissoes_compostagem_entrada_continua(massa_kg_dia, dias_simulacao=DIAS_PROJECAO):
    """
    Calcula emissões de CH4 da compostagem com entrada contínua
    Adaptado do script original tco2e
    """
    # Fator de emissão para compostagem termofílica (Yang et al. 2017)
    TOC_YANG = 0.436  # Fração de carbono orgânico total
    CH4_C_FRAC_THERMO = 0.006  # Fração do TOC emitida como CH4-C
    
    # Perfil temporal de 50 dias (Yang et al. 2017)
    PERFIL_CH4_THERMO = np.array([
        0.01, 0.02, 0.03, 0.05, 0.08,  # Dias 1-5
        0.12, 0.15, 0.18, 0.20, 0.18,  # Dias 6-10
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
    
    # Fator de conversão C para CH4
    fator_C_para_CH4 = 16/12
    
    # Emissão total por lote (por dia de entrada)
    ch4_por_lote_kg = massa_kg_dia * TOC_YANG * CH4_C_FRAC_THERMO * fator_C_para_CH4
    
    # Kernel para compostagem (50 dias)
    kernel_compost = PERFIL_CH4_THERMO * ch4_por_lote_kg
    
    # Entradas diárias CONSTANTES
    entradas_diarias = np.ones(dias_simulacao, dtype=float)
    
    # Convolução para distribuir emissões ACUMULADAS
    emissoes_CH4 = fftconvolve(entradas_diarias, kernel_compost, mode='full')[:dias_simulacao]
    
    return emissoes_CH4  # kg CH4 per day

def calcular_emissoes_vermicompostagem_entrada_continua(massa_kg_dia, dias_simulacao=DIAS_PROJECAO):
    """
    Calcula emissões de CH4 da vermicompostagem com entrada contínua
    Adaptado do script original tco2e
    """
    # Fator de emissão para vermicompostagem (Yang et al. 2017)
    TOC_YANG = 0.436  # Fração de carbono orgânico total
    CH4_C_FRAC_YANG = 0.13 / 100  # Fração do TOC emitida como CH4-C
    
    # Perfil temporal de 50 dias (Yang et al. 2017)
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
    
    # Fator de conversão C para CH4
    fator_C_para_CH4 = 16/12
    
    # Emissão total per lote (per day of entry)
    ch4_por_lote_kg = massa_kg_dia * TOC_YANG * CH4_C_FRAC_YANG * fator_C_para_CH4
    
    # Kernel para vermicompostagem (50 dias)
    kernel_vermi = PERFIL_CH4_VERMI * ch4_por_lote_kg
    
    # Entradas diárias CONSTANTES
    entradas_diarias = np.ones(dias_simulacao, dtype=float)
    
    # Convolução para distribuir emissões ACUMULADAS
    emissoes_CH4 = fftconvolve(entradas_diarias, kernel_vermi, mode='full')[:dias_simulacao]
    
    return emissoes_CH4  # kg CH4 per day

def calcular_emissoes_totais_entrada_continua(massa_t_ano, mcf):
    """
    Calcula emissões totais ao longo de 20 anos considerando ENTRADA CONTÍNUA ANUAL
    (mesma massa de 2023 a cada ano) e decaimento acumulado
    """
    # Converter massa anual para diária (kg/dia)
    # Supondo que a massa anual de 2023 se repete todos os anos
    massa_kg_dia = (massa_t_ano * 1000) / 365
    
    # Calcular emissões diárias com entrada contínua
    emissoes_ch4_aterro_dia = calcular_emissoes_aterro_entrada_continua(massa_kg_dia, mcf, DIAS_PROJECAO)
    emissoes_n2o_aterro_dia = calcular_emissoes_n2o_entrada_continua(massa_kg_dia, DIAS_PROJECAO)
    
    # Calcular emissões de tratamento biológico com entrada contínua
    emissoes_ch4_compostagem_dia = calcular_emissoes_compostagem_entrada_continua(massa_kg_dia, DIAS_PROJECAO)
    emissoes_ch4_vermicompostagem_dia = calcular_emissoes_vermicompostagem_entrada_continua(massa_kg_dia, DIAS_PROJECAO)
    
    # Somar emissões diárias para obter totais
    total_ch4_aterro_kg = emissoes_ch4_aterro_dia.sum()
    total_n2o_aterro_kg = emissoes_n2o_aterro_dia.sum()
    
    total_ch4_compostagem_kg = emissoes_ch4_compostagem_dia.sum()
    total_ch4_vermicompostagem_kg = emissoes_ch4_vermicompostagem_dia.sum()
    
    # Converter para toneladas
    total_ch4_aterro_t = total_ch4_aterro_kg / 1000
    total_n2o_aterro_t = total_n2o_aterro_kg / 1000
    
    total_ch4_compostagem_t = total_ch4_compostagem_kg / 1000
    total_ch4_vermicompostagem_t = total_ch4_vermicompostagem_kg / 1000
    
    # Calcular CO₂ equivalente (usando GWP de 20 anos do script original)
    co2eq_aterro = (total_ch4_aterro_t * GWP_CH4_20) + (total_n2o_aterro_t * GWP_N2O_20)
    co2eq_compostagem = total_ch4_compostagem_t * GWP_CH4_20
    co2eq_vermicompostagem = total_ch4_vermicompostagem_t * GWP_CH4_20
    
    # Emissões evitadas (diferença)
    co2eq_evitado_compostagem = co2eq_aterro - co2eq_compostagem
    co2eq_evitado_vermicompostagem = co2eq_aterro - co2eq_vermicompostagem
    
    return {
        'co2eq_aterro_total': co2eq_aterro,
        'co2eq_evitado_compostagem': co2eq_evitado_compostagem,
        'co2eq_evitado_vermicompostagem': co2eq_evitado_vermicompostagem,
        'co2eq_evitado_medio_anual_compostagem': co2eq_evitado_compostagem / ANOS_PROJECAO_CREDITOS,
        'co2eq_evitado_medio_anual_vermicompostagem': co2eq_evitado_vermicompostagem / ANOS_PROJECAO_CREDITOS,
        'ch4_aterro_total': total_ch4_aterro_t,  # CH4 total em toneladas (20 anos)
        'massa_anual_considerada': massa_t_ano,
        'massa_total_20_anos': massa_t_ano * ANOS_PROJECAO_CREDITOS
    }

def calcular_emissoes_diarias_detalhadas(massa_t_ano, mcf):
    """
    Calcula emissões diárias detalhadas para criar gráficos
    Retorna DataFrame com datas e emissões diárias em tCO₂eq
    """
    # Converter massa anual para diária (kg/dia)
    massa_kg_dia = (massa_t_ano * 1000) / 365
    
    # Calcular emissões diárias com entrada contínua
    emissoes_ch4_aterro_dia = calcular_emissoes_aterro_entrada_continua(massa_kg_dia, mcf, DIAS_PROJECAO)
    emissoes_n2o_aterro_dia = calcular_emissoes_n2o_entrada_continua(massa_kg_dia, DIAS_PROJECAO)
    
    # Calcular emissões de tratamento biológico com entrada contínua
    emissoes_ch4_compostagem_dia = calcular_emissoes_compostagem_entrada_continua(massa_kg_dia, DIAS_PROJECAO)
    emissoes_ch4_vermicompostagem_dia = calcular_emissoes_vermicompostagem_entrada_continua(massa_kg_dia, DIAS_PROJECAO)
    
    # Converter para tCO₂eq diário
    emissoes_aterro_tco2eq_dia = (emissoes_ch4_aterro_dia * GWP_CH4_20 + emissoes_n2o_aterro_dia * GWP_N2O_20) / 1000
    emissoes_compostagem_tco2eq_dia = (emissoes_ch4_compostagem_dia * GWP_CH4_20) / 1000
    emissoes_vermicompostagem_tco2eq_dia = (emissoes_ch4_vermicompostagem_dia * GWP_CH4_20) / 1000
    
    # Criar datas para 20 anos
    data_inicio = datetime(2024, 1, 1)
    datas = [data_inicio + timedelta(days=i) for i in range(DIAS_PROJECAO)]
    
    # Criar DataFrame
    df = pd.DataFrame({
        'Data': datas,
        'Emissoes_Aterro_tCO2eq_dia': emissoes_aterro_tco2eq_dia,
        'Emissoes_Compostagem_tCO2eq_dia': emissoes_compostagem_tco2eq_dia,
        'Emissoes_Vermicompostagem_tCO2eq_dia': emissoes_vermicompostagem_tCO2eq_dia
    })
    
    # Calcular acumuladas
    df['Total_Aterro_tCO2eq_acum'] = df['Emissoes_Aterro_tCO2eq_dia'].cumsum()
    df['Total_Compostagem_tCO2eq_acum'] = df['Emissoes_Compostagem_tCO2eq_dia'].cumsum()
    df['Total_Vermicompostagem_tCO2eq_acum'] = df['Emissoes_Vermicompostagem_tCO2eq_dia'].cumsum()
    
    # Calcular emissões evitadas acumuladas
    df['Reducao_Compostagem_tCO2eq_acum'] = df['Total_Aterro_tCO2eq_acum'] - df['Total_Compostagem_tCO2eq_acum']
    df['Reducao_Vermicompostagem_tCO2eq_acum'] = df['Total_Aterro_tCO2eq_acum'] - df['Total_Vermicompostagem_tCO2eq_acum']
    
    return df

# =========================================================
# Função para determinar MCF baseado no tipo de destino
# =========================================================
def determinar_mcf_por_destino(destino):
    """
    Determina o Methane Correction Factor (MCF) baseado no tipo de destino.
    Baseado no IPCC 2006 e realidade brasileira.
    """
    if pd.isna(destino):
        return 0.0
    
    destino_norm = normalizar_texto(destino)
    
    # Mapeamento de destinos para MCF
    if "ATERRO SANITARIO" in destino_norm:
        # Verificar se é realmente gerenciado
        if "GERENCIADO" in destino_norm or "COLETA GAS" in destino_norm or "COLETA DE GAS" in destino_norm:
            return 1.0  # Aterro sanitário gerenciado com coleta de gás
        else:
            return 0.8  # Aterro sanitário não gerenciado (mais comum no Brasil)
    
    elif "ATERRO CONTROLADO" in destino_norm:
        return 0.4  # Aterro controlado
    
    elif "LIXAO" in destino_norm or "VAZADOURO" in destino_norm or "DESCARGA DIRETA" in destino_norm:
        return 0.4  # Lixão (open dump)
    
    elif "COMPOSTAGEM" in destino_norm or "VERMICOMPOSTAGEM" in destino_norm:
        return 0.0  # Não aplicável - tratamento biológico
    
    elif "RECICLAGEM" in destino_norm or "TRIAGEM" in destino_norm:
        return 0.0  # Não aplicável - reciclagem
    
    elif "INCINERACAO" in destino_norm or "QUEIMA" in destino_norm:
        return 0.0  # Não aplicável - incineração
    
    elif "OUTRO" in destino_norm or "NAO INFORMADO" in destino_norm or "NAO SE APLICA" in destino_norm:
        return 0.0  # Não aplicável
    
    else:
        # Para destinos não classificados, assumir como não aterro
        return 0.0

# =========================================================
# Carga do Excel
# =========================================================
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/loopvinyl/tco2eqv7/main/rsuBrasil.xlsx"
    df = pd.read_excel(
        url,
        sheet_name="Manejo_Coleta_e_Destinação",
        header=13
    )
    df = df.dropna(how="all")
    df.columns = [str(col).strip() for col in df.columns]
    return df

df = load_data()

# =========================================================
# Definição de colunas
# =========================================================
df = df.rename(columns={
    df.columns[2]: "MUNICÍPIO",
    df.columns[17]: "TIPO_COLETA_EXECUTADA",
    df.columns[24]: "MASSA_COLETADA"
})

COL_MUNICIPIO = "MUNICÍPIO"
COL_TIPO_COLETA = "TIPO_COLETA_EXECUTADA"
COL_MASSA = "MASSA_COLETADA"
COL_DESTINO = df.columns[28]  # Coluna AC

# =========================================================
# Classificação técnica
# =========================================================
def classificar_coleta(texto):
    if pd.isna(texto):
        return ("Não informado", False, False, "Tipo não informado")

    t = str(texto).lower()
    palavras = {
        "poda": ("Orgânico direto", True, True, "Resíduo vegetal limpo"),
        "galhada": ("Orgânico direto", True, True, "Resíduo vegetal limpo"),
        "verde": ("Orgânico direto", True, True, "Resíduo vegetal limpo"),
        "orgânica": ("Orgânico direto", True, True, "Orgânico segregado"),
        "domiciliar": ("Orgânico potencial", True, False, "Exige triagem"),
        "varrição": ("Inapto", False, False, "Alta contaminação"),
        "seletiva": ("Não orgânico", False, False, "Recicláveis")
    }
    for p, c in palavras.items():
        if p in t:
            return c
    return ("Indefinido", False, False, "Não classificado")

# =========================================================
# Limpeza
# =========================================================
df_clean = df.dropna(subset=[COL_MUNICIPIO])
df_clean[COL_MUNICIPIO] = df_clean[COL_MUNICIPIO].astype(str).str.strip()

# =========================================================
# Interface
# =========================================================
municipios = ["BRASIL – Todos os municípios"] + sorted(df_clean[COL_MUNICIPIO].unique())
municipio = st.selectbox("Selecione o município:", municipios)

df_mun = df_clean.copy() if municipio == municipios[0] else df_clean[df_clean[COL_MUNICIPIO] == municipio]
st.subheader("🇧🇷 Brasil — Síntese Nacional de RSU" if municipio == municipios[0] else f"📍 {municipio}")

# =========================================================
# Tabela principal
# =========================================================
resultados = []
total_massa = massa_compostagem = massa_vermi = 0

for _, row in df_mun.iterrows():
    categoria, comp, vermi, just = classificar_coleta(row[COL_TIPO_COLETA])
    massa = pd.to_numeric(row[COL_MASSA], errors="coerce") or 0
    total_massa += massa
    if comp:
        massa_compostagem += massa
    if vermi:
        massa_vermi += massa

    resultados.append({
        "Tipo de coleta": row[COL_TIPO_COLETA],
        "Massa": formatar_massa_br(massa),
        "Categoria": categoria,
        "Compostagem": "✅" if comp else "❌",
        "Vermicompostagem": "✅" if vermi else "❌",
        "Justificativa": just
    })

st.dataframe(pd.DataFrame(resultados), use_container_width=True)

# ============================================================
# ♻️ DESTINAÇÃO DA COLETA SELETIVA DE RESÍDUOS ORGÂNICOS
# ============================================================
st.markdown("---")
st.subheader("♻️ Destinação da Coleta Seletiva de Resíduos Orgânicos")

# Filtrar apenas os registros de coleta seletiva de orgânicos
df_organicos = df_mun[df_mun[COL_TIPO_COLETA].astype(str).str.contains(
    "seletiva.*orgânico|orgânico.*seletiva", 
    case=False, 
    na=False, 
    regex=True
)].copy()

if not df_organicos.empty:
    # Calcular massa total de orgânicos coletados seletivamente
    df_organicos["MASSA_FLOAT"] = pd.to_numeric(df_organicos[COL_MASSA], errors="coerce").fillna(0)
    total_organicos = df_organicos["MASSA_FLOAT"].sum()
    
    st.metric("Massa total de orgânicos coletados seletivamente", f"{formatar_numero_br(total_organicos)} t")
    
    # Agrupar por destino
    df_organicos_destino = df_organicos.groupby(COL_DESTINO)["MASSA_FLOAT"].sum().reset_index()
    df_organicos_destino["Percentual (%)"] = df_organicos_destino["MASSA_FLOAT"] / total_organicos * 100
    df_organicos_destino = df_organicos_destino.sort_values("Percentual (%)", ascending=False)
    
    # Formatar para exibição
    df_view_organicos = df_organicos_destino.copy()
    df_view_organicos["Massa (t)"] = df_view_organicos["MASSA_FLOAT"].apply(formatar_numero_br)
    df_view_organicos["Percentual (%)"] = df_view_organicos["Percentual (%)"].apply(lambda x: formatar_numero_br(x, 1))
    
    st.dataframe(df_view_organicos[[COL_DESTINO, "Massa (t)", "Percentual (%)"]], use_container_width=True)
    
    # =========================================================
    # 🔥 Cálculo detalhado de emissões por tipo de destino (orgânicos)
    # =========================================================
    st.subheader("🔥 Cálculo Detalhado de Emissões de CH₄ por Tipo de Destino (Orgânicos)")
    
    # Adicionar coluna de MCF à tabela
    df_organicos_destino["MCF"] = df_organicos_destino[COL_DESTINO].apply(determinar_mcf_por_destino)
    
    # Lista para armazenar resultados detalhados
    resultados_emissoes_organicos = []
    ch4_total_aterro_20anos_organicos = 0  # AGORA COM DECAIMENTO
    massa_total_aterro_t_organicos = 0
    
    for _, row in df_organicos_destino.iterrows():
        destino = row[COL_DESTINO]
        massa_t_ano = row["MASSA_FLOAT"]  # Massa ANUAL de 2023
        mcf = row["MCF"]
        
        # Só calcular emissões para destinos com MCF > 0 (aterros)
        if mcf > 0 and massa_t_ano > 0:
            # CÁLCULO COM DECAIMENTO (20 anos com entrada contínua) - MESMO MÉTODO DO SCRIPT TCO2E
            ch4_20anos = calcular_ch4_total_aterro_20anos(massa_t_ano, mcf)
            
            ch4_total_aterro_20anos_organicos += ch4_20anos
            massa_total_aterro_t_organicos += massa_t_ano
            
            resultados_emissoes_organicos.append({
                "Destino": destino,
                "Massa anual (t)": formatar_numero_br(massa_t_ano),
                "MCF": formatar_numero_br(mcf, 2),
                "CH₄ Gerado (t) - 20 anos": formatar_numero_br(ch4_20anos, 3),
                "Tipo de Aterro": classificar_tipo_aterro(mcf)
            })
    
    # Se houver emissões de aterro, mostrar resultados
    if resultados_emissoes_organicos:
        st.dataframe(pd.DataFrame(resultados_emissoes_organicos), use_container_width=True)
        
        # =========================================================
        # 📊 Comparação com Cenário de Tratamento Biológico (orgânicos)
        # =========================================================
        st.subheader("📊 Comparação: Aterro vs Tratamento Biológico (Orgânicos)")
        
        # Calcular emissões do cenário de tratamento biológico (com entrada contínua)
        massa_kg_total_aterro_organicos = massa_total_aterro_t_organicos * 1000
        
        # Para compostagem: usar mesmo método de entrada contínua
        # Converter massa anual para diária
        massa_kg_dia_organicos = massa_kg_total_aterro_organicos / 365
        
        # Calcular emissões de CH4 da compostagem (20 anos com entrada contínua)
        emissoes_ch4_compostagem_dia = calcular_emissoes_compostagem_entrada_continua(massa_kg_dia_organicos, DIAS_PROJECAO)
        ch4_comp_total_t_20anos_organicos = emissoes_ch4_compostagem_dia.sum() / 1000
        
        # Calcular emissões de CH4 da vermicompostagem (20 anos com entrada contínua)
        emissoes_ch4_vermicompostagem_dia = calcular_emissoes_vermicompostagem_entrada_continua(massa_kg_dia_organicos, DIAS_PROJECAO)
        ch4_vermi_total_t_20anos_organicos = emissoes_ch4_vermicompostagem_dia.sum() / 1000
        
        # Emissões evitadas (20 anos)
        ch4_evitado_20anos_comp_organicos = ch4_total_aterro_20anos_organicos - ch4_comp_total_t_20anos_organicos
        ch4_evitado_20anos_vermi_organicos = ch4_total_aterro_20anos_organicos - ch4_vermi_total_t_20anos_organicos
        
        # Calcular CO₂ equivalente (20 anos) usando GWP de 20 anos
        co2eq_evitado_20anos_comp_organicos = ch4_evitado_20anos_comp_organicos * GWP_CH4_20
        co2eq_evitado_20anos_vermi_organicos = ch4_evitado_20anos_vermi_organicos * GWP_CH4_20
        
        # Médias anuais
        ch4_evitado_medio_anual_comp_organicos = ch4_evitado_20anos_comp_organicos / ANOS_PROJECAO_CREDITOS
        co2eq_evitado_medio_anual_comp_organicos = co2eq_evitado_20anos_comp_organicos / ANOS_PROJECAO_CREDITOS
        
        # Métricas comparativas ATUALIZADAS (com decaimento)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Massa em aterros (2023)",
                f"{formatar_numero_br(massa_total_aterro_t_organicos)} t",
                help="Total de orgânicos destinados a aterros em 2023 (base para projeção)"
            )
        
        with col2:
            st.metric(
                "CH₄ do aterro (20 anos)",
                f"{formatar_numero_br(ch4_total_aterro_20anos_organicos, 1)} t",
                delta=None,
                help=f"CH₄ gerado em aterros em {ANOS_PROJECAO_CREDITOS} anos com decaimento (k={k_ano} ano⁻¹)"
            )
        
        with col3:
            st.metric(
                "CH₄ evitado (Comp. 20 anos)",
                f"{formatar_numero_br(ch4_evitado_20anos_comp_organicos, 1)} t",
                delta=f"-{formatar_numero_br((ch4_evitado_20anos_comp_organicos/ch4_total_aterro_20anos_organicos)*100 if ch4_total_aterro_20anos_organicos > 0 else 0, 1)}%",
                delta_color="inverse",
                help=f"Redução de CH₄ em {ANOS_PROJECAO_CREDITOS} anos ao optar por compostagem"
            )
        
        with col4:
            st.metric(
                "CO₂e evitado (Comp. 20 anos)",
                f"{formatar_numero_br(co2eq_evitado_20anos_comp_organicos, 1)} t CO₂e",
                help=f"Equivalente em CO₂ (GWP20 = {GWP_CH4_20})"
            )
        
        # Nota explicativa sobre o método de cálculo
        st.info(f"""
        **🧮 Método de cálculo (igual ao script tco2e):**
        - **Período:** {ANOS_PROJECAO_CREDITOS} anos com entrada contínua
        - **Constante de decaimento (k):** {k_ano} ano⁻¹
        - **Modelo:** Decomposição exponencial com convolução (IPCC 2006)
        - **Entrada anual constante:** {formatar_numero_br(massa_total_aterro_t_organicos)} t/ano
        - **Massa total 20 anos:** {formatar_numero_br(massa_total_aterro_t_organicos * ANOS_PROJECAO_CREDITOS)} t
        - **Método matemático:** `fftconvolve(entradas_diarias, kernel_exponencial)`
        """)
        
        # Nota sobre compostagem de orgânicos
        st.info("""
        **💡 Importante para resíduos orgânicos:**
        - Resíduos orgânicos coletados seletivamente são **ideais para compostagem/vermicompostagem**
        - Já estão **segregados na fonte**, reduzindo custos de triagem
        - **Alto potencial de geração de créditos de carbono** devido à massa significativa
        - Podem ser tratados **localmente**, reduzindo custos de transporte
        """)
        
    else:
        st.success("✅ Não há massa de orgânicos coletados seletivamente destinada a aterros. Todo o material já está sendo direcionado para tratamentos adequados!")
else:
    st.info("ℹ️ Não foram encontrados registros de coleta seletiva de resíduos orgânicos para o município selecionado.")
    st.write("""
    **Nota:** A coleta seletiva de resíduos orgânicos é uma prática ainda em desenvolvimento no Brasil. 
    Muitos municípios não possuem sistemas específicos para coleta de resíduos orgânicos, que muitas vezes 
    são coletados junto com os resíduos indiferenciados.
    """)

st.markdown("---")

# ============================================================
# 🌳 DESTINAÇÃO DAS PODAS E GALHADAS DE ÁREAS VERDES PÚBLICAS
# ============================================================

st.subheader("🌳 Destinação das podas e galhadas de áreas verdes públicas")

df_podas = df_mun[df_mun[COL_TIPO_COLETA].astype(str).str.contains("áreas verdes públicas", case=False, na=False)].copy()

if not df_podas.empty:
    df_podas["MASSA_FLOAT"] = pd.to_numeric(df_podas[COL_MASSA], errors="coerce").fillna(0)
    total_podas = df_podas["MASSA_FLOAT"].sum()

    df_podas_destino = df_podas.groupby(COL_DESTINO)["MASSA_FLOAT"].sum().reset_index()
    df_podas_destino["Percentual (%)"] = df_podas_destino["MASSA_FLOAT"] / total_podas * 100
    df_podas_destino = df_podas_destino.sort_values("Percentual (%)", ascending=False)

    st.metric("Massa total de podas e galhadas", f"{formatar_numero_br(total_podas)} t")

    df_view = df_podas_destino.copy()
    df_view["Massa (t)"] = df_view["MASSA_FLOAT"].apply(formatar_numero_br)
    df_view["Percentual (%)"] = df_view["Percentual (%)"].apply(lambda x: formatar_numero_br(x, 1))

    st.dataframe(df_view[[COL_DESTINO, "Massa (t)", "Percentual (%)"]], use_container_width=True)

    # =========================================================
    # 🔥 Cálculo detalhado de emissões por tipo de destino
    # =========================================================
    st.subheader("🔥 Cálculo Detalhado de Emissões de CH₄ por Tipo de Destino")
    
    # Adicionar coluna de MCF à tabela (sem exibir)
    df_podas_destino["MCF"] = df_podas_destino[COL_DESTINO].apply(determinar_mcf_por_destino)
    
    # Lista para armazenar resultados detalhados
    resultados_emissoes = []
    ch4_total_aterro_20anos = 0  # AGORA COM DECAIMENTO
    massa_total_aterro_t = 0
    
    for _, row in df_podas_destino.iterrows():
        destino = row[COL_DESTINO]
        massa_t_ano = row["MASSA_FLOAT"]  # Massa ANUAL de 2023
        mcf = row["MCF"]
        
        # Só calcular emissões para destinos com MCF > 0 (aterros)
        if mcf > 0 and massa_t_ano > 0:
            # CÁLCULO COM DECAIMENTO (20 anos com entrada contínua) - MESMO MÉTODO DO SCRIPT TCO2E
            ch4_20anos = calcular_ch4_total_aterro_20anos(massa_t_ano, mcf)
            
            ch4_total_aterro_20anos += ch4_20anos
            massa_total_aterro_t += massa_t_ano
            
            resultados_emissoes.append({
                "Destino": destino,
                "Massa anual (t)": formatar_numero_br(massa_t_ano),
                "MCF": formatar_numero_br(mcf, 2),
                "CH₄ Gerado (t) - 20 anos": formatar_numero_br(ch4_20anos, 3),
                "Tipo de Aterro": classificar_tipo_aterro(mcf)
            })
    
    # Se houver emissões de aterro, mostrar resultados
    if resultados_emissoes:
        st.dataframe(pd.DataFrame(resultados_emissoes), use_container_width=True)
        
        # =========================================================
        # 📊 Comparação com Cenário de Tratamento Biológico
        # =========================================================
        st.subheader("📊 Comparação: Aterro vs Tratamento Biológico")
        
        # Métricas comparativas ATUALIZADAS (com decaimento)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Massa em aterros (2023)",
                f"{formatar_numero_br(massa_total_aterro_t)} t",
                help="Total de podas destinadas a aterros em 2023 (base para projeção)"
            )
        
        with col2:
            st.metric(
                "CH₄ do aterro (20 anos)",
                f"{formatar_numero_br(ch4_total_aterro_20anos, 1)} t",
                delta=None,
                help=f"CH₄ gerado em aterros em {ANOS_PROJECAO_CREDITOS} anos com decaimento (k={k_ano} ano⁻¹)"
            )
        
        # Nota explicativa sobre o método de cálculo
        st.info(f"""
        **🧮 Método de cálculo (igual ao script tco2e):**
        - **Período:** {ANOS_PROJECAO_CREDITOS} anos com entrada contínua
        - **Constante de decaimento (k):** {k_ano} ano⁻¹
        - **Modelo:** Decomposição exponencial com convolução (IPCC 2006)
        - **Entrada anual constante:** {formatar_numero_br(massa_total_aterro_t)} t/ano
        - **Massa total 20 anos:** {formatar_numero_br(massa_total_aterro_t * ANOS_PROJECAO_CREDITOS)} t
        - **Método matemático:** `fftconvolve(entradas_diarias, kernel_exponencial)`
        """)
        
        # =============================================================================
        # 🎯 CÁLCULO COM ENTRADA CONTÍNUA E DECAIMENTO PARA CRÉDITOS DE CARBONO (20 ANOS)
        # =============================================================================
        st.markdown("---")
        st.subheader("🎯 Projeção para Créditos de Carbono (20 anos com entrada contínua)")
        
        st.info(f"""
        **Metodologia avançada:** Este cálculo considera **entrada contínua de resíduos** (mesma massa de 2023 a cada ano)
        e o **decaimento acumulado das emissões no aterro ao longo de {ANOS_PROJECAO_CREDITOS} anos**,
        conforme modelo do IPCC 2006 e implementado no script original tco2e.
        
        - **Período:** {ANOS_PROJECAO_CREDITOS} anos (padrão para projetos de créditos de carbono)
        - **Entrada anual:** {formatar_numero_br(massa_total_aterro_t)} t/ano (mantendo massa de 2023)
        - **Total massa em 20 anos:** {formatar_numero_br(massa_total_aterro_t * ANOS_PROJECAO_CREDITOS)} t
        - **Constante de decaimento (k):** {k_ano} ano⁻¹
        - **GWP CH₄ (20 anos):** {GWP_CH4_20}
        - **Considera decomposição gradual** dos resíduos de todos os anos
        """)
        
        # Calcular emissões COM ENTRADA CONTÍNUA para cada tipo de aterro
        resultados_entrada_continua = []
        co2eq_total_aterro_20anos = 0
        co2eq_total_evitado_compostagem_20anos = 0
        co2eq_total_evitado_vermicompostagem_20anos = 0
        
        for _, row in df_podas_destino.iterrows():
            destino = row[COL_DESTINO]
            massa_t_ano = row["MASSA_FLOAT"]  # Massa ANUAL de 2023
            mcf = row["MCF"]
            
            if mcf > 0 and massa_t_ano > 0:
                # Calcular emissões com entrada contínua para 20 anos
                resultados = calcular_emissoes_totais_entrada_continua(massa_t_ano, mcf)
                
                co2eq_total_aterro_20anos += resultados['co2eq_aterro_total']
                co2eq_total_evitado_compostagem_20anos += resultados['co2eq_evitado_compostagem']
                co2eq_total_evitado_vermicompostagem_20anos += resultados['co2eq_evitado_vermicompostagem']
                
                resultados_entrada_continua.append({
                    "Destino": destino,
                    "Massa anual (t)": formatar_numero_br(massa_t_ano),
                    "MCF": formatar_numero_br(mcf, 2),
                    "Linha de Base (tCO₂e)": formatar_numero_br(resultados['co2eq_aterro_total'], 1),
                    "Emissões Evitadas - Compostagem (tCO₂e)": formatar_numero_br(resultados['co2eq_evitado_compostagem'], 1),
                    "Emissões Evitadas - Vermicompostagem (tCO₂e)": formatar_numero_br(resultados['co2eq_evitado_vermicompostagem'], 1),
                    "Média anual evitada (tCO₂e/ano)": formatar_numero_br(resultados['co2eq_evitado_medio_anual_compostagem'], 1)
                })
        
        if resultados_entrada_continua:
            # Mostrar tabela de resultados com entrada contínua
            st.dataframe(pd.DataFrame(resultados_entrada_continua), use_container_width=True)
            
            # Calcular médias anuais (dividindo por 20)
            media_anual_evitado_compostagem = co2eq_total_evitado_compostagem_20anos / ANOS_PROJECAO_CREDITOS
            media_anual_evitado_vermicompostagem = co2eq_total_evitado_vermicompostagem_20anos / ANOS_PROJECAO_CREDITOS
            
            # Resumo geral
            st.markdown("#### 📊 Resumo Geral da Projeção (20 anos)")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Massa total 20 anos",
                    f"{formatar_numero_br(massa_total_aterro_t * ANOS_PROJECAO_CREDITOS)} t",
                    help=f"{formatar_numero_br(massa_total_aterro_t)} t/ano × {ANOS_PROJECAO_CREDITOS} anos"
                )
            
            with col2:
                st.metric(
                    "Linha de Base total (tCO₂e)",
                    f"{formatar_numero_br(co2eq_total_aterro_20anos, 1)} tCO₂e",
                    help="Emissões acumuladas do aterro em 20 anos"
                )
            
            with col3:
                st.metric(
                    "Emissões Evitadas - Compostagem (tCO₂e)",
                    f"{formatar_numero_br(co2eq_total_evitado_compostagem_20anos, 1)} tCO₂e",
                    help="Emissões evitadas com compostagem em 20 anos"
                )
            
            # =============================================================================
            # 📈 GRÁFICO: REDUÇÃO DE EMISSÕES ACUMULADA (IGUAL AO SCRIPT TCO2E)
            # =============================================================================
            st.markdown("---")
            st.subheader("📉 Redução de Emissões Acumulada (20 anos)")
            
            # Calcular dados para o gráfico (somar todos os destinos)
            # Inicializar arrays de emissões diárias
            datas = []
            total_aterro_diario = np.zeros(DIAS_PROJECAO)
            total_compostagem_diario = np.zeros(DIAS_PROJECAO)
            total_vermicompostagem_diario = np.zeros(DIAS_PROJECAO)
            
            # Data inicial para o gráfico
            data_inicio = datetime(2024, 1, 1)
            
            # Para cada destino, calcular emissões diárias e somar
            for _, row in df_podas_destino.iterrows():
                massa_t_ano = row["MASSA_FLOAT"]
                mcf = row["MCF"]
                
                if mcf > 0 and massa_t_ano > 0:
                    # Calcular emissões diárias detalhadas
                    df_detalhado = calcular_emissoes_diarias_detalhadas(massa_t_ano, mcf)
                    
                    # Somar às totais
                    total_aterro_diario += df_detalhado['Emissoes_Aterro_tCO2eq_dia'].values
                    total_compostagem_diario += df_detalhado['Emissoes_Compostagem_tCO2eq_dia'].values
                    total_vermicompostagem_diario += df_detalhado['Emissoes_Vermicompostagem_tCO2eq_dia'].values
            
            # Criar DataFrame para o gráfico
            df_grafico = pd.DataFrame({
                'Data': [data_inicio + timedelta(days=i) for i in range(DIAS_PROJECAO)],
                'Total_Aterro_tCO2eq_dia': total_aterro_diario,
                'Total_Compostagem_tCO2eq_dia': total_compostagem_diario,
                'Total_Vermicompostagem_tCO2eq_dia': total_vermicompostagem_diario
            })
            
            # Calcular acumuladas
            df_grafico['Total_Aterro_tCO2eq_acum'] = df_grafico['Total_Aterro_tCO2eq_dia'].cumsum()
            df_grafico['Total_Compostagem_tCO2eq_acum'] = df_grafico['Total_Compostagem_tCO2eq_dia'].cumsum()
            df_grafico['Total_Vermicompostagem_tCO2eq_acum'] = df_grafico['Total_Vermicompostagem_tCO2eq_dia'].cumsum()
            
            # Criar gráfico
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Plotar linhas
            ax.plot(df_grafico['Data'], df_grafico['Total_Aterro_tCO2eq_acum'], 
                   'r-', label='Cenário Base (Aterro Sanitário)', linewidth=2)
            ax.plot(df_grafico['Data'], df_grafico['Total_Compostagem_tCO2eq_acum'], 
                   'g-', label='Projeto (Compostagem Termofílica)', linewidth=2)
            ax.plot(df_grafico['Data'], df_grafico['Total_Vermicompostagem_tCO2eq_acum'], 
                   'b-', label='Projeto (Vermicompostagem)', linewidth=2, linestyle='--')
            
            # Preencher área entre as linhas (emissões evitadas)
            ax.fill_between(df_grafico['Data'], 
                           df_grafico['Total_Compostagem_tCO2eq_acum'], 
                           df_grafico['Total_Aterro_tCO2eq_acum'],
                           color='lightgreen', alpha=0.3, label='Emissões Evitadas (Compostagem)')
            
            # Configurar eixos
            ax.set_title(f'Redução de Emissões Acumulada em {ANOS_PROJECAO_CREDITOS} Anos', fontsize=14, fontweight='bold')
            ax.set_xlabel('Ano', fontsize=12)
            ax.set_ylabel('tCO₂e Acumulado', fontsize=12)
            
            # Formatar eixo X para mostrar apenas anos
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            ax.xaxis.set_major_locator(mdates.YearLocator(2))  # Mostrar a cada 2 anos
            plt.xticks(rotation=45)
            
            # Formatar eixo Y no padrão brasileiro
            br_formatter = FuncFormatter(br_format)
            ax.yaxis.set_major_formatter(br_formatter)
            
            # Adicionar grid e legenda
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend(loc='upper left', fontsize=10)
            
            # Ajustar layout
            plt.tight_layout()
            
            # Mostrar gráfico no Streamlit
            st.pyplot(fig)
            
            # Adicionar informações abaixo do gráfico
            st.markdown(f"""
            **📊 Interpretação do Gráfico:**
            - **Linha Vermelha:** Emissões acumuladas do cenário base (aterro sanitário) - **{formatar_numero_br(df_grafico['Total_Aterro_tCO2eq_acum'].iloc[-1], 1)} tCO₂e**
            - **Linha Verde:** Emissões acumuladas do projeto (compostagem) - **{formatar_numero_br(df_grafico['Total_Compostagem_tCO2eq_acum'].iloc[-1], 1)} tCO₂e**
            - **Linha Azul Tracejada:** Emissões acumuladas do projeto (vermicompostagem) - **{formatar_numero_br(df_grafico['Total_Vermicompostagem_tCO2eq_acum'].iloc[-1], 1)} tCO₂e**
            - **Área Verde:** Emissões evitadas pela compostagem - **{formatar_numero_br(co2eq_total_evitado_compostagem_20anos, 1)} tCO₂e**
            
            **💡 Observações:**
            1. As emissões do aterro **acumulam mais rapidamente** devido ao decaimento gradual
            2. As emissões da compostagem/vermicompostagem são **imediatas** (processo em 50 dias)
            3. A **área entre as curvas** representa os créditos de carbono gerados
            4. Curva do aterro mostra o **efeito do decaimento exponencial** (k = {k_ano} ano⁻¹)
            """)
            
            # =============================================================================
            # SEÇÃO DE COTAÇÃO AUTOMÁTICA DO CARBONO
            # =============================================================================
            st.markdown("---")
            st.subheader("💰 Mercado de Carbono - Valor Financeiro das Emissões Evitadas")
            
            # Obter cotações automaticamente
            with st.spinner("🔄 Obtendo cotações em tempo real..."):
                # Obter cotação do carbono
                preco_carbono, moeda_carbono, contrato_info, sucesso_carbono, fonte_carbono = obter_cotacao_carbono()
                
                # Obter cotação do Euro
                taxa_cambio, moeda_real, sucesso_euro, fonte_euro = obter_cotacao_euro_real()
            
            # Exibir cotações atuais
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    label=f"Preço do Carbono (tCO₂eq)",
                    value=f"{moeda_carbono} {formatar_br(preco_carbono)}",
                    help=f"Fonte: {fonte_carbono}"
                )
            
            with col2:
                st.metric(
                    label="Euro (EUR/BRL)",
                    value=f"{moeda_real} {formatar_br(taxa_cambio)}",
                    help=f"Fonte: {fonte_euro}"
                )
            
            with col3:
                preco_carbono_reais = preco_carbono * taxa_cambio
                st.metric(
                    label=f"Carbono em Reais (tCO₂eq)",
                    value=f"R$ {formatar_br(preco_carbono_reais)}",
                    help="Preço do carbono convertido para Reais Brasileiros"
                )
            
            # =============================================================================
            # VALOR FINANCEIRO DAS EMISSÕES EVITADAS - PROJEÇÃO 20 ANOS COM ENTRADA CONTÍNUA
            # =============================================================================
            st.subheader("💵 Valor Financeiro do CO₂e Evitado (20 anos com entrada contínua)")
            
            # Calcular valores financeiros para 20 anos (TOTAL)
            valor_total_euros_20anos_comp = calcular_valor_creditos(
                co2eq_total_evitado_compostagem_20anos, preco_carbono, moeda_carbono
            )
            valor_total_reais_20anos_comp = calcular_valor_creditos(
                co2eq_total_evitado_compostagem_20anos, preco_carbono, "R$", taxa_cambio
            )
            
            valor_total_euros_20anos_vermi = calcular_valor_creditos(
                co2eq_total_evitado_vermicompostagem_20anos, preco_carbono, moeda_carbono
            )
            valor_total_reais_20anos_vermi = calcular_valor_creditos(
                co2eq_total_evitado_vermicompostagem_20anos, preco_carbono, "R$", taxa_cambio
            )
            
            # Calcular médias anuais (dividir por 20)
            valor_medio_anual_euros_comp = valor_total_euros_20anos_comp / ANOS_PROJECAO_CREDITOS
            valor_medio_anual_reais_comp = valor_total_reais_20anos_comp / ANOS_PROJECAO_CREDITOS
            
            valor_medio_anual_euros_vermi = valor_total_euros_20anos_vermi / ANOS_PROJECAO_CREDITOS
            valor_medio_anual_reais_vermi = valor_total_reais_20anos_vermi / ANOS_PROJECAO_CREDITOS
            
            # Exibir resultados da projeção - COMPOSTAGEM
            st.markdown("#### 🍂 Compostagem - Valor dos Créditos de Carbono")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Emissões Evitadas (tCO₂e)",
                    f"{formatar_br(co2eq_total_evitado_compostagem_20anos)} tCO₂e",
                    help=f"Total em {ANOS_PROJECAO_CREDITOS} anos com entrada contínua"
                )
            
            with col2:
                st.metric(
                    "Média anual (tCO₂e/ano)",
                    f"{formatar_br(media_anual_evitado_compostagem)} tCO₂e/ano",
                    help="Média anual (total ÷ 20)"
                )
            
            with col3:
                st.metric(
                    "Valor total (Euro)",
                    f"{moeda_carbono} {formatar_br(valor_total_euros_20anos_comp)}",
                    help=f"Valor acumulado em {ANOS_PROJECAO_CREDITOS} anos"
                )
            
            with col4:
                st.metric(
                    "Valor médio anual (Euro)",
                    f"{moeda_carbono} {formatar_br(valor_medio_anual_euros_comp)}/ano",
                    help="Média anual (total ÷ 20)"
                )
            
            # Linha 2: Compostagem em Reais
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "Valor total (R$)",
                    f"R$ {formatar_br(valor_total_reais_20anos_comp)}",
                    help=f"Valor acumulado em {ANOS_PROJECAO_CREDITOS} anos"
                )
            
            with col2:
                st.metric(
                    "Valor médio anual (R$)",
                    f"R$ {formatar_br(valor_medio_anual_reais_comp)}/ano",
                    help="Média anual (total ÷ 20)"
                )
            
            # Exibir resultados da projeção - VERMICOMPOSTAGEM
            st.markdown("#### 🐛 Vermicompostagem - Valor dos Créditos de Carbono")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Emissões Evitadas (tCO₂e)",
                    f"{formatar_br(co2eq_total_evitado_vermicompostagem_20anos)} tCO₂e",
                    help=f"Total em {ANOS_PROJECAO_CREDITOS} anos com entrada contínua"
                )
            
            with col2:
                st.metric(
                    "Média anual (tCO₂e/ano)",
                    f"{formatar_br(media_anual_evitado_vermicompostagem)} tCO₂e/ano",
                    help="Média anual (total ÷ 20)"
                )
            
            with col3:
                st.metric(
                    "Valor total (Euro)",
                    f"{moeda_carbono} {formatar_br(valor_total_euros_20anos_vermi)}",
                    help=f"Valor acumulado em {ANOS_PROJECAO_CREDITOS} anos"
                )
            
            with col4:
                st.metric(
                    "Valor médio anual (Euro)",
                    f"{moeda_carbono} {formatar_br(valor_medio_anual_euros_vermi)}/ano",
                    help="Média anual (total ÷ 20)"
                )
            
            # Linha 4: Vermicompostagem em Reais
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "Valor total (R$)",
                    f"R$ {formatar_br(valor_total_reais_20anos_vermi)}",
                    help=f"Valor acumulado em {ANOS_PROJECAO_CREDITOS} anos"
                )
            
            with col2:
                st.metric(
                    "Valor médio anual (R$)",
                    f"R$ {formatar_br(valor_medio_anual_reais_vermi)}/ano",
                    help="Média anual (total ÷ 20)"
                )
            
            # Explicação sobre como calcular o valor
            with st.expander("🧮 Como é calculado o valor dos créditos de carbono?"):
                st.markdown(f"""
                **📊 Fórmula de Cálculo:**
                ```
                Valor dos Créditos = Emissões Evitadas × Preço do Carbono
                ```
                
                **📈 Para Compostagem:**
                - **Emissões Evitadas:** {formatar_br(co2eq_total_evitado_compostagem_20anos)} tCO₂e
                - **Preço do Carbono:** {moeda_carbono} {formatar_br(preco_carbono)}/tCO₂eq
                - **Cálculo:** {formatar_br(co2eq_total_evitado_compostagem_20anos)} × {formatar_br(preco_carbono)} = {moeda_carbono} {formatar_br(valor_total_euros_20anos_comp)}
                
                **💰 Em Reais (com câmbio):**
                - **Taxa de câmbio:** 1 Euro = R$ {formatar_br(taxa_cambio)}
                - **Preço em Reais:** R$ {formatar_br(preco_carbono_reais)}/tCO₂eq
                - **Cálculo:** {formatar_br(co2eq_total_evitado_compostagem_20anos)} × {formatar_br(preco_carbono_reais)} = R$ {formatar_br(valor_total_reais_20anos_comp)}
                
                **📅 Média Anual (dividindo por 20 anos):**
                - **Emissões anuais:** {formatar_br(media_anual_evitado_compostagem)} tCO₂e/ano
                - **Valor anual em Euro:** {moeda_carbono} {formatar_br(valor_medio_anual_euros_comp)}/ano
                - **Valor anual em Real:** R$ {formatar_br(valor_medio_anual_reais_comp)}/ano
                
                **💡 O que isso significa na prática:**
                - Este é o **valor total** que poderia ser recebido vendendo os créditos de carbono
                - Ou o **custo total** para compensar essas emissões
                - Baseado no preço ATUAL do carbono ({moeda_carbono} {formatar_br(preco_carbono)}/tCO₂eq)
                """)
            
            # Nota sobre atualização automática
            st.info(f"""
            **🔄 Atualização Automática:**
            - As cotações são atualizadas automaticamente toda vez que você acessa o app
            - Preço atual do carbono: **{moeda_carbono} {formatar_br(preco_carbono)}/tCO₂eq**
            - Taxa de câmbio atual: **1 Euro = R$ {formatar_br(taxa_cambio)}**
            - **Emissões Evitadas totais:** {formatar_br(co2eq_total_evitado_compostagem_20anos)} tCO₂e
            - **Valor total dos créditos:** {moeda_carbono} {formatar_br(valor_total_euros_20anos_comp)} (ou R$ {formatar_br(valor_total_reais_20anos_comp)})
            """)
            
        else:
            st.info("✅ Não há massa de podas e galhadas destinada a aterros. Todo o material já está sendo direcionado para tratamentos adequados!")
    
    else:
        st.info("✅ Não há massa de podas e galhadas destinada a aterros. Todo o material já está sendo direcionado para tratamentos adequados!")
    
else:
    st.info("Não há dados de podas e galhadas para o município selecionado.")

# =========================================================
# Rodapé
# =========================================================
st.markdown("---")
st.caption("Fonte: SNIS – Sistema Nacional de Informações sobre Saneamento | Metodologia: IPCC 2006, Yang et al. (2017) | Cotações atualizadas automaticamente via Investing.com e APIs de câmbio | Projeção de créditos de carbono: 20 anos com entrada contínua e decaimento acumulado (k = 0.06 ano⁻¹)")
