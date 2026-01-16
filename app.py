# =========================================================
# 💰 Valoração econômica – mercado de carbono (tempo real)
# =========================================================

preco_carbono = st.session_state.get('preco_carbono', 85.5)
taxa_cambio = st.session_state.get('taxa_cambio', 5.5)

anos = 20

comp_20a = evitado_comp_co2eq * anos
vermi_20a = evitado_vermi_co2eq * anos

valor_comp_brl = calcular_valor_creditos(
    comp_20a,
    preco_carbono,
    "€",
    taxa_cambio
)

valor_vermi_brl = calcular_valor_creditos(
    vermi_20a,
    preco_carbono,
    "€",
    taxa_cambio
)

valor_comp_eur = comp_20a * preco_carbono
valor_vermi_eur = vermi_20a * preco_carbono

col1, col2 = st.columns(2)

with col1:
    st.markdown("**🌱 Compostagem**")
    st.metric("tCO₂eq evitado (20 anos)", formatar_numero_br(comp_20a))
    st.metric("Valor econômico (€)", f"€ {formatar_numero_br(valor_comp_eur)}")
    st.metric("Valor econômico (R$)", f"R$ {formatar_numero_br(valor_comp_brl)}")

with col2:
    st.markdown("**🐛 Vermicompostagem**")
    st.metric("tCO₂eq evitado (20 anos)", formatar_numero_br(vermi_20a))
    st.metric("Valor econômico (€)", f"€ {formatar_numero_br(valor_vermi_eur)}")
    st.metric("Valor econômico (R$)", f"R$ {formatar_numero_br(valor_vermi_brl)}")
