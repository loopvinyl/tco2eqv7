import streamlit as st
import pandas as pd
import numpy as np
import unicodedata
import requests
from bs4 import BeautifulSoup
import re

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
# PARÂMETROS DE PERÍODO - ADICIONADO
# =============================================================================

# Definir período de projeção (20 anos)
ANOS_PROJECAO = 20

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
# Funções de emissões de CH4 (script técnico anexo)
# =========================================================
def ch4_compostagem_total(massa_kg):
    # Yang et al. (2017) – compostagem termofílica
    return massa_kg * 0.0004  # kg CH4 / kg resíduo

def ch4_vermicompostagem_total(massa_kg):
    # Yang et al. (2017) – vermicompostagem
    return massa_kg * 0.00015  # kg CH4 / kg resíduo

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
# Função para calcular emissões de CH4 do aterro
# =========================================================
def calcular_emissoes_aterro(massa_t, mcf, temperatura=25.0):
    """
    Calcula emissões de CH4 do aterro usando metodologia IPCC 2006.
    """
    # Parâmetros IPCC 2006 para resíduos de poda
    DOC = 0.15  # Fraction of degradable organic carbon
    DOCf = 0.0147 * temperatura + 0.28  # Decomposable fraction of DOC
    F = 0.5  # Fraction of methane in landfill gas
    OX = 0.1  # Oxidation factor
    Ri = 0.0  # Recovery factor (assumindo sem recuperação inicial)
    
    massa_kg = massa_t * 1000
    ch4_kg = massa_kg * DOC * DOCf * mcf * F * (16/12) * (1 - Ri) * (1 - OX)
    ch4_t = ch4_kg / 1000
    
    return ch4_t

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

# =============================================================================
# ADICIONADO: Controle de período de projeção
# =============================================================================
st.sidebar.markdown("---")
st.sidebar.subheader("📅 Período de Projeção")
anos_projecao = st.sidebar.slider(
    "Anos de projeção",
    min_value=1,
    max_value=50,
    value=ANOS_PROJECAO,
    step=1,
    help="Período total para cálculo das emissões evitadas"
)

st.sidebar.info(f"""
**Configuração atual:**
- Período de projeção: **{anos_projecao} anos**
- Resultados mostram valores **acumulados** no período
- Média anual = Total acumulado ÷ {anos_projecao}
""")

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
    
    # Parâmetros para cálculo (IPCC 2006)
    temperatura = 25.0  # Temperatura média anual em °C
    DOC = 0.15  # Fraction of degradable organic carbon
    DOCf = 0.0147 * temperatura + 0.28  # Decomposable fraction of DOC
    F = 0.5  # Fraction of methane in landfill gas
    OX = 0.1  # Oxidation factor
    Ri = 0.0  # Recovery factor (sem recuperação de gás)
    
    # Lista para armazenar resultados detalhados
    resultados_emissoes = []
    ch4_total_aterro_t = 0
    massa_total_aterro_t = 0
    
    for _, row in df_podas_destino.iterrows():
        destino = row[COL_DESTINO]
        massa_t = row["MASSA_FLOAT"]
        mcf = row["MCF"]
        
        # Só calcular emissões para destinos com MCF > 0 (aterros)
        if mcf > 0 and massa_t > 0:
            ch4_t = calcular_emissoes_aterro(massa_t, mcf, temperatura)
            ch4_total_aterro_t += ch4_t
            massa_total_aterro_t += massa_t
            
            resultados_emissoes.append({
                "Destino": destino,
                "Massa (t)": formatar_numero_br(massa_t),
                "MCF": formatar_numero_br(mcf, 2),
                "CH₄ Gerado (t)": formatar_numero_br(ch4_t, 3),
                "Tipo de Aterro": classificar_tipo_aterro(mcf)
            })
    
    # Se houver emissões de aterro, mostrar resultados
    if resultados_emissoes:
        st.dataframe(pd.DataFrame(resultados_emissoes), use_container_width=True)
        
        # =========================================================
        # 📊 Comparação com Cenário de Tratamento Biológico
        # =========================================================
        st.subheader("📊 Comparação: Aterro vs Tratamento Biológico")
        
        # Calcular emissões do cenário de tratamento biológico
        massa_kg_total_aterro = massa_total_aterro_t * 1000
        ch4_comp_total_t = ch4_compostagem_total(massa_kg_total_aterro) / 1000
        ch4_vermi_total_t = ch4_vermicompostagem_total(massa_kg_total_aterro) / 1000
        
        # =============================================================================
        # AJUSTE: CONSIDERAR PERÍODO DE 20 ANOS
        # =============================================================================
        # Multiplicar pela quantidade de anos para obter o total acumulado
        ch4_total_aterro_t_acumulado = ch4_total_aterro_t * anos_projecao
        ch4_comp_total_t_acumulado = ch4_comp_total_t * anos_projecao
        ch4_vermi_total_t_acumulado = ch4_vermi_total_t * anos_projecao
        massa_total_aterro_t_acumulado = massa_total_aterro_t * anos_projecao
        
        # Emissões evitadas acumuladas
        ch4_evitado_t_acumulado = ch4_total_aterro_t_acumulado - ch4_comp_total_t_acumulado - ch4_vermi_total_t_acumulado
        
        # Calcular CO₂ equivalente (GWP100 do CH4 = 28, IPCC AR6)
        GWP100 = 28
        co2eq_evitado_t_acumulado = ch4_evitado_t_acumulado * GWP100
        
        # Calcular médias anuais
        ch4_evitado_media_anual = ch4_evitado_t_acumulado / anos_projecao
        co2eq_evitado_media_anual = co2eq_evitado_t_acumulado / anos_projecao
        
        # =============================================================================
        # EXIBIÇÃO DOS RESULTADOS - COM ACUMULADO E MÉDIA ANUAL
        # =============================================================================
        
        st.info(f"**Período considerado:** {anos_projecao} anos | **Massa anual de podas em aterros:** {formatar_numero_br(massa_total_aterro_t)} t")
        
        # Métricas acumuladas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                f"Massa acumulada ({anos_projecao} anos)",
                f"{formatar_numero_br(massa_total_aterro_t_acumulado)} t",
                help=f"Total de podas destinadas a aterros em {anos_projecao} anos"
            )
        
        with col2:
            st.metric(
                f"CH₄ do aterro ({anos_projecao} anos)",
                f"{formatar_numero_br(ch4_total_aterro_t_acumulado, 1)} t",
                delta=None,
                help=f"CH₄ total gerado em aterros em {anos_projecao} anos"
            )
        
        with col3:
            st.metric(
                f"CH₄ evitado acumulado",
                f"{formatar_numero_br(ch4_evitado_t_acumulado, 1)} t",
                delta=f"-{formatar_numero_br((ch4_evitado_t_acumulado/ch4_total_aterro_t_acumulado)*100 if ch4_total_aterro_t_acumulado > 0 else 0, 1)}%",
                delta_color="inverse",
                help=f"Redução total de CH₄ em {anos_projecao} anos ao optar por tratamento biológico"
            )
        
        with col4:
            st.metric(
                f"CO₂e evitado acumulado",
                f"{formatar_numero_br(co2eq_evitado_t_acumulado, 1)} t CO₂e",
                help=f"Equivalente total em CO₂ (GWP100 = {GWP100}) em {anos_projecao} anos"
            )
        
        # Métricas anuais
        st.subheader("📈 Métricas Anuais (Média)")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Massa anual média",
                f"{formatar_numero_br(massa_total_aterro_t)} t/ano",
                help="Média anual de podas destinadas a aterros"
            )
        
        with col2:
            st.metric(
                "CH₄ do aterro (anual)",
                f"{formatar_numero_br(ch4_total_aterro_t, 1)} t/ano",
                help="CH₄ gerado anualmente em aterros"
            )
        
        with col3:
            st.metric(
                "CH₄ evitado (anual)",
                f"{formatar_numero_br(ch4_evitado_media_anual, 1)} t/ano",
                delta=f"-{formatar_numero_br((ch4_evitado_media_anual/ch4_total_aterro_t)*100 if ch4_total_aterro_t > 0 else 0, 1)}%/ano",
                delta_color="inverse",
                help="Redução média anual de CH₄"
            )
        
        with col4:
            st.metric(
                "CO₂e evitado (anual)",
                f"{formatar_numero_br(co2eq_evitado_media_anual, 1)} t CO₂e/ano",
                help="Equivalente anual médio em CO₂"
            )
        
        # =============================================================================
        # SEÇÃO DE COTAÇÃO AUTOMÁTICA DO CARBONO (ADICIONADA APÓS CO₂e EVITADO)
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
        # VALOR FINANCEIRO DAS EMISSÕES EVITADAS - ACUMULADO E ANUAL
        # =============================================================================
        st.subheader("💵 Valor Financeiro do CO₂e Evitado")
        
        # Calcular valores financeiros ACUMULADOS
        valor_euros_acumulado = calcular_valor_creditos(co2eq_evitado_t_acumulado, preco_carbono, moeda_carbono)
        valor_reais_acumulado = calcular_valor_creditos(co2eq_evitado_t_acumulado, preco_carbono, "R$", taxa_cambio)
        
        # Calcular valores financeiros ANUAIS
        valor_euros_anual = valor_euros_acumulado / anos_projecao
        valor_reais_anual = valor_reais_acumulado / anos_projecao
        
        st.info(f"**Período:** {anos_projecao} anos | **Preço carbono:** {moeda_carbono} {formatar_br(preco_carbono)}/tCO₂eq")
        
        # Valores acumulados
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                f"Valor acumulado em Euros ({anos_projecao} anos)",
                f"{moeda_carbono} {formatar_br(valor_euros_acumulado)}",
                help=f"Baseado em {formatar_numero_br(co2eq_evitado_t_acumulado)} tCO₂eq evitadas acumuladas"
            )
        
        with col2:
            st.metric(
                f"Valor acumulado em Reais ({anos_projecao} anos)",
                f"R$ {formatar_br(valor_reais_acumulado)}",
                help=f"Baseado em {formatar_numero_br(co2eq_evitado_t_acumulado)} tCO₂eq evitadas acumuladas"
            )
        
        # Valores anuais
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Valor anual médio em Euros",
                f"{moeda_carbono} {formatar_br(valor_euros_anual)}/ano",
                help="Média anual do valor das emissões evitadas"
            )
        
        with col2:
            st.metric(
                "Valor anual médio em Reais",
                f"R$ {formatar_br(valor_reais_anual)}/ano",
                help="Média anual do valor das emissões evitadas"
            )
        
        # Explicação sobre compra e venda
        with st.expander("💡 Como funciona a comercialização no mercado de carbono?"):
            st.markdown(f"""
            **📊 Informações de Mercado Atuais:**
            - **Período de projeção:** {anos_projecao} anos
            - **Preço do Carbono (Euro):** {moeda_carbono} {formatar_br(preco_carbono)}/tCO₂eq
            - **Preço do Carbono (Real):** R$ {formatar_br(preco_carbono_reais)}/tCO₂eq
            - **Taxa de câmbio:** 1 Euro = R$ {formatar_br(taxa_cambio)}
            - **Fonte Carbono:** {fonte_carbono}
            - **Fonte Câmbio:** {fonte_euro}
            
            **💶 Comprar créditos (compensação - {anos_projecao} anos):**
            - Custo total em Euro: **{moeda_carbono} {formatar_br(valor_euros_acumulado)}**
            - Custo total em Real: **R$ {formatar_br(valor_reais_acumulado)}**
            - Custo anual médio em Euro: **{moeda_carbono} {formatar_br(valor_euros_anual)}/ano**
            - Custo anual médio em Real: **R$ {formatar_br(valor_reais_anual)}/ano**
            
            **💵 Vender créditos (comercialização - {anos_projecao} anos):**  
            - Receita total em Euro: **{moeda_carbono} {formatar_br(valor_euros_acumulado)}**
            - Receita total em Real: **R$ {formatar_br(valor_reais_acumulado)}**
            - Receita anual média em Euro: **{moeda_carbono} {formatar_br(valor_euros_anual)}/ano**
            - Receita anual média em Real: **R$ {formatar_br(valor_reais_anual)}/ano**
            
            **📈 Potencial de Geração:**
            - CO₂e evitado acumulado ({anos_projecao} anos): **{formatar_numero_br(co2eq_evitado_t_acumulado)} tCO₂eq**
            - CO₂e evitado anual (média): **{formatar_numero_br(co2eq_evitado_media_anual)} tCO₂eq/ano**
            - Valor acumulado em Euros: **{moeda_carbono} {formatar_br(valor_euros_acumulado)}**
            - Valor acumulado em Reais: **R$ {formatar_br(valor_reais_acumulado)}**
            
            **🌍 Mercado de Referência:**
            - European Union Allowances (EUA)
            - European Emissions Trading System (EU ETS)
            - Contratos futuros de carbono
            - Preços em tempo real do mercado regulado
            """)
        
        # =========================================================
        # 📈 Resumo por Tipo de Aterro (ANUAL)
        # =========================================================
        st.subheader("📈 Resumo por Categoria de Aterro (Dados Anuais)")
        
        # Converter string para float para agregação
        def to_float(val):
            if isinstance(val, str):
                # Remover pontos de milhar e substituir vírgula decimal por ponto
                val_clean = val.replace('.', '').replace(',', '.')
                return float(val_clean)
            return float(val)
        
        df_resumo = pd.DataFrame(resultados_emissoes)
        if not df_resumo.empty:
            df_resumo["Massa_num"] = df_resumo["Massa (t)"].apply(lambda x: to_float(x))
            df_resumo["CH4_num"] = df_resumo["CH₄ Gerado (t)"].apply(lambda x: to_float(x))
            
            resumo_agrupado = df_resumo.groupby("Tipo de Aterro").agg({
                "Massa_num": "sum",
                "CH4_num": "sum"
            }).reset_index()
            
            resumo_agrupado["Massa (t/ano)"] = resumo_agrupado["Massa_num"].apply(lambda x: formatar_numero_br(x))
            resumo_agrupado["CH₄ Gerado (t/ano)"] = resumo_agrupado["CH4_num"].apply(lambda x: formatar_numero_br(x, 1))
            resumo_agrupado["CH₄ por t"] = resumo_agrupado.apply(
                lambda row: formatar_numero_br(row["CH4_num"] / row["Massa_num"] if row["Massa_num"] > 0 else 0, 3), 
                axis=1
            )
            
            st.dataframe(resumo_agrupado[["Tipo de Aterro", "Massa (t/ano)", "CH₄ Gerado (t/ano)", "CH₄ por t"]], use_container_width=True)
            
            # Adicionar nota sobre projeção
            st.caption(f"*Nota: Para {anos_projecao} anos, multiplique os valores acima por {anos_projecao} para obter os totais acumulados*")
        
        # =========================================================
        # ℹ️ Notas Técnicas
        # =========================================================
        st.markdown("---")
        with st.expander("📋 Notas Técnicas sobre os Cálculos"):
            st.markdown(f"""
            **Metodologia de Cálculo:**
            
            1. **Período de Projeção:** {anos_projecao} anos
            2. **Massa Considerada:** Dados anuais do SNIS multiplicados por {anos_projecao} anos
            3. **Fator de Correção de Metano (MCF):**
               - **MCF = 1.0**: Aterro sanitário gerenciado com cobertura diária e sistema de coleta de gás
               - **MCF = 0.8**: Aterro sanitário não gerenciado (sem coleta de gás, mas com cobertura)
               - **MCF = 0.4**: Aterro controlado ou lixão (sem cobertura sistemática)
            
            4. **Parâmetros IPCC 2006 para resíduos de poda:**
               - DOC (Degradable Organic Carbon) = 0.15
               - DOCf = 0.0147 × Temperatura(°C) + 0.28
               - F (Fraction of CH4 in landfill gas) = 0.5
               - OX (Oxidation factor) = 0.1
               - Ri (Recovery factor) = 0.0 (sem recuperação de gás)
            
            5. **Emissões de tratamento biológico (Yang et al., 2017):**
               - Compostagem: 0.0004 kg CH4/kg resíduo
               - Vermicompostagem: 0.00015 kg CH4/kg resíduo
            
            6. **Equivalência CO₂:**
               - GWP100 do CH₄ = 28 (IPCC AR6, 2021)
            
            7. **Cotação do Carbono:**
               - Preço atual: {moeda_carbono} {formatar_br(preco_carbono)}/tCO₂eq
               - Fonte: {fonte_carbono}
               - Câmbio EUR/BRL: R$ {formatar_br(taxa_cambio)}
            
            **Considerações para o contexto brasileiro:**
            - A maioria dos "aterros sanitários" no Brasil opera com MCF entre 0.6-0.8
            - Poucos aterros têm sistemas eficientes de coleta de biogás
            - Este cálculo considera o pior cenário (sem recuperação de gás)
            - As cotações são atualizadas automaticamente ao acessar o aplicativo
            - Valores acumulados representam a projeção para {anos_projecao} anos
            """)
    
    else:
        st.info("✅ Não há massa de podas e galhadas destinada a aterros. Todo o material já está sendo direcionado para tratamentos adequados!")
    
else:
    st.info("Não há dados de podas e galhadas para o município selecionado.")

# =========================================================
# Rodapé
# =========================================================
st.markdown("---")
st.caption(f"Fonte: SNIS – Sistema Nacional de Informações sobre Saneamento | Metodologia: IPCC 2006, Yang et al. (2017) | Período: {anos_projecao} anos | Cotações atualizadas automaticamente via Investing.com e APIs de câmbio")
