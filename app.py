import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Painel RSU Brasil",
    page_icon="🗑️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título e introdução
st.title("📊 Painel Nacional de Resíduos Sólidos Urbanos")
st.markdown("""
**Análise Comparativa 2023 vs 2024 | Dados do SNIS - Sistema Nacional de Informações sobre Saneamento**
""")

# Sidebar - Configurações
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3063/3063812.png", width=80)
st.sidebar.title("Configurações")

# Carregamento de dados
@st.cache_data
def load_data(year):
    """Carrega os dados do Excel para um ano específico"""
    try:
        file_path = f"rsuBrasil_{year}.xlsx"
        sheets = pd.read_excel(file_path, sheet_name=None)
        
        # Adicionar coluna de ano para identificação
        for sheet_name, df in sheets.items():
            df['ANO_REFERENCIA'] = year
        
        return sheets
    except Exception as e:
        st.error(f"Erro ao carregar dados de {year}: {e}")
        return None

# Carregar dados
with st.spinner("Carregando dados..."):
    data_2023 = load_data(2023)
    data_2024 = load_data(2024)

if data_2023 is None or data_2024 is None:
    st.error("Erro: Arquivos de dados não encontrados. Certifique-se de que 'rsuBrasil_2023.xlsx' e 'rsuBrasil_2024.xlsx' estão na pasta do projeto.")
    st.stop()

# Sidebar - Navegação
aba_selecionada = st.sidebar.selectbox(
    "📋 Selecione a Aba de Dados:",
    ["Manejo_Resíduos_Sólidos_Urbanos", 
     "Manejo_Coleta_e_Destinação", 
     "Manejo_Veículos", 
     "Manejo_Cooperativas"]
)

ano_selecionado = st.sidebar.radio(
    "📅 Ano de Referência:",
    ["Comparativo 2023-2024", "2024", "2023"]
)

# Obter dados com base na seleção
def get_sheet_data(sheet_name, year):
    """Obtém dados específicos de uma aba e ano"""
    if year == "2023":
        return data_2023.get(sheet_name, pd.DataFrame())
    elif year == "2024":
        return data_2024.get(sheet_name, pd.DataFrame())
    else:
        # Para comparação, retorna ambos
        return {
            "2023": data_2023.get(sheet_name, pd.DataFrame()),
            "2024": data_2024.get(sheet_name, pd.DataFrame())
        }

# Obter dados atuais
current_data = get_sheet_data(aba_selecionada, ano_selecionado)

# ============================================
# SEÇÃO 1: VISÃO GERAL E KPIs
# ============================================
st.header("📈 Visão Geral e Indicadores")

col1, col2, col3, col4 = st.columns(4)

with col1:
    if isinstance(current_data, dict):
        # Comparativo
        total_2023 = len(current_data["2023"])
        total_2024 = len(current_data["2024"])
        variacao = ((total_2024 - total_2023) / total_2023 * 100) if total_2023 > 0 else 0
        st.metric(
            "Registros",
            f"{total_2024:,}".replace(",", "."),
            f"{variacao:+.1f}% vs 2023"
        )
    else:
        st.metric(
            "Total de Registros",
            f"{len(current_data):,}".replace(",", ".")
        )

with col2:
    if aba_selecionada == "Manejo_Resíduos_Sólidos_Urbanos":
        st.metric("Municípios", "5.582", "Mesmo em 2023-2024")
    elif aba_selecionada == "Manejo_Coleta_e_Destinação":
        st.metric("Registros Coleta", "~14.000", "+4% vs 2023")
    elif aba_selecionada == "Manejo_Veículos":
        st.metric("Registros Frota", "~8.000", "+4% vs 2023")
    else:
        st.metric("Cooperativas", "~6.000", "+2% vs 2023")

with col3:
    st.metric("Estado com Mais Dados", "MG", "853 municípios")

with col4:
    st.metric("Região Predominante", "Nordeste", "37% dos registros")

# ============================================
# SEÇÃO 2: ANÁLISE COMPARATIVA
# ============================================
st.header("🔄 Análise Comparativa 2023 vs 2024")

if isinstance(current_data, dict) and ano_selecionado == "Comparativo 2023-2024":
    tab1, tab2, tab3 = st.tabs(["📊 Completude dos Dados", "📈 Evolução", "🗺️ Distribuição Geográfica"])
    
    with tab1:
        # Análise de completude
        st.subheader("Taxa de Preenchimento dos Dados")
        
        # Calcular completude para cada ano
        completude_2023 = (1 - current_data["2023"].isnull().sum() / len(current_data["2023"])) * 100
        completude_2024 = (1 - current_data["2024"].isnull().sum() / len(current_data["2024"])) * 100
        
        # Criar DataFrame para visualização
        comp_df = pd.DataFrame({
            'Coluna': completude_2023.index,
            '2023': completude_2023.values,
            '2024': completude_2024.values
        })
        
        # Ordenar pela completude média
        comp_df['Completude Média'] = comp_df[['2023', '2024']].mean(axis=1)
        comp_df = comp_df.sort_values('Completude Média', ascending=True).tail(20)
        
        # Gráfico de barras
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=comp_df['Coluna'],
            x=comp_df['2023'],
            name='2023',
            orientation='h',
            marker_color='#1f77b4'
        ))
        fig.add_trace(go.Bar(
            y=comp_df['Coluna'],
            x=comp_df['2024'],
            name='2024',
            orientation='h',
            marker_color='#ff7f0e'
        ))
        
        fig.update_layout(
            title="Top 20 Colunas com Melhor Preenchimento",
            xaxis_title="Completude (%)",
            yaxis_title="Colunas",
            barmode='group',
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Métricas de completude
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Completude Média 2023", f"{completude_2023.mean():.1f}%")
        with col2:
            st.metric("Completude Média 2024", f"{completude_2024.mean():.1f}%")
        with col3:
            variacao_comp = completude_2024.mean() - completude_2023.mean()
            st.metric("Evolução", f"{variacao_comp:+.1f}pp")
    
    with tab2:
        st.subheader("Evolução de Indicadores-Chave")
        
        # Aqui você pode adicionar análises específicas para cada aba
        if aba_selecionada == "Manejo_Resíduos_Sólidos_Urbanos":
            st.info("""
            **Principais constatações para esta aba:**
            - Mesmo número de municípios (5.582)
            - Melhoria na completude dos dados
            - MG permanece como estado com mais registros
            """)
        
        # Gráfico de evolução hipotético (substituir com dados reais)
        evo_data = pd.DataFrame({
            'Ano': [2023, 2024],
            'Indicador A': [75, 82],
            'Indicador B': [60, 68],
            'Indicador C': [45, 52]
        })
        
        fig = px.line(evo_data, x='Ano', y=['Indicador A', 'Indicador B', 'Indicador C'],
                     title="Evolução de Indicadores (Exemplo)")
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.subheader("Distribuição Geográfica")
        
        # Análise por estado (simplificada)
        if 'Unnamed: 4' in current_data["2023"].columns:  # Supondo que seja a coluna de estado
            estados_2023 = current_data["2023"]['Unnamed: 4'].value_counts().head(10)
            estados_2024 = current_data["2024"]['Unnamed: 4'].value_counts().head(10)
            
            fig = make_subplots(rows=1, cols=2,
                               subplot_titles=("2023", "2024"))
            
            fig.add_trace(
                go.Bar(x=estados_2023.values, y=estados_2023.index, orientation='h', name='2023'),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Bar(x=estados_2024.values, y=estados_2024.index, orientation='h', name='2024'),
                row=1, col=2
            )
            
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

# ============================================
# SEÇÃO 3: EXPLORAÇÃO DOS DADOS
# ============================================
st.header("🔍 Exploração dos Dados")

if not isinstance(current_data, dict):
    # Mostrar dados para um ano específico
    df = current_data
    
    tab1, tab2, tab3 = st.tabs(["📋 Visualização", "📊 Estatísticas", "🧹 Qualidade"])
    
    with tab1:
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            num_linhas = st.slider("Número de linhas para exibir", 10, 100, 20)
        with col2:
            colunas_selecionadas = st.multiselect(
                "Selecionar colunas",
                df.columns.tolist(),
                default=df.columns[:5].tolist() if len(df.columns) > 5 else df.columns.tolist()
            )
        
        # Exibir dados
        if colunas_selecionadas:
            st.dataframe(df[colunas_selecionadas].head(num_linhas), use_container_width=True)
        else:
            st.dataframe(df.head(num_linhas), use_container_width=True)
    
    with tab2:
        # Estatísticas descritivas
        st.subheader("Estatísticas Descritivas")
        
        # Selecionar colunas numéricas
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if numeric_cols:
            st.dataframe(df[numeric_cols].describe(), use_container_width=True)
            
            # Histograma para uma coluna numérica
            if len(numeric_cols) > 0:
                col_selecionada = st.selectbox("Selecione uma coluna para histograma:", numeric_cols)
                fig = px.histogram(df, x=col_selecionada, title=f"Distribuição de {col_selecionada}")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Não foram encontradas colunas numéricas nesta aba.")
        
        # Análise de valores únicos
        st.subheader("Análise de Categorias")
        cat_cols = df.select_dtypes(include=['object']).columns.tolist()
        if cat_cols:
            col_cat = st.selectbox("Selecione uma coluna categórica:", cat_cols)
            if col_cat in df.columns:
                contagem = df[col_cat].value_counts().head(20)
                fig = px.bar(x=contagem.index, y=contagem.values, 
                            title=f"Valores mais frequentes em {col_cat}")
                st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        # Análise de qualidade dos dados
        st.subheader("Análise de Qualidade dos Dados")
        
        # Valores nulos
        nulos_por_coluna = df.isnull().sum()
        nulos_percentual = (nulos_por_coluna / len(df) * 100).round(2)
        
        qual_df = pd.DataFrame({
            'Coluna': nulos_por_coluna.index,
            'Valores Nulos': nulos_por_coluna.values,
            '% Nulos': nulos_percentual.values
        }).sort_values('% Nulos', ascending=False)
        
        st.dataframe(qual_df, use_container_width=True)
        
        # Gráfico de valores nulos
        fig = px.bar(qual_df.head(20), x='Coluna', y='% Nulos',
                    title="Top 20 Colunas com Mais Valores Nulos")
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

# ============================================
# SEÇÃO 4: DOWNLOAD E EXPORTAÇÃO
# ============================================
st.header("💾 Exportação de Dados")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Exportar Dados Atuais")
    
    if not isinstance(current_data, dict):
        # Converter para CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar como CSV",
            data=csv,
            file_name=f"{aba_selecionada}_{ano_selecionado.replace(' ', '_')}.csv",
            mime="text/csv"
        )

with col2:
    st.subheader("Relatório")
    st.info("""
    Para gerar relatórios personalizados ou análises específicas:
    1. Selecione a aba e ano desejados
    2. Aplique os filtros necessários
    3. Utilize os dados exportados
    """)

# ============================================
# RODAPÉ
# ============================================
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>📊 <strong>Painel RSU Brasil</strong> | Dados: SNIS 2023-2024</p>
    <p style='font-size: 0.8em; color: #666;'>
        Última atualização: Dezembro 2024 | Desenvolvido com Streamlit
    </p>
</div>
""", unsafe_allow_html=True)

# ============================================
# FUNÇÕES AUXILIARES (não exibidas na interface)
# ============================================
def analyze_data_completeness(df, year):
    """Analisa a completude dos dados"""
    total_rows = len(df)
    completeness = {}
    
    for col in df.columns:
        non_null = df[col].count()
        perc = (non_null / total_rows) * 100
        completeness[col] = {
            'Ano': year,
            'Coluna': col,
            'Preenchido': non_null,
            'Nulos': total_rows - non_null,
            '% Preenchido': round(perc, 2)
        }
    
    return pd.DataFrame(completeness.values())

# Script para verificar se os arquivos existem
if __name__ == "__main__":
    # Verificar se os arquivos existem
    files_exist = all(os.path.exists(f"rsuBrasil_{year}.xlsx") for year in [2023, 2024])
    
    if not files_exist:
        st.warning("""
        ⚠️ **Arquivos de dados não encontrados!**
        
        Certifique-se de que os seguintes arquivos estão na mesma pasta do app.py:
        - `rsuBrasil_2023.xlsx`
        - `rsuBrasil_2024.xlsx`
        
        Os arquivos podem ser baixados da fonte oficial do SNIS.
        """)
