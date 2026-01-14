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
        
        st.success(f"Dados carregados com sucesso! {len(df_filtrado)} registros após filtro.")
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

def buscar_municipio_avancado(df, municipio_nome):
    """Busca um município considerando diferentes variações"""
    municipio_normalizado = normalizar_texto(municipio_nome)
    
    # Procurar na coluna de municípios (provavelmente coluna B ou C)
    for col in ['Município', 'Cidade', 'Nome_Município', 'Municipio']:
        if col in df.columns:
            df[f'{col}_normalizado'] = df[col].apply(normalizar_texto)
            mask = df[f'{col}_normalizado'].str.contains(municipio_normalizado, na=False)
            
            resultados = df[mask]
            if len(resultados) > 0:
                return resultados.iloc[0], col
    
    # Se não encontrar, tentar busca mais ampla
    for col in df.columns:
        if any(term in str(col).lower() for term in ['município', 'municipio', 'cidade', 'local']):
            df[f'{col}_normalizado'] = df[col].apply(normalizar_texto)
            mask = df[f'{col}_normalizado'].str.contains(municipio_normalizado, na=False)
            
            resultados = df[mask]
            if len(resultados) > 0:
                return resultados.iloc[0], col
    
    return None, None

def calcular_per_capita(row):
    """Calcula a geração per capita baseada nos dados"""
    # Procurar colunas de massa e população
    massa_cols = [col for col in row.index if 'massa' in str(col).lower() or 'col_24' in str(col)]
    pop_cols = [col for col in row.index if 'população' in str(col).lower() or 'pop' in str(col).lower()]
    
    if massa_cols and pop_cols:
        massa = row[massa_cols[0]]
        pop = row[pop_cols[0]]
        
        if pd.notna(massa) and pd.notna(pop) and pop > 0:
            return (massa * 1000) / pop
    return None

def main():
    # Barra lateral
    with st.sidebar:
        st.header("⚙️ Configurações de Análise")
        
        # Opções de municípios baseados no relatório
        municipios_interesse = [
            "MANAUS", 
            "RIBEIRÃO PRETO", 
            "SERTÃOZINHO", 
            "SÃO JOSÉ DO RIO PRETO",
            "ARIQUEMES",
            "BOCA DO ACRE"
        ]
        
        municipio_selecionado = st.selectbox(
            "Selecione um município para análise detalhada:",
            municipios_interesse
        )
        
        st.markdown("---")
        st.header("📊 Filtros de Dados")
        
        # Filtro por região
        st.subheader("Filtrar por Região")
        todas_regioes = st.checkbox("Todas as regiões", value=True)
        
        if not todas_regioes:
            regioes = ["Centro-Oeste", "Nordeste", "Norte", "Sudeste", "Sul"]
            regiao_selecionada = st.selectbox("Região:", regioes)
        
        st.markdown("---")
        st.header("📈 Cenários de Simulação")
        
        cenario = st.radio(
            "Selecione o cenário para análise de GEE:",
            ["Cenário Atual", 
             "Cenário de Economia Circular", 
             "Cenário Otimizado (Máxima Reciclagem)"]
        )
    
    # Carregar dados
    st.header("📁 Carregamento de Dados SINISA 2023")
    
    with st.spinner("Carregando dados do SINISA 2023 com filtro aplicado..."):
        df = carregar_dados_filtrados()
    
    if df is None:
        st.error("Não foi possível carregar os dados. Verifique o arquivo e conexão.")
        return
    
    # Mostrar informações da base de dados
    st.subheader("📊 Informações da Base de Dados")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total de Registros", f"{len(df):,}")
    
    with col2:
        # Calcular massa total
        massa_cols = [col for col in df.columns if 'massa' in str(col).lower() or 'col_24' in str(col)]
        if massa_cols:
            massa_total = df[massa_cols[0]].sum()
            st.metric("Massa Total Coletada", f"{massa_total:,.1f} t")
    
    with col3:
        # Contar estados únicos
        estado_cols = [col for col in df.columns if 'estado' in str(col).lower() or 'col_3' in str(col)]
        if estado_cols:
            estados_unicos = df[estado_cols[0]].nunique()
            st.metric("Estados", estados_unicos)
    
    # Mostrar estrutura das colunas
    with st.expander("🔍 Ver estrutura completa das colunas"):
        st.write("**Colunas disponíveis:**")
        for i, col in enumerate(df.columns):
            st.write(f"{i+1}. {col}")
        
        st.write("\n**Colunas principais identificadas no relatório:**")
        st.write("- Coluna D (Col_3): Estado")
        st.write("- Coluna E (Col_4): Região")
        st.write("- Coluna R (Col_17): Tipo de Coleta")
        st.write("- Coluna Y (Col_24): Massa Total")
        st.write("- Coluna AC (Col_28): Destino")
    
    # Análise do município selecionado
    st.header(f"🏙️ Análise Detalhada: {municipio_selecionado}")
    
    # Buscar dados do município
    dados_municipio, col_municipio = buscar_municipio_avancado(df, municipio_selecionado)
    
    if dados_municipio is not None:
        # Identificar colunas importantes
        estado_col = None
        regiao_col = None
        tipo_coleta_col = None
        massa_col = None
        destino_col = None
        
        for col in df.columns:
            col_lower = str(col).lower()
            if 'estado' in col_lower or 'col_3' in str(col):
                estado_col = col
            elif 'região' in col_lower or 'col_4' in str(col):
                regiao_col = col
            elif 'tipo' in col_lower and 'coleta' in col_lower or 'col_17' in str(col):
                tipo_coleta_col = col
            elif 'massa' in col_lower or 'col_24' in str(col):
                massa_col = col
            elif 'destino' in col_lower or 'col_28' in str(col):
                destino_col = col
        
        # Mostrar informações do município
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.info("**Informações Básicas**")
            st.write(f"**Município:** {dados_municipio[col_municipio]}")
            
            if estado_col and estado_col in dados_municipio:
                st.write(f"**Estado:** {dados_municipio[estado_col]}")
            
            if regiao_col and regiao_col in dados_municipio:
                st.write(f"**Região:** {dados_municipio[regiao_col]}")
        
        with col2:
            st.info("**Coleta de Resíduos**")
            if massa_col and massa_col in dados_municipio:
                massa = dados_municipio[massa_col]
                st.write(f"**Massa coletada:** {massa:,.1f} t/ano")
                
                # Tentar encontrar população para calcular per capita
                per_capita = calcular_per_capita(dados_municipio)
                if per_capita:
                    st.write(f"**Per capita estimado:** {per_capita:.1f} kg/hab/ano")
                    st.write(f"**Equivalente diário:** {per_capita/365:.3f} kg/hab/dia")
                else:
                    # Usar média nacional como referência
                    st.write(f"**Per capita (média nacional):** 365.2 kg/hab/ano")
                    st.write(f"**Equivalente diário:** 1.001 kg/hab/dia")
        
        with col3:
            st.info("**Tipo de Coleta**")
            if tipo_coleta_col and tipo_coleta_col in dados_municipio:
                st.write(f"**Tipo:** {dados_municipio[tipo_coleta_col]}")
        
        with col4:
            st.info("**Destino Final**")
            if destino_col and destino_col in dados_municipio:
                destino = dados_municipio[destino_col]
                st.write(f"**Destino:** {destino}")
                
                # Classificar destino
                destinos_adequados = ['Aterro Sanitário', 'Compostagem', 'Reciclagem', 'Triagem']
                if any(adequado in str(destino) for adequado in destinos_adequados):
                    st.success("✅ Destino adequado")
                else:
                    st.warning("⚠️ Destino pode ser inadequado")
        
        # Simulação de cenários
        st.header(f"🔮 Simulação de Cenários - {cenario}")
        
        # Estimativa de massa base
        if massa_col and massa_col in dados_municipio:
            massa_anual = dados_municipio[massa_col]
            
            # Parâmetros por cenário
            if cenario == "Cenário Atual":
                fracoes = {
                    'Aterro': 0.92,
                    'Reciclagem': 0.05,
                    'Compostagem': 0.03,
                    'Emissões (t CO₂eq)': massa_anual * 0.9,
                    'Redução vs Atual': '0%'
                }
                cor = '#e74c3c'
            elif cenario == "Cenário de Economia Circular":
                fracoes = {
                    'Aterro': 0.50,
                    'Reciclagem': 0.20,
                    'Compostagem': 0.30,
                    'Emissões (t CO₂eq)': massa_anual * 0.5,
                    'Redução vs Atual': '44%'
                }
                cor = '#3498db'
            else:  # Cenário Otimizado
                fracoes = {
                    'Aterro': 0.30,
                    'Reciclagem': 0.30,
                    'Compostagem': 0.40,
                    'Emissões (t CO₂eq)': massa_anual * 0.3,
                    'Redução vs Atual': '67%'
                }
                cor = '#2ecc71'
            
            # Gráfico de destinação
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
            
            # Gráfico de pizza
            labels = ['Aterro', 'Reciclagem', 'Compostagem']
            sizes = [fracoes['Aterro'] * 100, fracoes['Reciclagem'] * 100, fracoes['Compostagem'] * 100]
            colors = ['#e74c3c', '#3498db', '#2ecc71']
            
            ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax1.set_title(f'Destinação Final - {cenario}')
            
            # Gráfico de emissões
            cenarios = ['Atual', 'Econ. Circular', 'Otimizado']
            emissões = [massa_anual * 0.9, massa_anual * 0.5, massa_anual * 0.3]
            
            bars = ax2.bar(cenarios, emissões, color=['#e74c3c', '#3498db', '#2ecc71'])
            ax2.set_ylabel('Emissões de CO₂eq (t/ano)')
            ax2.set_title('Comparativo de Emissões de GEE')
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
                st.info("**Resultados da Simulação**")
                st.write(f"**Massa anual:** {massa_anual:,.0f} t")
                st.write(f"**Emissões estimadas:** {fracoes['Emissões (t CO₂eq)']:,.0f} t CO₂eq/ano")
                
                if fracoes['Redução vs Atual'] != '0%':
                    st.success(f"**Redução de emissões:** {fracoes['Redução vs Atual']}")
                    
                    # Valor econômico do carbono
                    reducao_absoluta = (massa_anual * 0.9) - fracoes['Emissões (t CO₂eq)']
                    valor_carbono = reducao_absoluta * 50  # US$ 50 por tonelada
                    st.success(f"**Valor do carbono evitado:** US$ {valor_carbono:,.0f}/ano")
                    st.success(f"**Em reais:** R$ {valor_carbono * 5:,.0f}/ano")
                
                st.write(f"**Materiais recicláveis:** {massa_anual * fracoes['Reciclagem']:,.0f} t/ano")
                st.write(f"**Compostagem:** {massa_anual * fracoes['Compostagem']:,.0f} t/ano")
    else:
        st.warning(f"Município '{municipio_selecionado}' não encontrado nos dados filtrados.")
        
        # Mostrar municípios disponíveis
        with st.expander("🔍 Ver municípios disponíveis"):
            # Tentar encontrar coluna de municípios
            for col in df.columns:
                if any(term in str(col).lower() for term in ['município', 'municipio', 'cidade']):
                    municipios = df[col].unique()
                    st.write(f"**Municípios na coluna '{col}':**")
                    for mun in sorted(municipios)[:50]:  # Mostrar primeiros 50
                        st.write(f"- {mun}")
                    break
    
    # Análise comparativa por estado
    st.header("📈 Análise Comparativa por Estado")
    
    # Identificar coluna de estado
    estado_col = None
    for col in df.columns:
        if 'estado' in str(col).lower() or 'col_3' in str(col):
            estado_col = col
            break
    
    if estado_col:
        # Estatísticas por estado
        if massa_col:
            # Agrupar por estado
            estatisticas_estado = df.groupby(estado_col).agg(
                Total_Municipios=(massa_col, 'count'),
                Massa_Total=(massa_col, 'sum'),
                Massa_Media=(massa_col, 'mean')
            ).reset_index()
            
            # Ordenar por massa total
            estatisticas_estado = estatisticas_estado.sort_values('Massa_Total', ascending=False)
            
            # Mostrar tabela
            st.dataframe(
                estatisticas_estado.head(10),
                column_config={
                    estado_col: "Estado",
                    "Total_Municipios": "Nº Municípios",
                    "Massa_Total": st.column_config.NumberColumn(
                        "Massa Total (t)",
                        format="%.1f"
                    ),
                    "Massa_Media": st.column_config.NumberColumn(
                        "Média por Município (t)",
                        format="%.1f"
                    )
                }
            )
            
            # Gráfico de barras
            fig, ax = plt.subplots(figsize=(10, 6))
            top_10 = estatisticas_estado.head(10)
            bars = ax.bar(top_10[estado_col], top_10['Massa_Total'], color='#3498db')
            
            ax.set_ylabel('Massa Total Coletada (t)')
            ax.set_title('Top 10 Estados por Massa de Resíduos Coletados')
            ax.tick_params(axis='x', rotation=45)
            ax.grid(axis='y', alpha=0.3)
            
            # Adicionar valores nas barras
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2, height,
                       f'{height:,.0f}', ha='center', va='bottom', fontsize=9)
            
            plt.tight_layout()
            st.pyplot(fig)
    
    # Comparação com média nacional
    st.header("📊 Comparação com Média Nacional")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Média Nacional Per Capita",
            "365.2 kg/hab/ano",
            delta="Referência SINISA 2023"
        )
    
    with col2:
        st.metric(
            "Equivalente Diário",
            "1.001 kg/hab/dia",
            delta="Conversão anual/diária"
        )
    
    with col3:
        # Calcular massa total nacional do dataset
        if massa_col:
            massa_total_nacional = df[massa_col].sum()
            st.metric(
                "Massa Total no Dataset",
                f"{massa_total_nacional:,.0f} t",
                delta="Soma de todos os registros"
            )
    
    # Informações sobre o dataset
    with st.expander("📋 Sobre os Dados e Metodologia"):
        st.write("""
        **Fonte dos dados:** Sistema Nacional de Informações sobre Saneamento (SINISA) 2023
        
        **Filtro aplicado:** Apenas registros com valor 'Sim' na primeira coluna (Coluna A)
        
        **Colunas principais utilizadas:**
        - Estado: Coluna D (Col_3)
        - Região: Coluna E (Col_4)
        - Tipo de Coleta: Coluna R (Col_17)
        - Massa Total: Coluna Y (Col_24)
        - Destino: Coluna AC (Col_28)
        
        **Método de cálculo per capita:**
        - Massa em toneladas convertida para kg (× 1000)
        - Dividida pela população do município/estado
        - Média nacional: 365.21 kg/hab/ano
        
        **Cenários de simulação:**
        1. **Cenário Atual:** Baseado em médias brasileiras atuais
        2. **Cenário Economia Circular:** Aumento da reciclagem e compostagem
        3. **Cenário Otimizado:** Máxima recuperação de materiais
        
        **Fatores de emissão:** Baseados em metodologias IPCC para resíduos sólidos
        """)

if __name__ == "__main__":
    main()
