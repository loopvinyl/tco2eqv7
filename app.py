import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import BytesIO
import matplotlib.pyplot as plt

# Configuração da página
st.set_page_config(page_title="Análise RSU Brasil", layout="wide")

st.title("📊 Análise de Resíduos Sólidos Urbanos - Dados SINISA 2023")
st.markdown("Análise de dados municipais brasileiros para simulação de emissões de GEE")

# URL do arquivo Excel
EXCEL_URL = "https://github.com/loopvinyl/tco2eqv7/raw/main/rsuBrasil.xlsx"

@st.cache_data
def carregar_dados():
    """Carrega os dados do Excel do GitHub"""
    try:
        response = requests.get(EXCEL_URL, timeout=30)
        response.raise_for_status()
        excel_file = BytesIO(response.content)
        return excel_file
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {str(e)}")
        return None

def analisar_estrutura(excel_file):
    """Analisa a estrutura do arquivo Excel"""
    try:
        xls = pd.ExcelFile(excel_file)
        return xls
    except Exception as e:
        st.error(f"Erro ao ler Excel: {str(e)}")
        return None

def extrair_parametros_municipio(df, municipio_nome):
    """Extrai parâmetros específicos de um município"""
    # Procurar município
    municipio_cols = [col for col in df.columns if 'município' in str(col).lower() or 'municipio' in str(col).lower()]
    
    if not municipio_cols:
        return None
    
    municipio_col = municipio_cols[0]
    
    # Buscar município (case insensitive)
    mask = df[municipio_col].astype(str).str.lower() == municipio_nome.lower()
    dados = df[mask]
    
    if len(dados) == 0:
        return None
    
    return dados.iloc[0]

def calcular_emissoes(dados_municipio):
    """Calcula emissões de GEE com base nos dados do município"""
    # Esta é uma função simplificada - será expandida
    resultados = {
        'municipio': dados_municipio.get('Município', 'Desconhecido'),
        'populacao': dados_municipio.get('POP_TOT', 0),
        'massa_coletada': dados_municipio.get('Massa_Total_Coletada', 0),
        'per_capita': 0,
        'emissoes_estimadas': 0
    }
    
    if resultados['populacao'] > 0 and resultados['massa_coletada'] > 0:
        resultados['per_capita'] = (resultados['massa_coletada'] * 1000) / resultados['populacao']
        # Estimativa simplificada de emissões (kg CO2eq/ano)
        resultados['emissoes_estimadas'] = resultados['massa_coletada'] * 500  # Fator estimativo
    
    return resultados

def main():
    # Barra lateral para configurações
    with st.sidebar:
        st.header("⚙️ Configurações")
        municipio_selecionado = st.selectbox(
            "Selecione o município para análise:",
            ["MANAUS", "ARIQUEMES", "BOCA DO ACRE", "OUTRO"]
        )
        
        if municipio_selecionado == "OUTRO":
            municipio_selecionado = st.text_input("Digite o nome do município:")
        
        st.markdown("---")
        st.header("📈 Cenários")
        cenario = st.radio(
            "Selecione o cenário de simulação:",
            ["Cenário Atual", "Cenário de Economia Circular", "Cenário Otimizado"]
        )
    
    # Carregar dados
    with st.spinner("Carregando dados do SINISA 2023..."):
        excel_file = carregar_dados()
        
        if excel_file is None:
            st.error("Não foi possível carregar os dados. Verifique a conexão.")
            return
        
        xls = analisar_estrutura(excel_file)
        
        if xls is None:
            return
    
    # Mostrar abas disponíveis
    st.subheader("📁 Estrutura do Arquivo")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Número de abas:** {len(xls.sheet_names)}")
        st.write("**Abas disponíveis:**")
        for sheet in xls.sheet_names:
            st.write(f"- {sheet}")
    
    # Carregar aba principal
    try:
        df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
        
        with col2:
            st.write(f"**Registros na aba principal:** {len(df)}")
            st.write(f"**Colunas na aba principal:** {len(df.columns)}")
        
        # Mostrar prévia dos dados
        with st.expander("🔍 Visualizar amostra dos dados"):
            st.dataframe(df.head(10))
        
        # Estatísticas básicas
        st.subheader("📊 Estatísticas Básicas")
        
        # Identificar colunas numéricas
        colunas_numericas = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if colunas_numericas:
            stats_cols = st.columns(3)
            with stats_cols[0]:
                st.metric("Total de municípios", len(df))
            with stats_cols[1]:
                if 'POP_TOT' in df.columns:
                    st.metric("População média", f"{df['POP_TOT'].mean():,.0f}")
            with stats_cols[2]:
                mass_cols = [col for col in df.columns if 'massa' in str(col).lower()]
                if mass_cols:
                    st.metric("Massa total coletada", f"{df[mass_cols[0]].sum():,.0f} t")
        
        # Análise por município selecionado
        if municipio_selecionado and municipio_selecionado != "OUTRO":
            st.subheader(f"🏙️ Análise para {municipio_selecionado}")
            
            dados_municipio = extrair_parametros_municipio(df, municipio_selecionado)
            
            if dados_municipio is not None:
                # Mostrar dados do município
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.info("**Informações Básicas**")
                    st.write(f"Município: {municipio_selecionado}")
                    if 'UF' in dados_municipio:
                        st.write(f"UF: {dados_municipio['UF']}")
                    if 'POP_TOT' in dados_municipio:
                        st.write(f"População: {dados_municipio['POP_TOT']:,.0f}")
                
                with col2:
                    st.info("**Coleta de Resíduos**")
                    mass_cols = [col for col in df.columns if 'massa' in str(col).lower()]
                    if mass_cols and mass_cols[0] in dados_municipio:
                        massa = dados_municipio[mass_cols[0]]
                        st.write(f"Massa coletada: {massa:,.1f} t/ano")
                        if dados_municipio.get('POP_TOT', 0) > 0:
                            per_capita = (massa * 1000) / dados_municipio['POP_TOT']
                            st.write(f"Per capita: {per_capita:.1f} kg/hab/ano")
                
                with col3:
                    st.info("**Destinação**")
                    dest_cols = [col for col in df.columns if any(term in str(col).lower() 
                              for term in ['destino', 'aterro', 'lixão'])]
                    if dest_cols and dest_cols[0] in dados_municipio:
                        st.write(f"Destinação: {dados_municipio[dest_cols[0]]}")
                
                # Simulação de cenários
                st.subheader(f"🔮 Simulação - {cenario}")
                
                # Parâmetros base
                if 'POP_TOT' in dados_municipio and mass_cols and mass_cols[0] in dados_municipio:
                    populacao = dados_municipio['POP_TOT']
                    massa_anual = dados_municipio[mass_cols[0]]
                    
                    # Cálculos base
                    per_capita_diario = (massa_anual * 1000) / populacao / 365
                    massa_diaria = massa_anual * 1000 / 365
                    
                    # Estimativas por cenário
                    if cenario == "Cenário Atual":
                        reciclagem = 0.05  # 5%
                        compostagem = 0.03  # 3%
                        aterro = 0.92  # 92%
                    elif cenario == "Cenário de Economia Circular":
                        reciclagem = 0.20  # 20%
                        compostagem = 0.30  # 30%
                        aterro = 0.50  # 50%
                    else:  # Cenário Otimizado
                        reciclagem = 0.30  # 30%
                        compostagem = 0.40  # 40%
                        aterro = 0.30  # 30%
                    
                    # Gráfico de distribuição
                    fig, ax = plt.subplots(figsize=(8, 6))
                    destinos = ['Reciclagem', 'Compostagem', 'Aterro']
                    valores = [reciclagem * 100, compostagem * 100, aterro * 100]
                    cores = ['#2ecc71', '#3498db', '#e74c3c']
                    
                    ax.pie(valores, labels=destinos, colors=cores, autopct='%1.1f%%', startangle=90)
                    ax.set_title(f'Destinação Final - {cenario}')
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.pyplot(fig)
                    
                    with col2:
                        st.info("**Resultados Estimados**")
                        st.write(f"Massa diária: {massa_diaria:,.0f} kg/dia")
                        st.write(f"Per capita: {per_capita_diario:.3f} kg/hab/dia")
                        
                        # Estimativa de emissões evitadas
                        reducao_emissoes = (0.92 - aterro) * massa_anual * 0.5  # Fator simplificado
                        st.write(f"Redução estimada de GEE: {reducao_emissoes:.1f} t CO₂eq/ano")
            else:
                st.warning(f"Município '{municipio_selecionado}' não encontrado nos dados.")
        
        # Análise comparativa
        st.subheader("📈 Análise Comparativa por Estado")
        
        if 'UF' in df.columns:
            estados = df['UF'].unique()
            estado_selecionado = st.selectbox("Selecione um estado para análise:", estados)
            
            if estado_selecionado:
                df_estado = df[df['UF'] == estado_selecionado]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Estado: {estado_selecionado}**")
                    st.write(f"Número de municípios: {len(df_estado)}")
                    
                    if 'POP_TOT' in df_estado.columns:
                        st.write(f"População total: {df_estado['POP_TOT'].sum():,.0f}")
                
                with col2:
                    # Calcular per capita médio do estado
                    if 'POP_TOT' in df_estado.columns:
                        mass_cols = [col for col in df.columns if 'massa' in str(col).lower()]
                        if mass_cols:
                            massa_total = df_estado[mass_cols[0]].sum()
                            populacao_total = df_estado['POP_TOT'].sum()
                            
                            if populacao_total > 0:
                                per_capita_estado = (massa_total * 1000) / populacao_total
                                st.metric("Per capita estadual", f"{per_capita_estado:.1f} kg/hab/ano")
        
        # Download de dados processados
        st.subheader("💾 Exportar Dados")
        
        if st.button("Exportar dados processados para CSV"):
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Baixar CSV",
                data=csv,
                file_name="dados_rsu_brasil.csv",
                mime="text/csv"
            )
    
    except Exception as e:
        st.error(f"Erro ao processar os dados: {str(e)}")
        st.info("Dica: Verifique se a estrutura do arquivo Excel está correta.")

if __name__ == "__main__":
    main()
