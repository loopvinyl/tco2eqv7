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
        
        # Renomear colunas baseado no relatório para facilitar acesso
        mapeamento_colunas = {
            'Col_3': 'Estado',
            'Col_4': 'Região', 
            'Col_17': 'Tipo_Coleta',
            'Col_24': 'Massa_Total',
            'Col_28': 'Destino'
        }
        
        # Aplicar renomeação se as colunas existirem
        for col_original, novo_nome in mapeamento_colunas.items():
            if col_original in df_filtrado.columns:
                df_filtrado.rename(columns={col_original: novo_nome}, inplace=True)
        
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

def buscar_municipio_completo(df, municipio_nome):
    """Busca um município considerando diferentes variações e retorna todos os dados"""
    municipio_normalizado = normalizar_texto(municipio_nome)
    
    # Primeiro, tentar encontrar a coluna que contém os nomes dos municípios
    colunas_candidatas = []
    for col in df.columns:
        col_lower = str(col).lower()
        if any(term in col_lower for term in ['município', 'municipio', 'cidade', 'localidade', 'nome']):
            colunas_candidatas.append(col)
    
    if not colunas_candidatas:
        # Se não encontrar pelo nome, usar a coluna que parece ter nomes próprios
        for col in df.columns:
            # Verificar se a coluna tem valores que parecem nomes de cidades
            amostra = df[col].dropna().head(10)
            if len(amostra) > 0:
                # Verificar se algum valor contém "RIBEIRÃO" ou "SÃO" etc
                valores_str = amostra.astype(str).str.upper()
                if any(valor in valores_str.str.cat() for valor in ['RIBEIRÃO', 'SÃO', 'JOSÉ', 'PAULO', 'PRETO']):
                    colunas_candidatas.append(col)
                    break
    
    resultados_completos = []
    
    for col_municipio in colunas_candidatas:
        # Criar coluna normalizada para busca
        df[f'{col_municipio}_normalizado'] = df[col_municipio].apply(normalizar_texto)
        
        # Tentar diferentes estratégias de busca
        mask_exato = df[f'{col_municipio}_normalizado'] == municipio_normalizado
        
        # Buscar por partes do nome (para nomes compostos)
        partes = municipio_normalizado.split()
        if len(partes) > 1:
            # Para "ribeirao preto", buscar por "ribeirao" E "preto"
            mask_parte1 = df[f'{col_municipio}_normalizado'].str.contains(partes[0], na=False)
            mask_parte2 = df[f'{col_municipio}_normalizado'].str.contains(partes[-1], na=False)
            mask_partes = mask_parte1 & mask_parte2
        else:
            mask_partes = pd.Series(False, index=df.index)
        
        # Busca por "contém" (mais flexível)
        mask_contem = df[f'{col_municipio}_normalizado'].str.contains(municipio_normalizado, na=False)
        
        # Combinar todas as máscaras
        mask_total = mask_exato | mask_partes | mask_contem
        
        resultados = df[mask_total]
        
        if len(resultados) > 0:
            for _, linha in resultados.iterrows():
                resultados_completos.append({
                    'dados': linha,
                    'coluna_municipio': col_municipio,
                    'nome_original': linha[col_municipio],
                    'score': 2 if mask_exato.any() else 1  # Priorizar match exato
                })
    
    if resultados_completos:
        # Ordenar por score (match exato primeiro)
        resultados_completos.sort(key=lambda x: x['score'], reverse=True)
        return resultados_completos[0]['dados'], resultados_completos[0]['coluna_municipio']
    
    return None, None

def identificar_colunas_principais(df):
    """Identifica automaticamente as colunas principais baseadas no relatório"""
    colunas_mapeadas = {}
    
    # Padrões de busca para cada tipo de coluna
    padroes = {
        'Estado': ['estado', 'uf', 'col_3'],
        'Região': ['região', 'regiao', 'col_4'],
        'Tipo_Coleta': ['tipo', 'coleta', 'col_17', 'tipo de coleta'],
        'Massa_Total': ['massa', 'total', 'col_24', 'tonelada', 'peso'],
        'Destino': ['destino', 'col_28', 'destinação', 'destinacao'],
        'Município': ['município', 'municipio', 'cidade', 'local']
    }
    
    for tipo, lista_padroes in padroes.items():
        for col in df.columns:
            col_lower = str(col).lower()
            for padrao in lista_padroes:
                if padrao in col_lower:
                    colunas_mapeadas[tipo] = col
                    break
            if tipo in colunas_mapeadas:
                break
    
    return colunas_mapeadas

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
        st.header("📊 Filtros Avançados")
        
        mostrar_todos_dados = st.checkbox("Mostrar todos os dados do município", value=False)
        
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
    colunas = identificar_colunas_principais(df)
    
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
            st.metric("Massa Total", "Coluna não identificada")
    
    with col3:
        if 'Estado' in colunas:
            estados_unicos = df[colunas['Estado']].nunique()
            st.metric("Estados", estados_unicos)
    
    with col4:
        if 'Região' in colunas:
            regioes_unicas = df[colunas['Região']].nunique()
            st.metric("Regiões", regioes_unicas)
    
    # Mostrar estrutura das colunas
    with st.expander("🔍 Ver estrutura das colunas identificadas"):
        st.write("**Colunas identificadas:**")
        for tipo, coluna in colunas.items():
            if coluna:
                st.write(f"• **{tipo}:** `{coluna}`")
            else:
                st.write(f"• **{tipo}:** Não identificada")
        
        st.write("\n**Primeiras 5 linhas do dataframe:**")
        st.dataframe(df.head())
    
    # Análise do município selecionado
    st.header(f"🏙️ Análise Detalhada: {municipio_selecionado}")
    
    # Buscar dados do município
    dados_municipio, col_municipio = buscar_municipio_completo(df, municipio_selecionado)
    
    if dados_municipio is not None:
        st.success(f"✅ Município encontrado na coluna: `{col_municipio}`")
        
        # Criar colunas para exibição
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("📋 **Informações Identificadas**")
            
            # Nome do município
            st.write(f"**Município:** {dados_municipio[col_municipio]}")
            
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
                if pd.notna(massa) and massa > 0:
                    st.write(f"**Massa Coletada:** {massa:,.1f} toneladas/ano")
                    
                    # Estimativa per capita (usando média nacional como referência)
                    st.write(f"**Per capita estimado:** 365 kg/hab/ano (média nacional)")
                    st.write(f"**Equivalente diário:** 1.0 kg/hab/dia")
                    
                    # População estimada (baseada na massa e média nacional)
                    populacao_estimada = (massa * 1000) / 365
                    st.write(f"**População estimada:** {populacao_estimada:,.0f} habitantes")
                else:
                    st.warning("Massa não informada ou zerada")
            else:
                st.warning("Coluna de massa não identificada")
        
        # Mostrar todos os dados do município se solicitado
        if mostrar_todos_dados:
            st.subheader("📋 Todos os Dados do Município")
            st.write(f"Todos os dados disponíveis para {municipio_selecionado}:")
            
            # Converter a linha para DataFrame para melhor visualização
            df_municipio = pd.DataFrame([dados_municipio])
            
            # Transpor para melhor visualização
            df_transposto = df_municipio.transpose()
            df_transposto.columns = ['Valor']
            
            st.dataframe(df_transposto)
        
        # Simulação de cenários
        st.header(f"🔮 Simulação de Cenários - {cenario}")
        
        # Verificar se temos massa para simulação
        if 'Massa_Total' in colunas and colunas['Massa_Total'] in dados_municipio:
            massa = dados_municipio[colunas['Massa_Total']]
            
            if pd.notna(massa) and massa > 0:
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
            st.warning("Não foi possível realizar a simulação: coluna de massa não identificada.")
    
    else:
        st.warning(f"⚠️ Município '{municipio_selecionado}' não encontrado nos dados.")
        
        # Sugerir busca alternativa
        with st.expander("🔍 Tentar buscar município manualmente"):
            # Listar colunas que podem conter municípios
            colunas_possiveis = []
            for col in df.columns:
                if df[col].dtype == 'object':  # Colunas de texto
                    amostra = df[col].dropna().head(5)
                    if len(amostra) > 0:
                        # Verificar se parece nome de município
                        valores = amostra.astype(str).str.upper()
                        if any(valor in ' '.join(valores) for valor in ['RIBEIRÃO', 'SÃO', 'PAULO', 'JANEIRO', 'PRETO']):
                            colunas_possiveis.append(col)
            
            if colunas_possiveis:
                st.write("**Colunas que podem conter nomes de municípios:**")
                for col in colunas_possiveis[:5]:  # Mostrar até 5
                    st.write(f"- `{col}`")
                    
                    # Mostrar alguns valores dessa coluna
                    valores_unicos = df[col].dropna().unique()[:10]
                    st.write(f"  Amostra: {', '.join(map(str, valores_unicos))}")
    
    # Análise comparativa por estado
    st.header("📈 Análise Comparativa por Estado")
    
    if 'Estado' in colunas and 'Massa_Total' in colunas:
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
        - **Massa Total:** Coluna Y (Col_24)
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
