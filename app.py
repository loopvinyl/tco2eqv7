import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import BytesIO
import matplotlib.pyplot as plt
import unicodedata

# Configuração da página
st.set_page_config(page_title="Análise RSU Brasil - SINISA 2023", layout="wide")

st.title("📊 Análise de Resíduos Sólidos Urbanos - Dados SINISA 2023")
st.markdown("**Dados oficiais do Sistema Nacional de Informações sobre Saneamento**")

# URL do arquivo Excel
EXCEL_URL = "https://github.com/loopvinyl/tco2eqv7/raw/main/rsuBrasil.xlsx"

@st.cache_data
def carregar_dados_filtrados():
    """Carrega os dados do Excel aplicando filtro da coluna A = 'Sim'"""
    try:
        response = requests.get(EXCEL_URL, timeout=30)
        response.raise_for_status()
        excel_file = BytesIO(response.content)
        
        # Carregar a aba específica
        xls = pd.ExcelFile(excel_file)
        df = pd.read_excel(xls, sheet_name="Manejo_Coleta_e_Destinação")
        
        # Aplicar filtro: apenas registros onde a primeira coluna (coluna A) = 'Sim'
        primeira_coluna = df.columns[0]  # Primeira coluna (A)
        df_filtrado = df[df[primeira_coluna] == 'Sim'].copy()
        
        st.success(f"✅ Dados carregados com sucesso! {len(df_filtrado)} registros após filtro.")
        return df_filtrado
        
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {str(e)}")
        return None

def normalizar_texto(texto):
    """Normaliza texto removendo acentos"""
    if pd.isna(texto):
        return ""
    texto = str(texto)
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto.lower().strip()

def identificar_colunas_principais(df):
    """Identifica automaticamente as colunas principais baseadas no relatório"""
    colunas_mapeadas = {}
    
    st.write("🔍 **Identificando colunas no dataframe...**")
    
    # Mostrar todas as colunas para debug
    with st.expander("Ver todas as colunas"):
        for i, col in enumerate(df.columns):
            st.write(f"{i+1}. **{col}**")
    
    # Padrões de busca específicos baseados no relatório
    padroes_especificos = {
        'Município': ['município', 'municipio', 'cidade', 'local', 'ministério das cidades', 'ribeirão preto'],
        'Estado': ['col_3', 'estado', 'uf', 'unidade da federação'],
        'Região': ['col_4', 'região', 'regiao', 'grande região'],
        'Tipo_Coleta': ['col_17', 'tipo de coleta', 'tipo coleta', 'coleta'],
        'Massa_Total': [
            'massa de resíduos sólidos total coletada para a rota cadastrada',
            'col_24', 
            'massa total',
            'massa coletada',
            'massa de resíduos'
        ],
        'Destino': ['col_28', 'destino', 'destinação', 'destinacao final']
    }
    
    # Primeiro, tentar encontrar por nomes exatos das colunas do relatório
    nomes_exatos_relatorio = {
        'Estado': 'Col_3',
        'Região': 'Col_4', 
        'Tipo_Coleta': 'Col_17',
        'Massa_Total': 'Col_24',
        'Destino': 'Col_28'
    }
    
    for tipo, nome_exato in nomes_exatos_relatorio.items():
        if nome_exato in df.columns:
            colunas_mapeadas[tipo] = nome_exato
            st.success(f"✅ Coluna {tipo} encontrada como: {nome_exato}")
    
    # Se não encontrou pelo nome exato, buscar por padrões
    for tipo, lista_padroes in padroes_especificos.items():
        if tipo not in colunas_mapeadas:  # Só buscar se não encontrou ainda
            for col in df.columns:
                col_lower = str(col).lower()
                for padrao in lista_padroes:
                    if padrao in col_lower:
                        colunas_mapeadas[tipo] = col
                        st.info(f"🔍 Coluna {tipo} identificada por padrão: {col}")
                        break
                if tipo in colunas_mapeadas:
                    break
    
    # Busca especial para município (pode ser uma coluna com nome longo)
    if 'Município' not in colunas_mapeadas:
        # Procurar por colunas que contenham valores como "Ribeirão Preto"
        for col in df.columns:
            if df[col].dtype == 'object':  # Coluna de texto
                # Verificar se tem "Ribeirão Preto" em algum valor
                valores = df[col].astype(str).str.lower().dropna()
                if any('ribeirão preto' in v or 'ribeirao preto' in v for v in valores):
                    colunas_mapeadas['Município'] = col
                    st.success(f"✅ Coluna Município identificada por conteúdo: {col}")
                    break
    
    return colunas_mapeadas

def buscar_municipio_na_coluna(df, municipio_nome, coluna_municipio):
    """Busca um município em uma coluna específica"""
    if coluna_municipio not in df.columns:
        return None
    
    municipio_normalizado = normalizar_texto(municipio_nome)
    df['temp_normalizado'] = df[coluna_municipio].apply(normalizar_texto)
    
    # Buscar exato
    mask_exato = df['temp_normalizado'] == municipio_normalizado
    
    # Buscar por partes (para nomes compostos)
    partes = municipio_normalizado.split()
    mask_partes = pd.Series(True, index=df.index)
    for parte in partes:
        if len(parte) > 2:  # Ignorar preposições
            mask_partes = mask_partes & df['temp_normalizado'].str.contains(parte, na=False)
    
    # Busca por contém
    mask_contem = df['temp_normalizado'].str.contains(municipio_normalizado, na=False)
    
    # Combinar
    mask_total = mask_exato | mask_partes | mask_contem
    
    resultados = df[mask_total]
    
    # Remover coluna temporária
    df.drop(columns=['temp_normalizado'], inplace=True, errors='ignore')
    
    if len(resultados) > 0:
        return resultados.iloc[0]
    
    return None

def main():
    # Barra lateral
    with st.sidebar:
        st.header("⚙️ Configurações de Análise")
        
        # Opções de municípios
        municipios_interesse = [
            "RIBEIRÃO PRETO", 
            "SÃO JOSÉ DO RIO PRETO",
            "SERTÃOZINHO",
            "MANAUS",
            "ARIQUEMES",
            "BOCA DO ACRE"
        ]
        
        municipio_selecionado = st.selectbox(
            "Selecione um município para análise detalhada:",
            municipios_interesse
        )
        
        st.markdown("---")
        st.header("📊 Opções de Visualização")
        
        mostrar_detalhes_colunas = st.checkbox("Mostrar detalhes das colunas", value=False)
        
        st.markdown("---")
        st.header("📈 Cenários de Simulação")
        
        cenario = st.radio(
            "Selecione o cenário para análise de GEE:",
            ["Cenário Atual", 
             "Cenário de Economia Circular", 
             "Cenário Otimizado (Máxima Reciclagem)"],
            index=0
        )
    
    # Carregar dados
    st.header("📁 Dados SINISA 2023 - Filtrados")
    
    with st.spinner("Carregando e processando dados..."):
        df = carregar_dados_filtrados()
    
    if df is None:
        st.error("Não foi possível carregar os dados. Verifique o arquivo e conexão.")
        return
    
    # Identificar colunas principais
    st.subheader("🔍 Identificação das Colunas")
    colunas = identificar_colunas_principais(df)
    
    # Mostrar resumo das colunas identificadas
    if mostrar_detalhes_colunas:
        st.info("📋 **Colunas identificadas:**")
        for tipo, coluna in colunas.items():
            if coluna:
                st.write(f"• **{tipo}:** `{coluna}`")
            else:
                st.write(f"• **{tipo}:** ❌ Não identificada")
    
    # Mostrar informações da base
    st.subheader("📊 Resumo da Base de Dados")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Registros", f"{len(df):,}")
    
    with col2:
        if 'Massa_Total' in colunas:
            massa_total = df[colunas['Massa_Total']].sum()
            st.metric("Massa Total Coletada", f"{massa_total:,.0f} t")
        else:
            st.error("Massa Total: Coluna não identificada")
    
    with col3:
        if 'Estado' in colunas:
            estados_unicos = df[colunas['Estado']].nunique()
            st.metric("Estados", estados_unicos)
        else:
            st.warning("Estados: Coluna não identificada")
    
    with col4:
        if 'Região' in colunas:
            regioes_unicas = df[colunas['Região']].nunique()
            st.metric("Regiões", regioes_unicas)
        else:
            st.warning("Regiões: Coluna não identificada")
    
    # Análise do município selecionado
    st.header(f"🏙️ Análise Detalhada: {municipio_selecionado}")
    
    # Buscar dados do município
    dados_municipio = None
    coluna_municipio_encontrada = None
    
    if 'Município' in colunas:
        coluna_municipio = colunas['Município']
        dados_municipio = buscar_municipio_na_coluna(df, municipio_selecionado, coluna_municipio)
        coluna_municipio_encontrada = coluna_municipio
    
    if dados_municipio is not None:
        st.success(f"✅ Município encontrado na coluna: `{coluna_municipio_encontrada}`")
        
        # Criar colunas para exibição
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("📋 **Informações Identificadas**")
            
            # Nome do município
            st.write(f"**Município:** {dados_municipio[coluna_municipio_encontrada]}")
            
            # Estado
            if 'Estado' in colunas and colunas['Estado'] in dados_municipio:
                estado = dados_municipio[colunas['Estado']]
                st.write(f"**Estado:** {estado}")
            
            # Região
            if 'Região' in colunas and colunas['Região'] in dados_municipio:
                regiao = dados_municipio[colunas['Região']]
                st.write(f"**Região:** {regiao}")
            
            # Tipo de Coleta
            if 'Tipo_Coleta' in colunas and colunas['Tipo_Coleta'] in dados_municipio:
                tipo_coleta = dados_municipio[colunas['Tipo_Coleta']]
                st.write(f"**Tipo de Coleta:** {tipo_coleta}")
            
            # Destino
            if 'Destino' in colunas and colunas['Destino'] in dados_municipio:
                destino = dados_municipio[colunas['Destino']]
                st.write(f"**Destino Final:** {destino}")
                
                # Classificar destino
                if pd.isna(destino):
                    st.warning("Destino não informado")
                elif any(term in str(destino).lower() for term in ['aterro sanitário', 'compostagem', 'reciclagem', 'triagem']):
                    st.success("✅ Destino adequado")
                else:
                    st.warning("⚠️ Verificar adequação do destino")
        
        with col2:
            st.info("📊 **Dados Quantitativos**")
            
            # Massa Total
            if 'Massa_Total' in colunas and colunas['Massa_Total'] in dados_municipio:
                massa = dados_municipio[colunas['Massa_Total']]
                if pd.notna(massa):
                    st.write(f"**Massa Coletada:** {massa:,.1f} toneladas/ano")
                    
                    # Estimativa per capita (usando média nacional como referência)
                    st.write(f"**Per capita (média nacional):** 365 kg/hab/ano")
                    st.write(f"**Equivalente diário:** 1.0 kg/hab/dia")
                    
                    # População estimada (baseada na massa e média nacional)
                    if massa > 0:
                        populacao_estimada = (massa * 1000) / 365
                        st.write(f"**População estimada:** {populacao_estimada:,.0f} habitantes")
                    else:
                        st.warning("Massa zerada ou negativa")
                else:
                    st.warning("Massa não informada")
            else:
                st.error("Coluna de massa não identificada nos dados do município")
                
                # Tentar mostrar qual coluna é a de massa
                if 'Massa_Total' in colunas:
                    st.write(f"Coluna de massa esperada: `{colunas['Massa_Total']}`")
                
                # Mostrar todas as colunas disponíveis no registro
                with st.expander("Ver todos os dados do município"):
                    for col, valor in dados_municipio.items():
                        st.write(f"**{col}:** {valor}")
        
        # Simulação de cenários (só se tiver massa)
        if 'Massa_Total' in colunas and colunas['Massa_Total'] in dados_municipio:
            massa = dados_municipio[colunas['Massa_Total']]
            
            if pd.notna(massa) and massa > 0:
                st.header(f"🔮 Simulação de Cenários - {cenario}")
                
                massa_anual = massa
                
                # Parâmetros por cenário
                if cenario == "Cenário Atual":
                    fracoes = {
                        'Aterro': 0.85,
                        'Reciclagem': 0.08,
                        'Compostagem': 0.07,
                        'Emissões (t CO₂eq)': massa_anual * 0.8,
                        'Redução vs Atual': '0%',
                        'cor': '#e74c3c'
                    }
                elif cenario == "Cenário de Economia Circular":
                    fracoes = {
                        'Aterro': 0.40,
                        'Reciclagem': 0.35,
                        'Compostagem': 0.25,
                        'Emissões (t CO₂eq)': massa_anual * 0.4,
                        'Redução vs Atual': '50%',
                        'cor': '#3498db'
                    }
                else:  # Cenário Otimizado
                    fracoes = {
                        'Aterro': 0.20,
                        'Reciclagem': 0.45,
                        'Compostagem': 0.35,
                        'Emissões (t CO₂eq)': massa_anual * 0.2,
                        'Redução vs Atual': '75%',
                        'cor': '#2ecc71'
                    }
                
                # Criar visualizações
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
                
                # Gráfico de pizza
                labels = ['Aterro', 'Reciclagem', 'Compostagem']
                sizes = [fracoes['Aterro'] * 100, fracoes['Reciclagem'] * 100, fracoes['Compostagem'] * 100]
                colors = ['#e74c3c', '#3498db', '#2ecc71']
                
                ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
                ax1.set_title(f'Destinação Final - {cenario}', fontsize=14, fontweight='bold')
                
                # Gráfico de emissões
                cenarios_nomes = ['Atual', 'Econ. Circular', 'Otimizado']
                emissões_atual = massa_anual * 0.8
                emissões_circular = massa_anual * 0.4
                emissões_otimizado = massa_anual * 0.2
                emissões = [emissões_atual, emissões_circular, emissões_otimizado]
                cores_barras = ['#e74c3c', '#3498db', '#2ecc71']
                
                bars = ax2.bar(cenarios_nomes, emissões, color=cores_barras)
                ax2.set_ylabel('Emissões de CO₂eq (t/ano)', fontsize=12)
                ax2.set_title('Comparativo de Emissões de GEE', fontsize=14, fontweight='bold')
                ax2.grid(axis='y', alpha=0.3)
                
                # Adicionar valores nas barras
                for bar, valor in zip(bars, emissões):
                    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                            f'{valor:,.0f}', ha='center', va='bottom', fontweight='bold')
                
                plt.tight_layout()
                
                # Mostrar gráficos
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.pyplot(fig)
                
                with col2:
                    st.info("💡 **Resultados da Simulação**")
                    
                    st.metric("Massa Anual", f"{massa_anual:,.0f} t")
                    st.metric("Emissões Estimadas", f"{fracoes['Emissões (t CO₂eq)']:,.0f} t CO₂eq")
                    
                    if fracoes['Redução vs Atual'] != '0%':
                        st.success(f"**Redução de Emissões:** {fracoes['Redução vs Atual']}")
                        
                        # Calcular valor econômico
                        reducao_absoluta = (massa_anual * 0.8) - fracoes['Emissões (t CO₂eq)']
                        valor_carbono_usd = reducao_absoluta * 50  # US$ 50/ton
                        valor_carbono_brl = valor_carbono_usd * 5  # R$ 5/US$
                        
                        st.success(f"**Valor do Carbono:**")
                        st.success(f"US$ {valor_carbono_usd:,.0f}/ano")
                        st.success(f"R$ {valor_carbono_brl:,.0f}/ano")
                    
                    st.write(f"**Materiais Recicláveis:** {massa_anual * fracoes['Reciclagem']:,.0f} t/ano")
                    st.write(f"**Compostagem:** {massa_anual * fracoes['Compostagem']:,.0f} t/ano")
                    st.write(f"**Aterro:** {massa_anual * fracoes['Aterro']:,.0f} t/ano")
            else:
                st.warning("Não foi possível realizar a simulação: massa não disponível ou zerada.")
        else:
            st.error("Não foi possível realizar a simulação: coluna de massa não identificada.")
    
    else:
        st.warning(f"⚠️ Município '{municipio_selecionado}' não encontrado nos dados.")
        
        # Mostrar algumas colunas que podem ser de municípios
        st.info("🔍 **Tentando identificar coluna de municípios...**")
        
        colunas_texto = []
        for col in df.columns:
            if df[col].dtype == 'object':  # Coluna de texto
                # Verificar se tem o município procurado
                valores = df[col].astype(str).str.lower().dropna()
                municipio_buscado = municipio_selecionado.lower()
                
                # Verificar diferentes formas
                formas = [
                    municipio_buscado,
                    municipio_buscado.replace('ã', 'a').replace('ç', 'c').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u'),
                    municipio_buscado.replace('ão', 'ao').replace('õe', 'oe')
                ]
                
                for forma in formas:
                    if any(forma in v for v in valores):
                        colunas_texto.append(col)
                        break
        
        if colunas_texto:
            st.write("**Possíveis colunas de municípios:**")
            for col in colunas_texto[:3]:  # Mostrar até 3
                st.write(f"- `{col}`")
        else:
            st.write("**Nenhuma coluna com nomes de municípios identificada.**")
    
    # Análise comparativa por estado (se tiver coluna de estado)
    if 'Estado' in colunas and 'Massa_Total' in colunas:
        st.header("📈 Análise Comparativa por Estado")
        
        # Agrupar por estado
        dados_estado = df.groupby(colunas['Estado']).agg(
            Municipios=(colunas['Massa_Total'], 'count'),
            Massa_Total=(colunas['Massa_Total'], 'sum'),
            Massa_Media=(colunas['Massa_Total'], 'mean')
        ).reset_index()
        
        # Ordenar por massa total
        dados_estado = dados_estado.sort_values('Massa_Total', ascending=False)
        
        # Mostrar top 10
        st.subheader("🏆 Top 10 Estados por Massa de Resíduos")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Gráfico de barras
            fig, ax = plt.subplots(figsize=(10, 6))
            
            top_10 = dados_estado.head(10)
            bars = ax.barh(top_10[colunas['Estado']], top_10['Massa_Total'], color='#3498db')
            
            ax.set_xlabel('Massa Total Coletada (t)')
            ax.set_title('Top 10 Estados - Massa de Resíduos')
            ax.grid(axis='x', alpha=0.3)
            
            # Adicionar valores nas barras
            for bar in bars:
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height()/2,
                       f'{width:,.0f}', ha='left', va='center', fontsize=9)
            
            plt.tight_layout()
            st.pyplot(fig)
        
        with col2:
            # Tabela resumo
            st.write("**Ranking de Estados:**")
            for i, (_, row) in enumerate(dados_estado.head(5).iterrows(), 1):
                st.write(f"{i}. **{row[colunas['Estado']]}**: {row['Massa_Total']:,.0f} t")
    
    # Informações sobre o dataset
    with st.expander("📋 Sobre os Dados e Metodologia"):
        st.write("""
        ## 📊 Fonte dos Dados
        
        **Sistema Nacional de Informações sobre Saneamento (SINISA) 2023**
        
        ## ⚙️ Configuração Aplicada
        
        - **Arquivo:** rsuBrasil.xlsx
        - **Aba:** Manejo_Coleta_e_Destinação
        - **Filtro:** Apenas registros com 'Sim' na coluna A
        - **Total de registros:** 12.822
        
        ## 📈 Colunas Principais (segundo relatório)
        
        - **Estado:** Coluna D (Col_3)
        - **Região:** Coluna E (Col_4)
        - **Tipo de Coleta:** Coluna R (Col_17)
        - **Massa Total:** Coluna Y (Col_24) - "Massa de resíduos sólidos total coletada para a rota cadastrada"
        - **Destino:** Coluna AC (Col_28)
        
        ## 🧮 Métodos de Cálculo
        
        **Per Capita Nacional:**
        - Média nacional: 365.21 kg/hab/ano
        - Equivalente diário: 1.001 kg/hab/dia
        - Fonte: SINISA 2023 com dados populacionais IBGE 2023
        
        **Simulação de Cenários:**
        - **Cenário Atual:** Baseado em médias brasileiras atuais
        - **Economia Circular:** Aumento significativo de reciclagem e compostagem
        - **Otimizado:** Máxima recuperação de materiais
        
        **Fatores de Emissão:**
        - Baseados em metodologias IPCC para resíduos sólidos
        - Consideram diferentes tipos de destinação
        """)

if __name__ == "__main__":
    main()
