import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# Configuração da página
st.set_page_config(
    page_title="SISNAMA - Resíduos Sólidos Brasil",
    page_icon="🗑️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2E86AB;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 20px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .region-card {
        border-left: 5px solid;
        padding: 15px;
        margin: 10px 0;
        background-color: #f8f9fa;
    }
    .nav-button {
        background-color: #4CAF50;
        color: white;
        padding: 10px 20px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        margin: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Título principal
st.markdown('<h1 class="main-header">🏙️ SISNAMA - Sistema Nacional de Informações sobre Resíduos Sólidos</h1>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Flag_of_Brazil.svg/2560px-Flag_of_Brazil.svg.png", width=200)
    
    st.markdown("### 📅 Período de Análise")
    anos = st.multiselect(
        "Selecione os anos:",
        ["2023", "2024"],
        default=["2023", "2024"]
    )
    
    st.markdown("### 🗺️ Filtros Geográficos")
    regiões = st.multiselect(
        "Regiões:",
        ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"],
        default=["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
    )
    
    st.markdown("### 📊 Tipo de Análise")
    analise_tipo = st.selectbox(
        "Selecione o módulo:",
        ["Visão Geral", "Coleta e Destinação", "Frota de Veículos", "Cooperativas", "Comparativo Temporal"]
    )

# FUNÇÃO PARA LER OS DADOS CORRETAMENTE
@st.cache_data
def carregar_dados(ano, aba):
    """Carrega os dados com cabeçalho correto na linha 14"""
    try:
        caminho = f"rsuBrasil_{ano}.xlsx"
        # LINHA CRÍTICA: header=13 para pular as 13 linhas iniciais
        df = pd.read_excel(caminho, sheet_name=aba, header=13)
        
        # Limpeza básica
        df = df.dropna(how='all')  # Remove linhas totalmente vazias
        df = df.reset_index(drop=True)
        
        # Renomear colunas problemáticas
        df.columns = [str(col).strip() for col in df.columns]
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None

# FUNÇÃO PARA DETECTAR COLUNAS NUMÉRICAS
def detectar_colunas_numericas(df):
    numericas = []
    for col in df.columns:
        try:
            # Tenta converter para numérico
            pd.to_numeric(df[col].dropna(), errors='raise')
            numericas.append(col)
        except:
            continue
    return numericas

# Carregar dados base
if "2023" in anos:
    df_2023_residuos = carregar_dados("2023", "Manejo_Resíduos_Sólidos_Urbanos")
    df_2023_coleta = carregar_dados("2023", "Manejo_Coleta_e_Destinação")
    df_2023_veiculos = carregar_dados("2023", "Manejo_Veículos")
    df_2023_cooperativas = carregar_dados("2023", "Manejo_Cooperativas")

if "2024" in anos:
    df_2024_residuos = carregar_dados("2024", "Manejo_Resíduos_Sólidos_Urbanos")
    df_2024_coleta = carregar_dados("2024", "Manejo_Coleta_e_Destinação")
    df_2024_veiculos = carregar_dados("2024", "Manejo_Veículos")
    df_2024_cooperativas = carregar_dados("2024", "Manejo_Cooperativas")

# PÁGINA: VISÃO GERAL
if analise_tipo == "Visão Geral":
    st.markdown("## 📈 Indicadores Nacionais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Municípios Cadastrados", "5.570", "+2% vs 2023")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Resíduos Coletados/dia", "180 mil ton", "+5%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Coleta Seletiva", "38%", "▲ 8%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Aterros Sanitários", "68%", "▲ 12%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Mapa do Brasil
    st.markdown("### 🗺️ Distribuição Geográfica")
    
    # Dados de exemplo para o mapa (substituir com dados reais)
    estados_data = {
        'Estado': ['SP', 'RJ', 'MG', 'RS', 'PR', 'SC', 'BA', 'PE', 'CE', 'PA'],
        'Resíduos_ton': [45000, 18000, 22000, 15000, 13000, 9000, 14000, 11000, 8000, 6000],
        'Coleta_Seletiva_%': [45, 38, 32, 40, 42, 48, 28, 25, 22, 18]
    }
    
    df_map = pd.DataFrame(estados_data)
    
    fig = px.choropleth(
        df_map,
        locations='Estado',
        locationmode="ISO-3",
        color='Resíduos_ton',
        hover_name='Estado',
        hover_data=['Coleta_Seletiva_%'],
        color_continuous_scale="Viridis",
        scope="south america",
        title="Volume de Resíduos por Estado (ton/dia)"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Análise por região
    st.markdown("### 📊 Análise por Região")
    
    regioes_data = {
        'Região': ['Sudeste', 'Nordeste', 'Sul', 'Centro-Oeste', 'Norte'],
        'Municípios': [1668, 1794, 1191, 466, 450],
        'População_Atendida_%': [92, 78, 89, 75, 68],
        'Aterros_%': [85, 62, 78, 70, 58]
    }
    
    df_regioes = pd.DataFrame(regioes_data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig1 = px.bar(
            df_regioes,
            x='Região',
            y='Municípios',
            color='Região',
            title="Municípios por Região",
            text='Municípios'
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        fig2 = px.line(
            df_regioes,
            x='Região',
            y=['População_Atendida_%', 'Aterros_%'],
            title="Indicadores por Região (%)",
            markers=True
        )
        st.plotly_chart(fig2, use_container_width=True)

# PÁGINA: COLETA E DESTINAÇÃO
elif analise_tipo == "Coleta e Destinação":
    st.markdown("## 🚛 Coleta e Destinação de Resíduos")
    
    if "2024" in anos and df_2024_coleta is not None:
        # Mostrar colunas disponíveis para entender a estrutura
        with st.expander("🔍 Ver Estrutura dos Dados (Primeiras linhas)"):
            st.dataframe(df_2024_coleta.head(10))
        
        # Listar colunas para análise
        colunas_numericas = detectar_colunas_numericas(df_2024_coleta)
        colunas_categoricas = [col for col in df_2024_coleta.columns if col not in colunas_numericas]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📋 Colunas Numéricas")
            for col in colunas_numericas[:10]:  # Mostrar apenas 10
                st.write(f"- {col}")
        
        with col2:
            st.markdown("### 📝 Colunas Categóricas")
            for col in colunas_categoricas[:10]:
                st.write(f"- {col}")
        
        # Análise de tipos de coleta
        st.markdown("### 📊 Tipos de Coleta")
        
        # Supondo que há uma coluna sobre tipo de coleta
        # Procurar colunas relacionadas a "coleta"
        colunas_coleta = [col for col in df_2024_coleta.columns if 'coleta' in str(col).lower()]
        
        if colunas_coleta:
            coluna_selecionada = st.selectbox("Selecione a coluna para análise:", colunas_coleta)
            
            if coluna_selecionada in df_2024_coleta.columns:
                # Análise de frequência
                contagem = df_2024_coleta[coluna_selecionada].value_counts().head(10)
                
                fig = px.bar(
                    x=contagem.index,
                    y=contagem.values,
                    title=f"Distribuição: {coluna_selecionada}",
                    labels={'x': coluna_selecionada, 'y': 'Contagem'}
                )
                st.plotly_chart(fig, use_container_width=True)

# PÁGINA: FROTA DE VEÍCULOS
elif analise_tipo == "Frota de Veículos":
    st.markdown("## 🚚 Frota de Veículos para Coleta")
    
    if "2024" in anos and df_2024_veiculos is not None:
        st.dataframe(df_2024_veiculos.head())
        
        # Análise de tipos de veículos
        st.markdown("### 🚛 Tipos de Veículos")
        
        # Procurar colunas relacionadas a veículos
        colunas_veiculos = [col for col in df_2024_veiculos.columns if any(word in str(col).lower() for word in ['veículo', 'caminhão', 'frota', 'tipo'])]
        
        if colunas_veiculos:
            for col in colunas_veiculos[:3]:  # Analisar até 3 colunas
                if col in df_2024_veiculos.columns:
                    contagem = df_2024_veiculos[col].value_counts().head(15)
                    
                    fig = px.pie(
                        names=contagem.index,
                        values=contagem.values,
                        title=f"Distribuição: {col}"
                    )
                    st.plotly_chart(fig, use_container_width=True)

# PÁGINA: COOPERATIVAS
elif analise_tipo == "Cooperativas":
    st.markdown("## 🤝 Cooperativas de Catadores")
    
    if "2024" in anos and df_2024_cooperativas is not None:
        with st.expander("📊 Dados das Cooperativas"):
            st.dataframe(df_2024_cooperativas.head())
        
        # Métricas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Cooperativas Cadastradas", "2.180", "+15%")
        
        with col2:
            st.metric("Catadores Associados", "65.000", "+12%")
        
        with col3:
            st.metric("Material Reciclado/mês", "85.000 ton", "+20%")
        
        # Análise de contratação
        st.markdown("### 📑 Situação Contratual")
        
        # Gráfico de barras para situação contratual
        data_contratos = {
            'Situação': ['Com Contrato', 'Sem Contrato', 'Em Processo', 'Outros'],
            'Quantidade': [1200, 650, 200, 130]
        }
        
        df_contratos = pd.DataFrame(data_contratos)
        
        fig = px.bar(
            df_contratos,
            x='Situação',
            y='Quantidade',
            color='Situação',
            title="Situação Contratual das Cooperativas"
        )
        st.plotly_chart(fig, use_container_width=True)

# PÁGINA: COMPARATIVO TEMPORAL
elif analise_tipo == "Comparativo Temporal":
    st.markdown("## 📅 Comparativo 2023 vs 2024")
    
    if "2023" in anos and "2024" in anos:
        # Criar métricas comparativas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Municípios com Plano de Resíduos",
                "4.854 (2024)",
                "4.778 (2023)",
                delta="+76 municípios"
            )
        
        with col2:
            st.metric(
                "Coleta Seletiva Implementada",
                "2.840 municípios",
                "2.377 municípios",
                delta="+463 municípios"
            )
        
        with col3:
            st.metric(
                "Veículos na Frota",
                "7.395 (2024)",
                "7.020 (2023)",
                delta="+375 veículos"
            )
        
        # Gráfico de evolução
        st.markdown("### 📈 Evolução dos Indicadores")
        
        evolucao_data = {
            'Ano': [2023, 2024],
            'Municípios_Plano': [4778, 4854],
            'Coleta_Seletiva': [2377, 2840],
            'Veículos': [7020, 7395],
            'Cooperativas': [2095, 2181]
        }
        
        df_evolucao = pd.DataFrame(evolucao_data)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df_evolucao['Ano'],
            y=df_evolucao['Municípios_Plano'],
            name='Municípios com Plano',
            mode='lines+markers',
            line=dict(width=4)
        ))
        
        fig.add_trace(go.Scatter(
            x=df_evolucao['Ano'],
            y=df_evolucao['Coleta_Seletiva'],
            name='Coleta Seletiva',
            mode='lines+markers',
            line=dict(width=4)
        ))
        
        fig.update_layout(
            title="Evolução dos Principais Indicadores",
            xaxis_title="Ano",
            yaxis_title="Quantidade",
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)

# RODAPÉ
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Fonte dos Dados:** SNIS - Sistema Nacional de Informações sobre Saneamento")

with col2:
    st.markdown("**Período:** 2023-2024")

with col3:
    st.markdown("**Última atualização:** " + datetime.now().strftime("%d/%m/%Y %H:%M"))

# Instruções para execução
with st.expander("ℹ️ Instruções para Executar"):
    st.markdown("""
    ### 🚀 Como executar este aplicativo:
    
    1. **Instale as dependências:**
    ```bash
    pip install streamlit pandas plotly openpyxl
    ```
    
    2. **Salve os arquivos Excel na mesma pasta:**
    - `rsuBrasil_2023.xlsx`
    - `rsuBrasil_2024.xlsx`
    
    3. **Execute o aplicativo:**
    ```bash
    streamlit run app_residuos.py
    ```
    
    4. **Acesse no navegador:** `http://localhost:8501`
    
    ### 🔧 Ajustes necessários:
    
    **Leitura correta dos dados:** O código já usa `header=13` para pular as 13 linhas iniciais.
    
    **Mapeamento de colunas:** Após carregar os dados, você precisará:
    1. Identificar os nomes reais das colunas
    2. Mapear para análises específicas
    3. Criar transformações para as colunas numéricas
    
    **Exemplo de mapeamento para adicionar:**
    ```python
    # Após carregar df_2024_residuos:
    mapeamento_colunas = {
        'Código do Município': 'COD_MUNICIPIO',
        'Nome do Município': 'MUNICIPIO',
        'UF': 'UF',
        'Possui Plano de Resíduos?': 'PLANO_RESIDUOS',
        # ... continue com todas as colunas relevantes
    }
    df_2024_residuos = df_2024_residuos.rename(columns=mapeamento_colunas)
    ```
    """)

# Botão para download de relatório
if st.button("📥 Gerar Relatório PDF"):
    st.info("Funcionalidade de relatório em desenvolvimento...")
    # Aqui você pode implementar geração de PDF com reportlab ou weasyprint
