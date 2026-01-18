import streamlit as st
import pandas as pd
import numpy as np
import unicodedata
import requests
from bs4 import BeautifulSoup
import re
from scipy.signal import fftconvolve

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
DOCf_val = 0.0147 * T + 0.28
MCF = 1  # Fator de correção de metano (será ajustado por destino)
F = 0.5  # Fração de metano no biogás
OX = 0.1  # Fator de oxidação
Ri = 0.0  # Metano recuperado

# Constante de decaimento (fixa como no script anexo)
k_ano = 0.06  # Constante de decaimento anual

# GWP (IPCC AR6)
GWP_CH4_20 = 79.7  # Para comparabilidade com script original

# Período de Simulação (20 anos para projeção de créditos)
ANOS_PROJECAO_CREDITOS = 20
DIAS_PROJECAO = ANOS_PROJECAO_CREDITOS * 365

# Perfil temporal N2O (Wang et al. 2017) - para decomposição gradual
PERFIL_N2O = {1: 0.10, 2: 0.30, 3: 0.40, 4: 0.15, 5: 0.05}

# =========================================================
# FUNÇÕES DE CÁLCULO COM DECAIMENTO (DO SCRIPT ORIGINAL)
# =========================================================

def calcular_emissoes_aterro_com_decaimento(massa_kg_dia, mcf, dias_simulacao=DIAS_PROJECAO):
    """
    Calcula emissões de CH4 do aterro usando metodologia IPCC 2006 COM DECAIMENTO
    Adaptado do script original tco2e
    """
    # Parâmetros IPCC 2006
    DOCf = 0.0147 * T + 0.28  # Decomposable fraction of DOC
    
    # Calcular potencial diário de CH4
    potencial_CH4_por_kg = DOC * DOCf * mcf * F * (16/12) * (1 - Ri) * (1 - OX)
    potencial_CH4_diario_kg = massa_kg_dia * potencial_CH4_por_kg
    
    # Kernel de decaimento exponencial (igual ao script original)
    t = np.arange(1, dias_simulacao + 1, dtype=float)
    kernel_ch4 = np.exp(-k_ano * (t - 1) / 365.0) - np.exp(-k_ano * t / 365.0)
    
    # Entradas diárias (massa constante diária)
    entradas_diarias = np.ones(dias_simulacao, dtype=float)
    
    # Convolução para obter emissões com decaimento
    emissoes_CH4 = fftconvolve(entradas_diarias, kernel_ch4, mode='full')[:dias_simulacao]
    emissoes_CH4 *= potencial_CH4_diario_kg
    
    return emissoes_CH4

def calcular_emissoes_n2o_aterro(massa_kg_dia, dias_simulacao=DIAS_PROJECAO):
    """
    Calcula emissões de N2O do aterro com perfil temporal
    Adaptado do script original tco2e
    """
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
    
    # Convolução para distribuir emissões
    emissoes_N2O = fftconvolve(
        np.full(dias_simulacao, emissao_diaria_N2O_kg), 
        kernel_n2o, 
        mode='full'
    )[:dias_simulacao]
    
    return emissoes_N2O

def calcular_emissoes_compostagem(massa_kg_dia, dias_simulacao=DIAS_PROJECAO):
    """
    Calcula emissões de CH4 da compostagem (Yang et al. 2017)
    """
    # Fator de emissão para compostagem (0.0004 kg CH4/kg resíduo)
    fator_ch4_compostagem = 0.0004
    
    # Emissões diárias (processo rápido - compostagem em 50 dias)
    dias_compostagem = 50
    emissoes_CH4 = np.zeros(dias_simulacao)
    
    # Distribuir emissões ao longo do processo de compostagem
    for dia_entrada in range(dias_simulacao):
        # Para cada entrada, as emissões ocorrem nos próximos 50 dias
        for dia_processo in range(min(dias_compostagem, dias_simulacao - dia_entrada)):
            # Distribuição simplificada (pico no meio do processo)
            fracao = 1.0 / dias_compostagem  # Distribuição uniforme
            dia_emissao = dia_entrada + dia_processo
            emissoes_CH4[dia_emissao] += massa_kg_dia * fator_ch4_compostagem * fracao
    
    return emissoes_CH4

def calcular_emissoes_vermicompostagem(massa_kg_dia, dias_simulacao=DIAS_PROJECAO):
    """
    Calcula emissões de CH4 da vermicompostagem (Yang et al. 2017)
    """
    # Fator de emissão para vermicompostagem (0.00015 kg CH4/kg resíduo)
    fator_ch4_vermicompostagem = 0.00015
    
    # Emissões diárias (processo rápido)
    dias_processo = 50
    emissoes_CH4 = np.zeros(dias_simulacao)
    
    # Distribuir emissões ao longo do processo
    for dia_entrada in range(dias_simulacao):
        for dia_processo in range(min(dias_processo, dias_simulacao - dia_entrada)):
            fracao = 1.0 / dias_processo  # Distribuição uniforme
            dia_emissao = dia_entrada + dia_processo
            emissoes_CH4[dia_emissao] += massa_kg_dia * fator_ch4_vermicompostagem * fracao
    
    return emissoes_CH4

def calcular_emissoes_totais_com_decaimento(massa_t_ano, mcf):
    """
    Calcula emissões totais de CH4 ao longo de 20 anos considerando decaimento
    """
    # Converter massa anual para diária (kg/dia)
    massa_kg_dia = (massa_t_ano * 1000) / 365
    
    # Calcular emissões de CH4 com decaimento
    emissoes_ch4_aterro = calcular_emissoes_aterro_com_decaimento(massa_kg_dia, mcf, DIAS_PROJECAO)
    
    # Calcular emissões de N2O
    emissoes_n2o_aterro = calcular_emissoes_n2o_aterro(massa_kg_dia, DIAS_PROJECAO)
    
    # Calcular emissões de tratamento biológico
    emissoes_ch4_compostagem = calcular_emissoes_compostagem(massa_kg_dia, DIAS_PROJECAO)
    emissoes_ch4_vermicompostagem = calcular_emissoes_vermicompostagem(massa_kg_dia, DIAS_PROJECAO)
    
    # Converter para tCO₂eq
    total_ch4_aterro_t = emissoes_ch4_aterro.sum() / 1000  # kg para toneladas
    total_n2o_aterro_t = emissoes_n2o_aterro.sum() / 1000
    
    total_ch4_compostagem_t = emissoes_ch4_compostagem.sum() / 1000
    total_ch4_vermicompostagem_t = emissoes_ch4_vermicompostagem.sum() / 1000
    
    # Calcular CO₂ equivalente
    co2eq_aterro = (total_ch4_aterro_t * GWP_CH4_20) + (total_n2o_aterro_t * 273)  # GWP N2O = 273
    co2eq_compostagem = total_ch4_compostagem_t * GWP_CH4_20
    co2eq_vermicompostagem = total_ch4_vermicompostagem_t * GWP_CH4_20
    
    # Emissões evitadas
    co2eq_evitado_compostagem = co2eq_aterro - co2eq_compostagem
    co2eq_evitado_vermicompostagem = co2eq_aterro - co2eq_vermicompostagem
    
    return {
        'co2eq_aterro_total': co2eq_aterro,
        'co2eq_evitado_compostagem': co2eq_evitado_compostagem,
        'co2eq_evitado_vermicompostagem': co2eq_evitado_vermicompostagem,
        'co2eq_evitado_medio_anual_compostagem': co2eq_evitado_compostagem / ANOS_PROJECAO_CREDITOS,
        'co2eq_evitado_medio_anual_vermicompostagem': co2eq_evitado_vermicompostagem / ANOS_PROJECAO_CREDITOS
    }

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

# =========================================================
# 🌳 Destinação das podas e galhadas
# =========================================================
st.markdown("---")
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
    ch4_total_aterro_t_simplificado = 0
    massa_total_aterro_t = 0
    
    for _, row in df_podas_destino.iterrows():
        destino = row[COL_DESTINO]
        massa_t = row["MASSA_FLOAT"]
        mcf = row["MCF"]
        
        # Só calcular emissões para destinos com MCF > 0 (aterros)
        if mcf > 0 and massa_t > 0:
            # Cálculo simplificado (para exibição na tabela)
            massa_kg = massa_t * 1000
            DOCf = 0.0147 * T + 0.28
            ch4_kg = massa_kg * DOC * DOCf * mcf * F * (16/12) * (1 - Ri) * (1 - OX)
            ch4_t_simplificado = ch4_kg / 1000
            
            ch4_total_aterro_t_simplificado += ch4_t_simplificado
            massa_total_aterro_t += massa_t
            
            resultados_emissoes.append({
                "Destino": destino,
                "Massa (t)": formatar_numero_br(massa_t),
                "MCF": formatar_numero_br(mcf, 2),
                "CH₄ Gerado (t) - Potencial": formatar_numero_br(ch4_t_simplificado, 3),
                "Tipo de Aterro": classificar_tipo_aterro(mcf)
            })
    
    # Se houver emissões de aterro, mostrar resultados
    if resultados_emissoes:
        st.dataframe(pd.DataFrame(resultados_emissoes), use_container_width=True)
        
        # =========================================================
        # 📊 Comparação com Cenário de Tratamento Biológico
        # =========================================================
        st.subheader("📊 Comparação: Aterro vs Tratamento Biológico")
        
        # Calcular emissões do cenário de tratamento biológico (simplificado)
        massa_kg_total_aterro = massa_total_aterro_t * 1000
        ch4_comp_total_t_simplificado = massa_kg_total_aterro * 0.0004 / 1000  # Compostagem
        ch4_vermi_total_t_simplificado = massa_kg_total_aterro * 0.00015 / 1000  # Vermicompostagem
        
        # Emissões evitadas (simplificado)
        ch4_evitado_t_simplificado_comp = ch4_total_aterro_t_simplificado - ch4_comp_total_t_simplificado
        ch4_evitado_t_simplificado_vermi = ch4_total_aterro_t_simplificado - ch4_vermi_total_t_simplificado
        
        # Calcular CO₂ equivalente (GWP100 do CH4 = 28, IPCC AR6)
        GWP100 = 28
        co2eq_evitado_t_simplificado_comp = ch4_evitado_t_simplificado_comp * GWP100
        co2eq_evitado_t_simplificado_vermi = ch4_evitado_t_simplificado_vermi * GWP100
        
        # Métricas comparativas SIMPLIFICADAS (para contexto geral)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Massa em aterros",
                f"{formatar_numero_br(massa_total_aterro_t)} t",
                help="Total de podas destinadas a aterros (todos os tipos)"
            )
        
        with col2:
            st.metric(
                "CH₄ do aterro",
                f"{formatar_numero_br(ch4_total_aterro_t_simplificado, 1)} t",
                delta=None,
                help="CH₄ gerado em aterros (considerando MCF específico por destino)"
            )
        
        with col3:
            st.metric(
                "CH₄ evitado (Comp.)",
                f"{formatar_numero_br(ch4_evitado_t_simplificado_comp, 1)} t",
                delta=f"-{formatar_numero_br((ch4_evitado_t_simplificado_comp/ch4_total_aterro_t_simplificado)*100 if ch4_total_aterro_t_simplificado > 0 else 0, 1)}%",
                delta_color="inverse",
                help="Redução de CH₄ ao optar por compostagem"
            )
        
        with col4:
            st.metric(
                "CO₂e evitado (Comp.)",
                f"{formatar_numero_br(co2eq_evitado_t_simplificado_comp, 1)} t CO₂e",
                help=f"Equivalente em CO₂ (GWP100 = {GWP100})"
            )
        
        # =============================================================================
        # 🎯 CÁLCULO COM DECAIMENTO PARA CRÉDITOS DE CARBONO (20 ANOS)
        # =============================================================================
        st.markdown("---")
        st.subheader("🎯 Projeção para Créditos de Carbono (20 anos com decaimento)")
        
        st.info(f"""
        **Metodologia avançada:** Este cálculo considera o **decaimento das emissões no aterro ao longo de {ANOS_PROJECAO_CREDITOS} anos**,
        conforme modelo do IPCC 2006 e implementado no script original tco2e.
        
        - **Período:** {ANOS_PROJECAO_CREDITOS} anos (padrão para projetos de créditos de carbono)
        - **Constante de decaimento (k):** {k_ano} ano⁻¹
        - **GWP CH₄ (20 anos):** {GWP_CH4_20}
        - **Considera decomposição gradual** dos resíduos no aterro
        """)
        
        # Calcular emissões COM DECAIMENTO para cada tipo de aterro
        resultados_decaimento = []
        co2eq_total_aterro_20anos = 0
        
        for _, row in df_podas_destino.iterrows():
            destino = row[COL_DESTINO]
            massa_t_ano = row["MASSA_FLOAT"]  # Massa ANUAL
            mcf = row["MCF"]
            
            if mcf > 0 and massa_t_ano > 0:
                # Calcular emissões com decaimento para 20 anos
                resultados = calcular_emissoes_totais_com_decaimento(massa_t_ano, mcf)
                
                co2eq_total_aterro_20anos += resultados['co2eq_aterro_total']
                
                resultados_decaimento.append({
                    "Destino": destino,
                    "Massa anual (t)": formatar_numero_br(massa_t_ano),
                    "MCF": formatar_numero_br(mcf, 2),
                    "CO₂e aterro 20a (t)": formatar_numero_br(resultados['co2eq_aterro_total'], 1),
                    "CO₂e evitado Comp. 20a (t)": formatar_numero_br(resultados['co2eq_evitado_compostagem'], 1),
                    "CO₂e evitado Vermi. 20a (t)": formatar_numero_br(resultados['co2eq_evitado_vermicompostagem'], 1),
                    "Média anual evitado (t/ano)": formatar_numero_br(resultados['co2eq_evitado_medio_anual_compostagem'], 1)
                })
        
        if resultados_decaimento:
            # Mostrar tabela de resultados com decaimento
            st.dataframe(pd.DataFrame(resultados_decaimento), use_container_width=True)
            
            # Calcular totais agregados
            co2eq_total_evitado_compostagem_20anos = sum([float(r["CO₂e evitado Comp. 20a (t)"].replace('.', '').replace(',', '.')) 
                                                         for r in resultados_decaimento])
            co2eq_total_evitado_vermicompostagem_20anos = sum([float(r["CO₂e evitado Vermi. 20a (t)"].replace('.', '').replace(',', '.')) 
                                                             for r in resultados_decaimento])
            
            # Médias anuais (dividindo por 20)
            media_anual_evitado_compostagem = co2eq_total_evitado_compostagem_20anos / ANOS_PROJECAO_CREDITOS
            media_anual_evitado_vermicompostagem = co2eq_total_evitado_vermicompostagem_20anos / ANOS_PROJECAO_CREDITOS
            
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
            # VALOR FINANCEIRO DAS EMISSÕES EVITADAS - PROJEÇÃO 20 ANOS COM DECAIMENTO
            # =============================================================================
            st.subheader("💵 Valor Financeiro do CO₂e Evitado (Projeção 20 anos com decaimento)")
            
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
            
            # Exibir resultados da projeção
            st.markdown(f"**📊 Projeção para {ANOS_PROJECAO_CREDITOS} anos (com decaimento do aterro)**")
            
            # Linha 1: Compostagem
            st.markdown("#### 🍂 Compostagem")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "CO₂e evitado total",
                    f"{formatar_br(co2eq_total_evitado_compostagem_20anos)} tCO₂eq",
                    help=f"Acumulado em {ANOS_PROJECAO_CREDITOS} anos com decaimento"
                )
            
            with col2:
                st.metric(
                    "CO₂e evitado médio anual",
                    f"{formatar_br(media_anual_evitado_compostagem)} tCO₂eq/ano",
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
            
            # Linha 3: Vermicompostagem
            st.markdown("#### 🐛 Vermicompostagem")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "CO₂e evitado total",
                    f"{formatar_br(co2eq_total_evitado_vermicompostagem_20anos)} tCO₂eq",
                    help=f"Acumulado em {ANOS_PROJECAO_CREDITOS} anos com decaimento"
                )
            
            with col2:
                st.metric(
                    "CO₂e evitado médio anual",
                    f"{formatar_br(media_anual_evitado_vermicompostagem)} tCO₂eq/ano",
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
            
            # Explicação sobre compra e venda com projeção de 20 anos e decaimento
            with st.expander("💡 Como funciona a comercialização no mercado de carbono (projeção 20 anos com decaimento)?"):
                st.markdown(f"""
                **📊 Informações de Mercado Atuais:**
                - **Preço do Carbono (Euro):** {moeda_carbono} {formatar_br(preco_carbono)}/tCO₂eq
                - **Preço do Carbono (Real):** R$ {formatar_br(preco_carbono_reais)}/tCO₂eq
                - **Taxa de câmbio:** 1 Euro = R$ {formatar_br(taxa_cambio)}
                - **Fonte Carbono:** {fonte_carbono}
                - **Fonte Câmbio:** {fonte_euro}
                
                **📈 Projeção para {ANOS_PROJECAO_CREDITOS} anos (COM DECAIMENTO):**
                - **Metodologia:** IPCC 2006 com constante de decaimento k = {k_ano} ano⁻¹
                - **Considera:** Decomposição gradual dos resíduos no aterro ao longo do tempo
                - **GWP CH₄ (20 anos):** {GWP_CH4_20}
                - **CO₂e evitado total (Compostagem):** {formatar_br(co2eq_total_evitado_compostagem_20anos)} tCO₂eq
                - **CO₂e evitado total (Vermicompostagem):** {formatar_br(co2eq_total_evitado_vermicompostagem_20anos)} tCO₂eq
                
                **💶 Comprar créditos (compensação - {ANOS_PROJECAO_CREDITOS} anos):**
                - **Compostagem:**
                  - Custo total em Euro: **{moeda_carbono} {formatar_br(valor_total_euros_20anos_comp)}**
                  - Custo total em Real: **R$ {formatar_br(valor_total_reais_20anos_comp)}**
                  - Custo médio anual em Euro: **{moeda_carbono} {formatar_br(valor_medio_anual_euros_comp)}**
                  - Custo médio anual em Real: **R$ {formatar_br(valor_medio_anual_reais_comp)}**
                
                - **Vermicompostagem:**
                  - Custo total em Euro: **{moeda_carbono} {formatar_br(valor_total_euros_20anos_vermi)}**
                  - Custo total em Real: **R$ {formatar_br(valor_total_reais_20anos_vermi)}**
                  - Custo médio anual em Euro: **{moeda_carbono} {formatar_br(valor_medio_anual_euros_vermi)}**
                  - Custo médio anual em Real: **R$ {formatar_br(valor_medio_anual_reais_vermi)}**
                
                **💵 Vender créditos (comercialização - {ANOS_PROJECAO_CREDITOS} anos):**  
                - **Compostagem:**
                  - Receita total em Euro: **{moeda_carbono} {formatar_br(valor_total_euros_20anos_comp)}**
                  - Receita total em Real: **R$ {formatar_br(valor_total_reais_20anos_comp)}**
                  - Receita média anual em Euro: **{moeda_carbono} {formatar_br(valor_medio_anual_euros_comp)}**
                  - Receita média anual em Real: **R$ {formatar_br(valor_medio_anual_reais_comp)}**
                
                - **Vermicompostagem:**
                  - Receita total em Euro: **{moeda_carbono} {formatar_br(valor_total_euros_20anos_vermi)}**
                  - Receita total em Real: **R$ {formatar_br(valor_total_reais_20anos_vermi)}**
                  - Receita média anual em Euro: **{moeda_carbono} {formatar_br(valor_medio_anual_euros_vermi)}**
                  - Receita média anual em Real: **R$ {formatar_br(valor_medio_anual_reais_vermi)}**
                
                **🌍 Mercado de Referência:**
                - European Union Allowances (EUA)
                - European Emissions Trading System (EU ETS)
                - Contratos futuros de carbono
                - Preços em tempo real do mercado regulado
                
                **⚠️ Considerações importantes:**
                - Esta projeção considera o **decaimento das emissões no aterro** (k = {k_ano} ano⁻¹)
                - O cálculo assume quantidade anual **constante** de resíduos
                - O preço do carbono pode variar ao longo dos {ANOS_PROJECAO_CREDITOS} anos
                - Projeção baseada no preço **atual** do carbono
                - Modelo de decaimento baseado no IPCC 2006
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
st.caption("Fonte: SNIS – Sistema Nacional de Informações sobre Saneamento | Metodologia: IPCC 2006, Yang et al. (2017) | Cotações atualizadas automaticamente via Investing.com e APIs de câmbio | Projeção de créditos de carbono: 20 anos com decaimento (k = 0.06 ano⁻¹)")
