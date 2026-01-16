# =========================================================
# 💰 Valoração econômica das emissões evitadas (20 anos)
# =========================================================
st.markdown("### 💰 Valoração econômica das emissões evitadas (CH₄)")

st.markdown(
    "Estimativa econômica baseada nas **emissões evitadas de metano (CH₄)** "
    "ao longo de **20 anos**, com cálculo da média anual."
)

# -------------------------------
# Parâmetros econômicos (editáveis)
# -------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    preco_ch4_usd = st.number_input(
        "Preço do CH₄ (US$ / t)",
        min_value=0.0,
        value=1500.0,
        step=50.0
    )

with col2:
    cotacao_usd_brl = st.number_input(
        "Cotação US$ → R$",
        min_value=0.0,
        value=5.00,
        step=0.05
    )

with col3:
    cotacao_usd_eur = st.number_input(
        "Cotação US$ → €",
        min_value=0.0,
        value=0.92,
        step=0.01
    )

# -------------------------------
# Cálculos temporais
# -------------------------------
anos = 20

evitado_comp_20a = evitado_comp_t * anos
evitado_vermi_20a = evitado_vermi_t * anos

media_comp_anual = evitado_comp_20a / anos
media_vermi_anual = evitado_vermi_20a / anos

# -------------------------------
# Valoração econômica
# -------------------------------
valor_comp_usd = evitado_comp_20a * preco_ch4_usd
valor_vermi_usd = evitado_vermi_20a * preco_ch4_usd

valor_comp_brl = valor_comp_usd * cotacao_usd_brl
valor_vermi_brl = valor_vermi_usd * cotacao_usd_brl

valor_comp_eur = valor_comp_usd * cotacao_usd_eur
valor_vermi_eur = valor_vermi_usd * cotacao_usd_eur

# -------------------------------
# Exibição dos resultados
# -------------------------------
st.markdown("#### 📊 Resultados – Horizonte de 20 anos")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**🌱 Compostagem**")
    st.metric("CH₄ evitado (20 anos)", f"{formatar_numero_br(evitado_comp_20a)} t")
    st.metric("Média anual", f"{formatar_numero_br(media_comp_anual)} t/ano")
    st.metric("Valor estimado (R$)", f"R$ {formatar_numero_br(valor_comp_brl)}")
    st.metric("Valor estimado (€)", f"€ {formatar_numero_br(valor_comp_eur)}")

with col2:
    st.markdown("**🐛 Vermicompostagem**")
    st.metric("CH₄ evitado (20 anos)", f"{formatar_numero_br(evitado_vermi_20a)} t")
    st.metric("Média anual", f"{formatar_numero_br(media_vermi_anual)} t/ano")
    st.metric("Valor estimado (R$)", f"R$ {formatar_numero_br(valor_vermi_brl)}")
    st.metric("Valor estimado (€)", f"€ {formatar_numero_br(valor_vermi_eur)}")

st.caption(
    "Valoração econômica estimada a partir das emissões evitadas de CH₄, "
    "considerando horizonte de 20 anos e preço configurável por tonelada de metano. "
    "Cotações monetárias ajustáveis pelo usuário."
)
