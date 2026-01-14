import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import BytesIO
import matplotlib.pyplot as plt
import unicodedata

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

def normalizar_texto(texto):
    """Normaliza texto removendo acentos e convertendo para minúsculas"""
    if pd.isna(texto):
        return ""
    texto = str(texto)
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto.lower().strip()

def encontrar_municipios(df, municipio_col):
    """Encontra todos os municípios disponíveis na base"""
    if municipio_col in df.columns:
        municipios = df[municipio_col].dropna().unique()
        return sorted([str(m) for m in municipios if str(m).strip() != ''])
    return []

def buscar_municipio(df, municipio_nome, municipio_col):
    """Busca um município com diferentes variações de nome"""
    if municipio_col not in df.columns:
        return None
    
    # Tentativas de busca
    municipio_normalizado = normalizar_texto(municipio_nome)
    
    # Tentativa 1: Busca exata (case insensitive)
    mask_exata = df[municipio_col].astype(str).str.lower() == municipio_nome.lower()
    
    # Tentativa 2: Busca por parte do nome
    mask_contem = df[municipio_col].astype(str).str.lower().str.contains(municipio_nome.lower())
    
    # Tentativa 3: Busca normalizada (sem acentos)
    df['municipio_normalizado'] = df[municipio_col].apply(normalizar_texto)
    mask_normalizada = df['municipio_normalizado'].str.contains(municipio_normalizado)
    
    # Combinar resultados
    mask_final = mask_exata | mask_contem | mask_normalizada
    resultados = df[mask_final]
    
    if len(resultados) > 0:
        return resultados.iloc[0]
    
    return None

def main():
    # Barra lateral para configurações
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        # Carregar dados primeiro
        excel_file = carregar_dados()
        
        if excel_file is not None:
            xls = pd.ExcelFile(excel_file)
            df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
            
            # Identificar coluna de municípios
            municipio_col = None
            for col in df.columns:
                if 'município' in str(col).lower() or 'municipio' in str(col).lower() or 'nome' in str(col).lower():
                    municipio_col = col
                    break
            
            if municipio_col:
                # Municípios de interesse
                municipios_interesse = [
                    "MANAUS", "RIBEIRÃO PRETO", "SERTÃOZINHO", "SÃO JOSÉ DO RIO PRETO",
                    "ARIQUEMES", "BOCA DO ACRE"
                ]
                
                # Encontrar os municípios na base
                municipios_disponiveis = []
                for municipio in municipios_interesse:
                    if buscar_municipio(df, municipio, municipio_col) is not None:
                        municipios_disponiveis.append(municipio)
                
                # Adicionar opção de buscar outros
                municipios_disponiveis.append("OUTRO")
                
                municipio_selecionado = st.selectbox(
                    "Selecione o município para análise:",
                    municipios_disponiveis
                )
                
                if municipio_selecionado == "OUTRO":
                    # Listar todos os municípios disponíveis
                    todos_municipios = encontrar_municipios(df, municipio_col)
                    municipio_selecionado = st.selectbox(
                        "Selecione um município da lista completa:",
                        todos_municipios
                    )
            else:
                st.warning("Coluna de municípios não identificada")
                municipio_selecionado = st.text_input("Digite o nome do município:")
        
        st.markdown("---")
        st.header("📈 Cenários")
        cenario = st.radio(
            "Selecione o cenário de simulação:",
            ["Cenário Atual", "Cenário de Economia Circular", "Cenário Otimizado"]
        )
    
    # Carregar e mostrar dados
    if excel_file is None:
        st.error("Não foi possível carregar os dados. Verifique a conexão.")
        return
    
    xls = pd.ExcelFile(excel_file)
    
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
        
        # Identificar colunas importantes
        colunas_info = []
        for pattern in ['pop', 'massa', 'coleta', 'domicilio', 'habitante']:
            cols = [col for col in df.columns if pattern in str(col).lower()]
            colunas_info.extend(cols)
        
        if colunas_info:
            st.write("**Colunas identificadas:**")
            cols_display = st.columns(3)
            for i, col in enumerate(colunas_info[:9]):
                with cols_display[i % 3]:
                    st.write(f"• {col}")
        
        # Análise por município selecionado
        if 'municipio_selecionado' in locals():
            st.subheader(f"🏙️ Análise para {municipio_selecionado}")
            
            # Identificar coluna de municípios
            municipio_col = None
            for col in df.columns:
                if 'município' in str(col).lower() or 'municipio' in str(col).lower() or 'nome' in str(col).lower():
                    municipio_col = col
                    break
            
            if municipio_col:
                dados_municipio = buscar_municipio(df, municipio_selecionado, municipio_col)
                
                if dados_municipio is not None:
                    # Mostrar dados do município
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.info("**Informações Básicas**")
                        st.write(f"Município: {municipio_selecionado}")
                        
                        # Procurar coluna de UF
                        uf_cols = [col for col in df.columns if 'uf' == str(col).lower() or 'estado' == str(col).lower()]
                        if uf_cols and uf_cols[0] in dados_municipio:
                            st.write(f"UF: {dados_municipio[uf_cols[0]]}")
                        
                        # Procurar coluna de população
                        pop_cols = [col for col in df.columns if 'pop' in str(col).lower()]
                        if pop_cols and pop_cols[0] in dados_municipio:
                            populacao = dados_municipio[pop_cols[0]]
                            st.write(f"População: {populacao:,.0f}")
                    
                    with col2:
                        st.info("**Coleta de Resíduos**")
                        # Procurar colunas de massa
                        mass_cols = [col for col in df.columns if 'massa' in str(col).lower()]
                        if not mass_cols:
                            mass_cols = [col for col in df.columns if 'ton' in str(col).lower()]
                        
                        if mass_cols and mass_cols[0] in dados_municipio:
                            massa = dados_municipio[mass_cols[0]]
                            st.write(f"Massa coletada: {massa:,.1f} t/ano")
                            
                            # Calcular per capita se tiver população
                            if 'populacao' in locals() and populacao > 0:
                                per_capita = (massa * 1000) / populacao
                                st.write(f"Per capita: {per_capita:.1f} kg/hab/ano")
                                st.write(f"Per capita diário: {per_capita/365:.3f} kg/hab/dia")
                    
                    with col3:
                        st.info("**Destinação e Tecnologias**")
                        # Procurar informações de destinação
                        dest_cols = [col for col in df.columns if any(term in str(col).lower() 
                                  for term in ['destino', 'aterro', 'lixão', 'triagem', 'compostagem'])]
                        
                        if dest_cols:
                            for col in dest_cols[:3]:  # Mostrar até 3 colunas
                                if col in dados_municipio and not pd.isna(dados_municipio[col]):
                                    valor = dados_municipio[col]
                                    if valor != 0:
                                        st.write(f"{col}: {valor}")
                    
                    # Simulação de cenários
                    st.subheader(f"🔮 Simulação - {cenario}")
                    
                    # Verificar se temos dados suficientes
                    if 'populacao' in locals() and populacao > 0 and 'massa' in locals():
                        # Parâmetros base
                        massa_anual = massa
                        
                        # Cálculos base
                        per_capita_diario = (massa_anual * 1000) / populacao / 365
                        massa_diaria = massa_anual * 1000 / 365
                        
                        # Estimativas por cenário
                        if cenario == "Cenário Atual":
                            reciclagem = 0.05  # 5%
                            compostagem = 0.03  # 3%
                            aterro = 0.92  # 92%
                            economia_carbono = 0
                        elif cenario == "Cenário de Economia Circular":
                            reciclagem = 0.20  # 20%
                            compostagem = 0.30  # 30%
                            aterro = 0.50  # 50%
                            economia_carbono = massa_anual * 0.42 * 0.5  # Redução estimada
                        else:  # Cenário Otimizado
                            reciclagem = 0.30  # 30%
                            compostagem = 0.40  # 40%
                            aterro = 0.30  # 30%
                            economia_carbono = massa_anual * 0.62 * 0.5  # Redução estimada
                        
                        # Gráfico de distribuição
                        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
                        
                        # Gráfico de pizza
                        destinos = ['Reciclagem', 'Compostagem', 'Aterro']
                        valores = [reciclagem * 100, compostagem * 100, aterro * 100]
                        cores = ['#2ecc71', '#3498db', '#e74c3c']
                        
                        ax1.pie(valores, labels=destinos, colors=cores, autopct='%1.1f%%', startangle=90)
                        ax1.set_title(f'Destinação Final - {cenario}')
                        
                        # Gráfico de barras comparativo
                        cenarios = ['Atual', 'Econ. Circular', 'Otimizado']
                        emissoes = [massa_anual * 0.9, massa_anual * 0.5, massa_anual * 0.3]  # Valores ilustrativos
                        
                        ax2.bar(cenarios, emissoes, color=['#e74c3c', '#3498db', '#2ecc71'])
                        ax2.set_ylabel('Emissões de CO₂eq (t/ano)')
                        ax2.set_title('Comparativo de Emissões por Cenário')
                        ax2.grid(axis='y', alpha=0.3)
                        
                        plt.tight_layout()
                        
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.pyplot(fig)
                        
                        with col2:
                            st.info("**Resultados Estimados**")
                            st.write(f"Massa diária: {massa_diaria:,.0f} kg/dia")
                            st.write(f"Per capita: {per_capita_diario:.3f} kg/hab/dia")
                            st.write(f"Massa anual: {massa_anual:,.0f} t/ano")
                            
                            if economia_carbono > 0:
                                st.success(f"Redução de GEE: {economia_carbono:,.1f} t CO₂eq/ano")
                                
                                # Valor econômico estimado (US$ 50 por tonelada de CO₂)
                                valor_carbono = economia_carbono * 50
                                st.success(f"Valor do carbono: US$ {valor_carbono:,.0f}/ano")
                else:
                    st.warning(f"Município '{municipio_selecionado}' não encontrado nos dados.")
                    
                    # Sugerir municípios similares
                    if municipio_col:
                        todos_municipios = encontrar_municipios(df, municipio_col)
                        similares = [m for m in todos_municipios if municipio_selecionado.lower() in m.lower()]
                        
                        if similares:
                            st.write("**Sugestões de municípios similares:**")
                            for similar in similares[:5]:
                                st.write(f"- {similar}")
        
        # Análise comparativa por estado
        st.subheader("📈 Análise Comparativa por Estado")
        
        # Identificar coluna de UF
        uf_cols = [col for col in df.columns if 'uf' == str(col).lower() or 'estado' == str(col).lower()]
        
        if uf_cols:
            uf_col = uf_cols[0]
            estados = sorted([estado for estado in df[uf_col].dropna().unique() if str(estado).strip() != ''])
            
            if estados:
                estado_selecionado = st.selectbox("Selecione um estado para análise:", estados)
                
                if estado_selecionado:
                    df_estado = df[df[uf_col] == estado_selecionado]
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write(f"**Estado: {estado_selecionado}**")
                        st.write(f"Número de municípios: {len(df_estado)}")
                    
                    with col2:
                        # Calcular população total do estado
                        pop_cols = [col for col in df.columns if 'pop' in str(col).lower()]
                        if pop_cols:
                            pop_total = df_estado[pop_cols[0]].sum()
                            st.write(f"População total: {pop_total:,.0f}")
                    
                    with col3:
                        # Calcular massa total do estado
                        mass_cols = [col for col in df.columns if 'massa' in str(col).lower()]
                        if mass_cols:
                            massa_total = df_estado[mass_cols[0]].sum()
                            st.write(f"Massa total coletada: {massa_total:,.0f} t/ano")
                            
                            # Calcular per capita estadual
                            if 'pop_total' in locals() and pop_total > 0:
                                per_capita_estado = (massa_total * 1000) / pop_total
                                st.metric("Per capita estadual", f"{per_capita_estado:.1f} kg/hab/ano")
    
    except Exception as e:
        st.error(f"Erro ao processar os dados: {str(e)}")
        st.info("Tentando uma abordagem alternativa...")
        
        # Tentar carregar outra aba
        try:
            for sheet_name in xls.sheet_names[1:]:
                st.write(f"Tentando aba: {sheet_name}")
                df_alt = pd.read_excel(xls, sheet_name=sheet_name)
                st.write(f"Dimensões: {df_alt.shape}")
                st.dataframe(df_alt.head(3))
        except:
            st.error("Não foi possível processar nenhuma das abas.")

if __name__ == "__main__":
    main()
