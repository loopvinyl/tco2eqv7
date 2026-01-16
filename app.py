import streamlit as st
import pandas as pd
import unicodedata
import numpy as np

# =========================================================
# Configuração da página
# =========================================================
st.set_page_config(
    page_title="Potencial de Compostagem de RSU",
    layout="wide"
)

st.title("🌱 Potencial de Compostagem e Vermicompostagem por Município")
st.markdown("""
Este aplicativo interpreta os **tipos de coleta executada** informados pelos municípios
e avalia o **potencial técnico para compostagem e vermicompostagem**
de resíduos sólidos urbanos.
""")

# =========================================================
# Funções auxiliares
# =========================================================
def formatar_numero_br(valor, casas_decimais=2):
    if pd.isna(valor) or valor is None:
        return "Não informado"
    try:
        num = float(valor)
        formato = f"{{:,.{casas_decimais}f}}".format(num)
        partes = formato.split(".")
        milhar = partes[0].replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{milhar},{partes[1]}"
    except:
        return "Não informado"

def formatar_massa_br(valor):
    if pd.isna(valor) or valor is None:
        return "Não informado"
    return f"{formatar_numero_br(valor)} t"

def normalizar_texto(txt):
    if pd.isna(txt):
        return ""
    txt = unicodedata.normalize("NFKD", str(txt))
    txt = txt.encode("ASCII", "ignore").decode("utf-8")
    return txt.upper().strip()

def classificar_tipo_aterro(mcf):
    """
    Classifica o tipo de aterro baseado no valor do MCF.
    """
    if mcf >= 0.95:
        return "Aterro Sanitário Gerenciado"
    elif mcf >= 0.6:
        return "Aterro Sanitário Não Gerenciado"
    elif mcf > 0:
        return "Aterro Controlado/Lixão"
    else:
        return "Não Aterro"

# =========================================================
# Funções de emissões de CH4 (script técnico anexo)
# =========================================================
def ch4_compostagem_total(massa_kg):
    # Yang et al. (2017) – compostagem termofílica
    return massa_kg * 0.0004  # kg CH4 / kg resíduo

def ch4_vermicompostagem_total(massa_kg):
    # Yang et al. (2017) – vermicompostagem
    return massa_kg * 0.00015  # kg CH4 / kg resíduo

# =========================================================
# Função para determinar MCF baseado no tipo de destino
# =========================================================
def determinar_mcf_por_destino(destino):
    """
    Determina o Methane Correction Factor (MCF) baseado no tipo de destino.
    Baseado no IPCC 2006 e realidade brasileira.
    """
    if pd.isna(destino):
        return 0.0
    
    destino_norm = normalizar_texto(destino)
    
    # Mapeamento de destinos para MCF
    if "ATERRO SANITARIO" in destino_norm:
        # Verificar se é realmente gerenciado
        if "GERENCIADO" in destino_norm or "COLETA GAS" in destino_norm or "COLETA DE GAS" in destino_norm:
            return 1.0  # Aterro sanitário gerenciado com coleta de gás
        else:
            return 0.8  # Aterro sanitário não gerenciado (mais comum no Brasil)
    
    elif "ATERRO CONTROLADO" in destino_norm:
        return 0.4  # Aterro controlado
    
    elif "LIXAO" in destino_norm or "VAZADOURO" in destino_norm or "DESCARGA DIRETA" in destino_norm:
        return 0.4  # Lixão (open dump)
    
    elif "COMPOSTAGEM" in destino_norm or "VERMICOMPOSTAGEM" in destino_norm:
        return 0.0  # Não aplicável - tratamento biológico
    
    elif "RECICLAGEM" in destino_norm or "TRIAGEM" in destino_norm:
        return 0.0  # Não aplicável - reciclagem
    
    elif "INCINERACAO" in destino_norm or "QUEIMA" in destino_norm:
        return 0.0  # Não aplicável - incineração
    
    elif "OUTRO" in destino_norm or "NAO INFORMADO" in destino_norm or "NAO SE APLICA" in destino_norm:
        return 0.0  # Não aplicável
    
    else:
        # Para destinos não classificados, assumir como não aterro
        return 0.0

# =========================================================
# Função para calcular emissões de CH4 do aterro (Tier 1 - IPCC 2006)
# =========================================================
def calcular_emissoes_aterro_total(massa_t, mcf, temperatura=25.0):
    """
    Calcula emissões TOTAIS de CH4 do aterro usando metodologia IPCC 2006 Tier 1.
    Retorna emissões totais ao longo de toda a decomposição.
    """
    # Parâmetros IPCC 2006 para resíduos de poda
    DOC = 0.15  # Fraction of degradable organic carbon
    DOCf = 0.0147 * temperatura + 0.28  # Decomposable fraction of DOC
    F = 0.5  # Fraction of methane in landfill gas
    OX = 0.1  # Oxidation factor
    Ri = 0.0  # Recovery factor (assumindo sem recuperação inicial)
    
    massa_kg = massa_t * 1000
    ch4_kg = massa_kg * DOC * DOCf * mcf * F * (16/12) * (1 - Ri) * (1 - OX)
    ch4_t = ch4_kg / 1000
    
    return ch4_t

# =========================================================
# NOVA: Função para calcular emissões em 20 anos (FOD - First Order Decay)
# =========================================================
def calcular_emissoes_aterro_20anos(massa_t, mcf, temperatura=25.0):
    """
    Calcula emissões de CH4 do aterro em 20 anos usando modelo FOD simplificado.
    Baseado no IPCC 2006 First Order Decay para resíduos de jardim.
    """
    # Parâmetros para resíduos de jardim (poda) - IPCC 2006
    DOC = 0.15  # Fraction of degradable organic carbon
    DOCf = 0.0147 * temperatura + 0.28  # Decomposable fraction of DOC
    F = 0.5  # Fraction of methane in landfill gas
    OX = 0.1  # Oxidation factor
    Ri = 0.0  # Recovery factor
    
    # Constante de decomposição (k) para resíduos de jardim
    k = 0.06  # ano^-1 (IPCC default for garden/yard waste)
    
    # Período de cálculo (anos)
    t = 20  # anos
    
    massa_kg = massa_t * 1000
    
    # Cálculo FOD simplificado
    # Geração total de CH4 potencial (sem decaimento)
    ch4_potencial_total_kg = massa_kg * DOC * DOCf * mcf * F * (16/12) * (1 - Ri) * (1 - OX)
    
    # Fator de decomposição em t anos: (1 - e^(-k*t))
    fator_decomposicao = 1 - np.exp(-k * t)
    
    # CH4 gerado em t anos
    ch4_kg_20anos = ch4_potencial_total_kg * fator_decomposicao
    ch4_t_20anos = ch4_kg_20anos / 1000
    
    # CH4 que seria gerado após 20 anos (restante)
    ch4_restante_t = (ch4_potencial_total_kg * (1 - fator_decomposicao)) / 1000
    
    return ch4_t_20anos, ch4_restante_t

# =========================================================
# Carga do Excel
# =========================================================
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/loopvinyl/tco2eqv7/main/rsuBrasil.xlsx"
    df = pd.read_excel(
        url,
        sheet_name="Manejo_Coleta_e_Destinação",
        header=13
    )
    df = df.dropna(how="all")
    df.columns = [str(col).strip() for col in df.columns]
    return df

df = load_data()

# =========================================================
# Definição de colunas
# =========================================================
df = df.rename(columns={
    df.columns[2]: "MUNICÍPIO",
    df.columns[17]: "TIPO_COLETA_EXECUTADA",
    df.columns[24]: "MASSA_COLETADA"
})

COL_MUNICIPIO = "MUNICÍPIO"
COL_TIPO_COLETA = "TIPO_COLETA_EXECUTADA"
COL_MASSA = "MASSA_COLETADA"
COL_DESTINO = df.columns[28]  # Coluna AC

# =========================================================
# Classificação técnica
# =========================================================
def classificar_coleta(texto):
    if pd.isna(texto):
        return ("Não informado", False, False, "Tipo não informado")

    t = str(texto).lower()
    palavras = {
        "poda": ("Orgânico direto", True, True, "Resíduo vegetal limpo"),
        "galhada": ("Orgânico direto", True, True, "Resíduo vegetal limpo"),
        "verde": ("Orgânico direto", True, True, "Resíduo vegetal limpo"),
        "orgânica": ("Orgânico direto", True, True, "Orgânico segregado"),
        "domiciliar": ("Orgânico potencial", True, False, "Exige triagem"),
        "varrição": ("Inapto", False, False, "Alta contaminação"),
        "seletiva": ("Não orgânico", False, False, "Recicláveis")
    }
    for p, c in palavras.items():
        if p in t:
            return c
    return ("Indefinido", False, False, "Não classificado")

# =========================================================
# Limpeza
# =========================================================
df_clean = df.dropna(subset=[COL_MUNICIPIO])
df_clean[COL_MUNICIPIO] = df_clean[COL_MUNICIPIO].astype(str).str.strip()

# =========================================================
# Interface
# =========================================================
municipios = ["BRASIL – Todos os municípios"] + sorted(df_clean[COL_MUNICIPIO].unique())
municipio = st.selectbox("Selecione o município:", municipios)

df_mun = df_clean.copy() if municipio == municipios[0] else df_clean[df_clean[COL_MUNICIPIO] == municipio]
st.subheader("🇧🇷 Brasil — Síntese Nacional de RSU" if municipio == municipios[0] else f"📍 {municipio}")

# =========================================================
# Tabela principal
# =========================================================
resultados = []
total_massa = massa_compostagem = massa_vermi = 0

for _, row in df_mun.iterrows():
    categoria, comp, vermi, just = classificar_coleta(row[COL_TIPO_COLETA])
    massa = pd.to_numeric(row[COL_MASSA], errors="coerce") or 0
    total_massa += massa
    if comp:
        massa_compostagem += massa
    if vermi:
        massa_vermi += massa

    resultados.append({
        "Tipo de coleta": row[COL_TIPO_COLETA],
        "Massa": formatar_massa_br(massa),
        "Categoria": categoria,
        "Compostagem": "✅" if comp else "❌",
        "Vermicompostagem": "✅" if vermi else "❌",
        "Justificativa": just
    })

st.dataframe(pd.DataFrame(resultados), use_container_width=True)

# =========================================================
# 🌳 Destinação das podas e galhadas
# =========================================================
st.markdown("---")
st.subheader("🌳 Destinação das podas e galhadas de áreas verdes públicas")

df_podas = df_mun[df_mun[COL_TIPO_COLETA].astype(str).str.contains("áreas verdes públicas", case=False, na=False)].copy()

if not df_podas.empty:
    df_podas["MASSA_FLOAT"] = pd.to_numeric(df_podas[COL_MASSA], errors="coerce").fillna(0)
    total_podas = df_podas["MASSA_FLOAT"].sum()

    df_podas_destino = df_podas.groupby(COL_DESTINO)["MASSA_FLOAT"].sum().reset_index()
    df_podas_destino["Percentual (%)"] = df_podas_destino["MASSA_FLOAT"] / total_podas * 100
    df_podas_destino = df_podas_destino.sort_values("Percentual (%)", ascending=False)

    st.metric("Massa total de podas e galhadas", f"{formatar_numero_br(total_podas)} t")

    df_view = df_podas_destino.copy()
    df_view["Massa (t)"] = df_view["MASSA_FLOAT"].apply(formatar_numero_br)
    df_view["Percentual (%)"] = df_view["Percentual (%)"].apply(lambda x: formatar_numero_br(x, 1))

    st.dataframe(df_view[[COL_DESTINO, "Massa (t)", "Percentual (%)"]], use_container_width=True)

    # =========================================================
    # 🔥 Cálculo detalhado de emissões por tipo de destino
    # =========================================================
    st.subheader("🔥 Cálculo Detalhado de Emissões de CH₄ por Tipo de Destino")
    
    # Adicionar coluna de MCF à tabela (sem exibir)
    df_podas_destino["MCF"] = df_podas_destino[COL_DESTINO].apply(determinar_mcf_por_destino)
    
    # Parâmetros para cálculo
    temperatura = 25.0  # Temperatura média anual em °C
    
    # Lista para armazenar resultados detalhados
    resultados_emissoes = []
    resultados_emissoes_20anos = []
    ch4_total_aterro_t = 0
    ch4_total_20anos_t = 0
    massa_total_aterro_t = 0
    
    for _, row in df_podas_destino.iterrows():
        destino = row[COL_DESTINO]
        massa_t = row["MASSA_FLOAT"]
        mcf = row["MCF"]
        
        # Só calcular emissões para destinos com MCF > 0 (aterros)
        if mcf > 0 and massa_t > 0:
            # Emissões totais (ao longo de toda decomposição)
            ch4_total_t = calcular_emissoes_aterro_total(massa_t, mcf, temperatura)
            
            # Emissões em 20 anos
            ch4_20anos_t, ch4_restante_t = calcular_emissoes_aterro_20anos(massa_t, mcf, temperatura)
            
            ch4_total_aterro_t += ch4_total_t
            ch4_total_20anos_t += ch4_20anos_t
            massa_total_aterro_t += massa_t
            
            resultados_emissoes.append({
                "Destino": destino,
                "Massa (t)": formatar_numero_br(massa_t),
                "MCF": formatar_numero_br(mcf, 2),
                "CH₄ Total (t)": formatar_numero_br(ch4_total_t, 3),
                "CH₄ em 20 anos (t)": formatar_numero_br(ch4_20anos_t, 3),
                "% em 20 anos": formatar_numero_br((ch4_20anos_t/ch4_total_t)*100 if ch4_total_t > 0 else 0, 1),
                "Tipo de Aterro": classificar_tipo_aterro(mcf)
            })
    
    # Se houver emissões de aterro, mostrar resultados
    if resultados_emissoes:
        st.dataframe(pd.DataFrame(resultados_emissoes), use_container_width=True)
        
        # =========================================================
        # 📊 Comparação com Cenário de Tratamento Biológico
        # =========================================================
        st.subheader("📊 Comparação: Aterro vs Tratamento Biológico")
        
        # Adicionar seletor de horizonte temporal
        col_tempo1, col_tempo2 = st.columns(2)
        with col_tempo1:
            horizonte_temporal = st.selectbox(
                "Horizonte temporal para cálculo:",
                ["Total (toda decomposição)", "20 anos"],
                index=0
            )
        
        with col_tempo2:
            if horizonte_temporal == "20 anos":
                st.info("🌍 Modelo FOD (First Order Decay) - IPCC 2006")
            else:
                st.info("📈 Método Tier 1 - IPCC 2006")
        
        # Escolher qual valor de CH4 usar baseado no horizonte selecionado
        if horizonte_temporal == "20 anos":
            ch4_aterro_usar_t = ch4_total_20anos_t
            tempo_label = "em 20 anos"
        else:
            ch4_aterro_usar_t = ch4_total_aterro_t
            tempo_label = "total"
        
        # Calcular emissões do cenário de tratamento biológico
        massa_kg_total_aterro = massa_total_aterro_t * 1000
        ch4_comp_total_t = ch4_compostagem_total(massa_kg_total_aterro) / 1000
        ch4_vermi_total_t = ch4_vermicompostagem_total(massa_kg_total_aterro) / 1000
        
        # Emissões evitadas
        ch4_evitado_t = ch4_aterro_usar_t - ch4_comp_total_t - ch4_vermi_total_t
        
        # Calcular CO₂ equivalente (GWP100 do CH4 = 28, IPCC AR6)
        GWP100 = 28
        co2eq_evitado_t = ch4_evitado_t * GWP100
        
        # Métricas comparativas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Massa em aterros",
                f"{formatar_numero_br(massa_total_aterro_t)} t",
                help="Total de podas destinadas a aterros (todos os tipos)"
            )
        
        with col2:
            st.metric(
                f"CH₄ do aterro ({tempo_label})",
                f"{formatar_numero_br(ch4_aterro_usar_t, 1)} t",
                delta=None,
                help=f"CH₄ gerado em aterros {tempo_label}"
            )
        
        with col3:
            st.metric(
                "CH₄ evitado",
                f"{formatar_numero_br(ch4_evitado_t, 1)} t",
                delta=f"-{formatar_numero_br((ch4_evitado_t/ch4_aterro_usar_t)*100 if ch4_aterro_usar_t > 0 else 0, 1)}%",
                delta_color="inverse",
                help="Redução de CH₄ ao optar por tratamento biológico"
            )
        
        with col4:
            st.metric(
                "CO₂e evitado",
                f"{formatar_numero_br(co2eq_evitado_t, 1)} t CO₂e",
                help=f"Equivalente em CO₂ (GWP100 = {GWP100})"
            )
        
        # =========================================================
        # 📈 Resumo por Tipo de Aterro
        # =========================================================
        st.subheader("📈 Resumo por Categoria de Aterro")
        
        # Converter string para float para agregação
        def to_float(val):
            if isinstance(val, str):
                # Remover pontos de milhar e substituir vírgula decimal por ponto
                val_clean = val.replace('.', '').replace(',', '.')
                return float(val_clean)
            return float(val)
        
        df_resumo = pd.DataFrame(resultados_emissoes)
        if not df_resumo.empty:
            # Usar os valores de 20 anos ou total conforme seleção
            if horizonte_temporal == "20 anos":
                col_ch4 = "CH₄ em 20 anos (t)"
                titulo_ch4 = "CH₄ Gerado (t) - 20 anos"
            else:
                col_ch4 = "CH₄ Total (t)"
                titulo_ch4 = "CH₄ Gerado (t) - Total"
            
            df_resumo["Massa_num"] = df_resumo["Massa (t)"].apply(lambda x: to_float(x))
            df_resumo["CH4_num"] = df_resumo[col_ch4].apply(lambda x: to_float(x))
            
            resumo_agrupado = df_resumo.groupby("Tipo de Aterro").agg({
                "Massa_num": "sum",
                "CH4_num": "sum"
            }).reset_index()
            
            resumo_agrupado["Massa (t)"] = resumo_agrupado["Massa_num"].apply(lambda x: formatar_numero_br(x))
            resumo_agrupado[titulo_ch4] = resumo_agrupado["CH4_num"].apply(lambda x: formatar_numero_br(x, 1))
            resumo_agrupado["CH₄ por t"] = resumo_agrupado.apply(
                lambda row: formatar_numero_br(row["CH4_num"] / row["Massa_num"] if row["Massa_num"] > 0 else 0, 3), 
                axis=1
            )
            
            st.dataframe(resumo_agrupado[["Tipo de Aterro", "Massa (t)", titulo_ch4, "CH₄ por t"]], use_container_width=True)
        
        # =========================================================
        # 📅 Comparativo Total vs 20 anos
        # =========================================================
        st.subheader("📅 Comparativo: Emissões Totais vs 20 anos")
        
        col_t1, col_t2, col_t3 = st.columns(3)
        
        with col_t1:
            percentual_20anos = (ch4_total_20anos_t / ch4_total_aterro_t * 100) if ch4_total_aterro_t > 0 else 0
            st.metric(
                "CH₄ Total (toda decomposição)",
                f"{formatar_numero_br(ch4_total_aterro_t, 1)} t",
                help="Emissões totais ao longo de toda a decomposição"
            )
        
        with col_t2:
            st.metric(
                "CH₄ em 20 anos",
                f"{formatar_numero_br(ch4_total_20anos_t, 1)} t",
                delta=f"{formatar_numero_br(percentual_20anos, 1)}% do total",
                help="Emissões nos primeiros 20 anos (FOD - IPCC)"
            )
        
        with col_t3:
            ch4_apos_20anos = ch4_total_aterro_t - ch4_total_20anos_t
            st.metric(
                "CH₄ após 20 anos",
                f"{formatar_numero_br(ch4_apos_20anos, 1)} t",
                help="Emissões que ocorreriam após 20 anos"
            )
        
        # =========================================================
        # ℹ️ Notas Técnicas
        # =========================================================
        st.markdown("---")
        with st.expander("📋 Notas Técnicas sobre os Cálculos"):
            st.markdown("""
            **Metodologia de Cálculo:**
            
            1. **Fator de Correção de Metano (MCF):**
               - **MCF = 1.0**: Aterro sanitário gerenciado com cobertura diária e sistema de coleta de gás
               - **MCF = 0.8**: Aterro sanitário não gerenciado (sem coleta de gás, mas com cobertura)
               - **MCF = 0.4**: Aterro controlado ou lixão (sem cobertura sistemática)
            
            2. **Parâmetros IPCC 2006 para resíduos de poda:**
               - DOC (Degradable Organic Carbon) = 0.15
               - DOCf = 0.0147 × Temperatura(°C) + 0.28
               - F (Fraction of CH4 in landfill gas) = 0.5
               - OX (Oxidation factor) = 0.1
               - Ri (Recovery factor) = 0.0 (sem recuperação de gás)
            
            3. **Dois métodos de cálculo:**
               - **Método Total (Tier 1)**: Calcula emissões totais ao longo de toda decomposição
               - **Método 20 anos (FOD)**: Modelo First Order Decay - 85-90% das emissões ocorrem em 20 anos
            
            4. **Parâmetros FOD para resíduos de poda:**
               - Constante de decomposição (k) = 0.06 ano⁻¹
               - Fator decomposição 20 anos: 1 - e^(-0.06×20) = 0.70 (70%)
               - Na prática: ~70-75% do CH4 total é gerado em 20 anos
            
            5. **Emissões de tratamento biológico (Yang et al., 2017):**
               - Compostagem: 0.0004 kg CH4/kg resíduo (ocorre em semanas/meses)
               - Vermicompostagem: 0.00015 kg CH4/kg resíduo (ocorre em semanas/meses)
            
            6. **Equivalência CO₂:**
               - GWP100 do CH₄ = 28 (IPCC AR6, 2021)
            
            **Considerações para o contexto brasileiro:**
            - A maioria dos "aterros sanitários" no Brasil opera com MCF entre 0.6-0.8
            - Poucos aterros têm sistemas eficientes de coleta de biogás
            - Este cálculo considera o pior cenário (sem recuperação de gás)
            - Para análises conservadoras, recomenda-se usar o cenário de 20 anos
            """)
    
    else:
        st.info("✅ Não há massa de podas e galhadas destinada a aterros. Todo o material já está sendo direcionado para tratamentos adequados!")
    
else:
    st.info("Não há dados de podas e galhadas para o município selecionado.")

# =========================================================
# Rodapé
# =========================================================
st.markdown("---")
st.caption("Fonte: SNIS – Sistema Nacional de Informações sobre Saneamento | Metodologia: IPCC 2006, Yang et al. (2017)")
