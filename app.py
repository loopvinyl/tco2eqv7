import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import BytesIO
import matplotlib.pyplot as plt
import unicodedata
from collections import Counter

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

# Função para formatar números no padrão brasileiro
def formatar_br(numero, casas_decimais=1, sufixo=""):
    """Formata um número no padrão brasileiro (vírgula decimal, ponto milhar)"""
    if pd.isna(numero) or numero is None:
        return "N/A"
    
    try:
        # Converter para float se for string
        if isinstance(numero, str):
            # Remover pontos de milhar e substituir vírgula decimal por ponto
            numero = float(numero.replace(".", "").replace(",", "."))
        
        # Formatar com separador de milhar e vírgula decimal
        if casas_decimais == 0:
            formato = "{:,.0f}"
        else:
            formato = "{:,." + str(casas_decimais) + "f}"
        
        # Formatar com ponto para milhar
        formatado = formato.format(numero)
        
        # Substituir vírgula por ponto temporariamente, depois ponto por vírgula
        formatado = formatado.replace(",", "X").replace(".", ",").replace("X", ".")
        
        return f"{formatado}{sufixo}"
    except:
        return str(numero)

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
    
    # Mapeamento baseado nas colunas reais do SINISA (corrigido)
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
    
    # Fallback para colunas por índice se não encontrou por nome
    if 'Município' not in colunas and len(df.columns) > 2:
        # Tentar identificar por conteúdo
        for i, col in enumerate(df.columns):
            if i == 2:  # Provável coluna de município
                colunas['Município'] = col
                break
    
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
    if 'Secretaria' not in colunas and len(df.columns) > 6:
        colunas['Secretaria'] = df.columns[6]
    
    return colunas

def normalizar_texto(texto):
    """Normaliza texto removendo acentos e convertendo para minúsculas"""
    if pd.isna(texto):
        return ""
    texto = str(texto)
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto.lower().strip()

def buscar_todas_linhas_municipio(df, municipio_nome, coluna_municipio):
    """Busca TODAS as linhas de um município"""
    if coluna_municipio not in df.columns:
        return None
    
    # Normalizar nome do município buscado
    municipio_busca = normalizar_texto(municipio_nome)
    
    # Normalizar coluna para busca
    df_temp = df.copy()
    df_temp['_temp_norm'] = df_temp[coluna_municipio].apply(normalizar_texto)
    
    # Buscar exato primeiro
    mask_exato = df_temp['_temp_norm'] == municipio_busca
    
    # Se não encontrou exato, buscar por partes
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
    
    resultados = df_temp[mask].copy()
    
    return resultados

def calcular_simulacao(massa_anual, cenario):
    """Calcula a simulação de cenários de destinação de resíduos"""
    
    # Fatores de emissão por tipo de destinação (t CO₂eq/t resíduo)
    fatores_emissao = {
        'Aterro': 0.80,
        'Reciclagem': 0.15,
        'Compostagem': 0.10
    }
    
    # Valores econômicos (R$/tonelada)
    valores_economicos = {
        'Reciclagem': 250,  # R$/t de materiais recicláveis
        'Compostagem': 150,  # R$/t de composto orgânico
        'Carbono': 50,      # US$/t CO₂eq (convertido abaixo)
    }
    
    cenarios = {
        "Cenário Atual": {
            'Aterro': 0.85,
            'Reciclagem': 0.08,
            'Compostagem': 0.07,
            'descricao': 'Baseado em médias brasileiras atuais',
            'cor': '#e74c3c',
            'melhorias': [
                'Baixa taxa de reciclagem',
                'Alto índice de aterramento',
                'Pouco aproveitamento de orgânicos'
            ]
        },
        "Cenário de Economia Circular": {
            'Aterro': 0.40,
            'Reciclagem': 0.35,
            'Compostagem': 0.25,
            'descricao': 'Aumento significativo de reciclagem e compostagem',
            'cor': '#3498db',
            'melhorias': [
                'Reciclagem ampliada',
                'Compostagem em escala',
                'Redução de aterro em 45%'
            ]
        },
        "Cenário Otimizado (Máxima Reciclagem)": {
            'Aterro': 0.20,
            'Reciclagem': 0.45,
            'Compostagem': 0.35,
            'descricao': 'Máxima recuperação de materiais',
            'cor': '#2ecc71',
            'melhorias': [
                'Máxima recuperação de recicláveis',
                'Alta taxa de compostagem',
                'Redução de aterro em 65%'
            ]
        }
    }
    
    dados = cenarios[cenario].copy()
    
    # Calcular massa por destino
    dados['Massa_Aterro'] = massa_anual * dados['Aterro']
    dados['Massa_Reciclagem'] = massa_anual * dados['Reciclagem']
    dados['Massa_Compostagem'] = massa_anual * dados['Compostagem']
    
    # Calcular emissões
    dados['Emissões (t CO₂eq)'] = (
        dados['Massa_Aterro'] * fatores_emissao['Aterro'] +
        dados['Massa_Reciclagem'] * fatores_emissao['Reciclagem'] +
        dados['Massa_Compostagem'] * fatores_emissao['Compostagem']
    )
    
    # Calcular emissões do cenário atual para comparação
    emissao_atual = massa_anual * 0.80  # Cenário atual padrão
    dados['Redução Absoluta'] = emissao_atual - dados['Emissões (t CO₂eq)']
    dados['Redução Percentual'] = (dados['Redução Absoluta'] / emissao_atual) * 100 if emissao_atual > 0 else 0
    
    # Calcular benefícios econômicos
    dados['Valor_Reciclagem_R$'] = dados['Massa_Reciclagem'] * valores_economicos['Reciclagem']
    dados['Valor_Compostagem_R$'] = dados['Massa_Compostagem'] * valores_economicos['Compostagem']
    dados['Valor_Carbono_US$'] = dados['Redução Absoluta'] * valores_economicos['Carbono']
    dados['Valor_Carbono_R$'] = dados['Valor_Carbono_US$'] * 5  # Conversão USD para BRL
    
    # Valor total econômico
    dados['Valor_Total_R$'] = dados['Valor_Reciclagem_R$'] + dados['Valor_Compostagem_R$'] + dados['Valor_Carbono_R$']
    
    return dados

def criar_graficos_simulacao_ampliados(massa_anual, cenario):
    """Cria gráficos ampliados para visualização da simulação"""
    
    fracoes = calcular_simulacao(massa_anual, cenario)
    
    # Criar figura com subplots - 3x2 para mais gráficos
    fig, axes = plt.subplots(3, 2, figsize=(16, 18))
    
    # Configurar formatação brasileira nos gráficos
    def formatar_br_grafico(x, p):
        """Função para formatar números nos gráficos no padrão brasileiro"""
        x = float(x)
        if abs(x) >= 1_000_000:
            return formatar_br(x / 1_000_000, 1) + ' mi'
        elif abs(x) >= 1_000:
            return formatar_br(x / 1_000, 1) + ' mil'
        else:
            return formatar_br(x, 0)
    
    # Gráfico 1 (0,0): Destinação atual vs proposta
    destinos = ['Aterro', 'Reciclagem', 'Compostagem']
    valores_atual = [0.85, 0.08, 0.07]
    valores_cenario = [fracoes['Aterro'], fracoes['Reciclagem'], fracoes['Compostagem']]
    
    x = np.arange(len(destinos))
    width = 0.35
    
    ax1 = axes[0, 0]
    ax1.bar(x - width/2, valores_atual, width, label='Cenário Atual', color='#95a5a6')
    ax1.bar(x + width/2, valores_cenario, width, label=cenario, color=fracoes['cor'])
    ax1.set_ylabel('Proporção')
    ax1.set_title('Comparativo de Destinação de Resíduos')
    ax1.set_xticks(x)
    ax1.set_xticklabels(destinos)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
    
    # Gráfico 2 (0,1): Emissões por cenário
    ax2 = axes[0, 1]
    cenarios_nomes = ['Atual', 'Econ. Circular', 'Otimizado']
    emissões = [massa_anual * 0.8, massa_anual * 0.4, massa_anual * 0.2]
    cores = ['#e74c3c', '#3498db', '#2ecc71']
    
    bars = ax2.bar(cenarios_nomes, emissões, color=cores)
    ax2.set_ylabel('Emissões de CO₂eq (t/ano)')
    ax2.set_title('Emissões de GEE por Cenário')
    ax2.grid(True, alpha=0.3)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: formatar_br(y, 0)))
    
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, height,
                f'{formatar_br(height, 0)}', ha='center', va='bottom', fontweight='bold')
    
    # Gráfico 3 (1,0): Potencial de reciclagem
    ax3 = axes[1, 0]
    labels = ['Recicláveis Recuperáveis', 'Orgânicos Compostáveis', 'Rejeito']
    sizes = [fracoes['Reciclagem'] * 100, fracoes['Compostagem'] * 100, fracoes['Aterro'] * 100]
    colors = ['#3498db', '#2ecc71', '#e74c3c']
    
    ax3.pie(sizes, labels=labels, colors=colors, autopct=lambda p: f'{p:.1f}%', startangle=90)
    ax3.set_title(f'Potencial de Valorização - {cenario}')
    
    # Gráfico 4 (1,1): Valor econômico
    ax4 = axes[1, 1]
    if fracoes['Redução Percentual'] > 0:
        categorias = ['Redução de GEE', 'Valor Reciclagem', 'Valor Compostagem', 'Valor Total']
        valores = [fracoes['Redução Absoluta'], fracoes['Valor_Reciclagem_R$'], 
                  fracoes['Valor_Compostagem_R$'], fracoes['Valor_Total_R$']]
        cores_barras = ['#2ecc71', '#3498db', '#9b59b6', '#f39c12']
        
        bars = ax4.bar(categorias, valores, color=cores_barras)
        ax4.set_ylabel('Valor (R$)')
        ax4.set_title('Valor Econômico Anual')
        ax4.grid(True, alpha=0.3)
        ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: formatar_br(y, 0)))
        
        for i, (bar, val) in enumerate(zip(bars, valores)):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2, height,
                    f'R$ {formatar_br(val, 0)}', ha='center', va='bottom', 
                    fontweight='bold', fontsize=9)
    else:
        ax4.text(0.5, 0.5, 'Sem redução de emissões\nno cenário atual',
                ha='center', va='center', transform=ax4.transAxes, fontsize=12)
        ax4.set_title('Valor do Carbono')
    
    # Gráfico 5 (2,0): Comparação entre cenários (stacked)
    ax5 = axes[2, 0]
    cenarios_comparacao = ['Atual', 'Economia\nCircular', 'Otimizado']
    dados_stack = {
        'Aterro': [85, 40, 20],
        'Reciclagem': [8, 35, 45],
        'Compostagem': [7, 25, 35]
    }
    
    bottom = np.zeros(3)
    for destino, valores in dados_stack.items():
        ax5.bar(cenarios_comparacao, valores, bottom=bottom, label=destino, 
               color={'Aterro': '#e74c3c', 'Reciclagem': '#3498db', 'Compostagem': '#2ecc71'}[destino])
        bottom += valores
    
    ax5.set_ylabel('Percentual (%)')
    ax5.set_title('Comparação entre Cenários')
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    
    # Gráfico 6 (2,1): Impacto ambiental
    ax6 = axes[2, 1]
    if fracoes['Redução Percentual'] > 0:
        # Calcular impactos ambientais
        arvores = int(fracoes['Redução Absoluta'] * 1000 / 22)  # 22 kg CO₂ por árvore/ano
        carros = int(fracoes['Redução Absoluta'] / 2)  # 2 t CO₂ por carro/ano
        energia = fracoes['Massa_Reciclagem'] * 0.95 * 14  # 14 MWh por tonelada
        
        categorias_impacto = ['Árvores Plantadas', 'Carros Retirados', 'Energia Economizada']
        valores_impacto = [arvores, carros, energia]
        unidades = ['árvores', 'carros', 'MWh']
        
        bars = ax6.bar(categorias_impacto, valores_impacto, color=['#27ae60', '#8e44ad', '#f1c40f'])
        ax6.set_title('Impacto Ambiental Equivalente')
        ax6.grid(True, alpha=0.3)
        
        for i, (bar, val, unid) in enumerate(zip(bars, valores_impacto, unidades)):
            height = bar.get_height()
            ax6.text(bar.get_x() + bar.get_width()/2, height,
                    f'{formatar_br(val, 0)} {unid}', ha='center', va='bottom', 
                    fontweight='bold', fontsize=9)
    else:
        ax6.text(0.5, 0.5, 'Sem redução de emissões\npara calcular impacto',
                ha='center', va='center', transform=ax6.transAxes, fontsize=12)
        ax6.set_title('Impacto Ambiental')
    
    plt.tight_layout()
    return fig

def main():
    # Sidebar com configurações
    with st.sidebar:
        st.markdown("### SINISA 2023")
        
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
        st.metric("Registros Válidos", f"{formatar_br(len(df), 0)}", "Com 'Sim'")
    
    with col2:
        if 'Massa_Total' in colunas:
            massa_total = df[colunas['Massa_Total']].sum()
            st.metric("Massa Total Coletada", f"{formatar_br(massa_total, 0)} t", "Nacional")
    
    with col3:
        if 'Estado' in colunas:
            estados = df[colunas['Estado']].nunique()
            st.metric("Estados", f"{formatar_br(estados, 0)}", "Com dados")
    
    with col4:
        if 'Região' in colunas:
            regioes = df[colunas['Região']].nunique()
            st.metric("Regiões", f"{formatar_br(regioes, 0)}", "Brasil")
    
    # Análise do município selecionado
    st.header(f"🏙️ Análise Municipal: {municipio_selecionado}")
    
    if 'Município' in colunas:
        # Buscar TODAS as linhas do município
        dados_municipio_completo = buscar_todas_linhas_municipio(df, municipio_selecionado, colunas['Município'])
        
        if dados_municipio_completo is not None and len(dados_municipio_completo) > 0:
            st.success(f"✅ Município encontrado! {formatar_br(len(dados_municipio_completo), 0)} registro(s) no total.")
            
            # Layout em colunas para informações
            col_info1, col_info2 = st.columns(2)
            
            with col_info1:
                st.subheader("📋 Informações Gerais")
                
                info_card = st.container()
                with info_card:
                    # Município (usar o primeiro registro)
                    primeiro_registro = dados_municipio_completo.iloc[0]
                    st.markdown(f"**Município:** {primeiro_registro[colunas['Município']]}")
                    
                    # Estado e Região
                    if 'Estado' in colunas and colunas['Estado'] in primeiro_registro:
                        st.markdown(f"**Estado:** {primeiro_registro[colunas['Estado']]}")
                    
                    if 'Região' in colunas and colunas['Região'] in primeiro_registro:
                        st.markdown(f"**Região:** {primeiro_registro[colunas['Região']]}")
                    
                    # Secretaria/Setor (mantido apenas aqui, não na tabela)
                    if 'Secretaria' in colunas and colunas['Secretaria'] in primeiro_registro:
                        secretaria = primeiro_registro[colunas['Secretaria']]
                        if pd.notna(secretaria):
                            st.markdown(f"**Secretaria/Setor:** {secretaria}")
                    
                    # Tipos de Coleta (mostrar todos)
                    if 'Tipo_Coleta' in colunas:
                        tipos_coleta = dados_municipio_completo[colunas['Tipo_Coleta']].dropna().unique()
                        if len(tipos_coleta) > 0:
                            st.markdown("**Tipos de Coleta:**")
                            for tipo in tipos_coleta:
                                st.markdown(f"- {tipo}")
                    
                    # DESTINOS FINAIS - CORRIGIDO: USAR COLUNA AD (Destino_Texto)
                    if 'Destino_Texto' in colunas and colunas['Destino_Texto'] in dados_municipio_completo.columns:
                        destinos = dados_municipio_completo[colunas['Destino_Texto']].dropna()
                        
                        if len(destinos) > 0:
                            st.markdown("**Destinos Finais:**")
                            
                            # Contar ocorrências EXATAS
                            contador_destinos = Counter(destinos.astype(str))
                            
                            # Mostrar cada destino com contagem
                            for destino_texto, count in contador_destinos.items():
                                if pd.isna(destino_texto) or destino_texto == "nan":
                                    continue
                                
                                destino_limpo = str(destino_texto).strip()
                                if count > 1:
                                    st.markdown(f"- **{destino_limpo}** (aparece {formatar_br(count, 0)} vezes)")
                                else:
                                    st.markdown(f"- **{destino_limpo}**")
                        else:
                            st.markdown("*Destinos não informados*")
                    else:
                        st.markdown("*Coluna de destinos não identificada*")
            
            with col_info2:
                st.subheader("📊 Dados Quantitativos")
                
                if 'Massa_Total' in colunas:
                    # Soma a massa total de todas as linhas do município
                    massa_total_municipio = dados_municipio_completo[colunas['Massa_Total']].sum()
                    
                    if pd.notna(massa_total_municipio) and massa_total_municipio > 0:
                        # Obter população REAL da coluna J (primeiro valor não nulo)
                        populacao_real = None
                        if 'População' in colunas and colunas['População'] in dados_municipio_completo.columns:
                            # Filtrar valores não nulos e pegar o primeiro
                            valores_populacao = dados_municipio_completo[colunas['População']].dropna().unique()
                            if len(valores_populacao) > 0:
                                populacao_real = float(valores_populacao[0])
                        
                        # Exibição de métricas com formatação brasileira
                        st.metric("Massa Coletada Anual Total", f"{formatar_br(massa_total_municipio, 1)} t")
                        
                        if populacao_real and populacao_real > 0:
                            # Usar população REAL
                            st.metric("População Municipal", f"{formatar_br(populacao_real, 0)} hab", "Dados SINISA 2023")
                            
                            # Calcular geração per capita REAL
                            geracao_per_capita = (massa_total_municipio * 1000) / populacao_real
                            st.metric("Geração Per Capita", f"{formatar_br(geracao_per_capita, 1)} kg/hab/ano", 
                                     f"Média nacional: {formatar_br(365.21, 1)} kg/hab/ano")
                        else:
                            # Se não tiver população, mostrar estimativa
                            populacao_estimada = (massa_total_municipio * 1000) / 365.21
                            st.metric("População Estimada", f"{formatar_br(populacao_estimada, 0)} hab", "Baseado na média nacional")
                            st.metric("Geração Per Capita", f"{formatar_br(365.21, 1)} kg/hab/ano", "Média nacional (estimativa)")
                        
                        # Detalhamento por tipo de coleta
                        st.markdown("**Detalhamento por Tipo de Coleta:**")
                        if 'Tipo_Coleta' in colunas:
                            detalhes_coleta = dados_municipio_completo.groupby(colunas['Tipo_Coleta']).agg(
                                Massa_Total=(colunas['Massa_Total'], 'sum'),
                                Contagem=(colunas['Massa_Total'], 'count')
                            ).reset_index()
                            
                            for _, row in detalhes_coleta.iterrows():
                                st.markdown(f"- {row[colunas['Tipo_Coleta']]}: {formatar_br(row['Massa_Total'], 1)} t")
            
            # TABELA DE RELAÇÃO ENTRE TIPO DE COLETA, DESTINO E AGENTE EXECUTOR - SEM SECRETARIA
            st.subheader("📋 Relação: Tipo de Coleta → Destino Final → Agente Executor")
            
            # Criar tabela simplificada SEM Secretaria
            tabela_relacao = []
            
            for i, linha in dados_municipio_completo.iterrows():
                # Coletar informações CORRETAS
                tipo_coleta = linha[colunas['Tipo_Coleta']] if 'Tipo_Coleta' in colunas and colunas['Tipo_Coleta'] in linha else "Não informado"
                destino = linha[colunas['Destino_Texto']] if 'Destino_Texto' in colunas and colunas['Destino_Texto'] in linha else "Não informado"
                agente = linha[colunas['Agente_Executor']] if 'Agente_Executor' in colunas and colunas['Agente_Executor'] in linha else "Não informado"
                massa = linha[colunas['Massa_Total']] if 'Massa_Total' in colunas and colunas['Massa_Total'] in linha else 0
                
                # Limpar textos
                tipo_coleta = str(tipo_coleta).strip() if pd.notna(tipo_coleta) else "Não informado"
                destino = str(destino).strip() if pd.notna(destino) else "Não informado"
                agente = str(agente).strip() if pd.notna(agente) else "Não informado"
                
                tabela_relacao.append({
                    'Tipo de Coleta': tipo_coleta,
                    'Destino Final': destino,
                    'Agente Executor': agente,
                    'Massa (t)': formatar_br(massa, 1) if pd.notna(massa) else "0,0"
                })
            
            # Criar DataFrame
            df_relacao = pd.DataFrame(tabela_relacao)
            
            # Mostrar tabela
            if len(df_relacao) > 0:
                st.dataframe(df_relacao, use_container_width=True, height=300)
            else:
                st.info("Não foi possível criar a tabela de relação.")
            
            # Mostrar tabela detalhada original se houver múltiplos registros
            if len(dados_municipio_completo) > 1:
                with st.expander("📋 Ver todos os registros do município (detalhado)"):
                    # Selecionar colunas importantes para mostrar - GARANTINDO COLUNAS ÚNICAS
                    colunas_para_mostrar = []
                    colunas_ja_adicionadas = set()
                    
                    for tipo, col in colunas.items():
                        if col in dados_municipio_completo.columns and col not in colunas_ja_adicionadas:
                            colunas_para_mostrar.append(col)
                            colunas_ja_adicionadas.add(col)
                    
                    # Adicionar índice
                    dados_display = dados_municipio_completo[colunas_para_mostrar].copy()
                    dados_display.insert(0, 'Nº', range(1, len(dados_display) + 1))
                    
                    # Formatar colunas numéricas no padrão brasileiro
                    for col in dados_display.columns:
                        if col == 'Nº':  # Pular a coluna de índice
                            continue
                        
                        # Verificar se a coluna existe
                        if col not in dados_display.columns:
                            continue
                        
                        # Verificar de forma segura se é numérica
                        try:
                            # Primeiro, tentar verificar se podemos converter para numérico
                            col_data = dados_display[col]
                            
                            # Tentar detectar se é numérica
                            is_numeric = False
                            
                            # Método 1: Verificar dtype
                            if hasattr(col_data, 'dtype'):
                                dtype_str = str(col_data.dtype)
                                if any(num_type in dtype_str for num_type in ['int', 'float', 'Int', 'Float']):
                                    is_numeric = True
                            
                            # Método 2: Tentar converter amostra
                            if not is_numeric:
                                try:
                                    sample = col_data.dropna().iloc[0] if len(col_data.dropna()) > 0 else None
                                    if sample is not None:
                                        float(sample)
                                        is_numeric = True
                                except:
                                    is_numeric = False
                            
                            if is_numeric:
                                # Verificar se é uma coluna de população ou massa para formatação apropriada
                                col_name = str(col).lower()
                                if 'população' in col_name or 'populacao' in col_name or 'pop' in col_name:
                                    dados_display[col] = dados_display[col].apply(lambda x: formatar_br(x, 0) if pd.notna(x) else x)
                                elif 'massa' in col_name or 'toneladas' in col_name:
                                    dados_display[col] = dados_display[col].apply(lambda x: formatar_br(x, 1) if pd.notna(x) else x)
                                else:
                                    # Para outras colunas numéricas, usar 0 casas decimais
                                    dados_display[col] = dados_display[col].apply(lambda x: formatar_br(x, 0) if pd.notna(x) else x)
                        except Exception as e:
                            # Se houver erro, manter a coluna como está
                            if modo_detalhado:
                                st.write(f"Erro ao formatar coluna {col}: {str(e)}")
                    
                    st.dataframe(dados_display, use_container_width=True)
            
            # SEÇÃO AMPLIADA: SIMULAÇÃO DE CENÁRIOS
            st.subheader("🔮 Simulação de Cenários Avançada")
            
            # Container principal da simulação
            with st.container():
                # Informações do cenário selecionado
                fracoes = calcular_simulacao(massa_total_municipio, cenario)
                
                # Layout em 4 colunas para métricas principais
                col_met1, col_met2, col_met3, col_met4 = st.columns(4)
                
                with col_met1:
                    st.metric("Materiais Recicláveis", 
                             f"{formatar_br(fracoes['Massa_Reciclagem'], 0)} t/ano",
                             f"{fracoes['Reciclagem']*100:.1f}% do total")
                
                with col_met2:
                    st.metric("Compostagem", 
                             f"{formatar_br(fracoes['Massa_Compostagem'], 0)} t/ano",
                             f"{fracoes['Compostagem']*100:.1f}% do total")
                
                with col_met3:
                    st.metric("Emissões de GEE", 
                             f"{formatar_br(fracoes['Emissões (t CO₂eq)'], 0)} t CO₂eq/ano")
                
                with col_met4:
                    if fracoes['Redução Percentual'] > 0:
                        st.metric("Redução de Emissões", 
                                 f"{fracoes['Redução Percentual']:.1f}%",
                                 f"{formatar_br(fracoes['Redução Absoluta'], 0)} t CO₂eq")
                    else:
                        st.metric("Redução de Emissões", "0%", "Cenário atual")
                
                # Separador
                st.markdown("---")
                
                # GRÁFICOS AMPLIADOS (6 gráficos em 3x2)
                st.markdown("##### 📊 Visualização Completa da Simulação")
                fig_ampliada = criar_graficos_simulacao_ampliados(massa_total_municipio, cenario)
                st.pyplot(fig_ampliada)
                
                # Separador
                st.markdown("---")
                
                # TABELA COMPARATIVA DOS CENÁRIOS
                st.markdown("##### 📋 Comparativo entre Cenários")
                
                # Dados para tabela comparativa
                cenarios_comparar = ["Cenário Atual", "Cenário de Economia Circular", "Cenário Otimizado (Máxima Reciclagem)"]
                dados_comparativos = []
                
                for cenario_comp in cenarios_comparar:
                    dados_comp = calcular_simulacao(massa_total_municipio, cenario_comp)
                    dados_comparativos.append({
                        'Cenário': cenario_comp,
                        'Aterro (%)': f"{dados_comp['Aterro']*100:.1f}",
                        'Reciclagem (%)': f"{dados_comp['Reciclagem']*100:.1f}",
                        'Compostagem (%)': f"{dados_comp['Compostagem']*100:.1f}",
                        'Emissões (t CO₂eq)': formatar_br(dados_comp['Emissões (t CO₂eq)'], 0),
                        'Redução (%)': f"{dados_comp['Redução Percentual']:.1f}" if dados_comp['Redução Percentual'] > 0 else "0,0",
                        'Valor Total (R$)': formatar_br(dados_comp['Valor_Total_R$'], 0)
                    })
                
                df_comparativo = pd.DataFrame(dados_comparativos)
                
                # Destacar o cenário selecionado
                def highlight_selected(row):
                    if row['Cenário'] == cenario:
                        return ['background-color: #2ecc71; color: white'] * len(row)
                    return [''] * len(row)
                
                st.dataframe(df_comparativo.style.apply(highlight_selected, axis=1), use_container_width=True)
                
                # Separador
                st.markdown("---")
                
                # BENEFÍCIOS ECONÔMICOS DETALHADOS
                st.markdown("##### 💰 Benefícios Econômicos Detalhados")
                
                if fracoes['Redução Percentual'] > 0:
                    col_ben1, col_ben2, col_ben3, col_ben4 = st.columns(4)
                    
                    with col_ben1:
                        st.metric("Valor da Reciclagem", 
                                 f"R$ {formatar_br(fracoes['Valor_Reciclagem_R$'], 0)}",
                                 "R$ 250 por tonelada")
                    
                    with col_ben2:
                        st.metric("Valor da Compostagem", 
                                 f"R$ {formatar_br(fracoes['Valor_Compostagem_R$'], 0)}",
                                 "R$ 150 por tonelada")
                    
                    with col_ben3:
                        st.metric("Valor do Carbono", 
                                 f"R$ {formatar_br(fracoes['Valor_Carbono_R$'], 0)}",
                                 "US$ 50 por t CO₂eq")
                    
                    with col_ben4:
                        st.metric("Benefício Total", 
                                 f"R$ {formatar_br(fracoes['Valor_Total_R$'], 0)}/ano",
                                 "Economia anual")
                
                # Separador
                st.markdown("---")
                
                # IMPACTO AMBIENTAL
                st.markdown("##### 🌱 Impacto Ambiental")
                
                col_imp1, col_imp2, col_imp3 = st.columns(3)
                
                with col_imp1:
                    # Equivalente em árvores plantadas (cada árvore absorve ~22 kg CO₂/ano)
                    arvores_equivalentes = int(fracoes['Redução Absoluta'] * 1000 / 22) if fracoes['Redução Absoluta'] > 0 else 0
                    st.metric("Equivalente em Árvores", 
                             f"{formatar_br(arvores_equivalentes, 0)}",
                             "Árvores necessárias para absorver CO₂")
                
                with col_imp2:
                    # Equivalente em carros fora das ruas (cada carro emite ~2 t CO₂/ano)
                    carros_equivalentes = int(fracoes['Redução Absoluta'] / 2) if fracoes['Redução Absoluta'] > 0 else 0
                    st.metric("Equivalente em Carros", 
                             f"{formatar_br(carros_equivalentes, 0)}",
                             "Carros retirados das ruas")
                
                with col_imp3:
                    # Economia de energia (reciclagem economiza ~95% de energia)
                    energia_economizada = fracoes['Massa_Reciclagem'] * 0.95 * 14  # 14 MWh por tonelada reciclada
                    st.metric("Energia Economizada", 
                             f"{formatar_br(energia_economizada, 0)} MWh",
                             "Pela reciclagem de materiais")
                
                # Separador
                st.markdown("---")
                
                # DETALHES TÉCNICOS E METODOLOGIA
                with st.expander("📚 Detalhes Técnicos da Simulação"):
                    st.markdown(f"""
                    **Metodologia da Simulação:**
                    
                    **1. Fatores de Emissão (t CO₂eq/t resíduo):**
                    - Aterro sanitário: 0,80 t CO₂eq/t
                    - Reciclagem: 0,15 t CO₂eq/t
                    - Compostagem: 0,10 t CO₂eq/t
                    
                    **2. Valores Econômicos:**
                    - Materiais recicláveis: R$ 250 por tonelada
                    - Composto orgânico: R$ 150 por tonelada
                    - Crédito de carbono: US$ 50 por t CO₂eq (R$ 5/US$)
                    
                    **3. Cenários Analisados:**
                    - **Atual:** {formatar_br(massa_total_municipio * 0.85, 0)} t para aterro, {formatar_br(massa_total_municipio * 0.08, 0)} t recicláveis
                    - **Economia Circular:** Redução de 45% no aterro, aumento de 337% na reciclagem
                    - **Otimizado:** Redução de 65% no aterro, aumento de 463% na reciclagem
                    
                    **4. Benefícios Calculados:**
                    - Valor total anual: R$ {formatar_br(fracoes['Valor_Total_R$'], 0)}
                    - Redução de emissões: {fracoes['Redução Percentual']:.1f}%
                    - Emissões evitadas: {formatar_br(fracoes['Redução Absoluta'], 0)} t CO₂eq/ano
                    
                    **5. Premissas:**
                    - Baseado em dados SINISA 2023
                    - Fatores IPCC para resíduos sólidos urbanos
                    - Valores de mercado médios brasileiros
                    - Câmbio: R$ 5,00 por US$ 1,00
                    """)
            
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
                st.write("Primeiras linhas do DataFrame:")
                st.write(df.head())
    
    # Análise comparativa por estado
    if 'Estado' in colunas and 'Massa_Total' in colunas:
        st.header("📈 Análise Comparativa por Estado")
        
        # Preparar dados
        dados_estado = df.groupby(colunas['Estado']).agg(
            Municipios=(colunas['Massa_Total'], 'count'),
            Massa_Total=(colunas['Massa_Total'], 'sum'),
            Massa_Media=(colunas['Massa_Total'], 'mean')
        ).reset_index()
        
        # Renomear a coluna para facilitar
        dados_estado = dados_estado.rename(columns={colunas['Estado']: 'Estado'})
        dados_estado = dados_estado.sort_values('Massa_Total', ascending=False)
        
        # Layout para gráfico e tabela
        col_graf, col_tab = st.columns([2, 1])
        
        with col_graf:
            st.subheader("🏆 Top 10 Estados")
            
            fig, ax = plt.subplots(figsize=(10, 6))
            top_10 = dados_estado.head(10)
            
            bars = ax.barh(top_10['Estado'], top_10['Massa_Total'], color='#3498db')
            ax.set_xlabel('Massa Total Coletada (toneladas)')
            ax.set_title('Top 10 Estados por Massa de Resíduos Coletados')
            ax.invert_yaxis()
            ax.grid(axis='x', alpha=0.3)
            
            # Formatar eixo x no padrão brasileiro
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: formatar_br(x, 0)))
            
            # Adicionar valores formatados no padrão brasileiro
            for bar in bars:
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height()/2,
                       f'{formatar_br(width, 0)}', ha='left', va='center', fontsize=9)
            
            st.pyplot(fig)
        
        with col_tab:
            st.subheader("📋 Ranking Completo")
            
            # Tabela simplificada
            tabela_resumo = dados_estado[['Estado', 'Massa_Total', 'Municipios']].copy()
            tabela_resumo.columns = ['Estado', 'Massa (t)', 'Municípios']
            tabela_resumo['Massa (t)'] = tabela_resumo['Massa (t)'].round(0)
            
            # Formatar a coluna de massa no padrão brasileiro
            tabela_resumo['Massa (t)'] = tabela_resumo['Massa (t)'].apply(lambda x: formatar_br(x, 0))
            tabela_resumo['Municípios'] = tabela_resumo['Municípios'].apply(lambda x: formatar_br(x, 0))
            
            st.dataframe(tabela_resumo.head(15), height=400, use_container_width=True)
    
    # Dados brutos (se solicitado)
    if mostrar_dados and 'Massa_Total' in colunas:
        with st.expander("📄 Dados Brutos (Amostra)"):
            # Mostrar apenas colunas importantes - GARANTINDO COLUNAS ÚNICAS
            colunas_para_mostrar = []
            colunas_ja_adicionadas = set()
            
            for tipo, col in colunas.items():
                if col in df.columns and col not in colunas_ja_adicionadas:
                    colunas_para_mostrar.append(col)
                    colunas_ja_adicionadas.add(col)
            
            if colunas_para_mostrar:
                dados_amostra = df[colunas_para_mostrar].head(20).copy()
                
                # Formatar colunas numéricas no padrão brasileiro
                for col in dados_amostra.columns:
                    try:
                        # Verificar se é numérica
                        col_data = dados_amostra[col]
                        if hasattr(col_data, 'dtype'):
                            dtype_str = str(col_data.dtype)
                            if any(num_type in dtype_str for num_type in ['int', 'float', 'Int', 'Float']):
                                col_name = str(col).lower()
                                if 'população' in col_name or 'populacao' in col_name or 'pop' in col_name:
                                    dados_amostra[col] = dados_amostra[col].apply(lambda x: formatar_br(x, 0) if pd.notna(x) else x)
                                elif 'massa' in col_name or 'toneladas' in col_name:
                                    dados_amostra[col] = dados_amostra[col].apply(lambda x: formatar_br(x, 1) if pd.notna(x) else x)
                                else:
                                    dados_amostra[col] = dados_amostra[col].apply(lambda x: formatar_br(x, 0) if pd.notna(x) else x)
                    except:
                        # Se houver erro, manter como está
                        pass
                
                st.dataframe(dados_amostra, use_container_width=True)
    
    # Seção de informações técnicas
    with st.expander("📚 Informações Técnicas e Metodologia"):
        st.markdown(f"""
        ## 📊 Fonte dos Dados
        
        **Sistema Nacional de Informações sobre Saneamento (SINISA) 2023**
        
        ## ⚙️ Metodologia de Análise
        
        **Filtro aplicado:**
        - Apenas registros com valor 'Sim' na primeira coluna (Coluna A)
        - Total de {formatar_br(12822, 0)} registros válidos (94,1% do total)
        
        **Colunas principais utilizadas:**
        - Estado: Coluna D (Col_3)
        - Região: Coluna E (Col_4)
        - População: Coluna J (Col_9) - População municipal
        - Tipo de Coleta: Coluna Q (Col_16) - "Tipo de coleta executada"
        - Massa Total: Coluna Y (Col_24) - "Massa de resíduos sólidos total coletada para a rota cadastrada"
        - Destino (Texto): Coluna AD (Col_28) - "Tipo de unidade de destino" (ex: Aterro controlado)
        - Agente Executor: Coluna AE (Col_29) - "Tipo de executor do serviço de destino dos resíduos" (ex: Agente privado)
        
        **Cálculo per capita:**
        - Quando disponível: usa população real da coluna J
        - Fórmula: (Massa Total em kg) / População = kg/hab/ano
        - 1 tonelada = 1.000 kg
        - Se população não disponível: usa média nacional de {formatar_br(365.21, 1)} kg/hab/ano para estimativa
        
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
        3. Para municípios sem dados de população, usa estimativa baseada na média nacional
        4. Fatores de emissão médios, não específicos por tecnologia
        """)
    
    # Rodapé
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center'>
        <p>Desenvolvido para análise de dados SINISA 2023 | Dados: Sistema Nacional de Informações sobre Saneamento</p>
        <p>Última atualização: Janeiro 2026 | Versão 4.0</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
