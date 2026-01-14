"""
📊 SISTEMA DE ANÁLISE SINISA 2023 - Dashboard Interativo
Autor: [Seu Nome]
Descrição: Dashboard para análise de dados de resíduos sólidos municipais
Dados: https://github.com/loopvinyl/tco2eqv7
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
    .stDataFrame {
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# Título principal
st.markdown('<h1 class="main-header">📊 SISTEMA DE ANÁLISE SINISA 2023</h1>', unsafe_allow_html=True)
st.markdown("### Dashboard Interativo de Resíduos Sólidos Municipais")
st.markdown(f"**Repositório GitHub:** [loopvinyl/tco2eqv7](https://github.com/loopvinyl/tco2eqv7)")

# Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3067/3067256.png", width=100)
    st.title("Configurações")
    
    # Modo de carregamento
    st.markdown("### 📂 Fonte de Dados")
    data_source = st.radio(
        "Selecione a fonte:",
        ["GitHub (Automático)", "Upload Manual", "URL Personalizado"]
    )
    
    # Upload do arquivo (se selecionado)
    if data_source == "Upload Manual":
        uploaded_file = st.file_uploader("Carregar arquivo Excel", type=['xlsx', 'xls'])
    else:
        uploaded_file = None
    
    # URL personalizado
    if data_source == "URL Personalizado":
        custom_url = st.text_input(
            "URL do arquivo Excel (formato raw):",
            value="https://github.com/loopvinyl/tco2eqv7/raw/main/SINISA_RESIDUOS_Informacoes_Formulario_Manejo_2023%20-%20Copia.xlsx"
        )
    else:
        custom_url = None
    
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
    
    # Filtro de tipo de coleta
    tipo_coleta_opcoes = ["Todos", "Convencional", "Seletiva", "Outros"]
    tipo_coleta_filtro = st.multiselect("Tipo de Coleta", tipo_coleta_opcoes, default="Todos")
    
    st.markdown("---")
    st.markdown("#### 📈 Exibição")
    show_raw_data = st.checkbox("Mostrar dados brutos", value=False)
    show_advanced = st.checkbox("Análises avançadas", value=False)
    show_per_capita = st.checkbox("Detalhes per capita", value=True)
    
    st.markdown("---")
    st.markdown("#### ℹ️ Sobre")
    st.info("""
    **Dados:** SINISA 2023
    **Repositório:** loopvinyl/tco2eqv7
    **Ano base:** 2023
    **Última atualização:** Dez/2025
    """)

# URLs pré-definidos
GITHUB_URL = "https://github.com/loopvinyl/tco2eqv7/raw/main/SINISA_RESIDUOS_Informacoes_Formulario_Manejo_2023%20-%20Copia.xlsx"

# Função para carregar e processar dados
@st.cache_data(ttl=3600)  # Cache por 1 hora
def load_data(source="github", file=None, url=None):
    """
    Carrega e processa os dados do SINISA 2023
    """
    try:
        if source == "upload" and file is not None:
            df = pd.read_excel(file, sheet_name='Manejo_Coleta_e_Destinação')
            st.success("✅ Dados carregados do upload")
        elif source == "url" and url:
            df = pd.read_excel(url, sheet_name='Manejo_Coleta_e_Destinação')
            st.success(f"✅ Dados carregados de URL personalizado")
        else:
            # Usar GitHub por padrão
            df = pd.read_excel(GITHUB_URL, sheet_name='Manejo_Coleta_e_Destinação')
            st.success("✅ Dados carregados do GitHub automaticamente")
        
        # Renomear colunas para facilitar
        df.columns = [f'Col_{i}' if not isinstance(col, str) else col for i, col in enumerate(df.columns)]
        
        # Aplicar filtro da coluna A = 'Sim'
        if 'Col_0' in df.columns:
            df = df[df['Col_0'] == 'Sim'].copy()
        
        # Mapear colunas conforme especificado no relatório
        column_mapping = {
            'estado': 'Col_3',
            'regiao': 'Col_4',
            'tipo_coleta': 'Col_17',
            'massa_total': 'Col_24',
            'destino': 'Col_28',
            'municipio': 'Col_2'  # Supondo que Col_2 seja o município
        }
        
        # Renomear colunas
        for new_name, old_name in column_mapping.items():
            if old_name in df.columns:
                df[new_name] = df[old_name]
        
        # Converter massa para numérico
        if 'massa_total' in df.columns:
            df['massa_total'] = pd.to_numeric(df['massa_total'], errors='coerce')
            # Remover valores negativos ou extremos
            df = df[df['massa_total'] >= 0]
            df = df[df['massa_total'] <= 1e9]  # Limite de 1 bilhão de toneladas
        
        # Limpeza de dados
        if 'estado' in df.columns:
            df['estado'] = df['estado'].astype(str).str.strip().str.upper()
        
        if 'regiao' in df.columns:
            df['regiao'] = df['regiao'].astype(str).str.strip()
        
        return df
    
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {str(e)}")
        st.info("💡 Dica: Verifique se o arquivo está acessível e tem a aba 'Manejo_Coleta_e_Destinação'")
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
    indicators['municipios_unicos'] = df['municipio'].nunique() if 'municipio' in df.columns else 0
    indicators['estados_unicos'] = df['estado'].nunique() if 'estado' in df.columns else 0
    indicators['regioes_unicas'] = df['regiao'].nunique() if 'regiao' in df.columns else 0
    
    # Médias
    if 'municipio' in df.columns:
        indicators['media_massa_por_municipio'] = df.groupby('municipio')['massa_total'].sum().mean()
    
    # Distribuição por destino
    if 'destino' in df.columns:
        destinos = df['destino'].value_counts()
        indicators['destinos_principais'] = destinos.head(5).to_dict()
        indicators['total_destinos'] = len(destinos)
    
    # Distribuição por tipo de coleta
    if 'tipo_coleta' in df.columns:
        tipos = df['tipo_coleta'].value_counts()
        indicators['tipos_coleta'] = len(tipos)
        indicators['distribuicao_tipos'] = tipos.head(10).to_dict()
    
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
        'municipio': 'nunique' if 'municipio' in df.columns else ('Col_2', 'nunique')
    }).reset_index()
    
    df_estado.columns = ['estado', 'massa_total_kg', 'num_municipios']
    
    # Adicionar população
    df_estado['populacao'] = df_estado['estado'].map(populacao_estados)
    
    # Remover estados sem população
    df_estado = df_estado.dropna(subset=['populacao'])
    
    # Calcular per capita
    df_estado['per_capita_kg_ano'] = (df_estado['massa_total_kg'] * 1000) / df_estado['populacao']
    df_estado['per_capita_kg_dia'] = df_estado['per_capita_kg_ano'] / 365
    
    # Calcular percentual em relação à média nacional
    media_nacional = df_estado['per_capita_kg_ano'].mean()
    df_estado['percentual_media'] = (df_estado['per_capita_kg_ano'] / media_nacional) * 100
    
    # Ordenar
    df_estado = df_estado.sort_values('per_capita_kg_ano', ascending=False)
    
    return df_estado, media_nacional

# Função para aplicar filtros
def apply_filters(df, estados_filtro, pop_range, massa_range, tipo_coleta_filtro):
    """
    Aplica filtros selecionados na sidebar
    """
    df_filtered = df.copy()
    
    # Filtro de estado
    if estados_filtro and "Todos" not in estados_filtro:
        df_filtered = df_filtered[df_filtered['estado'].isin(estados_filtro)]
    
    # Filtro de tipo de coleta
    if tipo_coleta_filtro and "Todos" not in tipo_coleta_filtro:
        if 'tipo_coleta' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['tipo_coleta'].isin(tipo_coleta_filtro)]
    
    return df_filtered

# Função para criar visualizações
def create_visualizations(df, df_per_capita):
    """
    Cria visualizações interativas
    """
    col1, col2 = st.columns(2)
    
    with col1:
        # 1. Gráfico de barras - Massa total por estado
        if 'estado' in df.columns and 'massa_total' in df.columns:
            df_estado_massa = df.groupby('estado')['massa_total'].sum().reset_index().sort_values('massa_total', ascending=False).head(15)
            fig1 = px.bar(
                df_estado_massa,
                x='estado',
                y='massa_total',
                title='🔝 Top 15 Estados por Massa Coletada',
                labels={'estado': 'Estado', 'massa_total': 'Massa Total (ton)'},
                color='massa_total',
                color_continuous_scale='Viridis',
                text='massa_total'
            )
            fig1.update_traces(texttemplate='%{text:.2s}', textposition='outside')
            st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # 2. Mapa de calor - Correlações
        if not df_per_capita.empty:
            fig2 = px.scatter(
                df_per_capita,
                x='populacao',
                y='per_capita_kg_ano',
                size='massa_total_kg',
                color='estado',
                hover_name='estado',
                hover_data=['num_municipios', 'per_capita_kg_dia'],
                title='📈 População vs. Geração per Capita',
                labels={
                    'populacao': 'População (hab)',
                    'per_capita_kg_ano': 'kg/hab/ano',
                    'massa_total_kg': 'Massa Total (ton)'
                },
                size_max=50
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    col3, col4 = st.columns(2)
    
    with col3:
        # 3. Gráfico de pizza - Distribuição por tipo de coleta
        if 'tipo_coleta' in df.columns:
            tipo_coleta_counts = df['tipo_coleta'].value_counts().reset_index()
            tipo_coleta_counts.columns = ['tipo_coleta', 'quantidade']
            
            fig3 = px.pie(
                tipo_coleta_counts,
                values='quantidade',
                names='tipo_coleta',
                title='🔄 Distribuição por Tipo de Coleta',
                hole=0.3,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig3, use_container_width=True)
    
    with col4:
        # 4. Gráfico de barras horizontais - Per capita por estado
        if not df_per_capita.empty:
            df_top10 = df_per_capita.head(10).sort_values('per_capita_kg_ano')
            fig4 = px.bar(
                df_top10,
                y='estado',
                x='per_capita_kg_ano',
                title='🏆 Top 10 Estados - Geração per Capita',
                labels={'estado': 'Estado', 'per_capita_kg_ano': 'kg/hab/ano'},
                orientation='h',
                color='per_capita_kg_ano',
                color_continuous_scale='RdYlGn_r',
                text='per_capita_kg_ano'
            )
            fig4.update_traces(texttemplate='%{text:.1f}', textposition='outside')
            st.plotly_chart(fig4, use_container_width=True)
    
    # 5. Histograma - Distribuição da massa coletada
    st.markdown("#### 📊 Distribuição da Massa Coletada")
    fig5 = px.histogram(
        df,
        x='massa_total',
        nbins=50,
        title='Distribuição da Massa Coletada por Município',
        labels={'massa_total': 'Massa Coletada (ton)', 'count': 'Número de Municípios'},
        opacity=0.7,
        color_discrete_sequence=['#2E86AB']
    )
    fig5.update_layout(bargap=0.1)
    st.plotly_chart(fig5, use_container_width=True)

# Função para análise regional
def regional_analysis(df):
    """
    Análise detalhada por região
    """
    if 'regiao' not in df.columns:
        return
    
    st.markdown("#### 🌎 Análise Regional Detalhada")
    
    regional_stats = df.groupby('regiao').agg({
        'massa_total': ['sum', 'mean', 'count'],
        'estado': 'nunique',
        'municipio': 'nunique' if 'municipio' in df.columns else ('Col_2', 'nunique')
    }).round(2)
    
    # Ajustar nomes das colunas
    regional_stats.columns = ['Massa Total (ton)', 'Média por Município', 'Nº Registros', 'Estados', 'Municípios']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.dataframe(regional_stats, use_container_width=True)
    
    with col2:
        fig = px.bar(
            regional_stats.reset_index(),
            x='regiao',
            y='Massa Total (ton)',
            title='Massa Coletada por Região',
            color='Massa Total (ton)',
            color_continuous_scale='Blues',
            text='Massa Total (ton)'
        )
        fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

# Função principal
def main():
    """
    Função principal do aplicativo
    """
    # Determinar fonte de dados
    if data_source == "Upload Manual" and uploaded_file is not None:
        source = "upload"
        file = uploaded_file
        url = None
    elif data_source == "URL Personalizado" and custom_url:
        source = "url"
        file = None
        url = custom_url
    else:
        source = "github"
        file = None
        url = None
    
    # Carregar dados
    with st.spinner('📥 Carregando dados do SINISA 2023...'):
        df = load_data(source=source, file=file, url=url)
    
    if df.empty:
        st.error("Não foi possível carregar os dados. Verifique a fonte selecionada.")
        return
    
    # Aplicar filtros
    df_filtered = apply_filters(df, estados, pop_range, massa_range, tipo_coleta_filtro)
    
    # Calcular indicadores
    indicators = calculate_indicators(df_filtered)
    
    # Painel de métricas
    st.markdown('<h2 class="section-header">📈 Painel de Indicadores</h2>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Registros", f"{indicators.get('total_registros', 0):,}")
    
    with col2:
        massa_formatada = f"{indicators.get('massa_total_coletada', 0):,.0f}"
        st.metric("Massa Total Coletada", f"{massa_formatada} ton")
    
    with col3:
        st.metric("Municípios", f"{indicators.get('municipios_unicos', 0):,}")
    
    with col4:
        st.metric("Estados", f"{indicators.get('estados_unicos', 0)}")
    
    # Análise per capita
    if show_per_capita:
        st.markdown('<h2 class="section-header">👤 Análise Per Capita</h2>', unsafe_allow_html=True)
        
        df_per_capita, media_nacional = analyze_per_capita(df_filtered)
        
        if not df_per_capita.empty:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.dataframe(
                    df_per_capita[['estado', 'per_capita_kg_ano', 'per_capita_kg_dia', 'num_municipios']].round(2),
                    use_container_width=True,
                    height=400
                )
            
            with col2:
                # Média nacional
                st.metric("Média Nacional", f"{media_nacional:.2f} kg/hab/ano", 
                         f"{(1.001 - (media_nacional/365))*100:+.1f}% vs. relatório")
                
                # Estado com maior geração
                if len(df_per_capita) > 0:
                    estado_max = df_per_capita.iloc[0]['estado']
                    valor_max = df_per_capita.iloc[0]['per_capita_kg_ano']
                    st.metric("Maior Geração", f"{valor_max:.1f} kg/hab/ano", estado_max)
                
                # Estado com menor geração
                if len(df_per_capita) > 1:
                    estado_min = df_per_capita.iloc[-1]['estado']
                    valor_min = df_per_capita.iloc[-1]['per_capita_kg_ano']
                    st.metric("Menor Geração", f"{valor_min:.1f} kg/hab/ano", estado_min)
            
            with col3:
                # Distribuição percentual
                fig_dist = px.box(
                    df_per_capita,
                    y='per_capita_kg_ano',
                    title='Distribuição da Geração per Capita',
                    labels={'per_capita_kg_ano': 'kg/hab/ano'}
                )
                fig_dist.add_hline(y=media_nacional, line_dash="dash", line_color="red", 
                                 annotation_text=f"Média: {media_nacional:.1f}")
                st.plotly_chart(fig_dist, use_container_width=True)
    
    # Visualizações
    st.markdown('<h2 class="section-header">📊 Visualizações</h2>', unsafe_allow_html=True)
    create_visualizations(df_filtered, df_per_capita if 'df_per_capita' in locals() else pd.DataFrame())
    
    # Análises avançadas
    if show_advanced:
        st.markdown('<h2 class="section-header">🔬 Análises Avançadas</h2>', unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["Análise Regional", "Tendências", "Simulações"])
        
        with tab1:
            regional_analysis(df_filtered)
        
        with tab2:
            st.write("### 📈 Análise de Tendências")
            
            if 'tipo_coleta' in df_filtered.columns and 'massa_total' in df_filtered.columns:
                # Tendência por tipo de coleta
                tendencia_tipo = df_filtered.groupby('tipo_coleta')['massa_total'].sum().reset_index()
                fig_tendencia = px.bar(
                    tendencia_tipo,
                    x='tipo_coleta',
                    y='massa_total',
                    title='Massa Total por Tipo de Coleta',
                    color='tipo_coleta'
                )
                st.plotly_chart(fig_tendencia, use_container_width=True)
            
            # Estatísticas descritivas
            st.write("#### Estatísticas Descritivas")
            if 'massa_total' in df_filtered.columns:
                stats_df = df_filtered['massa_total'].describe().reset_index()
                stats_df.columns = ['Estatística', 'Valor']
                st.dataframe(stats_df, use_container_width=True)
        
        with tab3:
            st.write("### 🎯 Simulações de Cenários")
            
            # Simulação de aumento de coleta seletiva
            col1, col2 = st.columns(2)
            
            with col1:
                aumento_coleta = st.slider(
                    "Aumento de coleta seletiva (%)",
                    0, 100, 10, 5
                )
                
                if 'massa_total' in df_filtered.columns:
                    massa_atual = df_filtered['massa_total'].sum()
                    massa_projetada = massa_atual * (1 + aumento_coleta/100)
                    st.metric("Massa Total Projetada", 
                             f"{massa_projetada:,.0f} ton",
                             f"{aumento_coleta:+.0f}%")
            
            with col2:
                # Simulação de redução de destinação inadequada
                reducao_lixao = st.slider(
                    "Redução de destinação inadequada (%)",
                    0, 100, 20, 5
                )
                
                st.info(f"Com {reducao_lixao}% de redução na destinação inadequada, estima-se uma diminuição significativa nas emissões de GEE.")
    
    # Dados brutos
    if show_raw_data:
        st.markdown('<h2 class="section-header">📋 Dados Brutos</h2>', unsafe_allow_html=True)
        
        with st.expander("📊 Visualizar dados completos", expanded=False):
            st.dataframe(df_filtered, use_container_width=True, height=400)
            
            # Estatísticas dos dados
            st.write("#### 📝 Estatísticas dos Dados Filtrados")
            st.write(f"- **Total de linhas:** {len(df_filtered):,}")
            st.write(f"- **Colunas:** {len(df_filtered.columns)}")
            st.write(f"- **Valores nulos:** {df_filtered.isnull().sum().sum():,}")
            
            # Opções de download
            col_dl1, col_dl2 = st.columns(2)
            
            with col_dl1:
                csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Download CSV (UTF-8)",
                    data=csv,
                    file_name="sinisa_2023_filtrado.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col_dl2:
                # Preparar Excel
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_filtered.to_excel(writer, sheet_name='Dados_Filtrados', index=False)
                    if not df_per_capita.empty:
                        df_per_capita.to_excel(writer, sheet_name='Per_Capita', index=False)
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📥 Download Excel",
                    data=excel_data,
                    file_name="sinisa_2023_analise.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
    
    # Rodapé
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.9rem;'>
        <p>📅 <strong>SINISA 2023 - Sistema Nacional de Informações sobre Saneamento</strong></p>
        <p>📊 Dashboard desenvolvido para análise de dados de resíduos sólidos municipais</p>
        <p>🔗 <a href="https://github.com/loopvinyl/tco2eqv7" target="_blank">Repositório GitHub</a> • 
           📧 Contato: seu.email@instituicao.edu.br</p>
        <p>📝 Última atualização: Dezembro 2025 | Versão 1.0</p>
    </div>
    """, unsafe_allow_html=True)

# Executar aplicação
if __name__ == "__main__":
    main()
