import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import seaborn as sns
from matplotlib.ticker import FuncFormatter
from io import BytesIO
import requests
import warnings
import unicodedata

# =============================================================================
# CONFIGURAÇÕES INICIAIS
# =============================================================================
st.set_page_config(
    page_title="SINISA + Cálculo de Metano - Análise Integrada", 
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
# FUNÇÕES PARA CÁLCULO DE METANO (MÉTODO CORRIGIDO)
# =============================================================================

def calcular_metano_aterro(residuos_kg, umidade, temperatura, doc_val, dias=7300):
    """
    Calcula o potencial de geração de metano de resíduos no aterro
    Baseado na metodologia IPCC 2006 - Kernel NÃO normalizado (20 anos)
    """
    # Parâmetros fixos (IPCC 2006)
    MCF = 1.0   # Fator de correção de metano (para aterros sanitários)
    F = 0.5     # Fração de metano no biogás
    OX = 0.1    # Fator de oxidação
    Ri = 0.0    # Metano recuperado
    
    # DOCf calculado pela temperatura (DOCf = 0.0147 × T + 0.28)
    DOCf = 0.0147 * temperatura + 0.28
    
    # Cálculo do potencial de metano por kg de resíduo
    potencial_CH4_por_kg = doc_val * DOCf * MCF * F * (16/12) * (1 - Ri) * (1 - OX)
    
    # Potencial total
    potencial_CH4_total = residuos_kg * potencial_CH4_por_kg
    
    # Taxa de decaimento anual (k = 0.06 por ano)
    k_ano = 0.06
    k_dia = k_ano / 365.0
    
    # Kernel de decaimento NÃO normalizado (IPCC correto)
    t = np.arange(1, dias + 1, dtype=float)
    kernel_ch4 = np.exp(-k_dia * (t - 1)) - np.exp(-k_dia * t)
    kernel_ch4 = np.maximum(kernel_ch4, 0)
    
    # Emissões distribuídas no tempo (NÃO normalizar!)
    emissoes_CH4 = potencial_CH4_total * kernel_ch4
    
    # Fração total emitida no período
    fracao_total_emitida = kernel_ch4.sum()
    
    return emissoes_CH4.sum(), potencial_CH4_total, DOCf, fracao_total_emitida

def calcular_metano_compostagem_termofilica(residuos_kg, umidade):
    """
    Calcula emissões de metano na compostagem termofílica
    Baseado em Yang et al. (2017) - processo de 50 dias
    """
    # Parâmetros fixos para compostagem termofílica
    TOC = 0.436  # Fração de carbono orgânico total
    CH4_C_FRAC = 0.006  # Fração do TOC emitida como CH4-C (0.6%)
    fracao_ms = 1 - umidade  # Fração de matéria seca
    
    # Metano total
    ch4_total = residuos_kg * (TOC * CH4_C_FRAC * (16/12) * fracao_ms)
    
    return ch4_total

def calcular_metano_vermicompostagem(residuos_kg, umidade):
    """
    Calcula emissões de metano na vermicompostagem
    Baseado em Yang et al. (2017) - processo de 50 dias
    """
    # Parâmetros fixos para vermicompostagem
    TOC = 0.436  # Fração de carbono orgânico total
    CH4_C_FRAC = 0.13 / 100  # Fração do TOC emitida como CH4-C (0.13%)
    fracao_ms = 1 - umidade  # Fração de matéria seca
    
    # Metano total
    ch4_total = residuos_kg * (TOC * CH4_C_FRAC * (16/12) * fracao_ms)
    
    return ch4_total

# =============================================================================
# FUNÇÕES PARA CARREGAMENTO E ANÁLISE DOS DADOS SINISA
# =============================================================================

@st.cache_data(ttl=3600)
def carregar_dados_sinisa():
    """
    Carrega os dados do SINISA a partir do GitHub
    """
    try:
        # URL do arquivo Excel no GitHub
        EXCEL_URL = "https://github.com/loopvinyl/tco2eqv7/raw/main/rsuBrasil.xlsx"
        
        # Download do arquivo
        response = requests.get(EXCEL_URL, timeout=60)
        response.raise_for_status()
        excel_file = BytesIO(response.content)
        
        # Carregar como Excel
        xls = pd.ExcelFile(excel_file)
        
        # Carregar aba específica
        df_raw = pd.read_excel(xls, sheet_name="Manejo_Coleta_e_Destinação", header=None)
        
        # Encontrar linha de cabeçalho
        header_row = None
        for i in range(min(15, len(df_raw))):
            row_vals = df_raw.iloc[i].astype(str).str.lower().values
            if any('col_' in v or 'massa' in v or 'destino' in v for v in row_vals):
                header_row = i
                break
        
        if header_row is None:
            df = pd.read_excel(xls, sheet_name="Manejo_Coleta_e_Destinação")
        else:
            df = pd.read_excel(xls, sheet_name="Manejo_Coleta_e_Destinação", header=header_row)
        
        # Aplicar filtro: apenas registros com 'Sim' na primeira coluna
        primeira_col = df.columns[0]
        df_filtrado = df[df[primeira_col] == 'Sim'].copy()
        
        # Limpeza básica
        df_filtrado = df_filtrado.replace(['', ' ', 'NaN', 'nan', 'NaT', 'None'], np.nan)
        
        return df_filtrado
        
    except Exception as e:
        st.error(f"Erro ao carregar dados SINISA: {str(e)}")
        return None

def identificar_colunas_sinisa(df):
    """
    Identifica automaticamente as colunas principais no dataset SINISA
    """
    colunas = {}
    
    # Mapeamento baseado nas colunas reais do SINISA
    mapeamento = {
        'Município': ['município', 'municipio', 'cidade', 'local', 'nom_mun', 'localidade'],
        'Estado': ['uf', 'estado', 'unidade da federação'],
        'Região': ['região', 'regiao', 'nom_região', 'grande região', 'macrorregião'],
        'População': ['população', 'populacao', 'habitantes', 'hab', 'pop', 'dfe0001', 'população total'],
        'Tipo_Coleta': ['tipo de coleta executada', 'tipo_coleta', 'modalidade_coleta', 'gtr1001'],
        'Massa_Total': ['massa de resíduos sólidos total coletada', 'massa total', 'toneladas', 'gtr1008'],
        'Destino_Codigo': ['tipo de unidade de destino', 'código destino', 'destino_codigo', 'gtr1011'],
        'Destino_Texto': ['tipo de unidade de destino', 'destino texto', 'destino_descricao', 'gtr1011'],
        'Agente_Executor': ['tipo de executor do serviço de destino dos resíduos', 'agente executor', 'executor', 'gtr1012'],
        'Secretaria': ['secretaria', 'setor responsável', 'cad1001', 'secretaria ou setor responsável']
    }
    
    for tipo, padroes in mapeamento.items():
        encontrada = False
        for col in df.columns:
            col_lower = str(col).lower()
            for padrao in padroes:
                if padrao in col_lower:
                    colunas[tipo] = col
                    encontrada = True
                    break
            if encontrada:
                break
    
    # Fallback para colunas por índice
    if 'Município' not in colunas and len(df.columns) > 2:
        colunas['Município'] = df.columns[2]
    if 'Estado' not in colunas and len(df.columns) > 3:
        colunas['Estado'] = df.columns[3]
    if 'Região' not in colunas and len(df.columns) > 4:
        colunas['Região'] = df.columns[4]
    if 'População' not in colunas and len(df.columns) > 9:
        colunas['População'] = df.columns[9]
    if 'Tipo_Coleta' not in colunas and len(df.columns) > 16:
        colunas['Tipo_Coleta'] = df.columns[16]
    if 'Massa_Total' not in colunas and len(df.columns) > 24:
        colunas['Massa_Total'] = df.columns[24]
    if 'Destino_Texto' not in colunas and len(df.columns) > 28:
        colunas['Destino_Texto'] = df.columns[28]
    if 'Agente_Executor' not in colunas and len(df.columns) > 29:
        colunas['Agente_Executor'] = df.columns[29]
    
    return colunas

def normalizar_texto(texto):
    """Normaliza texto removendo acentos e convertendo para minúsculas"""
    if pd.isna(texto):
        return ""
    texto = str(texto)
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto.lower().strip()

def buscar_municipio(df, municipio_nome, coluna_municipio):
    """Busca todas as linhas de um município"""
    if coluna_municipio not in df.columns:
        return None
    
    municipio_busca = normalizar_texto(municipio_nome)
    df_temp = df.copy()
    df_temp['_temp_norm'] = df_temp[coluna_municipio].apply(normalizar_texto)
    
    mask_exato = df_temp['_temp_norm'] == municipio_busca
    
    if not mask_exato.any():
        partes = [p for p in municipio_busca.split() if len(p) > 2]
        if len(partes) > 1:
            mask_parte = pd.Series(True, index=df_temp.index)
            for parte in partes:
                mask_parte = mask_parte & df_temp['_temp_norm'].str.contains(parte, na=False)
            mask = mask_parte
        else:
            mask = df_temp['_temp_norm'].str.contains(municipio_busca[:5], na=False)
    else:
        mask = mask_exato
    
    return df_temp[mask].copy()

def classificar_fração_organica(tipo_coleta):
    """
    Classifica a fração orgânica baseada no tipo de coleta
    Baseado nas categorias do SINISA
    """
    if pd.isna(tipo_coleta):
        return 0.10  # Valor padrão conservador
    
    tipo_coleta_str = str(tipo_coleta).lower()
    
    # Categorias com alta fração orgânica (vegetais, frutas, orgânicos)
    categorias_alta_organica = [
        'domiciliar', 'residencial', 'doméstica', 'domicilia',
        'orgânico', 'organico', 'verde', 'vegetal', 'fruta',
        'alimento', 'resto de comida', 'restos alimentares',
        'podas', 'jardinagem', 'hortifruti'
    ]
    
    # Categorias com média fração orgânica
    categorias_media_organica = [
        'comercial', 'serviços', 'pública', 'varrição',
        'limpeza urbana', 'feira', 'mercado'
    ]
    
    # Categorias com baixa fração orgânica
    categorias_baixa_organica = [
        'industrial', 'construção civil', 'entulho',
        'saúde', 'hospitalar', 'saneamento',
        'seletiva', 'recicláveis', 'plástico', 'papel',
        'metal', 'vidro'
    ]
    
    # Verificar categorias
    for termo in categorias_alta_organica:
        if termo in tipo_coleta_str:
            return 0.60  # 60% orgânico
    
    for termo in categorias_media_organica:
        if termo in tipo_coleta_str:
            return 0.40  # 40% orgânico
    
    for termo in categorias_baixa_organica:
        if termo in tipo_coleta_str:
            return 0.10  # 10% orgânico
    
    return 0.30  # Valor padrão para tipos não classificados

# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def formatar_br(numero):
    """Formata números no padrão brasileiro: 1.234,56"""
    if pd.isna(numero) or numero is None:
        return "N/A"
    
    numero = round(float(numero), 2)
    return f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

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
# APLICATIVO PRINCIPAL
# =============================================================================

# Título principal
st.title("🌱 SINISA + Cálculo de Metano - Análise Integrada")
st.markdown("""
**Integração dos dados do SINISA 2023 com cálculos de metano para diferentes tecnologias**  
**Método Corrigido:** Kernel NÃO normalizado para aterro (metodologia IPCC correta)  
**Período:** Projeção para 20 anos (7.300 dias)  
**Foco:** Análise da fração orgânica baseada no "Tipo de coleta executada"
""")

# Carregar dados SINISA
st.header("📥 Carregamento de Dados SINISA 2023")

with st.spinner("Carregando dados do SINISA 2023..."):
    df_sinisa = carregar_dados_sinisa()

if df_sinisa is None:
    st.error("Não foi possível carregar os dados do SINISA. Verifique a conexão.")
    st.stop()

# Identificar colunas
colunas = identificar_colunas_sinisa(df_sinisa)

# Sidebar com configurações
with st.sidebar:
    st.header("⚙️ Configurações da Análise")
    
    # Seção de municípios
    st.subheader("🏙️ Seleção de Município")
    
    # Sugestões de municípios comuns
    municipios_sugeridos = [
        "RIBEIRÃO PRETO",
        "SÃO PAULO", 
        "RIO DE JANEIRO",
        "BELO HORIZONTE",
        "SALVADOR",
        "FORTALEZA",
        "BRASÍLIA",
        "CURITIBA",
        "MANAUS",
        "RECIFE"
    ]
    
    municipio_selecionado = st.selectbox(
        "Escolha um município:",
        municipios_sugeridos,
        key="select_municipio"
    )
    
    # Campo para buscar outros municípios
    outro_municipio = st.text_input("Ou digite outro município:")
    if outro_municipio:
        municipio_selecionado = outro_municipio.upper()
    
    st.markdown("---")
    
    # Parâmetros de cálculo
    st.subheader("🔬 Parâmetros de Cálculo")
    
    anos_simulacao = st.slider(
        "Anos de simulação", 
        1, 50, 20, 1,
        help="Período total da simulação em anos"
    )
    
    dias_simulacao = anos_simulacao * 365
    
    umidade = st.slider(
        "Umidade dos resíduos (%)", 
        50, 95, 85, 1
    ) / 100.0
    
    temperatura = st.slider(
        "Temperatura média (°C)", 
        15, 35, 25, 1
    )
    
    doc_val = st.slider(
        "DOC - Carbono Orgânico Degradável (fração)", 
        0.10, 0.50, 0.15, 0.01,
        help="Fração de carbono orgânico degradável nos resíduos"
    )
    
    st.markdown("---")
    
    # Opções de análise
    st.subheader("📊 Opções de Análise")
    
    mostrar_detalhes = st.checkbox("Mostrar detalhes por rota", value=False)
    usar_gwp = st.checkbox("Converter para CO₂eq (GWP 20 anos)", value=True)
    
    if usar_gwp:
        gwp_ch4 = st.number_input(
            "GWP CH₄ (20 anos)", 
            min_value=20.0, 
            max_value=100.0, 
            value=79.7, 
            step=0.1,
            help="Potencial de Aquecimento Global do metano para 20 anos"
        )
    
    st.markdown("---")
    
    # Botão de cálculo
    if st.button("🚀 Calcular Emissões", type="primary"):
        st.session_state.calcular_emissoes = True

# Buscar dados do município selecionado
if 'Município' in colunas:
    dados_municipio = buscar_municipio(df_sinisa, municipio_selecionado, colunas['Município'])
    
    if dados_municipio is not None and len(dados_municipio) > 0:
        st.success(f"✅ Município encontrado: {municipio_selecionado}")
        st.info(f"**{len(dados_municipio)}** rotas de coleta encontradas")
        
        # Exibir informações básicas
        col_info1, col_info2 = st.columns(2)
        
        with col_info1:
            st.subheader("📋 Informações do Município")
            
            primeiro_registro = dados_municipio.iloc[0]
            
            if 'Estado' in colunas and colunas['Estado'] in primeiro_registro:
                st.markdown(f"**Estado:** {primeiro_registro[colunas['Estado']]}")
            
            if 'Região' in colunas and colunas['Região'] in primeiro_registro:
                st.markdown(f"**Região:** {primeiro_registro[colunas['Região']]}")
            
            # População
            if 'População' in colunas and colunas['População'] in dados_municipio.columns:
                populacao_valores = dados_municipio[colunas['População']].dropna().unique()
                if len(populacao_valores) > 0:
                    st.markdown(f"**População:** {formatar_br(float(populacao_valores[0]))} hab")
        
        with col_info2:
            st.subheader("📊 Resumo das Rotas")
            
            # Massa total
            if 'Massa_Total' in colunas:
                massa_total = dados_municipio[colunas['Massa_Total']].sum()
                st.metric(
                    "Massa Total Coletada",
                    f"{formatar_br(massa_total)} t/ano",
                    help="Soma de todas as rotas do município"
                )
            
            # Tipos de coleta únicos
            if 'Tipo_Coleta' in colunas:
                tipos_coleta = dados_municipio[colunas['Tipo_Coleta']].dropna().unique()
                st.metric(
                    "Tipos de Coleta",
                    f"{len(tipos_coleta)}",
                    help="Diferentes tipos de coleta no município"
                )
        
        # Tabela resumida das rotas
        with st.expander("📋 Ver todas as rotas de coleta"):
            colunas_para_mostrar = []
            
            for tipo, col in colunas.items():
                if tipo in ['Tipo_Coleta', 'Massa_Total', 'Destino_Texto', 'Agente_Executor']:
                    if col in dados_municipio.columns:
                        colunas_para_mostrar.append(col)
            
            if colunas_para_mostrar:
                dados_display = dados_municipio[colunas_para_mostrar].copy()
                dados_display.insert(0, 'Nº', range(1, len(dados_display) + 1))
                
                # Formatar massa
                if 'Massa_Total' in colunas and colunas['Massa_Total'] in dados_display.columns:
                    dados_display[colunas['Massa_Total']] = dados_display[colunas['Massa_Total']].apply(
                        lambda x: formatar_br(x) if pd.notna(x) else "N/A"
                    )
                
                st.dataframe(dados_display, use_container_width=True, height=300)
        
        # Executar cálculos se solicitado
        if st.session_state.get('calcular_emissoes', False):
            st.header("🔬 Cálculo de Emissões de Metano")
            
            with st.spinner(f'Calculando emissões para {len(dados_municipio)} rotas...'):
                
                # Inicializar arrays para resultados
                resultados = []
                
                # Processar cada rota
                for idx, rota in dados_municipio.iterrows():
                    # Obter massa total da rota
                    if 'Massa_Total' in colunas and colunas['Massa_Total'] in rota:
                        massa_rota_ton = rota[colunas['Massa_Total']]
                        if pd.isna(massa_rota_ton) or massa_rota_ton <= 0:
                            continue
                    else:
                        continue
                    
                    # Obter tipo de coleta
                    tipo_coleta = ""
                    if 'Tipo_Coleta' in colunas and colunas['Tipo_Coleta'] in rota:
                        tipo_coleta = rota[colunas['Tipo_Coleta']]
                    
                    # Classificar fração orgânica baseada no tipo de coleta
                    fracao_organica = classificar_fração_organica(tipo_coleta)
                    
                    # Calcular massa orgânica (em kg)
                    massa_organica_kg = massa_rota_ton * fracao_organica * 1000
                    
                    # Calcular emissões para cada tecnologia
                    # Aterro
                    ch4_aterro, potencial_aterro, DOCf, fracao_emitida = calcular_metano_aterro(
                        massa_organica_kg, umidade, temperatura, doc_val, dias_simulacao
                    )
                    
                    # Compostagem Termofílica
                    ch4_compost = calcular_metano_compostagem_termofilica(
                        massa_organica_kg, umidade
                    )
                    
                    # Vermicompostagem
                    ch4_vermi = calcular_metano_vermicompostagem(
                        massa_organica_kg, umidade
                    )
                    
                    # Armazenar resultados
                    resultados.append({
                        'Tipo_Coleta': tipo_coleta if tipo_coleta else "Não informado",
                        'Massa_Total_ton': massa_rota_ton,
                        'Fração_Orgânica': fracao_organica,
                        'Massa_Orgânica_kg': massa_organica_kg,
                        'CH4_Aterro_kg': ch4_aterro,
                        'CH4_Compostagem_kg': ch4_compost,
                        'CH4_Vermicompostagem_kg': ch4_vermi,
                        'Redução_Compost_vs_Aterro_kg': ch4_aterro - ch4_compost,
                        'Redução_Vermi_vs_Aterro_kg': ch4_aterro - ch4_vermi
                    })
                
                # Criar DataFrame com resultados
                if resultados:
                    df_resultados = pd.DataFrame(resultados)
                    
                    # Calcular totais
                    totais = {
                        'Massa_Total_ton': df_resultados['Massa_Total_ton'].sum(),
                        'Massa_Orgânica_kg': df_resultados['Massa_Orgânica_kg'].sum(),
                        'CH4_Aterro_kg': df_resultados['CH4_Aterro_kg'].sum(),
                        'CH4_Compostagem_kg': df_resultados['CH4_Compostagem_kg'].sum(),
                        'CH4_Vermicompostagem_kg': df_resultados['CH4_Vermicompostagem_kg'].sum()
                    }
                    
                    totais['Redução_Compost_vs_Aterro_kg'] = totais['CH4_Aterro_kg'] - totais['CH4_Compostagem_kg']
                    totais['Redução_Vermi_vs_Aterro_kg'] = totais['CH4_Aterro_kg'] - totais['CH4_Vermicompostagem_kg']
                    
                    # Calcular percentuais de redução
                    totais['Redução_Compost_%'] = (totais['Redução_Compost_vs_Aterro_kg'] / totais['CH4_Aterro_kg'] * 100) if totais['CH4_Aterro_kg'] > 0 else 0
                    totais['Redução_Vermi_%'] = (totais['Redução_Vermi_vs_Aterro_kg'] / totais['CH4_Aterro_kg'] * 100) if totais['CH4_Aterro_kg'] > 0 else 0
                    
                    # 1. EXIBIR RESULTADOS PRINCIPAIS
                    st.header("📊 Resultados Principais")
                    
                    col_res1, col_res2, col_res3 = st.columns(3)
                    
                    with col_res1:
                        st.metric(
                            "Aterro Sanitário",
                            f"{formatar_br(totais['CH4_Aterro_kg'])} kg CH₄",
                            f"{formatar_br(totais['CH4_Aterro_kg']/1000)} ton",
                            delta_color="off"
                        )
                    
                    with col_res2:
                        st.metric(
                            "Compostagem Termofílica",
                            f"{formatar_br(totais['CH4_Compostagem_kg'])} kg CH₄",
                            f"-{formatar_br(totais['Redução_Compost_%'])}%",
                            delta_color="inverse"
                        )
                    
                    with col_res3:
                        st.metric(
                            "Vermicompostagem",
                            f"{formatar_br(totais['CH4_Vermicompostagem_kg'])} kg CH₄",
                            f"-{formatar_br(totais['Redução_Vermi_%'])}%",
                            delta_color="inverse"
                        )
                    
                    # Informação sobre fração orgânica
                    st.info(f"""
                    **📈 Análise da Fração Orgânica:**
                    - **Massa total coletada:** {formatar_br(totais['Massa_Total_ton'])} ton/ano
                    - **Massa orgânica estimada:** {formatar_br(totais['Massa_Orgânica_kg']/1000)} ton/ano
                    - **Fração orgânica média:** {(totais['Massa_Orgânica_kg']/(totais['Massa_Total_ton']*1000)*100):.1f}%
                    - **Método:** Classificação automática baseada no "Tipo de coleta executada"
                    """)
                    
                    # 2. GRÁFICO COMPARATIVO
                    st.subheader("📈 Comparação de Emissões por Tecnologia")
                    
                    fig, ax = plt.subplots(figsize=(10, 6))
                    
                    tecnologias = ['Aterro', 'Compostagem\nTermofílica', 'Vermicompostagem']
                    valores = [
                        totais['CH4_Aterro_kg'],
                        totais['CH4_Compostagem_kg'],
                        totais['CH4_Vermicompostagem_kg']
                    ]
                    cores = ['#e74c3c', '#3498db', '#2ecc71']
                    
                    bars = ax.bar(tecnologias, valores, color=cores)
                    ax.set_ylabel('Metano Total (kg CH₄)')
                    ax.set_title(f'Emissões Totais de Metano - {municipio_selecionado} ({anos_simulacao} anos)')
                    ax.grid(True, alpha=0.3, axis='y')
                    ax.yaxis.set_major_formatter(FuncFormatter(br_format))
                    
                    for bar, val in zip(bars, valores):
                        height = bar.get_height()
                        ax.text(bar.get_x() + bar.get_width()/2, height,
                               f'{formatar_br(val)}', ha='center', va='bottom', fontweight='bold')
                    
                    st.pyplot(fig)
                    
                    # 3. GRÁFICO DE REDUÇÃO
                    st.subheader("📉 Redução de Emissões vs Aterro")
                    
                    fig, ax = plt.subplots(figsize=(10, 6))
                    
                    reducoes = [
                        totais['Redução_Compost_vs_Aterro_kg'],
                        totais['Redução_Vermi_vs_Aterro_kg']
                    ]
                    reducoes_percent = [
                        totais['Redução_Compost_%'],
                        totais['Redução_Vermi_%']
                    ]
                    tecnologias_reducao = ['Compostagem\nTermofílica', 'Vermicompostagem']
                    cores_reducao = ['#3498db', '#2ecc71']
                    
                    x = np.arange(len(tecnologias_reducao))
                    width = 0.35
                    
                    ax.bar(x - width/2, reducoes, width, label='Redução (kg CH₄)', color=cores_reducao)
                    ax.set_ylabel('Redução (kg CH₄)')
                    ax.set_xlabel('Tecnologia')
                    ax.set_title('Redução de Emissões vs Cenário Aterro')
                    ax.set_xticks(x)
                    ax.set_xticklabels(tecnologias_reducao)
                    ax.yaxis.set_major_formatter(FuncFormatter(br_format))
                    
                    # Adicionar percentuais
                    ax2 = ax.twinx()
                    ax2.bar(x + width/2, reducoes_percent, width, label='Redução (%)', 
                           color=[c.replace('0.7', '0.4') for c in cores_reducao], alpha=0.7)
                    ax2.set_ylabel('Redução (%)')
                    
                    # Adicionar valores nos gráficos
                    for i, (kg, perc) in enumerate(zip(reducoes, reducoes_percent)):
                        ax.text(i - width/2, kg, f'{formatar_br(kg)} kg', 
                               ha='center', va='bottom', fontweight='bold')
                        ax2.text(i + width/2, perc, f'{perc:.1f}%', 
                                ha='center', va='bottom', fontweight='bold')
                    
                    ax.grid(True, alpha=0.3)
                    st.pyplot(fig)
                    
                    # 4. CONVERSÃO PARA CO₂eq (opcional)
                    if usar_gwp:
                        st.subheader("🌍 Conversão para CO₂eq (GWP 20 anos)")
                        
                        # Converter para CO₂eq
                        co2eq_aterro = totais['CH4_Aterro_kg'] * gwp_ch4 / 1000
                        co2eq_compost = totais['CH4_Compostagem_kg'] * gwp_ch4 / 1000
                        co2eq_vermi = totais['CH4_Vermicompostagem_kg'] * gwp_ch4 / 1000
                        
                        col_co2eq1, col_co2eq2, col_co2eq3 = st.columns(3)
                        
                        with col_co2eq1:
                            st.metric(
                                "Aterro (CO₂eq)",
                                f"{formatar_br(co2eq_aterro)} t",
                                f"GWP = {gwp_ch4}"
                            )
                        
                        with col_co2eq2:
                            reducao_co2eq_compost = co2eq_aterro - co2eq_compost
                            st.metric(
                                "Compostagem (CO₂eq)",
                                f"{formatar_br(co2eq_compost)} t",
                                f"-{formatar_br(reducao_co2eq_compost)} t",
                                delta_color="inverse"
                            )
                        
                        with col_co2eq3:
                            reducao_co2eq_vermi = co2eq_aterro - co2eq_vermi
                            st.metric(
                                "Vermicompostagem (CO₂eq)",
                                f"{formatar_br(co2eq_vermi)} t",
                                f"-{formatar_br(reducao_co2eq_vermi)} t",
                                delta_color="inverse"
                            )
                        
                        # Comparação com Script 2
                        if massa_organica_kg > 0:
                            # Calcular para 100 kg/dia equivalente
                            equivalente_100kg_dia = (totais['Massa_Orgânica_kg'] / 365) / 100
                            st.info(f"""
                            **🔗 Comparação com Script 2 (Tabela 18):**
                            
                            **Equivalente a:** {formatar_br(equivalente_100kg_dia)} × 100 kg/dia
                            **CO₂eq evitado (vermicompostagem):** {formatar_br(reducao_co2eq_vermi)} t
                            
                            *Script 2 mostra 1.405,87 t CO₂eq para 100 kg/dia × 20 anos com vermicompostagem*
                            """)
                    
                    # 5. ANÁLISE POR TIPO DE COLETA
                    if mostrar_detalhes and len(df_resultados) > 1:
                        st.subheader("📋 Análise Detalhada por Tipo de Coleta")
                        
                        # Agrupar por tipo de coleta
                        grupo_tipo_coleta = df_resultados.groupby('Tipo_Coleta').agg({
                            'Massa_Total_ton': 'sum',
                            'Fração_Orgânica': 'mean',
                            'CH4_Aterro_kg': 'sum',
                            'CH4_Compostagem_kg': 'sum',
                            'CH4_Vermicompostagem_kg': 'sum'
                        }).reset_index()
                        
                        # Calcular percentuais
                        grupo_tipo_coleta['Redução_Compost_%'] = (
                            (grupo_tipo_coleta['CH4_Aterro_kg'] - grupo_tipo_coleta['CH4_Compostagem_kg']) / 
                            grupo_tipo_coleta['CH4_Aterro_kg'] * 100
                        ).round(1)
                        
                        grupo_tipo_coleta['Redução_Vermi_%'] = (
                            (grupo_tipo_coleta['CH4_Aterro_kg'] - grupo_tipo_coleta['CH4_Vermicompostagem_kg']) / 
                            grupo_tipo_coleta['CH4_Aterro_kg'] * 100
                        ).round(1)
                        
                        # Ordenar por massa
                        grupo_tipo_coleta = grupo_tipo_coleta.sort_values('Massa_Total_ton', ascending=False)
                        
                        # Exibir tabela
                        st.dataframe(grupo_tipo_coleta, use_container_width=True)
                        
                        # Gráfico de contribuição por tipo de coleta
                        fig, ax = plt.subplots(figsize=(12, 6))
                        
                        # Agrupar tipos menores em "Outros"
                        if len(grupo_tipo_coleta) > 8:
                            principal = grupo_tipo_coleta.head(7)
                            outros = grupo_tipo_coleta.iloc[7:].sum()
                            outros['Tipo_Coleta'] = 'Outros'
                            principal = pd.concat([principal, pd.DataFrame([outros])], ignore_index=True)
                        else:
                            principal = grupo_tipo_coleta.copy()
                        
                        ax.pie(principal['Massa_Total_ton'], 
                              labels=principal['Tipo_Coleta'],
                              autopct='%1.1f%%',
                              startangle=90)
                        ax.set_title('Distribuição da Massa por Tipo de Coleta')
                        
                        st.pyplot(fig)
                    
                    # 6. RESUMO FINAL
                    st.subheader("📄 Resumo Executivo")
                    
                    col_resumo1, col_resumo2 = st.columns(2)
                    
                    with col_resumo1:
                        st.markdown("**🌱 Benefícios Ambientais:**")
                        st.markdown(f"""
                        - **Metano evitado com compostagem:** {formatar_br(totais['Redução_Compost_vs_Aterro_kg'])} kg CH₄
                        - **Metano evitado com vermicompostagem:** {formatar_br(totais['Redução_Vermi_vs_Aterro_kg'])} kg CH₄
                        - **Redução percentual máxima:** {totais['Redução_Vermi_%']:.1f}% (vermicompostagem)
                        """)
                        
                        if usar_gwp:
                            st.markdown(f"""
                            - **CO₂eq evitado com compostagem:** {formatar_br(reducao_co2eq_compost)} t
                            - **CO₂eq evitado com vermicompostagem:** {formatar_br(reducao_co2eq_vermi)} t
                            """)
                    
                    with col_resumo2:
                        st.markdown("**📊 Dados do Município:**")
                        st.markdown(f"""
                        - **Município:** {municipio_selecionado}
                        - **Rotas analisadas:** {len(dados_municipio)}
                        - **Massa total anual:** {formatar_br(totais['Massa_Total_ton'])} ton
                        - **Fração orgânica estimada:** {(totais['Massa_Orgânica_kg']/(totais['Massa_Total_ton']*1000)*100):.1f}%
                        - **Período de análise:** {anos_simulacao} anos ({dias_simulacao} dias)
                        """)
                    
                    # 7. RECOMENDAÇÕES
                    st.subheader("💡 Recomendações Técnicas")
                    
                    if totais['Redução_Vermi_%'] > 90:
                        st.success("""
                        **✅ Prioridade Alta para Vermicompostagem:**
                        - Vermicompostagem reduz mais de 90% das emissões vs aterro
                        - Recomenda-se implementação em larga escala
                        - Benefício máximo para resíduos com alta fração orgânica
                        """)
                    elif totais['Redução_Compost_%'] > 80:
                        st.info("""
                        **📈 Compostagem como Alternativa Viável:**
                        - Compostagem termofílica reduz mais de 80% das emissões
                        - Tecnologia mais simples que vermicompostagem
                        - Adequada para municípios com menor capacidade técnica
                        """)
                    else:
                        st.warning("""
                        **⚠️ Potencial Limitado de Redução:**
                        - Fração orgânica relativamente baixa
                        - Considerar separação na fonte para aumentar eficiência
                        - Avaliar outros benefícios (reciclagem, reutilização)
                        """)
                    
                else:
                    st.warning("Não foi possível calcular emissões para este município.")
    
    else:
        st.warning(f"Município '{municipio_selecionado}' não encontrado nos dados SINISA.")
        
        # Sugestões
        st.info("""
        **Sugestões:**
        1. Verifique a grafia do município
        2. Use acentos corretamente
        3. Tente o nome completo (ex: "SÃO PAULO" em vez de "SP")
        4. Verifique se o município respondeu ao SINISA 2023
        """)
else:
    st.error("Não foi possível identificar a coluna de municípios no dataset.")

# =============================================================================
# RODAPÉ
# =============================================================================
st.markdown("---")
st.markdown("""
**📚 Fontes e Metodologia:**
- **Dados:** SINISA 2023 - Sistema Nacional de Informações sobre Saneamento
- **Cálculo Aterro:** IPCC (2006) - Guidelines for National Greenhouse Gas Inventories
- **Cálculo Compostagem/Vermicompostagem:** Yang et al. (2017)
- **Classificação Fração Orgânica:** Baseada em "Tipo de coleta executada"
- **Método Corrigido:** Kernel NÃO normalizado para aterro

**⚙️ Parâmetros Padrão:**
- **Período:** 20 anos (7.300 dias)
- **Umidade:** 85%
- **Temperatura:** 25°C
- **DOC:** 0.15 (fração de carbono orgânico degradável)
- **GWP CH₄ (20 anos):** 79.7 (IPCC AR6)

**🔍 Classificação de Fração Orgânica:**
- **Alta (60%):** Domiciliar, orgânico, vegetal, fruta, alimento
- **Média (40%):** Comercial, serviços, pública, varrição
- **Baixa (10%):** Industrial, construção, saúde, seletiva
- **Padrão (30%):** Tipos não classificados
""")
