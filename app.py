import streamlit as st
import pandas as pd
import unicodedata

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
e avalia o **potencial técnico e climático** (GWP20) para desvio de resíduos orgânicos.
""")

# =========================================================
# Constantes Técnicas (Baseadas no Script Modelo - AR6 IPCC)
# =========================================================
GWP_CH4_20 = 79.7  # Potencial de Aquecimento Global do Metano (20 anos)
ANOS_SIMULACAO = 20 # Horizonte temporal padrão do modelo

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

# =========================================================
# Funções de emissões de CH4 (Yang et al. 2017)
# =========================================================
def ch4_compostagem_total(massa_kg):
    return massa_kg * 0.0004  # kg CH4 / kg resíduo

def ch4_vermicompostagem_total(massa_kg):
    return massa_kg * 0.00015  # kg CH4 / kg resíduo

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
# Limpeza e Interface
# =========================================================
df_clean = df.dropna(subset=[COL_MUNICIPIO])
df_clean[COL_MUNICIPIO] = df_clean[COL_MUNICIPIO].astype(str).str.strip()

municipios = ["BRASIL – Todos os municípios"] + sorted(df_clean[COL_MUNICIPIO].unique())
municipio = st.selectbox("Selecione o município:", municipios)

df_mun = df_clean.copy() if municipio == municipios[0] else df_clean[df_clean[COL_MUNICIPIO] == municipio]
st.subheader("🇧🇷 Brasil — Síntese Nacional de RSU" if municipio == municipios[0] else f"📍 {municipio}")

# =========================================================
# Tabela principal de Triagem Técnica
# =========================================================
resultados = []
for _, row in df_mun.iterrows():
    categoria, comp, vermi, just = classificar_coleta(row[COL_TIPO_COLETA])
    massa = pd.to_numeric(row[COL_MASSA], errors="coerce") or 0
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
# 🔥 IMPACTO CLIMÁTICO (ATERRO VS COMPOSTAGEM VS VERMICOMPOSTAGEM)
# =========================================================
st.markdown("---")
st.subheader("🌳 Análise de Emissões Evitadas (Média Anual - Horizonte 20 anos)")

df_podas = df_mun[df_mun[COL_TIPO_COLETA].astype(str).str.contains("áreas verdes públicas", case=False, na=False)].copy()

if not df_podas.empty:
    df_podas["MASSA_FLOAT"] = pd.to_numeric(df_podas[COL_MASSA], errors="coerce").fillna(0)
    massa_aterro_t = df_podas[df_podas[COL_DESTINO].apply(normalizar_texto) == "ATERRO SANITARIO"]["MASSA_FLOAT"].sum()

    if massa_aterro_t > 0:
        # Parâmetros IPCC 2006 (FOD Simplificado para 20 anos)
        DOC, MCF, F, OX, Ri = 0.15, 1.0, 0.5, 0.1, 0.0
        DOCf = 0.0147 * ANOS_SIMULACAO + 0.28 
        massa_kg = massa_aterro_t * 1000
        
        # 1. BASELINE: ATERRO SANITÁRIO
        ch4_aterro_t = (massa_kg * DOC * DOCf * MCF * F * (16/12) * (1-Ri) * (1-OX)) / 1000
        co2eq_aterro_ano = (ch4_aterro_t * GWP_CH4_20) / ANOS_SIMULACAO

        # 2. CENÁRIO A: COMPOSTAGEM
        ch4_comp_t = ch4_compostagem_total(massa_kg) / 1000
        co2eq_comp_ano = (ch4_comp_t * GWP_CH4_20) / ANOS_SIMULACAO
        evitado_comp_ano = co2eq_aterro_ano - co2eq_comp_ano

        # 3. CENÁRIO B: VERMICOMPOSTAGEM
        ch4_vermi_t = ch4_vermicompostagem_total(massa_kg) / 1000
        co2eq_vermi_ano = (ch4_vermi_t * GWP_CH4_20) / ANOS_SIMULACAO
        evitado_vermi_ano = co2eq_aterro_ano - co2eq_vermi_ano

        # --- EXIBIÇÃO ---
        st.write(f"Comparativo de redução de emissões para **{formatar_numero_br(massa_aterro_t)} t** de podas:")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Emissão no Aterro", f"{formatar_numero_br(co2eq_aterro_ano)} tCO₂eq/ano", help="Emissão média anual no baseline")
        with col2:
            st.metric("Evitado c/ Compostagem", f"{formatar_numero_br(evitado_comp_ano)} tCO₂eq/ano", delta="Redução")
        with col3:
            st.metric("Evitado c/ Vermicompostagem", f"{formatar_numero_br(evitado_vermi_ano)} tCO₂eq/ano", delta="Maior Redução", delta_color="normal")

        st.info(f"""
        **Conclusão Climática:** A Vermicompostagem apresenta o maior potencial de mitigação, 
        evitando em média **{formatar_numero_br(evitado_vermi_ano)} tCO₂eq por ano**, 
        devido ao menor fator de emissão de metano comparado à compostagem termofílica.
        """)
        
        st.caption(f"Fatores GWP20: CH₄={GWP_CH4_20}. Referências: IPCC (2006) e Yang et al. (2017).")
    else:
        st.info("Não há resíduos de áreas verdes destinados a aterro sanitário para análise de emissões evitadas.")
else:
    st.info("Sem dados de podas para este município.")

# =========================================================
# Rodapé
# =========================================================
st.markdown("---")
st.caption("Fonte: SNIS | Simulação baseada no horizonte de 20 anos (GWP20).")
