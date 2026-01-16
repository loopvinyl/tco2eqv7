# =========================================================
# 🔥 Metano – Aterro vs Tratamentos Biológicos
# =========================================================
st.subheader("🔥 Metano (CH₄): Aterro × Tratamentos Biológicos")

GWP_CH4 = 27.2  # AR6 – 100 anos

massa_aterro_t = df_podas_destino.loc[
    df_podas_destino[COL_DESTINO].apply(normalizar_texto) == "ATERRO SANITARIO",
    "MASSA_FLOAT"
].sum()

if massa_aterro_t > 0:
    DOC, MCF, F, OX, Ri = 0.15, 1.0, 0.5, 0.1, 0.0
    DOCf = 0.0147 * 25 + 0.28

    massa_kg = massa_aterro_t * 1000

    # CH₄ no aterro (IPCC)
    ch4_aterro_t = (
        massa_kg * DOC * DOCf * MCF * F * (16 / 12) * (1 - Ri) * (1 - OX)
    ) / 1000

    # CH₄ nos tratamentos (Yang et al.)
    ch4_comp_t = ch4_compostagem_total(massa_kg) / 1000
    ch4_vermi_t = ch4_vermicompostagem_total(massa_kg) / 1000

    # Emissões evitadas (CH₄)
    evitado_comp_ch4 = ch4_aterro_t - ch4_comp_t
    evitado_vermi_ch4 = ch4_aterro_t - ch4_vermi_t

    # Conversão para tCO₂eq
    evitado_comp_co2eq = evitado_comp_ch4 * GWP_CH4
    evitado_vermi_co2eq = evitado_vermi_ch4 * GWP_CH4

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("CH₄ no aterro", f"{formatar_numero_br(ch4_aterro_t)} t")
    with col2:
        st.metric("Emissões evitadas – Compostagem", f"{formatar_numero_br(evitado_comp_co2eq)} tCO₂eq")
    with col3:
        st.metric("Emissões evitadas – Vermicompostagem", f"{formatar_numero_br(evitado_vermi_co2eq)} tCO₂eq")

    # Gráfico
    df_graf = pd.DataFrame({
        "Cenário": ["Aterro", "Compostagem", "Vermicompostagem"],
        "Emissões (tCO₂eq)": [
            ch4_aterro_t * GWP_CH4,
            ch4_comp_t * GWP_CH4,
            ch4_vermi_t * GWP_CH4
        ]
    }).set_index("Cenário")

    st.bar_chart(df_graf, use_container_width=True)

    # =========================================================
    # 💰 Valoração econômica – tCO₂eq (20 anos)
    # =========================================================
    st.markdown("### 💰 Valoração econômica das emissões evitadas (tCO₂eq)")

    col1, col2, col3 = st.columns(3)
    with col1:
        preco_co2eq = st.number_input(
            "Preço do carbono (US$ / tCO₂eq)",
            value=50.0,
            step=5.0
        )
    with col2:
        cot_usd_brl = st.number_input("Cotação US$ → R$", value=5.0, step=0.05)
    with col3:
        cot_usd_eur = st.number_input("Cotação US$ → €", value=0.92, step=0.01)

    anos = 20

    comp_20a = evitado_comp_co2eq * anos
    vermi_20a = evitado_vermi_co2eq * anos

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🌱 Compostagem**")
        st.metric("tCO₂eq evitado (20 anos)", formatar_numero_br(comp_20a))
        st.metric("Valor (R$)", f"R$ {formatar_numero_br(comp_20a * preco_co2eq * cot_usd_brl)}")
        st.metric("Valor (€)", f"€ {formatar_numero_br(comp_20a * preco_co2eq * cot_usd_eur)}")

    with col2:
        st.markdown("**🐛 Vermicompostagem**")
        st.metric("tCO₂eq evitado (20 anos)", formatar_numero_br(vermi_20a))
        st.metric("Valor (R$)", f"R$ {formatar_numero_br(vermi_20a * preco_co2eq * cot_usd_brl)}")
        st.metric("Valor (€)", f"€ {formatar_numero_br(vermi_20a * preco_co2eq * cot_usd_eur)}")

    st.caption(
        "Emissões evitadas calculadas em tCO₂eq a partir do desvio de podas e galhadas "
        "do aterro sanitário para compostagem e vermicompostagem. "
        "Metodologia IPCC 2006 + Yang et al. | GWP CH₄ = 27,2 (AR6 – 100 anos)."
    )
