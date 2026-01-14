"""
📊 SISTEMA DE ANÁLISE SINISA 2023 - Dashboard Interativo
Autor: [Seu Nome]
Descrição: Dashboard para análise de dados de resíduos sólidos municipais
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
import geopandas as gpd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configuração da página
st.set_page_config(
    page_title="SINISA 2023 - Análise de Resíduos Sólidos",
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
        background-color: #F8F9FA;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #2E86AB;
        margin-bottom: 1rem;
    }
    .section-header {
        color: #264653;
        border-bottom: 2px solid #2A9D8F;
        padding-bottom: 0.5rem;
        margin-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Título principal
st.markdown('<h1 class="main-header">📊 SISTEMA DE ANÁLISE SINISA 2023</h1>', unsafe_allow_html=True)
st.markdown("### Dashboard Interativo de Resíduos Sólidos Municipais")

# Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3067/3067256.png", width=100)
    st.title("Configurações")
    
    # Upload do arquivo
    uploaded_file = st.file_uploader("📂 Carregar arquivo SINISA 2023", type=['xlsx', 'xls'])
    
    st.markdown("---")
    st.markdown("### 🔍 Filtros")
    
    # Filtro de estado
    estados = st.multiselect(
        "Estados",
        ["Todos"] + ["RO", "AC", "AM", "RR", "PA", "AP", "TO", "MA", "PI", "CE", "RN", "PB", "PE", "AL", "SE", "BA", "MG", "ES", "RJ", "SP", "PR", "SC", "RS", "MS", "MT", "GO", "DF"]
    )
    
    # Filtro de população
    pop_range = st.slider(
        "Faixa populacional (mil habitantes)",
        0, 10000, (0, 10000),
        step=100
    )
    
    # Filtro de massa coletada
    massa_range = st.slider(
        "Massa coletada anual (toneladas)",
        0.0, 1000000.0, (0.0, 1000000.0),
        step=1000.0
    )
    
    st.markdown("---")
    st.markdown("#### 📈 Exibição")
    show_raw_data = st.checkbox("Mostrar dados brutos")
    show_advanced = st.checkbox("Análises avançadas")
    
    st.markdown("---")
    st.markdown("#### ℹ️ Sobre")
    st.info("""
    Sistema de análise de dados do SINISA 2023.
    
    **Fonte:** Ministério do Meio Ambiente
    **Ano base:** 2023
    **Última atualização:** Dez/2025
    """)

# Função para carregar e processar dados
@st.cache_data
def load_data(file_path=None):
    """
    Carrega e processa os dados do SINISA 2023
    """
    try:
        if uploaded_file is not None:
            df = pd.read_excel(uploaded_file, sheet_name='Manejo_Coleta_e_Destinação')
        else:
            # Se não houver upload, usar dados de exemplo ou URL do GitHub
            github_url = "https://github.com/seu_usuario/seu_repositorio/raw/main/SINISA_RESIDUOS_Informacoes_Formulario_Manejo_2023%20-%20Copia.xlsx"
            df = pd.read_excel(github_url, sheet_name='Manejo_Coleta_e_Destinação')
        
        # Renomear colunas para facilitar
        df.columns = [f'Col_{i}' if not isinstance(col, str) else col for i, col in enumerate(df.columns)]
        
        # Aplicar filtro da coluna A = 'Sim'
        if 'Col_0' in df.columns:
            df = df[df['Col_0'] == 'Sim'].copy()
        
        # Mapear colunas conforme especificado
        column_mapping = {
            'estado': 'Col_3',
            'regiao': 'Col_4',
            'tipo_coleta': 'Col_17',
            'massa_total': 'Col_24',
            'destino': 'Col_28'
        }
        
        # Renomear colunas
        for new_name, old_name in column_mapping.items():
            if old_name in df.columns:
                df[new_name] = df[old_name]
        
        # Converter massa para numérico
        if 'massa_total' in df.columns:
            df['massa_total'] = pd.to_numeric(df['massa_total'], errors='coerce')
        
        return df
    
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

# Função para calcular indicadores
def calculate_indicators(df):
    """
    Calcula indicadores-chave dos dados
    """
    indicators = {}
    
    if df.empty:
        return indicators
    
    # Indicadores básicos
    indicators['total_registros'] = len(df)
    indicators['massa_total_coletada'] = df['massa_total'].sum()
    indicators['municipios_unicos'] = df['Col_2'].nunique() if 'Col_2' in df.columns else 0
    indicators['estados_unicos'] = df['estado'].nunique() if 'estado' in df.columns else 0
    
    # Médias
    indicators['media_massa_por_municipio'] = df.groupby('Col_2')['massa_total'].sum().mean() if 'Col_2' in df.columns else 0
    
    # Distribuição por destino
    if 'destino' in df.columns:
        destinos = df['destino'].value_counts()
        indicators['destinos_principais'] = destinos.head(5).to_dict()
    
    return indicators

# Função para análise per capita
def analyze_per_capita(df):
    """
    Realiza análise per capita
    """
    # Dados populacionais por estado (IBGE 2023)
    populacao_estados = {
        'RO': 1777225, 'AC': 906607, 'AM': 4207714, 'RR': 636707,
        'PA': 8602865, 'AP': 877613, 'TO': 1590245, 'MA': 7075181,
        'PI': 3273227, 'CE': 9240580, 'RN': 3534165, 'PB': 4039277,
        'PE': 9674793, 'AL': 3322820, 'SE': 2338474, 'BA': 14985284,
        'MG': 21411923, 'ES': 4108508, 'RJ': 17463349, 'SP': 46289333,
        'PR': 11516840, 'SC': 7338473, 'RS': 11422973, 'MS': 2867448,
        'MT': 3567234, 'GO': 7206589, 'DF': 3094325
    }
    
    if 'estado' not in df.columns or 'massa_total' not in df.columns:
        return pd.DataFrame()
    
    # Agrupar por estado
    df_estado = df.groupby('estado').agg({
        'massa_total': 'sum',
        'Col_2': 'nunique'  # Contar municípios
    }).reset_index()
    
    df_estado.columns = ['estado', 'massa_total_kg', 'num_municipios']
    
    # Adicionar população
    df_estado['populacao'] = df_estado['estado'].map(populacao_estados)
    
    # Calcular per capita
    df_estado['per_capita_kg_ano'] = (df_estado['massa_total_kg'] * 1000) / df_estado['populacao']
    df_estado['per_capita_kg_dia'] = df_estado['per_capita_kg_ano'] / 365
    
    # Ordenar
    df_estado = df_estado.sort_values('per_capita_kg_ano', ascending=False)
    
    return df_estado

# Função para criar visualizações
def create_visualizations(df, df_per_capita):
    """
    Cria visualizações interativas
    """
    # 1. Gráfico de barras - Massa total por estado
    if 'estado' in df.columns and 'massa_total' in df.columns:
        fig1 = px.bar(
            df.groupby('estado')['massa_total'].sum().reset_index().sort_values('massa_total', ascending=False).head(10),
            x='estado',
            y='massa_total',
            title='🔝 Top 10 Estados por Massa Coletada',
            labels={'estado': 'Estado', 'massa_total': 'Massa Total (ton)'},
            color='massa_total',
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    # 2. Mapa de calor - Correlações
    if not df_per_capita.empty:
        fig2 = px.scatter(
            df_per_capita,
            x='populacao',
            y='per_capita_kg_ano',
            size='massa_total_kg',
            color='estado',
            hover_name='estado',
            title='📈 Relação População vs. Geração per Capita',
            labels={'populacao': 'População', 'per_capita_kg_ano': 'kg/hab/ano'}
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # 3. Gráfico de pizza - Distribuição por tipo de coleta
    if 'tipo_coleta' in df.columns:
        tipo_coleta_counts = df['tipo_coleta'].value_counts()
        fig3 = px.pie(
            values=tipo_coleta_counts.values,
            names=tipo_coleta_counts.index,
            title='🔄 Distribuição por Tipo de Coleta',
            hole=0.3
        )
        st.plotly_chart(fig3, use_container_width=True)
    
    # 4. Histograma - Distribuição da massa coletada
    fig4 = px.histogram(
        df,
        x='massa_total',
        nbins=50,
        title='📊 Distribuição da Massa Coletada por Município',
        labels={'massa_total': 'Massa Coletada (ton)', 'count': 'Número de Municípios'}
    )
    st.plotly_chart(fig4, use_container_width=True)

# Função principal
def main():
    """
    Função principal do aplicativo
    """
    # Carregar dados
    with st.spinner('Carregando dados...'):
        df = load_data()
    
    if df.empty:
        st.warning("⚠️ Nenhum dado disponível. Por favor, faça upload do arquivo.")
        return
    
    # Calcular indicadores
    indicators = calculate_indicators(df)
    
    # Painel de métricas
    st.markdown('<h2 class="section-header">📈 Painel de Indicadores</h2>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Registros", f"{indicators.get('total_registros', 0):,}")
    
    with col2:
        st.metric("Massa Total Coletada", f"{indicators.get('massa_total_coletada', 0):,.0f} ton")
    
    with col3:
        st.metric("Municípios", f"{indicators.get('municipios_unicos', 0):,}")
    
    with col4:
        st.metric("Estados", f"{indicators.get('estados_unicos', 0)}")
    
    # Análise per capita
    st.markdown('<h2 class="section-header">👤 Análise Per Capita</h2>', unsafe_allow_html=True)
    
    df_per_capita = analyze_per_capita(df)
    
    if not df_per_capita.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.dataframe(
                df_per_capita[['estado', 'per_capita_kg_ano', 'per_capita_kg_dia']].round(2),
                use_container_width=True
            )
        
        with col2:
            # Média nacional
            media_nacional = df_per_capita['per_capita_kg_ano'].mean()
            st.metric("Média Nacional", f"{media_nacional:.2f} kg/hab/ano")
            
            # Estado com maior geração
            estado_max = df_per_capita.iloc[0]['estado']
            valor_max = df_per_capita.iloc[0]['per_capita_kg_ano']
            st.metric("Maior Geração", f"{valor_max:.1f} kg/hab/ano", estado_max)
    
    # Visualizações
    st.markdown('<h2 class="section-header">📊 Visualizações</h2>', unsafe_allow_html=True)
    create_visualizations(df, df_per_capita)
    
    # Análises avançadas
    if show_advanced:
        st.markdown('<h2 class="section-header">🔬 Análises Avançadas</h2>', unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["Análise Regional", "Tendências", "Simulações"])
        
        with tab1:
            # Análise regional
            if 'regiao' in df.columns:
                regional_analysis = df.groupby('regiao').agg({
                    'massa_total': 'sum',
                    'estado': 'nunique'
                }).reset_index()
                
                fig_regional = px.bar(
                    regional_analysis,
                    x='regiao',
                    y='massa_total',
                    title='Massa Coletada por Região',
                    labels={'regiao': 'Região', 'massa_total': 'Massa Total (ton)'}
                )
                st.plotly_chart(fig_regional, use_container_width=True)
        
        with tab2:
            # Análise de tendências
            st.write("Análise de tendências por tipo de coleta...")
        
        with tab3:
            # Simulações
            st.write("Simulações de cenários...")
    
    # Dados brutos
    if show_raw_data:
        st.markdown('<h2 class="section-header">📋 Dados Brutos</h2>', unsafe_allow_html=True)
        
        with st.expander("Visualizar dados completos"):
            st.dataframe(df, use_container_width=True)
            
            # Opções de download
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name="sinisa_2023_processed.csv",
                mime="text/csv"
            )
    
    # Rodapé
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>📅 Última atualização: Dezembro 2025</p>
        <p>📧 Contato: seu.email@instituicao.edu.br</p>
        <p>🔗 Fonte dos dados: Ministério do Meio Ambiente - SINISA 2023</p>
    </div>
    """, unsafe_allow_html=True)

# Executar aplicação
if __name__ == "__main__":
    main()
