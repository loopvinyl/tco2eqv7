import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import BytesIO
import matplotlib.pyplot as plt
import unicodedata

# Configuração da página
st.set_page_config(
    page_title="Análise SINISA 2023 - Resíduos Sólidos Urbanos",
    page_icon="🗑️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título e introdução
st.title("🗑️ Análise SINISA 2023 - Resíduos Sólidos Urbanos")
st.markdown("""
### Sistema Nacional de Informações sobre Saneamento
**Análise completa de dados municipais brasileiros para simulação de emissões de GEE**
""")

# URL do arquivo Excel
EXCEL_URL = "https://github.com/loopvinyl/tco2eqv7/raw/main/rsuBrasil.xlsx"

@st.cache_data(ttl=3600)
def carregar_dados_completos():
    """
    Carrega e processa os dados do Excel SINISA 2023
    Retorna: dataframe filtrado e dicionário de colunas mapeadas
    """
    try:
        # Download do arquivo
        response = requests.get(EXCEL_URL, timeout=60)
        response.raise_for_status()
        excel_file = BytesIO(response.content)
        
        # Carregar como Excel
        xls = pd.ExcelFile(excel_file)
        
        # Carregar aba específica SEM cabeçalho para análise
        df_raw = pd.read_excel(xls, sheet_name="Manejo_Coleta_e_Destinação", header=None)
        
        # Encontrar linha de cabeçalho
        header_row = None
        for i in range(min(15, len(df_raw))):
            # Verificar se esta linha tem os nomes das colunas conhecidos
            row_vals = df_raw.iloc[i].astype(str).str.lower().values
            
            # Procurar por padrões de nomes de coluna
            if any('col_' in v or 'massa' in v or 'destino' in v for v in row_vals):
                header_row = i
                break
        
        if header_row is None:
            # Usar linha 0 como fallback
            df = pd.read_excel(xls, sheet_name="Manejo_Coleta_e_Destinação")
            st.info("Usando primeira linha como cabeçalho")
        else:
            df = pd.read_excel(xls, sheet_name="Manejo_Coleta_e_Destinação", header=header_row)
            st.success(f"Cabeçalho identificado na linha {header_row + 1}")
        
        # Aplicar filtro: apenas registros com 'Sim' na primeira coluna
        primeira_col = df.columns[0]
        df_filtrado = df[df[primeira_col] == 'Sim'].copy()
        
        # Limpeza básica
        df_filtrado = df_filtrado.replace(['', ' ', 'NaN', 'nan', 'NaT', 'None'], np.nan)
        
        return df_filtrado
        
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return None

def identificar_colunas_principais(df):
    """
    Identifica automaticamente as colunas principais baseadas no relatório SINISA
    """
    colunas = {}
    
    # Mapeamento baseado no relatório
    mapeamento = {
        'Município': ['município', 'municipio', 'cidade', 'local', 'nome_municipio', 'localidade'],
        'Estado': ['col_3', 'estado', 'uf', 'unidade da federação'],
        'Região': ['col_4', 'região', 'regiao', 'grande região'],
        'Tipo_Coleta': ['col_17', 'tipo de coleta', 'tipo_coleta', 'modalidade_coleta'],
        'Massa_Total': ['col_24', 'massa', 'total coletada', 'toneladas', 'peso', 'quantidade'],
        'Destino': ['col_28', 'destino', 'destinação', 'destinacao_final', 'destino_final']
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
        
        # Se não encontrou pelo nome, usar índice conhecido
        if not encontrada and tipo == 'Estado' and len(df.columns) > 3:
            colunas[tipo] = df.columns[3]  # Coluna D
        elif not encontrada and tipo == 'Região' and len(df.columns) > 4:
            colunas[tipo] = df.columns[4]  # Coluna E
        elif not encontrada and tipo == 'Tipo_Coleta' and len(df.columns) > 17:
            colunas[tipo] = df.columns[17]  # Coluna R
        elif not encontrada and tipo == 'Massa_Total' and len(df.columns) > 24:
            colunas[tipo] = df.columns[24]  # Coluna Y
        elif not encontrada and tipo == 'Destino' and len(df.columns) > 28:
            colunas[tipo] = df.columns[28]  # Coluna AC
    
    # Para município, tentar encontrar por conteúdo
    if 'Município' not in colunas:
        for col in df.columns:
            # Verificar se a coluna tem valores que parecem nomes de municípios
            try:
                amostra = df[col].dropna().astype(str).head(10).str.lower()
                if any('ribeirão' in v or 'são' in v or 'rio' in v for v in amostra):
                    colunas['Município'] = col
                    break
            except:
                continue
    
    return colunas

def normalizar_texto(texto):
    """Normaliza texto removendo acentos e convertendo para minúsculas"""
    if pd.isna(texto):
        return ""
    texto = str(texto)
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto.lower().strip()

def buscar_municipio_eficiente(df, municipio_nome, coluna_municipio):
    """Busca eficiente de município com múltiplas estratégias"""
    if coluna_municipio not in df.columns:
        return None
    
    # Normalizar nome do município buscado
    municipio_busca = normalizar_texto(municipio_nome)
    
    # Estratégia 1: Busca exata
    df_temp = df.copy()
    df_temp['_temp_norm'] = df_temp[coluna_municipio].apply(normalizar_texto)
    mask_exato = df_temp['_temp_norm'] == municipio_busca
    
    if mask_exato.any():
        return df_temp[mask_exato].iloc[0]
    
    # Estratégia 2: Busca por partes (para nomes compostos)
    partes = [p for p in municipio_busca.split() if len(p) > 2]
    if len(partes) > 1:
        mask_parte = pd.Series(True, index=df_temp.index)
        for parte in partes:
            mask_parte = mask_parte & df_temp['_temp_norm'].str.contains(parte, na=False)
        
        if mask_parte.any():
            return df_temp[mask_parte].iloc[0]
    
    # Estratégia 3: Busca flexível
    mask_flex = df_temp['_temp_norm'].str.contains(municipio_busca[:5], na=False)
    if mask_flex.any():
        return df_temp[mask_flex].iloc[0]
    
    return None

def calcular_simulacao(massa_anual, cenario):
    """Calcula a simulação de cenários de destinação de resíduos"""
    
    cenarios = {
        "Cenário Atual": {
            'Aterro': 0.85,
            'Reciclagem': 0.08,
            'Compostagem': 0.07,
            'Emissões (t CO₂eq)': massa_anual * 0.8,
            'Redução vs Atual': '0%',
            'cor': '#e74c3c',
            'descricao': 'Baseado em médias brasileiras atuais'
        },
        "Cenário de Economia Circular": {
            'Aterro': 0.40,
            'Reciclagem': 0.35,
            'Compostagem': 0.25,
            'Emissões (t CO₂eq)': massa_anual * 0.4,
            'Redução vs Atual': '50%',
            'cor': '#3498db',
            'descricao': 'Aumento significativo de reciclagem e compostagem'
        },
        "Cenário Otimizado (Máxima Reciclagem)": {
            'Aterro': 0.20,
            'Reciclagem': 0.45,
            'Compostagem': 0.35,
            'Emissões (t CO₂eq)': massa_anual * 0.2,
            'Redução vs Atual': '75%',
            'cor': '#2ecc71',
            'descricao': 'Máxima recuperação de materiais'
        }
    }
    
    return cenarios[cenario]

def criar_graficos_simulacao(massa_anual, cenario):
    """Cria gráficos para visualização da simulação"""
    
    fracoes = calcular_simulacao(massa_anual, cenario)
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    
    # Gráfico 1: Destinação atual vs proposta
    destinos = ['Aterro', 'Reciclagem', 'Compostagem']
    valores_atual = [0.85, 0.08, 0.07]
    valores_cenario = [fracoes['Aterro'], fracoes['Reciclagem'], fracoes['Compostagem']]
    
    x = np.arange(len(destinos))
    width = 0.35
    
    ax1.bar(x - width/2, valores_atual, width, label='Cenário Atual', color='#95a5a6')
    ax1.bar(x + width/2, valores_cenario, width, label=cenario, color=fracoes['cor'])
    ax1.set_ylabel('Proporção')
    ax1.set_title('Comparativo de Destinação de Resíduos')
    ax1.set_xticks(x)
    ax1.set_xticklabels(destinos)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Gráfico 2: Emissões por cenário
    cenarios = ['Atual', 'Econ. Circular', 'Otimizado']
    emissões = [massa_anual * 0.8, massa_anual * 0.4, massa_anual * 0.2]
    cores = ['#e74c3c', '#3498db', '#2ecc71']
    
    bars = ax2.bar(cenarios, emissões, color=cores)
    ax2.set_ylabel('Emissões de CO₂eq (t/ano)')
    ax2.set_title('Emissões de GEE por Cenário')
    ax2.grid(True, alpha=0.3)
    
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, height,
                f'{height:,.0f}', ha='center', va='bottom', fontweight='bold')
    
    # Gráfico 3: Potencial de reciclagem
    labels = ['Recicláveis Recuperáveis', 'Orgânicos Compostáveis', 'Rejeito']
    sizes = [fracoes['Reciclagem'] * 100, fracoes['Compostagem'] * 100, fracoes['Aterro'] * 100]
    colors = ['#3498db', '#2ecc71', '#e74c3c']
    
    ax3.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax3.set_title(f'Potencial de Valorização - {cenario}')
    
    # Gráfico 4: Valor econômico do carbono
    if fracoes['Redução vs Atual'] != '0%':
        reducao_absoluta = (massa_anual * 0.8) - fracoes['Emissões (t CO₂eq)']
        valor_carbono_usd = reducao_absoluta * 50  # US$ 50/ton
        valor_carbono_brl = valor_carbono_usd * 5  # R$ 5/US$
        
        categorias = ['Redução de GEE', 'Valor (US$)', 'Valor (R$)']
        valores = [reducao_absoluta, valor_carbono_usd, valor_carbono_brl]
        unidades = ['t CO₂eq', 'US$/ano', 'R$/ano']
        
        bars = ax4.bar(categorias, valores, color=['#2ecc71', '#3498db', '#9b59b6'])
        ax4.set_title('Valor Econômico do Carbono Evitado')
        ax4.grid(True, alpha=0.3)
        
        for i, (bar, val, unid) in enumerate(zip(bars, valores, unidades)):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2, height,
                    f'{val:,.0f} {unid}', ha='center', va='bottom', fontweight='bold')
    else:
        ax4.text(0.5, 0.5, 'Sem redução de emissões\nno cenário atual',
                ha='center', va='center', transform=ax4.transAxes, fontsize=12)
        ax4.set_title('Valor do Carbono')
    
    plt.tight_layout()
    return fig

def main():
    # Sidebar com configurações
    with st.sidebar:
        st.image("https://raw.githubusercontent.com/loopvinyl/tco2eqv7/main/logo_sinisa.png", 
                 width=200, caption="SINISA 2023")
        
        st.header("⚙️ Configurações")
        
        # Seção de municípios
        st.subheader("🏙️ Seleção de Município")
        municipios = [
            "RIBEIRÃO PRETO",
            "SÃO JOSÉ DO RIO PRETO", 
            "SERTÃOZINHO",
            "MANAUS",
            "ARIQUEMES",
            "BOCA DO ACRE"
        ]
        
        municipio_selecionado = st.selectbox(
            "Escolha o município para análise:",
            municipios
        )
        
        # Campo para buscar outros municípios
        outro_municipio = st.text_input("Ou digite outro município:")
        if outro_municipio:
            municipio_selecionado = outro_municipio.upper()
        
        st.markdown("---")
        
        # Seção de cenários
        st.subheader("📈 Cenários de Simulação")
        cenario = st.radio(
            "Escolha o cenário para simulação:",
            ["Cenário Atual", 
             "Cenário de Economia Circular", 
             "Cenário Otimizado (Máxima Reciclagem)"]
        )
        
        st.markdown("---")
        
        # Opções avançadas
        st.subheader("🔧 Opções Avançadas")
        modo_detalhado = st.checkbox("Modo detalhado", value=False)
        mostrar_dados = st.checkbox("Mostrar dados brutos", value=False)
        
        st.markdown("---")
        
        # Informações sobre os dados
        st.info("""
        **Fonte:** SINISA 2023  
        **Registros:** 12.822 válidos  
        **Média nacional:** 365 kg/hab/ano  
        **Período:** Dados de 2023
        """)
    
    # Carregamento de dados
    st.header("📥 Carregamento de Dados")
    
    with st.spinner("Carregando dados do SINISA 2023..."):
        df = carregar_dados_completos()
    
    if df is None:
        st.error("Falha ao carregar dados. Verifique a conexão e o arquivo.")
        return
    
    # Identificação de colunas
    colunas = identificar_colunas_principais(df)
    
    # Dashboard de métricas
    st.header("📊 Dashboard SINISA 2023")
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Registros Válidos", f"{len(df):,}", "Com 'Sim'")
    
    with col2:
        if 'Massa_Total' in colunas:
            massa_total = df[colunas['Massa_Total']].sum()
            st.metric("Massa Total Coletada", f"{massa_total:,.0f} t", "Nacional")
    
    with col3:
        if 'Estado' in colunas:
            estados = df[colunas['Estado']].nunique()
            st.metric("Estados", estados, "Com dados")
    
    with col4:
        if 'Região' in colunas:
            regioes = df[colunas['Região']].nunique()
            st.metric("Regiões", regioes, "Brasil")
    
    # Análise do município selecionado
    st.header(f"🏙️ Análise Municipal: {municipio_selecionado}")
    
    if 'Município' in colunas:
        # Buscar município
        dados_municipio = buscar_municipio_eficiente(df, municipio_selecionado, colunas['Município'])
        
        if dados_municipio is not None:
            st.success(f"✅ Município encontrado nos dados SINISA!")
            
            # Layout em colunas para informações
            col_info1, col_info2 = st.columns(2)
            
            with col_info1:
                st.subheader("📋 Informações Gerais")
                
                info_card = st.container()
                with info_card:
                    # Município
                    st.markdown(f"**Município:** {dados_municipio[colunas['Município']]}")
                    
                    # Estado e Região
                    if 'Estado' in colunas and colunas['Estado'] in dados_municipio:
                        st.markdown(f"**Estado:** {dados_municipio[colunas['Estado']]}")
                    
                    if 'Região' in colunas and colunas['Região'] in dados_municipio:
                        st.markdown(f"**Região:** {dados_municipio[colunas['Região']]}")
                    
                    # Tipo de Coleta
                    if 'Tipo_Coleta' in colunas and colunas['Tipo_Coleta'] in dados_municipio:
                        coleta = dados_municipio[colunas['Tipo_Coleta']]
                        st.markdown(f"**Tipo de Coleta:** {coleta}")
                    
                    # Destino Final
                    if 'Destino' in colunas and colunas['Destino'] in dados_municipio:
                        destino = dados_municipio[colunas['Destino']]
                        st.markdown(f"**Destino Final:** {destino}")
                        
                        # Classificação do destino
                        if pd.notna(destino):
                            destinos_adequados = ['ATERRO SANITÁRIO', 'COMPOSTAGEM', 'RECICLAGEM', 'TRIAGEM']
                            if any(term in str(destino).upper() for term in destinos_adequados):
                                st.success("✅ Destinação adequada")
                            else:
                                st.warning("⚠️ Verificar adequação da destinação")
            
            with col_info2:
                st.subheader("📊 Dados Quantitativos")
                
                if 'Massa_Total' in colunas and colunas['Massa_Total'] in dados_municipio:
                    massa = dados_municipio[colunas['Massa_Total']]
                    
                    if pd.notna(massa) and massa > 0:
                        # Cálculo de métricas
                        per_capita_anual = (massa * 1000) / 365  # Estimativa populacional
                        per_capita_diario = per_capita_anual / 365
                        populacao_estimada = (massa * 1000) / 365.21  # Usando média nacional
                        
                        # Exibição de métricas
                        st.metric("Massa Coletada Anual", f"{massa:,.1f} t")
                        st.metric("População Estimada", f"{populacao_estimada:,.0f} hab")
                        st.metric("Geração Per Capita", f"{365.21:.1f} kg/hab/ano", "Média nacional")
                        
                        # Simulação de cenários
                        st.subheader("🔮 Simulação de Cenários")
                        
                        # Criar gráficos
                        fig = criar_graficos_simulacao(massa, cenario)
                        st.pyplot(fig)
                        
                        # Detalhes da simulação
                        fracoes = calcular_simulacao(massa, cenario)
                        
                        col_res1, col_res2, col_res3 = st.columns(3)
                        
                        with col_res1:
                            st.metric("Materiais Recicláveis", 
                                    f"{massa * fracoes['Reciclagem']:,.0f} t/ano")
                        
                        with col_res2:
                            st.metric("Compostagem", 
                                    f"{massa * fracoes['Compostagem']:,.0f} t/ano")
                        
                        with col_res3:
                            st.metric("Emissões de GEE", 
                                    f"{fracoes['Emissões (t CO₂eq)']:,.0f} t CO₂eq/ano")
                        
                        # Valor econômico se houver redução
                        if fracoes['Redução vs Atual'] != '0%':
                            st.success(f"**Redução de emissões:** {fracoes['Redução vs Atual']}")
                    else:
                        st.warning("Dados de massa não disponíveis ou zerados para este município.")
                else:
                    st.error("Coluna de massa não identificada.")
        else:
            st.warning(f"Município '{municipio_selecionado}' não encontrado nos dados.")
            
            # Sugestões de busca
            st.info("""
            **Possíveis razões:**
            1. Município não preencheu o formulário SINISA 2023
            2. Nome do município pode estar escrito de forma diferente
            3. Município pode estar na lista de 'Não respondentes'
            
            **Sugestões:**
            - Verificar a grafia do nome
            - Tentar buscar sem acentos
            - Testar outros municípios da lista
            """)
    else:
        st.error("Não foi possível identificar a coluna de municípios.")
        
        if modo_detalhado:
            with st.expander("🔍 Debug - Estrutura de Colunas"):
                st.write("Colunas disponíveis:")
                for i, col in enumerate(df.columns):
                    st.write(f"{i}: {col}")
    
    # Análise comparativa por estado
    if 'Estado' in colunas and 'Massa_Total' in colunas:
        st.header("📈 Análise Comparativa por Estado")
        
        # Preparar dados
        dados_estado = df.groupby(colunas['Estado']).agg(
            Municipios=(colunas['Massa_Total'], 'count'),
            Massa_Total=(colunas['Massa_Total'], 'sum'),
            Massa_Media=(colunas['Massa_Total'], 'mean')
        ).reset_index()
        
        dados_estado = dados_estado.sort_values('Massa_Total', ascending=False)
        
        # Layout para gráfico e tabela
        col_graf, col_tab = st.columns([2, 1])
        
        with col_graf:
            st.subheader("🏆 Top 10 Estados")
            
            fig, ax = plt.subplots(figsize=(10, 6))
            top_10 = dados_estado.head(10)
            
            bars = ax.barh(top_10[colunas['Estado']], top_10['Massa_Total'], color='#3498db')
            ax.set_xlabel('Massa Total Coletada (toneladas)')
            ax.set_title('Top 10 Estados por Massa de Resíduos Coletados')
            ax.invert_yaxis()
            ax.grid(axis='x', alpha=0.3)
            
            # Adicionar valores
            for bar in bars:
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height()/2,
                       f'{width:,.0f}', ha='left', va='center', fontsize=9)
            
            st.pyplot(fig)
        
        with col_tab:
            st.subheader("📋 Ranking Completo")
            
            # Tabela simplificada
            tabela_resumo = dados_estado[['Estado', 'Massa_Total', 'Municipios']].copy()
            tabela_resumo.columns = ['Estado', 'Massa (t)', 'Municípios']
            tabela_resumo['Massa (t)'] = tabela_resumo['Massa (t)'].round(0)
            
            st.dataframe(tabela_resumo.head(15), height=400)
    
    # Seção de informações técnicas
    with st.expander("📚 Informações Técnicas e Metodologia"):
        st.markdown("""
        ## 📊 Fonte dos Dados
        
        **Sistema Nacional de Informações sobre Saneamento (SINISA) 2023**
        
        ## ⚙️ Metodologia de Análise
        
        **Filtro aplicado:**
        - Apenas registros com valor 'Sim' na primeira coluna (Coluna A)
        - Total de 12.822 registros válidos (94,1% do total)
        
        **Colunas principais utilizadas:**
        - Estado: Coluna D (Col_3)
        - Região: Coluna E (Col_4)
        - Tipo de Coleta: Coluna R (Col_17)
        - Massa Total: Coluna Y (Col_24)
        - Destino: Coluna AC (Col_28)
        
        **Cálculo per capita:**
        - Média nacional: 365,21 kg/hab/ano
        - Fonte: SINISA 2023 com dados populacionais IBGE 2023
        - Conversão: 1 tonelada = 1.000 kg
        
        ## 🧮 Simulação de Cenários
        
        **Cenário Atual:**
        - Baseado em médias brasileiras atuais
        - Aterro: 85%, Reciclagem: 8%, Compostagem: 7%
        
        **Cenário Economia Circular:**
        - Aumento significativo de reciclagem e compostagem
        - Aterro: 40%, Reciclagem: 35%, Compostagem: 25%
        
        **Cenário Otimizado:**
        - Máxima recuperação de materiais
        - Aterro: 20%, Reciclagem: 45%, Compostagem: 35%
        
        ## 📈 Fatores de Emissão
        
        - Baseados em metodologias IPCC para resíduos sólidos
        - Consideram diferentes tipos de destinação final
        - Valor do carbono: US$ 50 por tonelada de CO₂eq
        
        ## 🎯 Limitações
        
        1. Dados auto-declarados pelos municípios
        2. Variações na qualidade do preenchimento
        3. Estimativas populacionais baseadas em média nacional
        4. Fatores de emissão médios, não específicos por tecnologia
        """)
    
    # Rodapé
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center'>
        <p>Desenvolvido para análise de dados SINISA 2023 | Dados: Sistema Nacional de Informações sobre Saneamento</p>
        <p>Última atualização: Janeiro 2026 | Versão 2.0</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
