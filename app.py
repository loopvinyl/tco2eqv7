# =========================================================
# 🔥 Metano – Aterro vs Tratamento Biológico
# =========================================================
st.subheader("🔥 Potencial de geração de metano (CH₄) – Aterro Sanitário")

massa_aterro_t = df_podas_destino.loc[
    df_podas_destino[COL_DESTINO].apply(normalizar_texto) == "ATERRO SANITARIO",
    "MASSA_FLOAT"
].sum()

if massa_aterro_t > 0:
    # IPCC 2006 – Aterro
    DOC, MCF, F, OX, Ri = 0.15, 1.0, 0.5, 0.1, 0.0
    DOCf = 0.0147 * 25 + 0.28

    massa_kg = massa_aterro_t * 1000

    ch4_aterro_t = (
        massa_kg * DOC * DOCf * MCF * F * (16 / 12) * (1 - Ri) * (1 - OX)
    ) / 1000

    # Compostagem e vermicompostagem (Yang et al.)
    ch4_comp_t = ch4_compostagem_total(massa_kg) / 1000
    ch4_vermi_t = ch4_vermicompostagem_total(massa_kg) / 1000

    # Emissões evitadas
    evitado_comp_t = ch4_aterro_t - ch4_comp_t
    evitado_vermi_t = ch4_aterro_t - ch4_vermi_t

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Massa no aterro", f"{formatar_numero_br(massa_aterro_t)} t")
    with col2:
        st.metric("CH₄ potencial no aterro", f"{formatar_numero_br(ch4_aterro_t)} t CH₄")
    with col3:
        st.metric("Emissões evitadas (máx.)", f"{formatar_numero_br(evitado_vermi_t)} t CH₄")

    st.markdown("### 🌱 Emissões Evitadas por Tipo de Tratamento")

    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Compostagem",
            f"{formatar_numero_br(evitado_comp_t)} t CH₄"
        )
    with col2:
        st.metric(
            "Vermicompostagem",
            f"{formatar_numero_br(evitado_vermi_t)} t CH₄"
        )

    # =========================================================
    # 📊 Gráfico comparativo
    # =========================================================
    df_grafico = pd.DataFrame({
        "Cenário": [
            "Aterro Sanitário",
            "Compostagem",
            "Vermicompostagem"
        ],
        "Emissões de CH₄ (t)": [
            ch4_aterro_t,
            ch4_comp_t,
            ch4_vermi_t
        ]
    })

    st.bar_chart(
        df_grafico.set_index("Cenário"),
        use_container_width=True
    )

    st.caption(
        "Emissões evitadas calculadas comparando o cenário de aterro sanitário "
        "com os tratamentos biológicos. "
        "Metodologia: IPCC 2006 (aterro) e Yang et al. (2017) para compostagem "
        "e vermicompostagem. Apenas CH₄ considerado."
    )

else:
    st.info("Não há massa de podas e galhadas destinada a aterro sanitário.")
