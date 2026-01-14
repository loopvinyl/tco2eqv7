import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import BytesIO
import matplotlib.pyplot as plt
import re

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
        
        # Carregar a aba principal SEM cabeçalho primeiro para análise
        df_raw = pd.read_excel(xls, sheet_name="Manejo_Coleta_e_Destinação", header=None)
        
        st.write(f"📐 **Arquivo bruto carregado:** {df_raw.shape[0]} linhas × {df_raw.shape[1]} colunas")
        
        # Encontrar a linha onde começa o cabeçalho real
        # Procurar por 'Sim' na primeira coluna
        linha_comeco_dados = None
        for i in range(min(20, len(df_raw))):
            if str(df_raw.iloc[i, 0]).strip() == 'Sim':
                linha_comeco_dados = i
                break
        
        if linha_comeco_dados is None:
            # Se não encontrou, tentar encontrar a linha que tem os nomes das colunas
            for i in range(min(10, len(df_raw))):
                # Verificar se esta linha tem valores como "Col_3", "Col_4", etc.
                linha_vals = df_raw.iloc[i].astype(str).str.lower().values
                if any('col_' in str(v) for v in linha_vals):
                    linha_comeco_dados = i + 1  # Dados começam na próxima linha
                    break
        
        if linha_comeco_dados is None:
            # Último recurso: usar linha 0 como cabeçalho
            df = pd.read_excel(xls, sheet_name="Manejo_Coleta_e_Destinação")
            st.warning("Usando linha 0 como cabeçalho (não foi possível identificar automaticamente)")
        else:
            # A linha anterior deve ser o cabeçalho
            linha_cabecalho = linha_comeco_dados - 1
            df = pd.read_excel(xls, sheet_name="Manejo_Coleta_e_Destinação", header=linha_cabecalho)
            st.info(f"✅ Usando linha {linha_cabecalho + 1} como cabeçalho")
        
        # Aplicar filtro: apenas registros onde a primeira coluna = 'Sim'
        primeira_coluna = df.columns[0]
        df_filtrado = df[df[primeira_coluna] == 'Sim'].copy()
        
        st.success(f"✅ Dados filtrados com sucesso! {len(df_filtrado)} registros válidos (com 'Sim').")
        
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
    
    st.write("🔍 **Identificando colunas importantes...**")
    
    # Mostrar todas as colunas para debug
    st.write("**Todas as colunas disponíveis:**")
    for i, col in enumerate(df.columns):
        st.write(f"{i}: {col}")
    
    # Mapear nomes de coluna para tipos - BUSCA ESPECÍFICA PARA COLUNA DE MUNICÍPIOS
    for col_name in df.columns:
        col_str = str(col_name).lower()
        
        # 1. PRIMEIRO: Buscar especificamente por municípios
        if 'município' in col_str or 'municipio' in col_str:
            colunas['Município'] = col_name
            st.success(f"✅ Coluna de Município identificada: '{col_name}'")
        
        # Coluna de Estado (Col_3)
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
            st.success(f"✅ Coluna de Massa identificada: '{col_name}'")
        
        # Coluna de Destino (Col_28)
        elif 'col_28' in col_str or 'destino' in col_str:
            colunas['Destino'] = col_name
    
    # Se não encontrou a coluna de municípios pelo nome, procurar pelo conteúdo
    if 'Município' not in colunas:
        st.warning("⚠️ Coluna de Município não encontrada pelo nome. Buscando pelo conteúdo...")
        
        for col in df.columns:
            try:
                # Verificar se a coluna tem valores que parecem nomes de municípios
                amostra = df[col].dropna().astype(str).head(10)
                
                # Contar quantos valores parecem ser nomes de municípios
                contagem_municipios = 0
                for v in amostra:
                    v_str = str(v).strip()
                    # Critérios para ser um município:
                    # 1. Tem mais de 3 caracteres
                    # 2. Não é numérico
                    # 3. Pode conter espaços, hífens, etc.
                    # 4. Não contém palavras como "col_", "total", "massa"
                    if (len(v_str) > 3 and 
                        not v_str.replace(',', '').replace('.', '').isdigit() and
                        not any(term in v_str.lower() for term in ['col_', 'total', 'massa', 'destino', 'coleta'])):
                        contagem_municipios += 1
                
                # Se pelo menos 70% dos valores parecem ser municípios
                if len(amostra) > 0 and contagem_municipios / len(amostra) > 0.7:
                    colunas['Município'] = col
                    st.success(f"✅ Coluna de Município identificada pelo conteúdo: '{col}'")
                    break
                    
            except Exception as e:
                continue
    
    # Se ainda não encontrou, usar posições conhecidas (base 0)
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
    
    # Para município, se ainda não encontrou, tentar coluna 1 ou 2 (B ou C)
    if 'Município' not in colunas:
        if len(df.columns) > 1:
            # Tentar coluna 1 (B) - muitas vezes é a coluna de municípios
            colunas['Município'] = df.columns[1]
            st.info(f"⚠️ Usando coluna {df.columns[1]} como Município (suposição)")
    
    return colunas

def buscar_municipio_em_todas_colunas(df, municipio_nome):
    """Busca um município em TODAS as colunas do dataframe"""
    resultados = []
    
    # Normalizar o nome do município para busca
    def normalizar(nome):
        if pd.isna(nome):
            return ""
        nome = str(nome).lower()
        # Remover acentos
        substituicoes = {'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a',
                        'é': 'e', 'è': 'e', 'ê': 'e',
                        'í': 'i', 'ì': 'i', 'î': 'i',
                        'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o',
                        'ú': 'u', 'ù': 'u', 'û': 'u',
                        'ç': 'c', 'ñ': 'n'}
        for orig, subst in substituicoes.items():
            nome = nome.replace(orig, subst)
        return nome.strip()
    
    municipio_busca = normalizar(municipio_nome)
    
    for col in df.columns:
        try:
            # Criar versão normalizada da coluna para busca
            col_normalizada = df[col].apply(normalizar)
            
            # Buscar o município
            mask = col_normalizada.str.contains(municipio_busca, na=False)
            
            if mask.any():
                qtd = mask.sum()
                exemplos = df.loc[mask, col].head(3).tolist()
                resultados.append({
                    'coluna': col,
                    'quantidade': qtd,
                    'exemplos': exemplos,
                    'dados': df[mask].iloc[0] if qtd > 0 else None
                })
        except:
            continue
    
    return resultados

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
        st.header("🔧 Modo de Operação")
        
        modo_debug = st.checkbox("Modo Debug (mostrar detalhes técnicos)", value=True)
        
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
    
    # Modo Debug - Mostrar informações detalhadas
    if modo_debug:
        with st.expander("🔍 DEBUG - Informações Detalhadas do DataFrame"):
            st.write("**📋 Colunas identificadas automaticamente:**")
            for tipo, nome_coluna in colunas.items():
                st.write(f"• **{tipo}:** `{nome_coluna}`")
            
            st.write("\n**📊 Primeiras 10 linhas do dataframe:**")
            st.dataframe(df.head(10))
            
            st.write("\n**🔤 Amostra de valores por coluna:**")
            for col in df.columns[:10]:  # Mostrar apenas 10 colunas
                st.write(f"**{col}:** {df[col].dropna().unique()[:5].tolist()}")
    
    # Análise do município selecionado
    st.header(f"🏙️ Análise Detalhada: {municipio_selecionado}")
    
    # Buscar o município em TODAS as colunas se necessário
    resultados_busca = buscar_municipio_em_todas_colunas(df, municipio_selecionado)
    
    if resultados_busca:
        st.success(f"✅ Município encontrado em {len(resultados_busca)} coluna(s)!")
        
        # Mostrar onde foi encontrado
        for resultado in resultados_busca:
            st.info(f"**Coluna:** `{resultado['coluna']}` - {resultado['quantidade']} ocorrência(s)")
            st.write(f"Exemplos: {resultado['exemplos']}")
        
        # Usar o primeiro resultado encontrado
        dados_municipio = resultados_busca[0]['dados']
        
        if dados_municipio is not None:
            # Atualizar a coluna de municípios se necessário
            if 'Município' not in colunas or colunas['Município'] != resultados_busca[0]['coluna']:
                colunas['Município'] = resultados_busca[0]['coluna']
                st.success(f"✅ Atualizando coluna de Município para: `{colunas['Município']}`")
            
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
                    if pd.notna(massa) and massa != 0:
                        st.write(f"**Massa Coletada:** {massa:,.1f} toneladas/ano")
                        
                        # Estimativa per capita (usando média nacional como referência)
                        st.write(f"**Per capita (média nacional):** 365 kg/hab/ano")
                        st.write(f"**Equivalente diário:** 1.0 kg/hab/dia")
                        
                        # População estimada (baseada na massa e média nacional)
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
                        st.warning("Massa não informada ou zerada para este município")
                else:
                    st.error("Coluna de massa não identificada")
        else:
            st.warning("Encontrado, mas não foi possível recuperar os dados completos.")
    else:
        st.warning(f"⚠️ Município '{municipio_selecionado}' não encontrado em nenhuma coluna.")
        
        if modo_debug:
            with st.expander("🔍 DEBUG - Tentando entender o problema"):
                st.write("**Procurando por termos similares em todas as colunas...**")
                
                # Normalizar para busca
                def normalizar_simples(nome):
                    nome = str(nome).lower()
                    substituicoes = {'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a',
                                   'é': 'e', 'è': 'e', 'ê': 'e',
                                   'í': 'i', 'ì': 'i', 'î': 'i',
                                   'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o',
                                   'ú': 'u', 'ù': 'u', 'û': 'u', 'ç': 'c'}
                    for orig, subst in substituicoes.items():
                        nome = nome.replace(orig, subst)
                    return nome
                
                municipio_busca = normalizar_simples(municipio_selecionado)
                
                # Procurar por partes do nome
                for parte in municipio_busca.split():
                    if len(parte) > 3:
                        st.write(f"\n**Buscando por: '{parte}'**")
                        encontrou_algo = False
                        for col in df.columns:
                            try:
                                col_normalizada = df[col].apply(normalizar_simples)
                                mask = col_normalizada.str.contains(parte, na=False)
                                if mask.any():
                                    qtd = mask.sum()
                                    exemplos = df.loc[mask, col].head(3).tolist()
                                    st.write(f"  • Coluna '{col}': {qtd} resultado(s) - Ex: {exemplos}")
                                    encontrou_algo = True
                            except:
                                continue
                        
                        if not encontrou_algo:
                            st.write(f"  Nenhum resultado encontrado para '{parte}'")
    
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
    
    # Resumo final
    st.header("📋 Resumo da Análise")
    
    st.write(f"""
    ## ✅ **O que está funcionando:**
    
    1. **Carregamento de dados:** {len(df):,} registros filtrados (com 'Sim')
    2. **Identificação da massa:** Total de {df[colunas['Massa_Total']].sum():,.0f} t coletadas
    3. **Análise por estado:** {df[colunas['Estado']].nunique()} estados identificados
    4. **Análise por região:** {df[colunas['Região']].nunique()} regiões identificadas
    
    ## 🔧 **Próximos passos necessários:**
    
    1. **Identificar a coluna correta de municípios** - O município não está sendo encontrado
    2. **Verificar se o município existe nos dados** - Pode não ter preenchido o formulário
    3. **Ajustar busca de municípios** - Pode estar com nome diferente no arquivo
    
    ## 💡 **Sugestões:**
    
    - Verificar no modo DEBUG quais colunas têm nomes de municípios
    - Procurar por partes do nome (ex: "Ribeirão" ou "Preto")
    - Verificar se o município está na lista de 'Não' respondentes
    """)

if __name__ == "__main__":
    main()
