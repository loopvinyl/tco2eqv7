import streamlit as st
import pandas as pd
import numpy as np
import unicodedata
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests
import io

# =========================================================
# Configuração da página
# =========================================================
st.set_page_config(
    page_title="Análise de Resíduos Sólidos - SNIS 2023-2024",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🌍 Análise de Resíduos Sólidos Urbanos - SNIS 2023-2024")
st.markdown("""
Esta aplicação analisa dados do **Sistema Nacional de Informações sobre Saneamento (SNIS)** 
para os anos de 2023 e 2024, focando em:
- **Potencial de compostagem** de resíduos orgânicos
- **Disposição final** e destinação adequada
- **Emissões de metano (CH₄)** e potencial de redução
- **Comparativo entre anos** para análise de tendências
""")

# =========================================================
# Funções auxiliares
# =========================================================
def formatar_numero_br(valor, casas_decimais=2):
    """Formata números no padrão brasileiro"""
    if pd.isna(valor) or valor is None:
        return "Não informado"
    try:
        num = float(valor)
        if num == 0:
            return "0"
        formato = f"{{:,.{casas_decimais}f}}".format(num)
        partes = formato.split(".")
        milhar = partes[0].replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{milhar},{partes[1]}"
    except:
        return "Não informado"

def formatar_massa_br(valor):
    """Formata valores de massa com unidade"""
    if pd.isna(valor) or valor is None:
        return "Não informado"
    return f"{formatar_numero_br(valor)} t"

def normalizar_texto(txt):
    """Normaliza texto removendo acentos e convertendo para maiúsculas"""
    if pd.isna(txt):
        return ""
    txt = unicodedata.normalize("NFKD", str(txt))
    txt = txt.encode("ASCII", "ignore").decode("utf-8")
    return txt.upper().strip()

def extrair_numero(texto):
    """Extrai número de strings que podem conter texto"""
    if pd.isna(texto):
        return 0
    try:
        # Remove caracteres não numéricos, exceto ponto e vírgula
        import re
        texto_str = str(texto)
        # Substitui vírgula por ponto para decimal
        texto_str = texto_str.replace(',', '.')
        # Encontra todos os números (incluindo decimais)
        numeros = re.findall(r"[-+]?\d*\.\d+|\d+", texto_str)
        if numeros:
            return float(numeros[0])
        return 0
    except:
        return 0

# =========================================================
# URLs dos arquivos no GitHub
# =========================================================
URL_2023 = "https://raw.githubusercontent.com/loopvinyl/tco2eqv7/main/rsuBrasil_2023.xlsx"
URL_2024 = "https://raw.githubusercontent.com/loopvinyl/tco2eqv7/main/rsuBrasil_2024.xlsx"

# =========================================================
# Funções para cálculos de emissões
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

def calcular_emissoes_aterro(massa_t, mcf, temperatura=25.0):
    """
    Calcula emissões de CH4 do aterro usando metodologia IPCC 2006.
    """
    # Parâmetros IPCC 2006 para resíduos orgânicos
    DOC = 0.15  # Fraction of degradable organic carbon
    DOCf = 0.0147 * temperatura + 0.28  # Decomposable fraction of DOC
    F = 0.5  # Fraction of methane in landfill gas
    OX = 0.1  # Oxidation factor
    Ri = 0.0  # Recovery factor (assumindo sem recuperação inicial)
    
    massa_kg = massa_t * 1000
    ch4_kg = massa_kg * DOC * DOCf * mcf * F * (16/12) * (1 - Ri) * (1 - OX)
    ch4_t = ch4_kg / 1000
    
    return ch4_t

def ch4_compostagem_total(massa_kg):
    """Emissões de CH4 da compostagem (Yang et al., 2017)"""
    return massa_kg * 0.0004  # kg CH4 / kg resíduo

def ch4_vermicompostagem_total(massa_kg):
    """Emissões de CH4 da vermicompostagem (Yang et al., 2017)"""
    return massa_kg * 0.00015  # kg CH4 / kg resíduo

# =========================================================
# Funções de carregamento de dados
# =========================================================
@st.cache_data(ttl=3600)  # Cache por 1 hora
def load_data_2023():
    """Carrega dados de 2023 do GitHub"""
    try:
        st.info("📥 Baixando dados de 2023 do GitHub...")
        
        # Baixar arquivo do GitHub
        response = requests.get(URL_2023)
        response.raise_for_status()  # Verifica se houve erro na requisição
        
        # Carregar Excel
        df = pd.read_excel(
            io.BytesIO(response.content),
            sheet_name="Manejo_Coleta_e_Destinação",
            header=13
        )
        
        # Limpar dados
        df = df.dropna(how='all')
        df.columns = [str(col).strip() for col in df.columns]
        
        # Renomear colunas importantes
        rename_dict = {}
        for i, col in enumerate(df.columns):
            if "Unnamed" in col:
                # Tentar identificar o conteúdo da primeira linha não nula
                first_val = df[col].dropna().iloc[0] if not df[col].dropna().empty else f"Col_{i}"
                rename_dict[col] = f"{first_val}"[:50]
            else:
                rename_dict[col] = col
        
        df = df.rename(columns=rename_dict)
        
        # Extrair números das colunas de massa
        colunas_massa = [col for col in df.columns if any(x in str(col).upper() for x in ['MASSA', 'PESO', 'TOTAL'])]
        for col in colunas_massa:
            if col in df.columns:
                df[f"{col}_NUM"] = df[col].apply(extrair_numero)
        
        st.success(f"✅ Dados 2023 carregados: {len(df)} registros")
        return df
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados 2023: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)  # Cache por 1 hora
def load_data_2024():
    """Carrega dados de 2024 do GitHub"""
    try:
        st.info("📥 Baixando dados de 2024 do GitHub...")
        
        # Baixar arquivo do GitHub
        response = requests.get(URL_2024)
        response.raise_for_status()  # Verifica se houve erro na requisição
        
        # Carregar Excel
        df = pd.read_excel(
            io.BytesIO(response.content),
            sheet_name="Disp_final_entradas_residuos",
            header=13
        )
        
        # Limpar dados
        df = df.dropna(how='all')
        df.columns = [str(col).strip() for col in df.columns]
        
        # Renomear colunas importantes baseado na análise
        rename_mapping = {}
        
        # Mapear colunas baseado na análise dos dados
        for i, col in enumerate(df.columns):
            col_name = str(col)
            # Tentar identificar pelo conteúdo das primeiras linhas
            if not df.empty and i < len(df.columns):
                sample_value = df.iloc[0, i] if not df.iloc[:, i].isnull().all() else ""
                
                if "COD_MUN" in col_name or "Código" in str(sample_value):
                    rename_mapping[col] = "COD_MUNICIPIO"
                elif "MUNIC" in col_name or isinstance(sample_value, str) and any(x in sample_value for x in ['Minas', 'Leão', 'Leopoldina']):
                    rename_mapping[col] = "MUNICIPIO"
                elif any(x in col_name.upper() for x in ['UF', 'ESTADO', 'SIGLA']):
                    rename_mapping[col] = "UF"
                elif any(x in col_name.upper() for x in ['REGIAO', 'MACRORREGIAO']):
                    rename_mapping[col] = "REGIAO"
                elif any(x in col_name.upper() for x in ['TIPO', 'UNIDADE', 'DISP', 'DESTINO']):
                    rename_mapping[col] = "TIPO_DESTINO"
                elif any(x in col_name.upper() for x in ['NOME', 'DENOMINACAO']):
                    rename_mapping[col] = "NOME_DESTINO"
                elif any(x in col_name.upper() for x in ['MASSA', 'PESO', 'QUANTIDADE', 'TON']):
                    rename_mapping[col] = "MASSA_TON"
        
        # Aplicar renomeação
        df = df.rename(columns=rename_mapping)
        
        # Se não encontrou coluna de massa, procurar por valores numéricos
        if "MASSA_TON" not in df.columns:
            for col in df.columns:
                # Verificar se a coluna tem valores que parecem ser massa
                if df[col].apply(lambda x: isinstance(x, (int, float)) or (isinstance(x, str) and any(c.isdigit() for c in str(x)))).any():
                    sample_vals = df[col].dropna().head(5)
                    if not sample_vals.empty and any(isinstance(v, (int, float)) or (isinstance(v, str) and any(c.isdigit() for c in str(v))) for v in sample_vals):
                        df = df.rename(columns={col: "MASSA_TON"})
                        break
        
        # Extrair números da coluna de massa
        if "MASSA_TON" in df.columns:
            df["MASSA_NUM"] = df["MASSA_TON"].apply(extrair_numero)
        else:
            # Se não encontrou, criar coluna vazia
            df["MASSA_NUM"] = 0
        
        st.success(f"✅ Dados 2024 carregados: {len(df)} registros")
        return df
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados 2024: {str(e)}")
        return pd.DataFrame()

# =========================================================
# Interface principal
# =========================================================
st.sidebar.header("⚙️ Configurações")

# Seleção de ano
ano_selecionado = st.sidebar.selectbox(
    "Selecione o ano de análise:",
    ["2023", "2024", "Comparativo 2023-2024"],
    index=0
)

# Botão para recarregar dados
if st.sidebar.button("🔄 Recarregar Dados"):
    st.cache_data.clear()
    st.rerun()

# Carregar dados conforme seleção
if "2023" in ano_selecionado:
    with st.spinner("Carregando dados de 2023..."):
        df_2023 = load_data_2023()
        dados_carregados_2023 = not df_2023.empty
else:
    df_2023 = pd.DataFrame()
    dados_carregados_2023 = False

if "2024" in ano_selecionado:
    with st.spinner("Carregando dados de 2024..."):
        df_2024 = load_data_2024()
        dados_carregados_2024 = not df_2024.empty
else:
    df_2024 = pd.DataFrame()
    dados_carregados_2024 = False

# Mostrar status de carregamento na sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Status dos Dados")

if dados_carregados_2023:
    st.sidebar.success(f"✅ 2023: {len(df_2023)} registros")
else:
    st.sidebar.error("❌ 2023: Não carregado")

if dados_carregados_2024:
    st.sidebar.success(f"✅ 2024: {len(df_2024)} registros")
else:
    st.sidebar.error("❌ 2024: Não carregado")

# Links para os arquivos originais
st.sidebar.markdown("---")
st.sidebar.subheader("🔗 Links dos Dados")
st.sidebar.markdown(f"[📄 Dados 2023 no GitHub]({URL_2023})")
st.sidebar.markdown(f"[📄 Dados 2024 no GitHub]({URL_2024})")

# =========================================================
# Análise para 2023
# =========================================================
if ano_selecionado == "2023" and dados_carregados_2023:
    st.header("📊 Análise de Manejo, Coleta e Destinação - 2023")
    
    # Estatísticas rápidas
    st.subheader("📈 Estatísticas Gerais")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total de Registros", f"{len(df_2023):,}")
    
    with col2:
        num_colunas = len(df_2023.columns)
        st.metric("Número de Colunas", num_colunas)
    
    with col3:
        # Tentar identificar municípios únicos
        col_municipio = None
        for col in df_2023.columns:
            if any(x in str(col).upper() for x in ['MUNIC', 'CIDADE', 'NOME']):
                col_municipio = col
                break
        
        if col_municipio:
            num_municipios = df_2023[col_municipio].nunique()
            st.metric("Municípios Únicos", f"{num_municipios:,}")
        else:
            st.metric("Municípios Únicos", "Não identificado")
    
    # Pré-visualização dos dados
    with st.expander("📋 Visualizar amostra dos dados 2023", expanded=True):
        st.dataframe(df_2023.head(20), use_container_width=True)
    
    # Mostrar todas as colunas
    with st.expander("🔍 Ver todas as colunas e tipos"):
        col_info = pd.DataFrame({
            'Coluna': df_2023.columns,
            'Tipo': df_2023.dtypes.astype(str).values,
            'Valores Únicos': df_2023.nunique().values,
            'Valores Nulos': df_2023.isnull().sum().values
        })
        st.dataframe(col_info, use_container_width=True)
    
    # Identificar colunas relevantes automaticamente
    st.subheader("🎯 Identificação Automática de Colunas")
    
    colunas_identificadas = {}
    
    # Procurar colunas por padrões
    for col in df_2023.columns:
        col_upper = str(col).upper()
        
        if any(x in col_upper for x in ['MUNIC', 'CIDADE', 'MUNICP']):
            colunas_identificadas['Município'] = col
        elif any(x in col_upper for x in ['COLETA', 'TIPO', 'SERVICO', 'GTR1001']):
            colunas_identificadas['Tipo de Coleta'] = col
        elif any(x in col_upper for x in ['MASSA', 'PESO', 'QUANTIDADE', 'TONELADA']):
            colunas_identificadas['Massa'] = col
        elif any(x in col_upper for x in ['DESTINO', 'DESTINACAO', 'ATERRO', 'LIXAO']):
            colunas_identificadas['Destino Final'] = col
        elif any(x in col_upper for x in ['UF', 'ESTADO', 'SIGLA']):
            colunas_identificadas['UF'] = col
        elif any(x in col_upper for x in ['REGIAO', 'MACRORREGIAO']):
            colunas_identificadas['Região'] = col
    
    # Mostrar colunas identificadas
    if colunas_identificadas:
        st.write("Colunas identificadas automaticamente:")
        for key, value in colunas_identificadas.items():
            st.write(f"**{key}:** `{value}`")
        
        # Permitir ajuste manual
        st.write("### 🔧 Ajuste Manual das Colunas")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            col_municipio = st.selectbox(
                "Coluna de Município:",
                df_2023.columns,
                index=list(df_2023.columns).index(colunas_identificadas.get('Município', df_2023.columns[0])) if colunas_identificadas.get('Município') in df_2023.columns else 0
            )
        
        with col2:
            col_coleta = st.selectbox(
                "Coluna de Tipo de Coleta:",
                df_2023.columns,
                index=list(df_2023.columns).index(colunas_identificadas.get('Tipo de Coleta', df_2023.columns[0])) if colunas_identificadas.get('Tipo de Coleta') in df_2023.columns else 0
            )
        
        with col3:
            col_massa = st.selectbox(
                "Coluna de Massa:",
                [col for col in df_2023.columns if '_NUM' in col] + list(df_2023.columns),
                index=0
            )
        
        with col4:
            col_destino = st.selectbox(
                "Coluna de Destino Final:",
                df_2023.columns,
                index=list(df_2023.columns).index(colunas_identificadas.get('Destino Final', df_2023.columns[0])) if colunas_identificadas.get('Destino Final') in df_2023.columns else 0
            )
        
        # Análise de tipos de coleta
        if col_coleta in df_2023.columns:
            st.subheader("🔍 Análise de Tipos de Coleta")
            
            # Contar tipos de coleta
            tipos_coleta = df_2023[col_coleta].value_counts().head(20)
            
            if not tipos_coleta.empty:
                # Classificar tipos de coleta para compostagem
                def classificar_para_compostagem(tipo):
                    if pd.isna(tipo):
                        return "Não informado"
                    tipo_str = str(tipo).lower()
                    if any(x in tipo_str for x in ['poda', 'galhada', 'verde', 'vegetal', 'orgânica', 'organica', 'arbórea']):
                        return "✅ Apto para compostagem"
                    elif any(x in tipo_str for x in ['domiciliar', 'indiferenciada', 'resíduos domiciliares']):
                        return "🟡 Potencial com triagem"
                    elif any(x in tipo_str for x in ['seletiva', 'recicláveis']):
                        return "🔵 Recicláveis"
                    elif any(x in tipo_str for x in ['construção', 'entulho']):
                        return "⚫ Resíduos da construção"
                    else:
                        return "⚪ Outros"
                
                df_2023['CLASS_COMPOSTAGEM'] = df_2023[col_coleta].apply(classificar_para_compostagem)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Gráfico de tipos de coleta
                    fig = px.bar(
                        x=tipos_coleta.index[:10],
                        y=tipos_coleta.values[:10],
                        title="Top 10 Tipos de Coleta",
                        labels={'x': 'Tipo de Coleta', 'y': 'Quantidade'}
                    )
                    fig.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Distribuição para compostagem
                    dist_compostagem = df_2023['CLASS_COMPOSTAGEM'].value_counts()
                    fig = px.pie(
                        values=dist_compostagem.values,
                        names=dist_compostagem.index,
                        title="Aptidão para Compostagem",
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        # Análise de destinação final
        if col_destino in df_2023.columns:
            st.subheader("🗑️ Análise de Destinação Final")
            
            # Distribuição de destinos
            destinos = df_2023[col_destino].value_counts().head(15)
            
            if not destinos.empty:
                fig = px.bar(
                    x=destinos.index,
                    y=destinos.values,
                    title="Principais Destinos dos Resíduos",
                    labels={'x': 'Tipo de Destino', 'y': 'Quantidade de Registros'},
                    color=destinos.values,
                    color_continuous_scale='viridis'
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
                
                # Calcular MCF para cada destino
                st.subheader("🔥 Potencial de Emissões de CH₄")
                
                # Agrupar por destino e calcular massa total
                if col_massa in df_2023.columns:
                    # Criar dataframe simplificado
                    df_emissoes = df_2023[[col_destino, col_massa]].copy()
                    df_emissoes['MCF'] = df_emissoes[col_destino].apply(determinar_mcf_por_destino)
                    df_emissoes['MASSA_T'] = df_emissoes[col_massa].apply(lambda x: float(x) if pd.notna(x) and not isinstance(x, str) else extrair_numero(x))
                    
                    # Agrupar por destino
                    df_agrupado = df_emissoes.groupby(col_destino).agg({
                        'MASSA_T': 'sum',
                        'MCF': 'first'
                    }).reset_index()
                    
                    # Calcular emissões
                    df_agrupado['CH4_T'] = df_agrupado.apply(
                        lambda row: calcular_emissoes_aterro(row['MASSA_T'], row['MCF']), 
                        axis=1
                    )
                    
                    # Filtrar apenas destinos com emissões
                    df_emissoes_filtrado = df_agrupado[df_agrupado['CH4_T'] > 0].sort_values('CH4_T', ascending=False)
                    
                    if not df_emissoes_filtrado.empty:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            massa_total = df_emissoes_filtrado['MASSA_T'].sum()
                            st.metric(
                                "Massa total em aterros",
                                f"{formatar_numero_br(massa_total)} t"
                            )
                        
                        with col2:
                            ch4_total = df_emissoes_filtrado['CH4_T'].sum()
                            st.metric(
                                "CH₄ total estimado",
                                f"{formatar_numero_br(ch4_total, 1)} t"
                            )
                        
                        # Gráfico de emissões por destino
                        fig = px.bar(
                            df_emissoes_filtrado.head(10),
                            x=col_destino,
                            y='CH4_T',
                            title="Emissões de CH₄ por Tipo de Destino (Top 10)",
                            labels={'CH4_T': 'CH₄ (toneladas)', col_destino: 'Tipo de Destino'},
                            color='CH4_T',
                            color_continuous_scale='reds'
                        )
                        fig.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Tabela detalhada
                        with st.expander("📊 Ver tabela detalhada de emissões"):
                            df_display = df_emissoes_filtrado.copy()
                            df_display["Massa (t)"] = df_display["MASSA_T"].apply(formatar_numero_br)
                            df_display["CH₄ (t)"] = df_display["CH4_T"].apply(lambda x: formatar_numero_br(x, 1))
                            df_display["MCF"] = df_display["MCF"].apply(lambda x: formatar_numero_br(x, 2))
                            
                            st.dataframe(
                                df_display[[col_destino, "Massa (t)", "CH₄ (t)", "MCF"]],
                                use_container_width=True
                            )
                    else:
                        st.info("Não foram encontrados dados de emissões significativas para os destinos informados.")

# =========================================================
# Análise para 2024
# =========================================================
elif ano_selecionado == "2024" and dados_carregados_2024:
    st.header("📊 Análise de Disposição Final - 2024")
    
    # Estatísticas básicas
    st.subheader("📈 Estatísticas Gerais 2024")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total de Registros", f"{len(df_2024):,}")
    
    with col2:
        st.metric("Número de Colunas", len(df_2024.columns))
    
    with col3:
        if "MUNICIPIO" in df_2024.columns:
            num_municipios = df_2024["MUNICIPIO"].nunique()
            st.metric("Municípios Únicos", f"{num_municipios:,}")
        else:
            st.metric("Municípios Únicos", "Não identificado")
    
    # Pré-visualização dos dados
    with st.expander("📋 Visualizar amostra dos dados 2024", expanded=True):
        st.dataframe(df_2024.head(20), use_container_width=True)
    
    # Mostrar todas as colunas
    with st.expander("🔍 Ver todas as colunas e tipos"):
        col_info = pd.DataFrame({
            'Coluna': df_2024.columns,
            'Tipo': df_2024.dtypes.astype(str).values,
            'Valores Únicos': df_2024.nunique().values,
            'Valores Nulos': df_2024.isnull().sum().values
        })
        st.dataframe(col_info, use_container_width=True)
    
    # Verificar quais colunas temos
    st.subheader("🔍 Estrutura dos Dados 2024")
    
    # Listar colunas disponíveis
    st.write("**Colunas disponíveis:**")
    for i, col in enumerate(df_2024.columns):
        st.write(f"{i+1}. `{col}`")
    
    # Análise por tipo de destino (se a coluna existe)
    if "TIPO_DESTINO" in df_2024.columns:
        st.subheader("🏭 Distribuição por Tipo de Destino Final")
        
        # Distribuição de tipos
        tipos_destino = df_2024["TIPO_DESTINO"].value_counts()
        
        if not tipos_destino.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.pie(
                    values=tipos_destino.values,
                    names=tipos_destino.index,
                    title="Tipos de Unidades de Disposição Final",
                    hole=0.3
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Gráfico de barras horizontal
                fig = px.bar(
                    x=tipos_destino.values,
                    y=tipos_destino.index,
                    orientation='h',
                    title="Quantidade por Tipo de Destino",
                    labels={'x': 'Quantidade', 'y': 'Tipo de Destino'},
                    color=tipos_destino.values,
                    color_continuous_scale='blues'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Análise por região (se a coluna existe)
            if "REGIAO" in df_2024.columns:
                st.subheader("🗺️ Distribuição Regional dos Tipos de Destino")
                
                # Criar tabela cruzada
                tabela_cruzada = pd.crosstab(
                    df_2024["REGIAO"], 
                    df_2024["TIPO_DESTINO"],
                    normalize='index'
                ) * 100
                
                fig = px.imshow(
                    tabela_cruzada,
                    title="Distribuição Percentual por Região (%)",
                    labels=dict(x="Tipo de Destino", y="Região", color="%"),
                    aspect="auto",
                    color_continuous_scale='viridis'
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # Análise de emissões
    st.subheader("🔥 Cálculo de Emissões de CH₄")
    
    # Determinar coluna de tipo de destino
    col_tipo_destino = None
    for col in df_2024.columns:
        if any(x in str(col).upper() for x in ['TIPO', 'DESTINO', 'DISP', 'ATERRO', 'LIXAO']):
            col_tipo_destino = col
            break
    
    if col_tipo_destino and "MASSA_NUM" in df_2024.columns:
        # Calcular MCF para cada registro
        df_2024["MCF"] = df_2024[col_tipo_destino].apply(determinar_mcf_por_destino)
        
        # Calcular emissões
        df_2024["CH4_T"] = df_2024.apply(
            lambda row: calcular_emissoes_aterro(row["MASSA_NUM"], row["MCF"]), 
            axis=1
        )
        
        # Agrupar por tipo de destino
        df_emissoes_2024 = df_2024.groupby(col_tipo_destino).agg({
            "MASSA_NUM": "sum",
            "CH4_T": "sum",
            "MCF": "first"
        }).reset_index()
        
        # Filtrar apenas com emissões
        df_emissoes_2024 = df_emissoes_2024[df_emissoes_2024["CH4_T"] > 0].sort_values("CH4_T", ascending=False)
        
        if not df_emissoes_2024.empty:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                massa_total = df_emissoes_2024["MASSA_NUM"].sum()
                st.metric(
                    "Massa destinada a aterros",
                    f"{formatar_numero_br(massa_total)} t"
                )
            
            with col2:
                ch4_total = df_emissoes_2024["CH4_T"].sum()
                st.metric(
                    "CH₄ total estimado",
                    f"{formatar_numero_br(ch4_total, 1)} t"
                )
            
            with col3:
                # Calcular CO₂ equivalente (GWP100 = 28)
                co2eq_total = ch4_total * 28
                st.metric(
                    "Equivalente CO₂",
                    f"{formatar_numero_br(co2eq_total, 1)} t CO₂e"
                )
            
            # Gráfico de emissões
            fig = px.bar(
                df_emissoes_2024,
                x=col_tipo_destino,
                y="CH4_T",
                title="Emissões de CH₄ por Tipo de Destino (2024)",
                labels={"CH4_T": "CH₄ (toneladas)", col_tipo_destino: "Tipo de Destino"},
                color="CH4_T",
                color_continuous_scale="reds"
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela detalhada
            with st.expander("📊 Ver tabela detalhada de emissões"):
                df_display = df_emissoes_2024.copy()
                df_display["Massa (t)"] = df_display["MASSA_NUM"].apply(formatar_numero_br)
                df_display["CH₄ (t)"] = df_display["CH4_T"].apply(lambda x: formatar_numero_br(x, 1))
                df_display["MCF"] = df_display["MCF"].apply(lambda x: formatar_numero_br(x, 2))
                
                st.dataframe(
                    df_display[[col_tipo_destino, "Massa (t)", "CH₄ (t)", "MCF"]],
                    use_container_width=True
                )
        else:
            st.info("Não foram encontradas emissões significativas de CH₄ nos dados de 2024.")
    else:
        st.warning("Não foi possível identificar as colunas necessárias para cálculo de emissões.")

# =========================================================
# Análise comparativa 2023-2024
# =========================================================
elif ano_selecionado == "Comparativo 2023-2024" and dados_carregados_2023 and dados_carregados_2024:
    st.header("📊 Comparativo 2023 vs 2024")
    
    # Métricas comparativas
    st.subheader("📈 Comparativo de Escopo")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Registros (2023)",
            f"{len(df_2023):,}",
            delta=f"{len(df_2023) - len(df_2024):+,}" if len(df_2024) > 0 else None
        )
    
    with col2:
        st.metric(
            "Registros (2024)",
            f"{len(df_2024):,}" if len(df_2024) > 0 else "N/A"
        )
    
    with col3:
        colunas_2023 = len(df_2023.columns)
        colunas_2024 = len(df_2024.columns)
        st.metric(
            "Colunas (2024)",
            colunas_2024,
            delta=f"{colunas_2024 - colunas_2023:+}"
        )
    
    with col4:
        # Tentar estimar massa
        massa_2024 = df_2024["MASSA_NUM"].sum() if "MASSA_NUM" in df_2024.columns else 0
        
        # Estimar massa 2023
        massa_2023 = 0
        for col in df_2023.columns:
            if '_NUM' in col:
                massa_2023 += df_2023[col].apply(extrair_numero).sum()
        
        if massa_2024 > 0 and massa_2023 > 0:
            variacao = ((massa_2024 - massa_2023) / massa_2023 * 100) if massa_2023 > 0 else 0
            st.metric(
                "Variação de Massa",
                f"{formatar_numero_br(variacao, 1)}%",
                delta=f"{formatar_numero_br(massa_2024 - massa_2023, 0)} t"
            )
        else:
            st.metric("Variação de Massa", "Dados insuficientes")
    
    # Análise de evolução do tratamento
    st.subheader("🔄 Evolução do Tratamento de Resíduos")
    
    # Para 2024, calcular distribuição se houver coluna de tipo de destino
    col_tipo_destino_2024 = None
    for col in df_2024.columns:
        if any(x in str(col).upper() for x in ['TIPO', 'DESTINO', 'DISP', 'ATERRO']):
            col_tipo_destino_2024 = col
            break
    
    if col_tipo_destino_2024:
        # Classificar destinos 2024
        def classificar_destino_2024(destino):
            if pd.isna(destino):
                return "Não informado"
            destino_str = str(destino).upper()
            if any(x in destino_str for x in ['ATERRO SANITARIO']):
                return "Aterro Sanitário"
            elif any(x in destino_str for x in ['LIXAO', 'VAZADOURO']):
                return "Lixão"
            elif any(x in destino_str for x in ['COMPOSTAGEM', 'VERMICOMPOSTAGEM']):
                return "Tratamento Biológico"
            elif any(x in destino_str for x in ['RECICLAGEM', 'TRIAGEM']):
                return "Reciclagem"
            else:
                return "Outros"
        
        df_2024["CATEGORIA_DESTINO"] = df_2024[col_tipo_destino_2024].apply(classificar_destino_2024)
        categorias_2024 = df_2024["CATEGORIA_DESTINO"].value_counts(normalize=True) * 100
        
        # Para 2023, tentar classificar
        col_destino_2023 = None
        for col in df_2023.columns:
            if any(x in str(col).upper() for x in ['DESTINO', 'DESTINACAO', 'ATERRO']):
                col_destino_2023 = col
                break
        
        if col_destino_2023:
            def classificar_destino_2023(destino):
                if pd.isna(destino):
                    return "Não informado"
                destino_str = str(destino).upper()
                if any(x in destino_str for x in ['ATERRO SANITARIO']):
                    return "Aterro Sanitário"
                elif any(x in destino_str for x in ['LIXAO', 'VAZADOURO']):
                    return "Lixão"
                elif any(x in destino_str for x in ['COMPOSTAGEM', 'VERMICOMPOSTAGEM']):
                    return "Tratamento Biológico"
                elif any(x in destino_str for x in ['RECICLAGEM', 'TRIAGEM']):
                    return "Reciclagem"
                else:
                    return "Outros"
            
            df_2023["CATEGORIA_DESTINO"] = df_2023[col_destino_2023].apply(classificar_destino_2023)
            categorias_2023 = df_2023["CATEGORIA_DESTINO"].value_counts(normalize=True) * 100
            
            # Criar dataframe comparativo
            todas_categorias = set(categorias_2023.index).union(set(categorias_2024.index))
            df_comparativo = pd.DataFrame(index=list(todas_categorias))
            df_comparativo["2023 (%)"] = [categorias_2023.get(cat, 0) for cat in df_comparativo.index]
            df_comparativo["2024 (%)"] = [categorias_2024.get(cat, 0) for cat in df_comparativo.index]
            
            # Gráfico comparativo
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                name="2023",
                x=df_comparativo.index,
                y=df_comparativo["2023 (%)"],
                marker_color='blue',
                opacity=0.7
            ))
            
            fig.add_trace(go.Bar(
                name="2024",
                x=df_comparativo.index,
                y=df_comparativo["2024 (%)"],
                marker_color='green',
                opacity=0.7
            ))
            
            fig.update_layout(
                title="Comparativo de Destinação Final (% por categoria)",
                xaxis_title="Categoria de Destino",
                yaxis_title="Percentual (%)",
                barmode="group",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Análise de redução de emissões
    st.subheader("🔥 Comparativo de Emissões")
    
    # Calcular emissões 2024 se possível
    if col_tipo_destino_2024 and "MASSA_NUM" in df_2024.columns:
        df_2024["MCF_2024"] = df_2024[col_tipo_destino_2024].apply(determinar_mcf_por_destino)
        df_2024["CH4_T_2024"] = df_2024.apply(
            lambda row: calcular_emissoes_aterro(row["MASSA_NUM"], row["MCF_2024"]), 
            axis=1
        )
        
        emissao_2024 = df_2024["CH4_T_2024"].sum()
        
        # Estimar emissões 2023
        emissao_2023 = 0
        if col_destino_2023:
            # Encontrar coluna de massa 2023
            col_massa_2023 = None
            for col in df_2023.columns:
                if '_NUM' in col:
                    col_massa_2023 = col
                    break
            
            if col_massa_2023:
                df_2023["MCF_2023"] = df_2023[col_destino_2023].apply(determinar_mcf_por_destino)
                df_2023["MASSA_NUM_2023"] = df_2023[col_massa_2023].apply(lambda x: float(x) if pd.notna(x) and not isinstance(x, str) else extrair_numero(x))
                df_2023["CH4_T_2023"] = df_2023.apply(
                    lambda row: calcular_emissoes_aterro(row["MASSA_NUM_2023"], row["MCF_2023"]), 
                    axis=1
                )
                emissao_2023 = df_2023["CH4_T_2023"].sum()
        
        if emissao_2023 > 0 and emissao_2024 > 0:
            reducao = emissao_2023 - emissao_2024
            percentual_reducao = (reducao / emissao_2023 * 100) if emissao_2023 > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Emissões estimadas 2023",
                    f"{formatar_numero_br(emissao_2023, 1)} t CH₄"
                )
            
            with col2:
                st.metric(
                    "Emissões calculadas 2024",
                    f"{formatar_numero_br(emissao_2024, 1)} t CH₄"
                )
            
            with col3:
                st.metric(
                    "Variação de emissões",
                    f"{formatar_numero_br(reducao, 1)} t CH₄",
                    delta=f"{formatar_numero_br(percentual_reducao, 1)}%",
                    delta_color="inverse" if reducao > 0 else "normal"
                )

# =========================================================
# Seção de recomendações
# =========================================================
st.markdown("---")
st.subheader("💡 Recomendações e Insights")

if ano_selecionado == "2023":
    st.markdown("""
    ### Principais Recomendações para 2023:
    
    1. **Ampliar coleta seletiva de orgânicos**: Apenas uma pequena fração dos resíduos orgânicos é coletada separadamente
    2. **Investir em compostagem municipal**: Grande potencial não aproveitado, especialmente para resíduos de poda
    3. **Reduzir destinação para lixões**: Ainda há municípios utilizando destinação inadequada
    4. **Melhorar qualidade dos dados**: Muitos registros com valores não numéricos ou inconsistentes
    """)

elif ano_selecionado == "2024":
    st.markdown("""
    ### Principais Recomendações para 2024:
    
    1. **Aumentar aterros sanitários**: Ainda há muitos resíduos indo para lixões e aterros controlados
    2. **Implementar tratamento biológico**: Baixíssima penetração de compostagem e vermicompostagem
    3. **Monitorar emissões de CH₄**: Estabelecer sistema de monitoramento para aterros existentes
    4. **Integrar dados regionais**: Criar consórcios intermunicipais para destinação adequada
    """)

else:
    st.markdown("""
    ### Tendências e Oportunidades 2023-2024:
    
    1. **Expansão da cobertura**: Aumento no número de municípios com dados reportados
    2. **Melhoria na destinação**: Tendência de redução de lixões (dados a confirmar)
    3. **Oportunidade de créditos de carbono**: Potencial para projetos de redução de metano
    4. **Necessidade de padronização**: Diferentes metodologias entre anos dificultam comparação
    """)

# =========================================================
# Rodapé
# =========================================================
st.markdown("---")
st.caption("""
**Fontes de dados:** SNIS - Sistema Nacional de Informações sobre Saneamento | 
**Metodologia:** IPCC 2006, Yang et al. (2017) | 
**Última atualização:** {} | 
**Desenvolvido para análise técnica de resíduos sólidos**
""".format(datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
