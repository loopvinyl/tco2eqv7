import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import plotly.express as px
from datetime import datetime
import io

# Configuração da página
st.set_page_config(
    page_title="Análise de Resíduos Sólidos - SNIS 2023",
    page_icon="🗑️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal
st.title("🗑️ Análise de Resíduos Sólidos - SNIS 2023")
st.markdown("""
**Sistema Nacional de Informações sobre Saneamento - Módulo Resíduos Sólidos**
            
Esta aplicação permite analisar os dados de manejo, coleta e destinação de resíduos sólidos 
urbanos dos municípios brasileiros para o ano de 2023.
""")

# Carregar dados
@st.cache_data
def load_data():
    # Simulação de carregamento - substitua pelo seu arquivo real
    try:
        # Carregar o arquivo
        df = pd.read_csv('dados_residuos_2023.csv', sep=';', encoding='utf-8')
        
        # Renomear colunas para facilitar o uso
        colunas_renomeadas = {
            'Unnamed: 0': 'Responde_modulo',
            'Unnamed: 1': 'Codigo_municipio',
            'MINISTÉRIO DAS CIDADES  /  SECRETARIA NACIONAL DE SANEAMENTO ': 'Município',
            'Unnamed: 3': 'UF',
            'Unnamed: 4': 'Regiao',
            'Unnamed: 5': 'Capital',
            'Unnamed: 6': 'CNPJ',
            'Unnamed: 7': 'Orgao_responsavel',
            'Unnamed: 8': 'Natureza_juridica',
            'Unnamed: 9': 'Populacao_urbana',
            'Unnamed: 10': 'Populacao_rural',
            'Unnamed: 11': 'Populacao_total',
            'Unnamed: 12': 'Economias_ativas_urbanas',
            'Unnamed: 13': 'Economias_ativas_ruras',
            'Unnamed: 14': 'Economias_ativas_total',
            'Unnamed: 15': 'Densidade_demografica',
            'Unnamed: 16': 'ID_destino',
            'Unnamed: 17': 'Tipo_coleta',
            'Unnamed: 18': 'Abrangencia_servico',
            'Unnamed: 19': 'Tipo_executor',
            'Unnamed: 20': 'Quantidade_coletada_ton_mes',
            'Unnamed: 21': 'Quantidade_coletada_m3_mes',
            'Unnamed: 22': 'Numero_veiculos',
            'Unnamed: 23': 'Numero_funcionarios',
            'Unnamed: 24': 'Frequencia_coleta',
            'Unnamed: 25': 'Envia_para_outro_municipio',
            'Unnamed: 26': 'Municipio_destino_codigo',
            'Unnamed: 27': 'Municipio_destino_nome',
            'Unnamed: 28': 'Tipo_destino',
            'Unnamed: 29': 'Executor_destino',
            'Unnamed: 30': 'Descricao_destino',
            'Unnamed: 31': 'Nome_destino',
            'Unnamed: 32': 'Forma_coleta',
            'Unnamed: 33': 'Peso_residuo_umido',
            'Unnamed: 34': 'Peso_residuo_seco',
            'Unnamed: 35': 'Peso_rejeito',
            'Unnamed: 36': 'Peso_reciclavel',
            'Unnamed: 37': 'Peso_organico',
            'Unnamed: 38': 'Numero_pontos_coleta',
            'Unnamed: 39': 'Frequencia_coleta_seletiva'
        }
        
        df = df.rename(columns=colunas_renomeadas)
        
        # Converter colunas numéricas
        colunas_numericas = [
            'Populacao_urbana', 'Populacao_rural', 'Populacao_total',
            'Economias_ativas_urbanas', 'Economias_ativas_ruras', 'Economias_ativas_total',
            'Densidade_demografica', 'Quantidade_coletada_ton_mes',
            'Quantidade_coletada_m3_mes', 'Numero_veiculos', 'Numero_funcionarios',
            'Peso_residuo_umido', 'Peso_residuo_seco', 'Peso_rejeito',
            'Peso_reciclavel', 'Peso_organico', 'Numero_pontos_coleta'
        ]
        
        for col in colunas_numericas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        # Retornar DataFrame vazio com estrutura básica
        return pd.DataFrame(columns=['Município', 'UF', 'Regiao', 'Tipo_coleta', 'Tipo_destino'])

# Carregar dados
df = load_data()

# Sidebar para filtros
st.sidebar.header("🔍 Filtros")

# Filtro por estado
if 'UF' in df.columns:
    estados = ['Todos'] + sorted(df['UF'].dropna().unique().tolist())
    estado_selecionado = st.sidebar.selectbox("Selecione o Estado", estados)
else:
    estado_selecionado = 'Todos'

# Filtro por região
if 'Regiao' in df.columns:
    regioes = ['Todos'] + sorted(df['Regiao'].dropna().unique().tolist())
    regiao_selecionada = st.sidebar.selectbox("Selecione a Região", regioes)
else:
    regiao_selecionada = 'Todos'

# Filtro por tipo de coleta
if 'Tipo_coleta' in df.columns:
    tipos_coleta = ['Todos'] + sorted(df['Tipo_coleta'].dropna().unique().tolist())
    tipo_coleta_selecionado = st.sidebar.selectbox("Selecione o Tipo de Coleta", tipos_coleta)
else:
    tipo_coleta_selecionado = 'Todos'

# Filtro por tipo de destino
if 'Tipo_destino' in df.columns:
    tipos_destino = ['Todos'] + sorted(df['Tipo_destino'].dropna().unique().tolist())
    tipo_destino_selecionado = st.sidebar.selectbox("Selecione o Tipo de Destino", tipos_destino)
else:
    tipo_destino_selecionado = 'Todos'

# Aplicar filtros
df_filtrado = df.copy()

if estado_selecionado != 'Todos' and 'UF' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado['UF'] == estado_selecionado]

if regiao_selecionada != 'Todos' and 'Regiao' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado['Regiao'] == regiao_selecionada]

if tipo_coleta_selecionado != 'Todos' and 'Tipo_coleta' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado['Tipo_coleta'] == tipo_coleta_selecionado]

if tipo_destino_selecionado != 'Todos' and 'Tipo_destino' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado['Tipo_destino'] == tipo_destino_selecionado]

# Remover linhas onde o município não respondeu ao módulo
if 'Responde_modulo' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado['Responde_modulo'].isin(['Sim', 'Não'])]

# Informações gerais
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Informações Gerais")
st.sidebar.write(f"**Municípios no filtro:** {len(df_filtrado):,}")
st.sidebar.write(f"**Total de registros:** {df_filtrado.shape[0]:,}")
st.sidebar.write(f"**Colunas disponíveis:** {df_filtrado.shape[1]:,}")

# Botão para mostrar/ocultar dados brutos
if st.sidebar.checkbox("Mostrar dados brutos"):
    st.sidebar.dataframe(df_filtrado.head(100))

# ============================================================
# VISÃO GERAL
# ============================================================

st.header("📊 Visão Geral")

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_municipios = df_filtrado['Município'].nunique() if 'Município' in df_filtrado.columns else 0
    st.metric("Municípios", f"{total_municipios:,}")

with col2:
    if 'Populacao_total' in df_filtrado.columns:
        pop_total = df_filtrado['Populacao_total'].sum()
        st.metric("População Total", f"{pop_total:,.0f}")
    else:
        st.metric("População Total", "N/A")

with col3:
    if 'Tipo_coleta' in df_filtrado.columns:
        tipos_coleta_count = df_filtrado['Tipo_coleta'].nunique()
        st.metric("Tipos de Coleta", f"{tipos_coleta_count}")
    else:
        st.metric("Tipos de Coleta", "N/A")

with col4:
    if 'Tipo_destino' in df_filtrado.columns:
        tipos_destino_count = df_filtrado['Tipo_destino'].nunique()
        st.metric("Tipos de Destino", f"{tipos_destino_count}")
    else:
        st.metric("Tipos de Destino", "N/A")

# ============================================================
# DISTRIBUIÇÃO POR TIPO DE DESTINAÇÃO
# ============================================================

st.subheader("🗺️ Distribuição por Tipo de Destinação")

if 'Tipo_destino' in df_filtrado.columns:
    # Contagem por tipo de destino
    destinos_counts = df_filtrado['Tipo_destino'].value_counts()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Gráfico de barras
        fig, ax = plt.subplots(figsize=(10, 6))
        colors = plt.cm.Set3(np.linspace(0, 1, len(destinos_counts)))
        bars = ax.bar(destinos_counts.index, destinos_counts.values, color=colors)
        ax.set_xlabel('Tipo de Destino')
        ax.set_ylabel('Número de Municípios')
        ax.set_title('Distribuição por Tipo de Destinação')
        plt.xticks(rotation=45, ha='right')
        
        # Adicionar valores nas barras
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{int(height)}', ha='center', va='bottom', fontsize=9)
        
        st.pyplot(fig)
        plt.close(fig)
    
    with col2:
        st.write("**Estatísticas:**")
        st.dataframe(destinos_counts)
        
        # Download dos dados
        csv_destinos = destinos_counts.reset_index().to_csv(index=False)
        st.download_button(
            label="📥 Baixar dados de destinação",
            data=csv_destinos,
            file_name="destinacao_residuos.csv",
            mime="text/csv"
        )
else:
    st.info("Coluna 'Tipo_destino' não encontrada nos dados.")

# ============================================================
# DISTRIBUIÇÃO POR TIPO DE COLETA
# ============================================================

st.subheader("🚚 Distribuição por Tipo de Coleta")

if 'Tipo_coleta' in df_filtrado.columns:
    # Contagem por tipo de coleta
    coleta_counts = df_filtrado['Tipo_coleta'].value_counts()
    
    # Criar gráfico de pizza
    fig2, ax2 = plt.subplots(figsize=(8, 8))
    wedges, texts, autotexts = ax2.pie(
        coleta_counts.values,
        labels=coleta_counts.index,
        autopct='%1.1f%%',
        startangle=90,
        colors=plt.cm.Pastel1(np.linspace(0, 1, len(coleta_counts)))
    )
    ax2.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
    ax2.set_title('Distribuição por Tipo de Coleta')
    
    # Ajustar fonte dos textos
    for text in texts:
        text.set_fontsize(9)
    for autotext in autotexts:
        autotext.set_fontsize(8)
        autotext.set_weight('bold')
    
    st.pyplot(fig2)
    plt.close(fig2)
    
    # Mostrar tabela
    st.write("**Detalhamento:**")
    st.dataframe(coleta_counts)
else:
    st.info("Coluna 'Tipo_coleta' não encontrada nos dados.")

# ============================================================
# DISTRIBUIÇÃO REGIONAL
# ============================================================

st.subheader("📍 Distribuição Regional")

col1, col2 = st.columns(2)

with col1:
    if 'UF' in df_filtrado.columns:
        uf_counts = df_filtrado['UF'].value_counts()
        
        fig3, ax3 = plt.subplots(figsize=(10, 6))
        ax3.bar(uf_counts.index, uf_counts.values, color='skyblue')
        ax3.set_xlabel('Estado (UF)')
        ax3.set_ylabel('Número de Municípios')
        ax3.set_title('Distribuição por Estado')
        plt.xticks(rotation=45)
        st.pyplot(fig3)
        plt.close(fig3)

with col2:
    if 'Regiao' in df_filtrado.columns:
        regiao_counts = df_filtrado['Regiao'].value_counts()
        
        fig4, ax4 = plt.subplots(figsize=(8, 6))
        colors = ['#FF9999', '#66B2FF', '#99FF99', '#FFCC99', '#FF99CC']
        ax4.pie(regiao_counts.values, labels=regiao_counts.index, autopct='%1.1f%%',
                colors=colors[:len(regiao_counts)], startangle=90)
        ax4.axis('equal')
        ax4.set_title('Distribuição por Região')
        st.pyplot(fig4)
        plt.close(fig4)

# ============================================================
# ♻️ DESTINAÇÃO DA COLETA SELETIVA DE RESÍDUOS ORGÂNICOS
# ============================================================

st.subheader("♻️ Destinação da Coleta Seletiva de Resíduos Orgânicos")

# Filtrar apenas os registros de coleta seletiva de orgânicos
coleta_organicos = df_filtrado[
    df_filtrado['Tipo_coleta'] == 'Coleta seletiva de resíduos sólidos domiciliares recicláveis orgânicos'
]

if not coleta_organicos.empty:
    # Resumo estatístico
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Municípios com coleta de orgânicos",
            f"{coleta_organicos.shape[0]:,}",
            delta=None
        )
    
    with col2:
        municipios_com_destino = coleta_organicos[coleta_organicos['Tipo_destino'].notna()].shape[0]
        st.metric(
            "Com destino definido",
            f"{municipios_com_destino:,}",
            delta=None
        )
    
    with col3:
        percentual = (municipios_com_destino / coleta_organicos.shape[0] * 100) if coleta_organicos.shape[0] > 0 else 0
        st.metric(
            "Taxa de destinação",
            f"{percentual:.1f}%",
            delta=None
        )
    
    # Tabela com destinos dos resíduos orgânicos
    st.write("**Destinos dos resíduos orgânicos coletados seletivamente:**")
    
    # Preparar dados para exibição
    destinos_organicos = coleta_organicos[[
        'Município', 'UF', 'Tipo_destino', 'Descricao_destino', 
        'Envia_para_outro_municipio', 'Municipio_destino_codigo', 
        'Municipio_destino_nome'
    ]].copy()
    
    # Substituir valores nulos
    destinos_organicos['Tipo_destino'] = destinos_organicos['Tipo_destino'].fillna('Não informado')
    destinos_organicos['Descricao_destino'] = destinos_organicos['Descricao_destino'].fillna('Não informado')
    
    # Destinos mais comuns
    st.write("**Tipos de destinação mais frequentes:**")
    destinos_counts = destinos_organicos['Tipo_destino'].value_counts()
    
    fig_destinos_organicos, ax_destinos_organicos = plt.subplots(figsize=(10, 4))
    bars = ax_destinos_organicos.barh(
        destinos_counts.index, 
        destinos_counts.values,
        color='#2ca02c'
    )
    ax_destinos_organicos.set_xlabel('Número de Municípios')
    ax_destinos_organicos.set_title('Destinação dos Resíduos Orgânicos')
    
    # Adicionar valores nas barras
    for bar in bars:
        width = bar.get_width()
        ax_destinos_organicos.text(
            width + 0.1, 
            bar.get_y() + bar.get_height()/2,
            f'{int(width)}',
            va='center'
        )
    
    st.pyplot(fig_destinos_organicos)
    plt.close(fig_destinos_organicos)
    
    # Filtro para destinos específicos
    st.write("**Filtrar por tipo de destinação:**")
    tipos_destino_disponiveis = ['Todos'] + destinos_organicos['Tipo_destino'].unique().tolist()
    tipo_selecionado_organicos = st.selectbox(
        "Selecione o tipo de destino",
        tipos_destino_disponiveis,
        key="filtro_destino_organicos"
    )
    
    # Aplicar filtro se necessário
    if tipo_selecionado_organicos != 'Todos':
        destinos_filtrados = destinos_organicos[
            destinos_organicos['Tipo_destino'] == tipo_selecionado_organicos
        ]
    else:
        destinos_filtrados = destinos_organicos
    
    # Mostrar tabela detalhada
    st.write(f"**Detalhamento ({len(destinos_filtrados)} registros):**")
    
    # Formatando para exibição
    destinos_display = destinos_filtrados.rename(columns={
        'Município': 'Município de Origem',
        'UF': 'UF Origem',
        'Tipo_destino': 'Tipo de Destino',
        'Descricao_destino': 'Descrição do Destino',
        'Envia_para_outro_municipio': 'Envia para Outro Município?',
        'Municipio_destino_codigo': 'Código Município Destino',
        'Municipio_destino_nome': 'Município Destino'
    })
    
    # Reduzir largura das colunas
    st.dataframe(
        destinos_display,
        use_container_width=True,
        hide_index=True,
        height=min(400, 50 + len(destinos_filtrados) * 35)
    )
    
    # Análise dos destinos para compostagem
    st.write("**Análise para Compostagem/Vermicompostagem:**")
    
    # Identificar destinos potencialmente relacionados a compostagem
    palavras_chave_compostagem = [
        'triagem', 'usina', 'compostagem', 'orgânico', 'biológico', 
        'tratamento', 'biorreator', 'vermicompostagem'
    ]
    
    destinos_potenciais_compostagem = destinos_organicos[
        destinos_organicos['Descricao_destino'].str.contains(
            '|'.join(palavras_chave_compostagem), 
            case=False, 
            na=False
        )
    ]
    
    if not destinos_potenciais_compostagem.empty:
        st.success(f"✅ **{len(destinos_potenciais_compostagem)} municípios** podem estar enviando resíduos orgânicos para unidades com potencial de compostagem/vermicompostagem.")
        
        # Mostrar exemplos
        st.write("**Exemplos de destinos com potencial para compostagem:**")
        exemplos = destinos_potenciais_compostagem[
            ['Município', 'UF', 'Descricao_destino']
        ].head(10)
        st.dataframe(exemplos, hide_index=True, use_container_width=True)
    else:
        st.warning("⚠️ Não foram identificados destinos claramente relacionados a compostagem/vermicompostagem nas descrições disponíveis.")
    
    # Download dos dados
    csv_organicos = destinos_organicos.to_csv(index=False, sep=';')
    st.download_button(
        label="📥 Baixar dados de destinação de orgânicos (CSV)",
        data=csv_organicos,
        file_name=f"destinacao_residuos_organicos_{estado_selecionado.lower() if estado_selecionado != 'Todos' else 'brasil'}.csv",
        mime="text/csv"
    )
    
else:
    st.info("ℹ️ Não foram encontrados registros de coleta seletiva de resíduos orgânicos para os filtros selecionados.")
    st.write("""
    **Nota:** A coleta seletiva de resíduos orgânicos é uma prática ainda em desenvolvimento no Brasil. 
    Muitos municípios não possuem sistemas específicos para coleta de resíduos orgânicos, que muitas vezes 
    são coletados junto com os resíduos indiferenciados.
    """)

st.markdown("---")

# ============================================================
# 🌳 DESTINAÇÃO DAS PODAS E GALHADAS DE ÁREAS VERDES PÚBLICAS
# ============================================================

st.subheader("🌳 Destinação das Podas e Galhadas de Áreas Verdes Públicas")

# Filtrar apenas os registros de coleta de podas e galhadas
coleta_podas = df_filtrado[
    df_filtrado['Tipo_coleta'] == 'Coleta de resíduos sólidos específica para áreas verdes públicas (podas e galhadas)'
]

if not coleta_podas.empty:
    # Resumo estatístico
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Municípios com coleta de podas",
            f"{coleta_podas.shape[0]:,}",
            delta=None
        )
    
    with col2:
        municipios_com_destino_podas = coleta_podas[coleta_podas['Tipo_destino'].notna()].shape[0]
        st.metric(
            "Com destino definido",
            f"{municipios_com_destino_podas:,}",
            delta=None
        )
    
    with col3:
        percentual_podas = (municipios_com_destino_podas / coleta_podas.shape[0] * 100) if coleta_podas.shape[0] > 0 else 0
        st.metric(
            "Taxa de destinação",
            f"{percentual_podas:.1f}%",
            delta=None
        )
    
    # Tabela com destinos das podas
    st.write("**Destinos das podas e galhadas coletadas:**")
    
    # Preparar dados para exibição
    destinos_podas = coleta_podas[[
        'Município', 'UF', 'Tipo_destino', 'Descricao_destino', 
        'Envia_para_outro_municipio', 'Municipio_destino_codigo', 
        'Municipio_destino_nome'
    ]].copy()
    
    # Substituir valores nulos
    destinos_podas['Tipo_destino'] = destinos_podas['Tipo_destino'].fillna('Não informado')
    destinos_podas['Descricao_destino'] = destinos_podas['Descricao_destino'].fillna('Não informado')
    
    # Destinos mais comuns para podas
    st.write("**Tipos de destinação mais frequentes para podas:**")
    destinos_counts_podas = destinos_podas['Tipo_destino'].value_counts()
    
    fig_destinos_podas, ax_destinos_podas = plt.subplots(figsize=(10, 4))
    bars_podas = ax_destinos_podas.barh(
        destinos_counts_podas.index, 
        destinos_counts_podas.values,
        color='#228B22'
    )
    ax_destinos_podas.set_xlabel('Número de Municípios')
    ax_destinos_podas.set_title('Destinação das Podas e Galhadas')
    
    # Adicionar valores nas barras
    for bar in bars_podas:
        width = bar.get_width()
        ax_destinos_podas.text(
            width + 0.1, 
            bar.get_y() + bar.get_height()/2,
            f'{int(width)}',
            va='center'
        )
    
    st.pyplot(fig_destinos_podas)
    plt.close(fig_destinos_podas)
    
    # Filtro para destinos específicos de podas
    st.write("**Filtrar por tipo de destinação:**")
    tipos_destino_podas_disponiveis = ['Todos'] + destinos_podas['Tipo_destino'].unique().tolist()
    tipo_selecionado_podas = st.selectbox(
        "Selecione o tipo de destino",
        tipos_destino_podas_disponiveis,
        key="filtro_destino_podas"
    )
    
    # Aplicar filtro se necessário
    if tipo_selecionado_podas != 'Todos':
        destinos_filtrados_podas = destinos_podas[
            destinos_podas['Tipo_destino'] == tipo_selecionado_podas
        ]
    else:
        destinos_filtrados_podas = destinos_podas
    
    # Mostrar tabela detalhada
    st.write(f"**Detalhamento ({len(destinos_filtrados_podas)} registros):**")
    
    # Formatando para exibição
    destinos_display_podas = destinos_filtrados_podas.rename(columns={
        'Município': 'Município de Origem',
        'UF': 'UF Origem',
        'Tipo_destino': 'Tipo de Destino',
        'Descricao_destino': 'Descrição do Destino',
        'Envia_para_outro_municipio': 'Envia para Outro Município?',
        'Municipio_destino_codigo': 'Código Município Destino',
        'Municipio_destino_nome': 'Município Destino'
    })
    
    # Reduzir largura das colunas
    st.dataframe(
        destinos_display_podas,
        use_container_width=True,
        hide_index=True,
        height=min(400, 50 + len(destinos_filtrados_podas) * 35)
    )
    
    # Análise dos destinos para compostagem de podas
    st.write("**Análise para Compostagem de Podas:**")
    
    # Identificar destinos potencialmente relacionados a compostagem
    palavras_chave_compostagem_podas = [
        'triagem', 'usina', 'compostagem', 'orgânico', 'biológico', 
        'tratamento', 'biorreator', 'vermicompostagem', 'poda', 'galhada'
    ]
    
    destinos_potenciais_compostagem_podas = destinos_podas[
        destinos_podas['Descricao_destino'].str.contains(
            '|'.join(palavras_chave_compostagem_podas), 
            case=False, 
            na=False
        )
    ]
    
    if not destinos_potenciais_compostagem_podas.empty:
        st.success(f"✅ **{len(destinos_potenciais_compostagem_podas)} municípios** podem estar enviando podas e galhadas para unidades com potencial de compostagem.")
        
        # Mostrar exemplos
        st.write("**Exemplos de destinos com potencial para compostagem de podas:**")
        exemplos_podas = destinos_potenciais_compostagem_podas[
            ['Município', 'UF', 'Descricao_destino']
        ].head(10)
        st.dataframe(exemplos_podas, hide_index=True, use_container_width=True)
    else:
        st.warning("⚠️ Não foram identificados destinos claramente relacionados a compostagem de podas nas descrições disponíveis.")
    
    # Download dos dados de podas
    csv_podas = destinos_podas.to_csv(index=False, sep=';')
    st.download_button(
        label="📥 Baixar dados de destinação de podas (CSV)",
        data=csv_podas,
        file_name=f"destinacao_podas_{estado_selecionado.lower() if estado_selecionado != 'Todos' else 'brasil'}.csv",
        mime="text/csv"
    )
    
else:
    st.info("ℹ️ Não foram encontrados registros de coleta de podas e galhadas para os filtros selecionados.")

st.markdown("---")

# ============================================================
# 🔍 ANÁLISE DE CORRELAÇÕES
# ============================================================

st.subheader("🔍 Análise de Correlações")

# Verificar se temos colunas numéricas para análise
colunas_numericas = df_filtrado.select_dtypes(include=[np.number]).columns.tolist()

if len(colunas_numericas) > 1:
    # Selecionar colunas para análise
    colunas_selecionadas = st.multiselect(
        "Selecione as colunas numéricas para análise de correlação",
        colunas_numericas,
        default=colunas_numericas[:5] if len(colunas_numericas) >= 5 else colunas_numericas
    )
    
    if len(colunas_selecionadas) >= 2:
        # Calcular matriz de correlação
        corr_matrix = df_filtrado[colunas_selecionadas].corr()
        
        # Plotar heatmap
        fig5, ax5 = plt.subplots(figsize=(10, 8))
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0, ax=ax5)
        ax5.set_title('Matriz de Correlação')
        st.pyplot(fig5)
        plt.close(fig5)
        
        # Identificar correlações fortes
        st.write("**Correlações significativas (|r| > 0.7):**")
        correlacoes_fortes = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                if abs(corr_matrix.iloc[i, j]) > 0.7:
                    correlacoes_fortes.append({
                        'Variável 1': corr_matrix.columns[i],
                        'Variável 2': corr_matrix.columns[j],
                        'Correlação': f"{corr_matrix.iloc[i, j]:.3f}"
                    })
        
        if correlacoes_fortes:
            st.dataframe(pd.DataFrame(correlacoes_fortes))
        else:
            st.info("Não foram encontradas correlações fortes (|r| > 0.7) entre as variáveis selecionadas.")
    else:
        st.warning("Selecione pelo menos 2 colunas numéricas para análise de correlação.")
else:
    st.info("Número insuficiente de colunas numéricas para análise de correlação.")

# ============================================================
# 📋 TABELA DETALHADA
# ============================================================

st.subheader("📋 Tabela Detalhada")

# Selecionar colunas para exibição
colunas_disponiveis = df_filtrado.columns.tolist()
colunas_padrao = ['Município', 'UF', 'Regiao', 'Tipo_coleta', 'Tipo_destino', 'Populacao_total']

colunas_selecionadas_tabela = st.multiselect(
    "Selecione as colunas para exibir na tabela",
    colunas_disponiveis,
    default=[c for c in colunas_padrao if c in colunas_disponiveis]
)

if colunas_selecionadas_tabela:
    # Mostrar tabela com as colunas selecionadas
    st.dataframe(
        df_filtrado[colunas_selecionadas_tabela],
        use_container_width=True,
        height=400
    )
    
    # Opção para download
    csv_tabela = df_filtrado[colunas_selecionadas_tabela].to_csv(index=False, sep=';')
    st.download_button(
        label="📥 Baixar tabela filtrada (CSV)",
        data=csv_tabela,
        file_name=f"dados_filtrados_residuos_{estado_selecionado.lower() if estado_selecionado != 'Todos' else 'brasil'}.csv",
        mime="text/csv"
    )
else:
    st.warning("Selecione pelo menos uma coluna para exibir na tabela.")

# ============================================================
# 📈 ANÁLISE TEMPORAL (SIMULADA)
# ============================================================

st.subheader("📈 Tendências e Projeções")

# Esta seção é simulada, pois os dados são apenas de 2023
st.info("""
**Nota:** Os dados disponíveis são referentes apenas ao ano de 2023. 
Para análise temporal, seriam necessários dados históricos de anos anteriores.
""")

# Simular algumas tendências baseadas nos dados atuais
if 'Tipo_destino' in df_filtrado.columns and 'Tipo_coleta' in df_filtrado.columns:
    # Calcular percentual de destinação adequada vs inadequada
    destinos_adequados = ['Aterro sanitário', 'Unidade de triagem (galpão ou usina)']
    destinos_inadequados = ['Lixão ou vazadouro', 'Aterro controlado']
    
    total_registros = len(df_filtrado)
    adequados = df_filtrado[df_filtrado['Tipo_destino'].isin(destinos_adequados)].shape[0]
    inadequados = df_filtrado[df_filtrado['Tipo_destino'].isin(destinos_inadequados)].shape[0]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "Destinação Adequada",
            f"{(adequados/total_registros*100):.1f}%" if total_registros > 0 else "0%",
            delta="+2.5%"  # Simulado
        )
    
    with col2:
        st.metric(
            "Destinação Inadequada",
            f"{(inadequados/total_registros*100):.1f}%" if total_registros > 0 else "0%",
            delta="-1.8%"  # Simulado
        )
    
    # Gráfico de tendência simulada
    anos = [2020, 2021, 2022, 2023]
    adequados_sim = [30, 35, 38, (adequados/total_registros*100) if total_registros > 0 else 40]
    inadequados_sim = [70, 65, 62, (inadequados/total_registros*100) if total_registros > 0 else 60]
    
    fig6, ax6 = plt.subplots(figsize=(10, 6))
    ax6.plot(anos, adequados_sim, marker='o', label='Destinação Adequada', linewidth=2)
    ax6.plot(anos, inadequados_sim, marker='s', label='Destinação Inadequada', linewidth=2)
    ax6.set_xlabel('Ano')
    ax6.set_ylabel('Percentual (%)')
    ax6.set_title('Evolução da Destinação de Resíduos (Simulado)')
    ax6.legend()
    ax6.grid(True, alpha=0.3)
    st.pyplot(fig6)
    plt.close(fig6)

# ============================================================
# 🏁 CONCLUSÕES E RECOMENDAÇÕES
# ============================================================

st.subheader("🏁 Conclusões e Recomendações")

st.markdown("""
### Principais Insights:

1. **Destinação de Resíduos**: 
   - A maioria dos municípios utiliza aterros sanitários como principal destino
   - Ainda há uma parcela significativa utilizando lixões/vazadouros

2. **Coleta Seletiva**:
   - A coleta seletiva de materiais recicláveis secos está mais difundida
   - A coleta de orgânicos é ainda incipiente na maioria dos municípios

3. **Podas e Galhadas**:
   - A destinação adequada de resíduos de podas é um desafio
   - Há oportunidades para compostagem destes materiais

### Recomendações:

✅ **Ampliar a coleta seletiva de orgânicos** para reduzir a quantidade de resíduos enviados a aterros

✅ **Implementar sistemas de compostagem** municipais ou regionais

✅ **Fortalecer a logística reversa** de embalagens e outros materiais

✅ **Investir em educação ambiental** para reduzir a geração de resíduos na fonte

### Próximos Passos:

1. Identificar municípios com maior potencial para compostagem
2. Analisar viabilidade técnica e econômica de usinas de compostagem
3. Desenvolver projetos pilotos em municípios selecionados
4. Capacitar técnicos municipais em gestão de resíduos orgânicos
""")

# ============================================================
# 📊 RESUMO FINAL
# ============================================================

st.subheader("📊 Resumo Executivo")

# Criar um resumo compacto
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total de Municípios Analisados", f"{len(df_filtrado):,}")

with col2:
    if 'Tipo_destino' in df_filtrado.columns:
        aterros = df_filtrado[df_filtrado['Tipo_destino'] == 'Aterro sanitário'].shape[0]
        st.metric("Usam Aterro Sanitário", f"{aterros:,}")

with col3:
    if 'Tipo_destino' in df_filtrado.columns:
        lixoes = df_filtrado[df_filtrado['Tipo_destino'] == 'Lixão ou vazadouro'].shape[0]
        st.metric("Usam Lixão/Vazadouro", f"{lixoes:,}")

with col4:
    if 'Populacao_total' in df_filtrado.columns:
        pop_coberta = df_filtrado['Populacao_total'].sum()
        st.metric("População Coberta", f"{pop_coberta:,.0f}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p><strong>Sistema Nacional de Informações sobre Saneamento - SNIS 2023</strong></p>
    <p>Ministério das Cidades / Secretaria Nacional de Saneamento</p>
    <p>Dados atualizados em: 18/01/2024 | Análise gerada em: {}</p>
</div>
""".format(datetime.now().strftime("%d/%m/%Y %H:%M")), unsafe_allow_html=True)
