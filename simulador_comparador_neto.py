
import streamlit as st
import pandas as pd

VALOR_INDICE_ABRIL = 85.056195
VALOR_INDICE_MAYO = 87.608881

GREMIOS = {
    "AMET": 0.015, "SUTEF": 0.02, "SUETRA": 0.02,
    "ATE": 0.022, "UDAF": 0.013, "UDA": 0.015, "UPCN": 0.022
}

antiguedad_tabla = {
    range(0, 6): 0.40, range(6, 8): 0.50, range(8, 10): 0.60,
    range(10, 12): 0.70, range(12, 14): 0.80, range(14, 16): 0.90,
    range(16, 18): 1.00, range(18, 20): 1.10, range(20, 22): 1.20,
    range(22, 24): 1.30, range(24, 100): 1.35
}

def calcular_antiguedad_factor(antiguedad):
    for r in antiguedad_tabla:
        if antiguedad in r:
            return antiguedad_tabla[r]
    return 0

@st.cache_data
def cargar_datos():
    df = pd.read_excel("Cargos_Abril2025.xlsx", sheet_name="Simulador Abril 2025")
    df["IDENTIFICADOR"] = df["COD."].astype(int).astype(str) + " - " + df["CARGO"].str.strip()
    return (
        dict(zip(df["IDENTIFICADOR"], df["PUNTAJE 04/2025"])),
        dict(zip(df["IDENTIFICADOR"], df["PUNTAJE 05/2025"])),
        df["IDENTIFICADOR"].dropna().tolist()
    )

puntajes_abril, puntajes_mayo, lista_cargos = cargar_datos()

def calcular_total(cargos, cantidades, vi, puntajes_dict, descuentos, antiguedad):
    desglose = []
    total_puntaje = 0
    total_horas = 0
    simples = 0
    completo = False

    for i, cargo in enumerate(cargos):
        if not cargo or cantidades[i] <= 0:
            continue
        puntaje = puntajes_dict.get(cargo, 0)
        puntaje_total = puntaje * cantidades[i]
        total_puntaje += puntaje_total

        if "HORA" in cargo.upper():
            total_horas += cantidades[i]
        elif "COMPLETO" in cargo.upper():
            completo = True
        elif "SIMPLE" in cargo.upper():
            simples += cantidades[i]

        desglose.append((cargo, cantidades[i], puntaje_total, puntaje_total * vi))

    unidades_bono = 38 if completo else min(19 * min(simples, 2) + total_horas, 38)

    basico = total_puntaje * vi
    funcion_docente = basico * 2.30
    antiguedad_valor = basico * calcular_antiguedad_factor(antiguedad)
    transformacion = basico * 1.23
    subtotal = basico + funcion_docente + antiguedad_valor + transformacion
    zona = subtotal
    total_remun = subtotal + zona

    jubilacion = total_remun * 0.16
    obra_social = total_remun * 0.03
    seguro = 3000
    descuentos_legales = jubilacion + obra_social + seguro

    gremial = sum(GREMIOS[g] * (total_remun + (unidades_bono * (90000 / 38))) for g in descuentos if g in GREMIOS)

    bonos = unidades_bono * (90000 / 38) + unidades_bono * (142600 / 38)

    total_descuentos = descuentos_legales + gremial
    neto = total_remun - total_descuentos + bonos

    return {
        "Desglose": desglose,
        "Básico": basico,
        "Función Docente": funcion_docente,
        "Antigüedad": antiguedad_valor,
        "Transformación": transformacion,
        "Zona": zona,
        "Remunerativo": total_remun,
        "Bonos": bonos,
        "Descuentos Legales": descuentos_legales,
        "Descuento Gremial": gremial,
        "Total Descuentos": total_descuentos,
        "Neto": neto
    }

# ---------- INTERFAZ ----------
st.title("📊 Comparador Salarial Abril vs Mayo 2025")

antiguedad = st.number_input("Antigüedad (años):", min_value=0, max_value=40, value=0)

st.markdown("### Cargar hasta 3 cargos u horas")
cargos_selec = []
cantidades = []

for i in range(3):
    col1, col2 = st.columns([3, 1])
    with col1:
        c = st.selectbox("Cargo u horas #%d" % (i+1), options=[""] + sorted(lista_cargos), key="cargo_%d" % i)
    with col2:
        q = st.number_input("Cantidad:", min_value=0, value=0, key="cantidad_%d" % i)
    cargos_selec.append(c)
    cantidades.append(q)

gremio1 = st.selectbox("Gremio 1:", ["Ninguno"] + list(GREMIOS.keys()))
gremio2 = st.selectbox("Gremio 2:", ["Ninguno"] + list(GREMIOS.keys()))

descuentos = []
if gremio1 != "Ninguno": descuentos.append(gremio1)
if gremio2 != "Ninguno" and gremio2 != gremio1: descuentos.append(gremio2)

if st.button("Calcular Comparación"):
    abril = calcular_total(cargos_selec, cantidades, VALOR_INDICE_ABRIL, puntajes_abril, descuentos, antiguedad)
    mayo = calcular_total(cargos_selec, cantidades, VALOR_INDICE_MAYO, puntajes_mayo, descuentos, antiguedad)

    st.markdown("### 🧾 Detalle por ítem")
    df_resultado = pd.DataFrame({
        "Concepto": abril.keys(),
        "Abril ($)": abril.values(),
        "Mayo ($)": mayo.values(),
        "Diferencia ($)": [mayo[k] - abril[k] if isinstance(mayo[k], (int, float)) else 0 for k in abril],
        "Variación (%)": [((mayo[k] - abril[k]) / abril[k] * 100) if isinstance(abril[k], (int, float)) and abril[k] != 0 else 0 for k in abril]
    })

    st.dataframe(
        df_resultado.style.format(subset=["Abril ($)", "Mayo ($)", "Diferencia ($)"], formatter="{:,.2f}")
        .format({"Variación (%)": "{:+.2f}%"})
    )

    st.markdown("### 📋 Desglose por cargo")
    st.markdown("**Abril:**")
    for cargo, cantidad, puntaje, basico in abril["Desglose"]:
        st.markdown(f"- {cargo} - Cant: {cantidad} - Puntaje: {puntaje:.2f} - Básico: ${basico:,.2f}")
    st.markdown("**Mayo:**")
    for cargo, cantidad, puntaje, basico in mayo["Desglose"]:
        st.markdown(f"- {cargo} - Cant: {cantidad} - Puntaje: {puntaje:.2f} - Básico: ${basico:,.2f}")
