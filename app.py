import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import BytesIO
import matplotlib.pyplot as plt

# Configuração da página
st.set_page_config(page_title="Análise RSU Brasil - SINISA 2023", layout="wide")

st.title("📊 Análise de Resíduos Sólidos Urbanos - Dados SINISA 2023")
st.markdown("**Dados oficiais do Sistema Nacional de Informações sobre Saneamento**")

# URL do arquivo Excel
EXCEL_URL = "https://github.com/loopvinyl/tco2eqv7/raw/main/rsuBrasil.xlsx"

@st.cache_data
def carregar_dados_corretamente():
    """Carrega os dados do Excel pulando as linhas de cabeçalho/legenda"""
    try:
        response = requests.get(EXCEL_URL, timeout=30)
        response.raise_for_status()
        excel_file = BytesIO(response.content)
        
        # Carregar a aba específica
        xls = pd.ExcelFile(excel_file)
        
        # Primeiro, carregar sem cabeçalho para ver a estrutura
        df_raw = pd.read_excel(xls, sheet_name="Manejo_Coleta_e_Destinação", header=None)
        
        # Encontrar a linha onde começa o cabeçalho real
        # Procurar por 'Sim' na primeira coluna para saber onde começam os dados
        linha_comeco_dados = None
        for i in range(min(20, len(df_raw))):
            if str(df_raw.iloc[i, 0]).strip() == 'Sim':
                linha_comeco_dados = i
                break
        
        if linha_comeco_dados is None:
            # Se não encontrou, usar linha 0 como cabeçalho
            df = pd.read_excel(xls, sheet_name="Manejo_Coleta_e_Destinação")
            st.warning("Não foi possível identificar automaticamente o início dos dados.")
        else:
            # A linha anterior deve ser o cabeçalho
            linha_cabecalho = linha_comeco_dados - 1
            df = pd.read_excel(xls, sheet_name="Manejo_Coleta_e_Destinação", header=linha_cabecalho)
        
        # Aplicar filtro: apenas registros onde a primeira coluna = 'Sim'
        primeira_coluna = df.columns[0]
        df_filtrado = df[df[primeira_coluna] == 'Sim'].copy()
        
        # Remover possíveis espaços em branco extras
        df_filtrado = df_filtrado.dropna(subset=[primeira_coluna])
        
        st.success(f"✅ Dados carregados com sucesso! {len(df_filtrado)} registros válidos (com 'Sim').")
        
        # Identificar automaticamente as colunas importantes
        colunas_mapeadas = identificar_colunas_importantes(df_filtrado)
        
        return df_filtrado, colunas_mapeadas
        
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None, None

def identificar_colunas_importantes(df):
    """Identifica as colunas importantes baseadas no relatório"""
    colunas = {}
    
    # Mapear nomes de coluna para tipos
    for col_name in df.columns:
        col_str = str(col_name).lower()
        
        # Coluna de Município - buscar por padrões específicos
        if any(term in col_str for term in ['município', 'municipio', 'cidade', 'nome']):
            colunas['Município'] = col_name
        
        # Coluna de Estado (Col_3) - pode ser 'Col_3' ou ter 'estado' no nome
        elif 'col_3' in col_str or 'estado' in col_str or 'uf' in col_str:
            colunas['Estado'] = col_name
        
        # Coluna de Região (Col_4)
        elif 'col_4' in col_str or 'região' in col_str or 'regiao' in col_str:
            colunas['Região'] = col_name
        
        # Coluna de Tipo de Coleta (Col_17)
        elif 'col_17' in col_str or 'tipo de coleta' in col_str:
            colunas['Tipo_Coleta'] = col_name
        
        # Coluna de Massa Total (Col_24) - buscar por 'massa' ou 'col_24'
        elif 'col_24' in col_str or 'massa' in col_str:
            colunas['Massa_Total'] = col_name
        
        # Coluna de Destino (Col_28)
        elif 'col_28' in col_str or 'destino' in col_str:
            colunas['Destino'] = col_name
    
    # Se não encontrou pelo nome, tentar pelas posições
    if len(df.columns) >= 29:  # Precisamos até a coluna AC (índice 28)
        if 'Estado' not in colunas:
            colunas['Estado'] = df.columns[3]  # Coluna D (índice 3)
        if 'Região' not in colunas:
            colunas['Região'] = df.columns[4]  # Coluna E (índice 4)
        if 'Tipo_Coleta' not in colunas:
            colunas['Tipo_Coleta'] = df.columns[17]  # Coluna R (índice 17)
        if 'Massa_Total' not in colunas:
            colunas['Massa_Total'] = df.columns[24]  # Coluna Y (índice 24)
        if 'Destino' not in colunas:
            colunas['Destino'] = df.columns[28]  # Coluna AC (índice 28)
    
    # Para município, usar a coluna que parece ter nomes de cidades
    if 'Município' not in colunas:
        for col in df.columns:
            # Verificar se a coluna tem nomes como "Ribeirão Preto"
            amostra = df[col].dropna().astype(str).head(10)
            if any('ribeirão' in v.lower() or 'são' in v.lower() or 'rio' in v.lower() for v in amostra):
                colunas['Município'] = col
                break
        
        # Se ainda não encontrou, usar uma coluna de texto com muitos valores únicos
        if 'Município' not in colunas:
            for col in df.columns:
                if df[col].dtype == 'object' and df[col].nunique() > 1000:
                    colunas['Município'] = col
                    break
    
    return colunas

def buscar_municipio(df, col_municipio, municipio_nome):
    """Busca um município na coluna específica"""
    if col_municipio not in df.columns:
        return None
    
    # Normalizar o nome do município para busca
    def normalizar(nome):
        if pd.isna(nome):
            return ""
        nome = str(nome).lower()
        # Remover acentos simples
        substituicoes = {'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a',
                        'é': 'e', 'è': 'e', 'ê': 'e',
                        'í': 'i', 'ì': 'i', 'î': 'i',
                        'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o',
                        'ú': 'u', 'ù': 'u', 'û': 'u',
                        'ç': 'c'}
        for orig, subst in substituicoes.items():
            nome = nome.replace(orig, subst)
        return nome.strip()
    
    municipio_busca = normalizar(municipio_nome)
    
    # Criar coluna normalizada temporária
    df_temp = df.copy()
    df_temp['temp_normalizado'] = df_temp[col_municipio].apply(normalizar)
    
    # Buscar
    mask = df_temp['temp_normalizado'].str.contains(municipio_busca, na=False)
    resultados = df_temp[mask]
    
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
        
        mostrar_detalhes_tecnicos = st.checkbox("Mostrar detalhes técnicos", value=False)
        
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
    st.header("📁 Dados SINISA 2023 - Filtrados (apenas 'Sim')")
    
    with st.spinner("Carregando e processando dados..."):
        df, colunas = carregar_dados_corretamente()
    
    if df is None or colunas is None:
        st.error("Não foi possível carregar os dados.")
        return
    
    # Mostrar estatísticas
    st.subheader("📊 Estatísticas da Base de Dados")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Registros válidos", f"{len(df):,}")
    
    with col2:
        if 'Massa_Total' in colunas:
            massa_total = df[colunas['Massa_Total']].sum()
            st.metric("Massa total coletada", f"{massa_total:,.0f} t")
        else:
            st.error("Coluna de massa não encontrada")
    
    with col3:
        if 'Estado' in colunas:
            estados_unicos = df[colunas['Estado']].nunique()
            st.metric("Estados", estados_unicos)
    
    with col4:
        if 'Região' in colunas:
            regioes_unicas = df[colunas['Região']].nunique()
            st.metric("Regiões", regioes_unicas)
    
    # Mostrar colunas identificadas
    if mostrar_detalhes_tecnicos:
        with st.expander("🔍 Colunas identificadas"):
            st.write("**Mapeamento das colunas:**")
            for tipo, nome_coluna in colunas.items():
                st.write(f"• **{tipo}:** `{nome_coluna}`")
            
            st.write("\n**Primeiras 5 linhas do dataframe:**")
            st.dataframe(df.head())
    
    # Análise do município selecionado
    st.header(f"🏙️ Análise Detalhada: {municipio_selecionado}")
    
    if 'Município' in colunas:
        dados_municipio = buscar_municipio(df, colunas['Município'], municipio_selecionado)
        
        if dados_municipio is not None:
            st.success(f"✅ Município encontrado!")
            
            # Criar colunas para exibição
            col1, col2 = st.columns(2)
            
            with col1:
                st.info("📋 **Informações Identificadas**")
                
                # Nome do município
                st.write(f"**Município:** {dados_municipio[colunas['Município']]}")
                
                # Estado
                if 'Estado' in colunas:
                    estado = dados_municipio[colunas['Estado']]
                    st.write(f"**Estado:** {estado}")
                
                # Região
                if 'Região' in colunas:
                    regiao = dados_municipio[colunas['Região']]
                    st.write(f"**Região:** {regiao}")
                
                # Tipo de Coleta
                if 'Tipo_Coleta' in colunas:
                    tipo_coleta = dados_municipio[colunas['Tipo_Coleta']]
                    st.write(f"**Tipo de Coleta:** {tipo_coleta}")
                
                # Destino
                if 'Destino' in colunas:
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
                if 'Massa_Total' in colunas:
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
                        
                        # Simulação de cenários
                        st.subheader(f"🔮 Simulação - {cenario}")
                        
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
                        st.pyplot(fig)
                        
                        # Resultados
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
                        st.warning("Massa não informada para este município")
                else:
                    st.error("Coluna de massa não identificada")
        else:
            st.warning(f"⚠️ Município '{municipio_selecionado}' não encontrado nos dados filtrados.")
            
            # Mostrar algumas linhas para debug
            if mostrar_detalhes_tecnicos:
                with st.expander("🔍 Debug - Primeiras linhas da coluna de municípios"):
                    if 'Município' in colunas:
                        st.write(f"Coluna identificada como município: `{colunas['Município']}`")
                        st.write("Valores únicos (primeiros 20):")
                        st.write(df[colunas['Município']].dropna().unique()[:20])
    else:
        st.error("Não foi possível identificar a coluna de municípios.")
    
    # Análise comparativa por estado
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
    
    # Informações sobre qualidade dos dados
    with st.expander("📋 Informações sobre Qualidade dos Dados"):
        st.write("""
        ## 📊 Análise da Qualidade dos Dados
        
        Com base na análise completa do arquivo:
        
        **Total de registros na aba principal:** 13.626
        - ✅ **Com 'Sim' (válidos):** 12.822 (94,1%)
        - ❌ **Com 'Não':** 792 (5,8%)
        - ⚠️ **Outros/Legendas:** 12 (0,1%)
        
        **Percentual de dados faltantes:** 28,4%
        
        ## ⚙️ Configuração Aplicada
        
        - **Filtro:** Apenas registros com 'Sim' na coluna A
        - **Registros após filtro:** 12.822
        - **Média nacional per capita:** 365,21 kg/hab/ano
        
        ## 🎯 Próximos Passos
        
        1. Validar se todos os municípios de interesse estão nos dados filtrados
        2. Verificar valores específicos de massa para cada município
        3. Ajustar fatores de emissão conforme realidade brasileira
        """)

if __name__ == "__main__":
    main()
