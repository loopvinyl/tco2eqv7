"""
📊 SISTEMA DE ANÁLISE SINISA 2023 - Dashboard Interativo
Autor: Sistema de Análise SINISA
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
    .stDataFrame {
        font-size: 0.9rem;
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
    
    # Modo de carregamento
    carregar_modo = st.radio(
        "Modo de carregamento:",
        ["Usar arquivo do GitHub", "Fazer upload de arquivo"]
    )
    
    if carregar_modo == "Fazer upload de arquivo":
        uploaded_file = st.file_uploader(
            "📂 Carregar arquivo SINISA 2023",
            type=['xlsx', 'xls']
        )
    else:
        uploaded_file = None
        st.info("Usando arquivo padrão do GitHub")
    
    st.markdown("---")
    st.markdown("### 🔍 Filtros")
    
    # Filtro de estado
    estados_brasil = ["Todos"] + [
        "RO", "AC", "AM", "RR", "PA", "AP", "TO", "MA", "PI", "CE", "RN", "PB", 
        "PE", "AL", "SE", "BA", "MG", "ES", "RJ", "SP", "PR", "SC", "RS", "MS", 
        "MT", "GO", "DF"
    ]
    
    estados_selecionados = st.multiselect(
        "Estados",
        estados_brasil,
        default=["Todos"]
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
def load_data(uploaded_file=None):
    """
    Carrega e processa os dados do SINISA 2023
    """
    try:
        if uploaded_file is not None:
            df = pd.read_excel(uploaded_file, sheet_name='Manejo_Coleta_e_Destinação')
        else:
            # Usar arquivo do GitHub
            github_url = "https://github.com/loopvinyl/tco2eqv7/raw/main/SINISA_RESIDUOS_Informacoes_Formulario_Manejo_2023%20-%20Copia.xlsx"
            df = pd.read_excel(github_url, sheet_name='Manejo_Coleta_e_Destinação')
        
        st.success(f"Dados carregados com sucesso! Total de registros: {len(df):,}")
        
        # Renomear colunas para facilitar
        df.columns = [str(col).strip() for col in df.columns]
        
        # Exibir informações sobre as colunas
        st.sidebar.info(f"Colunas carregadas: {len(df.columns)}")
        
        # Lista de colunas esperadas baseada na estrutura do arquivo
        colunas_esperadas = {
            'A': 'Selecionar',  # Coluna A
            'B': 'Cod Municipio',
            'C': 'Municipio',
            'D': 'UF',
            'E': 'Regiao',
            'F': 'Populacao',
            # Adicione mais conforme necessário
        }
        
        # Verificar colunas disponíveis
        colunas_disponiveis = df.columns.tolist()
        
        # Mapear colunas com base em padrões
        colunas_mapeadas = {}
        
        for col in colunas_disponiveis:
            col_lower = str(col).lower()
            
            if 'uf' in col_lower or 'estado' in col_lower:
                colunas_mapeadas['estado'] = col
            elif 'município' in col_lower or 'municipio' in col_lower:
                colunas_mapeadas['municipio'] = col
            elif 'região' in col_lower or 'regiao' in col_lower:
                colunas_mapeadas['regiao'] = col
            elif 'população' in col_lower or 'populacao' in col_lower:
                colunas_mapeadas['populacao'] = col
            elif 'massa' in col_lower and ('total' in col_lower or 'anual' in col_lower):
                colunas_mapeadas['massa_total'] = col
            elif 'tipo' in col_lower and 'coleta' in col_lower:
                colunas_mapeadas['tipo_coleta'] = col
            elif 'destino' in col_lower:
                colunas_mapeadas['destino'] = col
            elif 'selecionar' in col_lower:
                colunas_mapeadas['selecionar'] = col
        
        # Aplicar filtro da coluna A = 'Sim' se existir
        if 'selecionar' in colunas_mapeadas:
            filtro_original = len(df)
            df = df[df[colunas_mapeadas['selecionar']] == 'Sim'].copy()
            st.info(f"Filtro aplicado: {filtro_original - len(df)} registros removidos")
        
        # Converter colunas numéricas
        if 'massa_total' in colunas_mapeadas:
            df['massa_total_numeric'] = pd.to_numeric(
                df[colunas_mapeadas['massa_total']], 
                errors='coerce'
            )
            df['massa_total_numeric'].fillna(0, inplace=True)
        
        if 'populacao' in colunas_mapeadas:
            df['populacao_numeric'] = pd.to_numeric(
                df[colunas_mapeadas['populacao']], 
                errors='coerce'
            )
            df['populacao_numeric'].fillna(0, inplace=True)
        
        return df, colunas_mapeadas
    
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame(), {}

# Função para calcular indicadores
def calculate_indicators(df, colunas_mapeadas):
    """
    Calcula indicadores-chave dos dados
    """
    indicators = {}
    
    if df.empty:
        return indicators
    
    # Indicadores básicos
    indicators['total_registros'] = len(df)
    
    if 'massa_total_numeric' in df.columns:
        indicators['massa_total_coletada'] = df['massa_total_numeric'].sum()
    
    if 'municipio' in colunas_mapeadas:
        indicators['municipios_unicos'] = df[colunas_mapeadas['municipio']].nunique()
    
    if 'estado' in colunas_mapeadas:
        indicators['estados_unicos'] = df[colunas_mapeadas['estado']].nunique()
    
    # Médias
    if 'massa_total_numeric' in df.columns and 'municipio' in colunas_mapeadas:
        media_por_municipio = df.groupby(colunas_mapeadas['municipio'])['massa_total_numeric'].sum().mean()
        indicators['media_massa_por_municipio'] = media_por_municipio
    
    # Distribuição por destino
    if 'destino' in colunas_mapeadas:
        destinos = df[colunas_mapeadas['destino']].value_counts()
        indicators['destinos_principais'] = destinos.head(10).to_dict()
    
    return indicators

# Função para análise per capita
def analyze_per_capita(df, colunas_mapeadas):
    """
    Realiza análise per capita
    """
    if 'estado' not in colunas_mapeadas or 'massa_total_numeric' not in df.columns:
        return pd.DataFrame()
    
    # Agrupar por estado
    df_estado = df.groupby(colunas_mapeadas['estado']).agg({
        'massa_total_numeric': 'sum'
    }).reset_index()
    
    df_estado.columns = ['estado', 'massa_total_ton']
    
    # Converter para kg
    df_estado['massa_total_kg'] = df_estado['massa_total_ton'] * 1000
    
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
    
    # Adicionar população
    df_estado['populacao'] = df_estado['estado'].map(populacao_estados)
    
    # Calcular per capita
    df_estado['per_capita_kg_ano'] = df_estado['massa_total_kg'] / df_estado['populacao']
    df_estado['per_capita_kg_dia'] = df_estado['per_capita_kg_ano'] / 365
    
    # Ordenar
    df_estado = df_estado.sort_values('per_capita_kg_ano', ascending=False)
    
    return df_estado

# Função para criar visualizações
def create_visualizations(df, colunas_mapeadas, df_per_capita):
    """
    Cria visualizações interativas
    """
    col1, col2 = st.columns(2)
    
    with col1:
        # 1. Gráfico de barras - Massa total por estado
        if 'estado' in colunas_mapeadas and 'massa_total_numeric' in df.columns:
            df_estado_massa = df.groupby(colunas_mapeadas['estado'])['massa_total_numeric'].sum().reset_index()
            df_estado_massa.columns = ['estado', 'massa_total']
            df_estado_massa = df_estado_massa.sort_values('massa_total', ascending=False).head(15)
            
            fig1 = px.bar(
                df_estado_massa,
                x='estado',
                y='massa_total',
                title='🔝 Top 15 Estados por Massa Coletada',
                labels={'estado': 'Estado', 'massa_total': 'Massa Total (ton)'},
                color='massa_total',
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # 2. Gráfico de pizza - Distribuição por tipo de coleta
        if 'tipo_coleta' in colunas_mapeadas:
            tipo_coleta_counts = df[colunas_mapeadas['tipo_coleta']].value_counts()
            fig2 = px.pie(
                values=tipo_coleta_counts.values,
                names=tipo_coleta_counts.index,
                title='🔄 Distribuição por Tipo de Coleta',
                hole=0.3
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    col3, col4 = st.columns(2)
    
    with col3:
        # 3. Histograma - Distribuição da massa coletada
        if 'massa_total_numeric' in df.columns:
            fig3 = px.histogram(
                df,
                x='massa_total_numeric',
                nbins=50,
                title='📊 Distribuição da Massa Coletada',
                labels={'massa_total_numeric': 'Massa Coletada (ton)', 'count': 'Número de Registros'}
            )
            st.plotly_chart(fig3, use_container_width=True)
    
    with col4:
        # 4. Gráfico de dispersão - Per capita
        if not df_per_capita.empty:
            fig4 = px.scatter(
                df_per_capita,
                x='populacao',
                y='per_capita_kg_ano',
                size='massa_total_ton',
                color='estado',
                hover_name='estado',
                title='📈 Relação População vs. Geração per Capita',
                labels={
                    'populacao': 'População',
                    'per_capita_kg_ano': 'kg/hab/ano',
                    'massa_total_ton': 'Massa Total (ton)'
                }
            )
            st.plotly_chart(fig4, use_container_width=True)
    
    # 5. Mapa de calor - Distribuição por estado e destino
    if 'estado' in colunas_mapeadas and 'destino' in colunas_mapeadas:
        st.markdown("---")
        st.subheader("🌡️ Mapa de Calor: Distribuição por Estado e Destino")
        
        # Criar tabela pivô
        pivot_data = df.pivot_table(
            index=colunas_mapeadas['estado'],
            columns=colunas_mapeadas['destino'],
            values='massa_total_numeric' if 'massa_total_numeric' in df.columns else None,
            aggfunc='sum',
            fill_value=0
        )
        
        fig5 = px.imshow(
            pivot_data,
            labels=dict(x="Destino", y="Estado", color="Massa (ton)"),
            title="Distribuição da Massa por Estado e Destino Final",
            color_continuous_scale="YlOrRd"
        )
        st.plotly_chart(fig5, use_container_width=True)

# Função principal
def main():
    """
    Função principal do aplicativo
    """
    # Carregar dados
    with st.spinner('Carregando dados do SINISA 2023...'):
        df, colunas_mapeadas = load_data(uploaded_file)
    
    if df.empty:
        st.warning("⚠️ Nenhum dado disponível. Por favor, verifique o arquivo.")
        return
    
    # Aplicar filtros
    if 'estado' in colunas_mapeadas and estados_selecionados and "Todos" not in estados_selecionados:
        df_filtrado = df[df[colunas_mapeadas['estado']].isin(estados_selecionados)].copy()
    else:
        df_filtrado = df.copy()
    
    st.success(f"Registros após filtros: {len(df_filtrado):,}")
    
    # Calcular indicadores
    indicators = calculate_indicators(df_filtrado, colunas_mapeadas)
    
    # Painel de métricas
    st.markdown('<h2 class="section-header">📈 Painel de Indicadores</h2>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Registros", f"{indicators.get('total_registros', 0):,}")
    
    with col2:
        massa_total = indicators.get('massa_total_coletada', 0)
        st.metric("Massa Total Coletada", f"{massa_total:,.0f} ton")
    
    with col3:
        st.metric("Municípios", f"{indicators.get('municipios_unicos', 0):,}")
    
    with col4:
        st.metric("Estados", f"{indicators.get('estados_unicos', 0)}")
    
    # Análise per capita
    st.markdown('<h2 class="section-header">👤 Análise Per Capita</h2>', unsafe_allow_html=True)
    
    df_per_capita = analyze_per_capita(df_filtrado, colunas_mapeadas)
    
    if not df_per_capita.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Ranking por Geração per Capita")
            display_df = df_per_capita[['estado', 'per_capita_kg_ano', 'per_capita_kg_dia']].copy()
            display_df['per_capita_kg_ano'] = display_df['per_capita_kg_ano'].round(2)
            display_df['per_capita_kg_dia'] = display_df['per_capita_kg_dia'].round(3)
            display_df.columns = ['Estado', 'kg/hab/ano', 'kg/hab/dia']
            
            st.dataframe(
                display_df,
                use_container_width=True,
                height=400
            )
        
        with col2:
            # Estatísticas
            st.subheader("Estatísticas Gerais")
            
            if not df_per_capita.empty:
                media_nacional = df_per_capita['per_capita_kg_ano'].mean()
                max_estado = df_per_capita.iloc[0]['estado']
                max_valor = df_per_capita.iloc[0]['per_capita_kg_ano']
                min_estado = df_per_capita.iloc[-1]['estado']
                min_valor = df_per_capita.iloc[-1]['per_capita_kg_ano']
                
                st.metric("Média Nacional", f"{media_nacional:.2f} kg/hab/ano")
                st.metric("Maior Geração", f"{max_valor:.1f} kg/hab/ano", f"({max_estado})")
                st.metric("Menor Geração", f"{min_valor:.2f} kg/hab/ano", f"({min_estado})")
    
    # Visualizações
    st.markdown('<h2 class="section-header">📊 Visualizações</h2>', unsafe_allow_html=True)
    create_visualizations(df_filtrado, colunas_mapeadas, df_per_capita)
    
    # Análises avançadas
    if show_advanced:
        st.markdown('<h2 class="section-header">🔬 Análises Avançadas</h2>', unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["Análise Regional", "Correlações", "Distribuição"])
        
        with tab1:
            # Análise regional
            if 'regiao' in colunas_mapeadas:
                regional_analysis = df_filtrado.groupby(colunas_mapeadas['regiao']).agg({
                    'massa_total_numeric': 'sum',
                    'populacao_numeric': 'sum' if 'populacao_numeric' in df_filtrado.columns else None
                }).reset_index()
                
                regional_analysis.columns = ['Região', 'Massa Total (ton)', 'População']
                
                fig_regional = px.bar(
                    regional_analysis,
                    x='Região',
                    y='Massa Total (ton)',
                    title='Massa Coletada por Região',
                    color='Massa Total (ton)',
                    color_continuous_scale='Blues'
                )
                st.plotly_chart(fig_regional, use_container_width=True)
        
        with tab2:
            # Análise de correlações
            st.subheader("Matriz de Correlação")
            
            # Selecionar colunas numéricas
            numeric_cols = df_filtrado.select_dtypes(include=[np.number]).columns.tolist()
            
            if len(numeric_cols) > 1:
                corr_matrix = df_filtrado[numeric_cols].corr()
                
                fig_corr = px.imshow(
                    corr_matrix,
                    text_auto=True,
                    aspect="auto",
                    color_continuous_scale='RdBu_r',
                    title='Matriz de Correlação entre Variáveis Numéricas'
                )
                st.plotly_chart(fig_corr, use_container_width=True)
            else:
                st.info("Poucas colunas numéricas disponíveis para análise de correlação.")
        
        with tab3:
            # Distribuição por tipo de destino
            if 'destino' in colunas_mapeadas:
                destinos_analysis = df_filtrado[colunas_mapeadas['destino']].value_counts().reset_index()
                destinos_analysis.columns = ['Destino', 'Contagem']
                
                fig_destinos = px.treemap(
                    destinos_analysis,
                    path=['Destino'],
                    values='Contagem',
                    title='Distribuição por Destino Final',
                    color='Contagem',
                    color_continuous_scale='Greens'
                )
                st.plotly_chart(fig_destinos, use_container_width=True)
    
    # Dados brutos
    if show_raw_data:
        st.markdown('<h2 class="section-header">📋 Dados Brutos</h2>', unsafe_allow_html=True)
        
        with st.expander("Visualizar dados completos", expanded=False):
            # Mostrar primeiras linhas
            st.dataframe(df_filtrado.head(100), use_container_width=True)
            
            # Estatísticas descritivas
            st.subheader("Estatísticas Descritivas")
            if 'massa_total_numeric' in df_filtrado.columns:
                stats_df = df_filtrado['massa_total_numeric'].describe().reset_index()
                stats_df.columns = ['Estatística', 'Valor']
                st.dataframe(stats_df, use_container_width=True)
            
            # Opções de download
            csv = df_filtrado.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV (dados filtrados)",
                data=csv,
                file_name="sinisa_2023_filtrado.csv",
                mime="text/csv",
                help="Baixar os dados atualmente filtrados em formato CSV"
            )
    
    # Informações técnicas
    st.markdown("---")
    with st.expander("🔧 Informações Técnicas"):
        st.markdown("""
        ### Estrutura dos Dados
        
        **Colunas carregadas:** {}
        
        **Colunas mapeadas:**
        {}
        
        **Processamento:**
        - Filtro aplicado: Coluna 'Selecionar' = 'Sim'
        - Conversão de tipos numéricos
        - Tratamento de valores ausentes
        
        **Indicadores calculados:**
        - Massa total coletada (ton)
        - Geração per capita (kg/hab/ano)
        - Distribuição por estado e destino
        
        **Fonte:** Ministério do Meio Ambiente - SINISA 2023
        """.format(
            len(df.columns),
            "\n".join([f"- {k}: {v}" for k, v in colunas_mapeadas.items()])
        ))
    
    # Rodapé
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>📅 Sistema desenvolvido para análise SINISA 2023</p>
        <p>📧 Dúvidas técnicas: suporte@sinisa.gov.br</p>
        <p>🔗 Dados oficiais: Ministério do Meio Ambiente - SINISA 2023</p>
        <p>🔄 Última atualização: Dezembro 2025 | v1.0.0</p>
    </div>
    """, unsafe_allow_html=True)

# Executar aplicação
if __name__ == "__main__":
    main()
