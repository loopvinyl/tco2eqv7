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

st.title("🗑️ Análise SINISA 2023 - Resíduos Sólidos Urbanos")
st.markdown("""
### Sistema Nacional de Informações sobre Saneamento
**Análise completa de dados municipais brasileiros para simulação de emissões de GEE**
""")

# URL do arquivo Excel
EXCEL_URL = "https://github.com/loopvinyl/tco2eqv7/raw/main/rsuBrasil.xlsx"

# Dicionário de mapeamento de códigos de destino (baseado em padrões SINISA)
MAPEAMENTO_DESTINOS = {
    1: "Aterro Sanitário",
    2: "Aterro Controlado",
    3: "Lixão",
    4: "Compostagem",
    5: "Reciclagem/Triagem",
    6: "Unidade de Triagem",
    7: "Outros",
    8: "Incineração",
    9: "Coperação",
    # Adicione outros códigos conforme encontrados
    3518859: "Aterro Sanitário",  # Exemplo - precisa verificar
    3543402: "Aterro Controlado",  # Exemplo - precisa verificar
}

@st.cache_data(ttl=3600)
def carregar_dados_completos():
    """
    Carrega e processa os dados do Excel SINISA 2023
    Retorna: dataframe filtrado
    """
    try:
        response = requests.get(EXCEL_URL, timeout=60)
        response.raise_for_status()
        excel_file = BytesIO(response.content)
        
        xls = pd.ExcelFile(excel_file)
        
        # Carregar aba específica SEM cabeçalho para análise
        df_raw = pd.read_excel(xls, sheet_name="Manejo_Coleta_e_Destinação", header=None)
        
        # Encontrar linha de cabeçalho (procurar por 'Sim' na primeira coluna)
        header_row = None
        for i in range(min(20, len(df_raw))):
            if str(df_raw.iloc[i, 0]).strip() == 'Sim':
                header_row = i - 1  # Linha anterior deve ser o cabeçalho
                break
        
        if header_row is None:
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
    
    st.write("🔍 **Analisando estrutura das colunas...**")
    
    # Primeiro, mostrar todas as colunas para debug
    with st.expander("📋 Ver todas as colunas disponíveis"):
        for i, col in enumerate(df.columns):
            st.write(f"{i}: **{col}**")
            # Mostrar alguns valores únicos
            if df[col].dtype == 'object':
                valores = df[col].dropna().unique()[:5]
                if len(valores) > 0:
                    st.write(f"   Valores: {list(valores)}")
    
    # Procurar especificamente pela coluna AC (índice 28 - 0-based)
    if len(df.columns) > 28:
        coluna_ac = df.columns[28]
        st.info(f"**Coluna AC (índice 28):** `{coluna_ac}`")
        
        # Verificar o conteúdo da coluna AC
        valores_unicos = df[coluna_ac].dropna().unique()[:10]
        st.write(f"**Valores únicos na coluna AC:** {list(valores_unicos)}")
        
        # Analisar se são códigos numéricos
        if df[coluna_ac].dtype in ['int64', 'float64']:
            st.info("Coluna AC contém valores numéricos (códigos)")
            colunas['Destino'] = coluna_ac
            colunas['Destino_Tipo'] = 'codigo'
        else:
            # Se não for numérico, pode ser texto
            st.info("Coluna AC contém valores textuais")
            colunas['Destino'] = coluna_ac
            colunas['Destino_Tipo'] = 'texto'
    
    # Procurar colunas comuns
    mapeamento = {
        'Município': ['município', 'municipio', 'cidade', 'local', 'nome_municipio'],
        'Estado': ['col_3', 'estado', 'uf', 'unidade da federação'],
        'Região': ['col_4', 'região', 'regiao', 'grande região'],
        'Tipo_Coleta': ['col_17', 'tipo de coleta', 'tipo_coleta', 'modalidade_coleta'],
        'Massa_Total': ['col_24', 'massa', 'total coletada', 'toneladas', 'peso'],
        'Destino_Texto': ['destino', 'destinação', 'destinacao_final', 'destino_final', 'tipo_destino']
    }
    
    for tipo, padroes in mapeamento.items():
        for col in df.columns:
            col_lower = str(col).lower()
            for padrao in padroes:
                if padrao in col_lower:
                    colunas[tipo] = col
                    st.success(f"✅ {tipo}: `{col}`")
                    break
            if tipo in colunas:
                break
    
    # Verificar índices conhecidos
    indices_conhecidos = {
        3: 'Estado',    # Coluna D
        4: 'Região',    # Coluna E
        17: 'Tipo_Coleta',  # Coluna R
        24: 'Massa_Total',  # Coluna Y
        28: 'Destino'   # Coluna AC
    }
    
    for idx, nome in indices_conhecidos.items():
        if idx < len(df.columns) and nome not in colunas:
            colunas[nome] = df.columns[idx]
            st.info(f"📌 {nome} (por índice {idx}): `{df.columns[idx]}`")
    
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
    
    municipio_busca = normalizar_texto(municipio_nome)
    
    # Estratégia 1: Busca exata
    df_temp = df.copy()
    df_temp['_temp_norm'] = df_temp[coluna_municipio].apply(normalizar_texto)
    mask_exato = df_temp['_temp_norm'] == municipio_busca
    
    if mask_exato.any():
        return df_temp[mask_exato].iloc[0]
    
    # Estratégia 2: Busca por partes
    partes = [p for p in municipio_busca.split() if len(p) > 2]
    if len(partes) > 1:
        mask_parte = pd.Series(True, index=df_temp.index)
        for parte in partes:
            mask_parte = mask_parte & df_temp['_temp_norm'].str.contains(parte, na=False)
        
        if mask_parte.any():
            return df_temp[mask_parte].iloc[0]
    
    return None

def decodificar_destino(codigo_destino):
    """Decodifica código de destino para descrição"""
    if pd.isna(codigo_destino):
        return "Não informado"
    
    try:
        # Converter para inteiro se possível
        codigo = int(float(codigo_destino))
        
        # Verificar no mapeamento
        if codigo in MAPEAMENTO_DESTINOS:
            return MAPEAMENTO_DESTINOS[codigo]
        
        # Se for um código grande (7 dígitos), pode ser código de município
        if 1000000 <= codigo <= 9999999:
            return f"Código de Município: {codigo} (verificar destino real)"
        
        return f"Código: {codigo} (desconhecido)"
        
    except:
        # Se não for numérico, retornar o valor original
        return str(codigo_destino)

def classificar_destino_adequacao(descricao_destino):
    """Classifica se o destino é adequado ou não"""
    descricao = str(descricao_destino).lower()
    
    destinos_adequados = [
        'aterro sanitário', 'aterro sanitario', 
        'compostagem', 'reciclagem', 'triagem',
        'unidade de triagem'
    ]
    
    destinos_inadequados = [
        'lixão', 'lixao', 'vazadouro', 'ceu aberto',
        'aterro controlado'  # depende da classificação
    ]
    
    for adequado in destinos_adequados:
        if adequado in descricao:
            return "✅ Adequado", "success"
    
    for inadequado in destinos_inadequados:
        if inadequado in descricao:
            return "⚠️ Pode ser inadequado", "warning"
    
    if 'código' in descricao or 'desconhecido' in descricao:
        return "❓ Necessita verificação", "error"
    
    return "⚠️ Verificar adequação", "warning"

def calcular_simulacao(massa_anual, cenario):
    """Calcula a simulação de cenários de destinação de resíduos"""
    cenarios = {
        "Cenário Atual": {
            'Aterro': 0.85,
            'Reciclagem': 0.08,
            'Compostagem': 0.07,
            'Emissões (t CO₂eq)': massa_anual * 0.8,
            'Redução vs Atual': '0%',
            'cor': '#e74c3c'
        },
        "Cenário de Economia Circular": {
            'Aterro': 0.40,
            'Reciclagem': 0.35,
            'Compostagem': 0.25,
            'Emissões (t CO₂eq)': massa_anual * 0.4,
            'Redução vs Atual': '50%',
            'cor': '#3498db'
        },
        "Cenário Otimizado (Máxima Reciclagem)": {
            'Aterro': 0.20,
            'Reciclagem': 0.45,
            'Compostagem': 0.35,
            'Emissões (t CO₂eq)': massa_anual * 0.2,
            'Redução vs Atual': '75%',
            'cor': '#2ecc71'
        }
    }
    return cenarios[cenario]

def criar_graficos_simulacao(massa_anual, cenario):
    """Cria gráficos para visualização da simulação"""
    fracoes = calcular_simulacao(massa_anual, cenario)
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    
    # Gráfico 1: Destinação
    labels = ['Aterro', 'Reciclagem', 'Compostagem']
    sizes = [fracoes['Aterro'] * 100, fracoes['Reciclagem'] * 100, fracoes['Compostagem'] * 100]
    colors = ['#e74c3c', '#3498db', '#2ecc71']
    ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax1.set_title(f'Destinação Final - {cenario}')
    
    # Gráfico 2: Emissões
    cenarios_nomes = ['Atual', 'Econ. Circular', 'Otimizado']
    emissões = [massa_anual * 0.8, massa_anual * 0.4, massa_anual * 0.2]
    bars = ax2.bar(cenarios_nomes, emissões, color=['#e74c3c', '#3498db', '#2ecc71'])
    ax2.set_ylabel('Emissões de CO₂eq (t/ano)')
    ax2.set_title('Comparativo de Emissões')
    ax2.grid(axis='y', alpha=0.3)
    for bar, valor in zip(bars, emissões):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f'{valor:,.0f}', ha='center', va='bottom', fontweight='bold')
    
    # Gráfico 3: Potencial de valorização
    ax3.bar(['Recicláveis', 'Compostáveis'], 
            [massa_anual * fracoes['Reciclagem'], massa_anual * fracoes['Compostagem']],
            color=['#3498db', '#2ecc71'])
    ax3.set_ylabel('Toneladas/ano')
    ax3.set_title('Potencial de Valorização de Resíduos')
    ax3.grid(axis='y', alpha=0.3)
    
    # Gráfico 4: Valor econômico
    if fracoes['Redução vs Atual'] != '0%':
        reducao = (massa_anual * 0.8) - fracoes['Emissões (t CO₂eq)']
        valor_usd = reducao * 50
        valor_brl = valor_usd * 5
        
        ax4.bar(['Redução GEE', 'Valor (US$)', 'Valor (R$)'], 
                [reducao, valor_usd, valor_brl],
                color=['#2ecc71', '#3498db', '#9b59b6'])
        ax4.set_title('Valor Econômico do Carbono')
        ax4.grid(axis='y', alpha=0.3)
    else:
        ax4.text(0.5, 0.5, 'Sem redução no cenário atual',
                ha='center', va='center', transform=ax4.transAxes, fontsize=12)
        ax4.set_title('Valor do Carbono')
    
    plt.tight_layout()
    return fig

def main():
    # Sidebar
    with st.sidebar:
        st.markdown("### SINISA 2023")
        st.header("⚙️ Configurações")
        
        st.subheader("🏙️ Seleção de Município")
        municipios = [
            "RIBEIRÃO PRETO",
            "SÃO JOSÉ DO RIO PRETO", 
            "SERTÃOZINHO",
            "MANAUS",
            "ARIQUEMES",
            "BOCA DO ACRE"
        ]
        
        municipio_selecionado = st.selectbox("Escolha o município:", municipios)
        
        outro_municipio = st.text_input("Ou digite outro município:")
        if outro_municipio:
            municipio_selecionado = outro_municipio.upper()
        
        st.markdown("---")
        st.subheader("📈 Cenários de Simulação")
        cenario = st.radio(
            "Escolha o cenário:",
            ["Cenário Atual", "Cenário de Economia Circular", "Cenário Otimizado (Máxima Reciclagem)"]
        )
        
        st.markdown("---")
        st.subheader("🔧 Opções Avançadas")
        modo_detalhado = st.checkbox("Modo detalhado", value=True)
        mostrar_dados = st.checkbox("Mostrar dados brutos", value=False)
        
        st.markdown("---")
        st.info("""
        **Fonte:** SINISA 2023  
        **Registros:** 12.822 válidos  
        **Média nacional:** 365 kg/hab/ano  
        **Período:** Dados de 2023
        """)
    
    # Carregar dados
    st.header("📥 Carregamento de Dados")
    
    with st.spinner("Carregando dados do SINISA 2023..."):
        df = carregar_dados_completos()
    
    if df is None:
        st.error("Falha ao carregar dados.")
        return
    
    # Identificar colunas
    colunas = identificar_colunas_principais(df)
    
    # Dashboard
    st.header("📊 Dashboard SINISA 2023")
    
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
    
    # Análise do município
    st.header(f"🏙️ Análise Municipal: {municipio_selecionado}")
    
    if 'Município' in colunas:
        dados_municipio = buscar_municipio_eficiente(df, municipio_selecionado, colunas['Município'])
        
        if dados_municipio is not None:
            st.success(f"✅ Município encontrado!")
            
            col_info1, col_info2 = st.columns(2)
            
            with col_info1:
                st.subheader("📋 Informações Gerais")
                
                st.markdown(f"**Município:** {dados_municipio[colunas['Município']]}")
                
                if 'Estado' in colunas:
                    st.markdown(f"**Estado:** {dados_municipio[colunas['Estado']]}")
                
                if 'Região' in colunas:
                    st.markdown(f"**Região:** {dados_municipio[colunas['Região']]}")
                
                if 'Tipo_Coleta' in colunas:
                    st.markdown(f"**Tipo de Coleta:** {dados_municipio[colunas['Tipo_Coleta']]}")
                
                if 'Destino' in colunas:
                    codigo_destino = dados_municipio[colunas['Destino']]
                    descricao_destino = decodificar_destino(codigo_destino)
                    
                    st.markdown(f"**Destino Final:**")
                    st.markdown(f"- **Código:** {codigo_destino}")
                    st.markdown(f"- **Descrição:** {descricao_destino}")
                    
                    # Classificar adequação
                    classificacao, tipo = classificar_destino_adequacao(descricao_destino)
                    
                    if tipo == "success":
                        st.success(classificacao)
                    elif tipo == "warning":
                        st.warning(classificacao)
                    else:
                        st.error(classificacao)
            
            with col_info2:
                st.subheader("📊 Dados Quantitativos")
                
                if 'Massa_Total' in colunas:
                    massa = dados_municipio[colunas['Massa_Total']]
                    
                    if pd.notna(massa) and massa > 0:
                        populacao_estimada = (massa * 1000) / 365.21
                        
                        st.metric("Massa Coletada Anual", f"{massa:,.1f} t")
                        st.metric("População Estimada", f"{populacao_estimada:,.0f} hab")
                        st.metric("Geração Per Capita", f"{365.21:.1f} kg/hab/ano", "Média nacional")
                        
                        # Simulação
                        st.subheader("🔮 Simulação de Cenários")
                        
                        fig = criar_graficos_simulacao(massa, cenario)
                        st.pyplot(fig)
                        
                        fracoes = calcular_simulacao(massa, cenario)
                        
                        col_res1, col_res2, col_res3 = st.columns(3)
                        
                        with col_res1:
                            st.metric("Materiais Recicláveis", f"{massa * fracoes['Reciclagem']:,.0f} t/ano")
                        
                        with col_res2:
                            st.metric("Compostagem", f"{massa * fracoes['Compostagem']:,.0f} t/ano")
                        
                        with col_res3:
                            st.metric("Emissões de GEE", f"{fracoes['Emissões (t CO₂eq)']:,.0f} t CO₂eq/ano")
                        
                        if fracoes['Redução vs Atual'] != '0%':
                            st.success(f"**Redução de emissões:** {fracoes['Redução vs Atual']}")
        else:
            st.warning(f"Município '{municipio_selecionado}' não encontrado.")
    
    # Análise por estado
    if 'Estado' in colunas and 'Massa_Total' in colunas:
        st.header("📈 Análise Comparativa por Estado")
        
        dados_estado = df.groupby(colunas['Estado']).agg(
            Municipios=(colunas['Massa_Total'], 'count'),
            Massa_Total=(colunas['Massa_Total'], 'sum')
        ).reset_index()
        
        dados_estado = dados_estado.rename(columns={colunas['Estado']: 'Estado'})
        dados_estado = dados_estado.sort_values('Massa_Total', ascending=False)
        
        col_graf, col_tab = st.columns([2, 1])
        
        with col_graf:
            st.subheader("🏆 Top 10 Estados")
            
            fig, ax = plt.subplots(figsize=(10, 6))
            top_10 = dados_estado.head(10)
            
            bars = ax.barh(top_10['Estado'], top_10['Massa_Total'], color='#3498db')
            ax.set_xlabel('Massa Total Coletada (t)')
            ax.set_title('Top 10 Estados - Massa de Resíduos')
            ax.invert_yaxis()
            ax.grid(axis='x', alpha=0.3)
            
            for bar in bars:
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height()/2,
                       f'{width:,.0f}', ha='left', va='center', fontsize=9)
            
            st.pyplot(fig)
        
        with col_tab:
            st.subheader("📋 Ranking Completo")
            
            tabela_resumo = dados_estado[['Estado', 'Massa_Total', 'Municipios']].copy()
            tabela_resumo.columns = ['Estado', 'Massa (t)', 'Municípios']
            tabela_resumo['Massa (t)'] = tabela_resumo['Massa (t)'].round(0)
            
            st.dataframe(tabela_resumo.head(15), height=400, use_container_width=True)
    
    # Informações técnicas
    with st.expander("📚 Informações Técnicas"):
        st.markdown("""
        ## 🔍 Sobre os Códigos de Destino
        
        Os códigos numéricos na coluna de destino (Coluna AC) podem representar:
        
        **Códigos Comuns:**
        - 1: Aterro Sanitário
        - 2: Aterro Controlado
        - 3: Lixão
        - 4: Compostagem
        - 5: Reciclagem/Triagem
        - 6: Unidade de Triagem
        - 7: Outros
        - 8: Incineração
        - 9: Coperação
        
        **Códigos de 7 dígitos** (ex: 3518859, 3543402):
        - Provavelmente são códigos de municípios IBGE
        - Indicam que os resíduos são enviados para outro município
        - Necessita verificação específica para cada código
        
        ## 🎯 Próximos Passos
        
        1. **Validar códigos de destino** com a tabela oficial do SINISA
        2. **Mapear códigos de municípios** para nomes reais
        3. **Ajustar classificação** de adequação conforme realidade
        """)
    
    # Rodapé
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center'>
        <p>Desenvolvido para análise de dados SINISA 2023 | Versão 2.2</p>
        <p><small>⚠️ Atenção: Códigos de destino necessitam verificação manual</small></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
