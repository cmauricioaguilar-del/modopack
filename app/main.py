import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from processor import cargar_ventas, cargar_compras, resumen_mensual, ranking_pareto
from processor_rrhh import cargar_rrhh, resumen_mensual_rrhh, ranking_empleados, resumen_por_centro_costo
from github_loader import EN_RAILWAY, carpetas_railway

st.set_page_config(
    page_title="Control de Gestión",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Login ─────────────────────────────────────────────────────────────────────
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    import base64, os
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background: #f4f6f9; }
    [data-testid="stHeader"] { display: none; }
    .login-box {
        background: white;
        border-radius: 12px;
        padding: 48px 40px 36px 40px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.10);
        max-width: 420px;
        margin: 60px auto 0 auto;
    }
    .login-divider {
        border: none; border-top: 1px solid #e5e8ef;
        margin: 24px 0 20px 0;
    }
    .login-footer {
        text-align: center;
        color: #aab0bb;
        font-size: 12px;
        margin-top: 28px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Cargar logo
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="width:100%;max-width:280px;display:block;margin:0 auto 8px auto;">'
    else:
        logo_html = '<h2 style="text-align:center;color:#1a5276;">MODOPACK</h2>'

    st.markdown(f"""
    <div class="login-box">
        {logo_html}
        <p style="text-align:center;color:#7f8c9a;font-size:13px;margin-bottom:4px;">
            Control de Gestión
        </p>
        <hr class="login-divider">
    </div>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        with st.form("login"):
            usuario = st.text_input("Usuario", placeholder="Ingrese su usuario")
            clave   = st.text_input("Contraseña", type="password", placeholder="Ingrese su contraseña")
            ok      = st.form_submit_button("Ingresar →", use_container_width=True)
        if ok:
            if usuario == "admin" and clave == "modopack2026":
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")

    st.markdown('<p class="login-footer">© 2026 Modopack · Soluciones en Aislación Térmica</p>', unsafe_allow_html=True)
    st.stop()

st.markdown("""
<style>
[data-testid="stMetric"] { background:#f0f2f6; border-radius:8px; padding:12px; }
</style>
""", unsafe_allow_html=True)

MESES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
COLORES = ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd"]


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Configuración")

    if EN_RAILWAY:
        st.info("📡 Leyendo datos desde GitHub")
        _c = carpetas_railway()
        carpeta_ventas_2025  = _c["ventas_2025"]
        carpeta_ventas_2026  = _c["ventas_2026"]
        carpeta_compras_2025 = _c["compras_2025"]
        carpeta_compras_2026 = _c["compras_2026"]
        carpeta_rrhh_2025    = _c["rrhh_2025"]
        carpeta_rrhh_2026    = _c["rrhh_2026"]
    else:
        with st.expander("📁 Carpetas de datos", expanded=False):
            carpeta_ventas_2025 = st.text_input(
                "Carpeta Ventas 2025",
                value=r"C:\Users\pc\OneDrive\Escritorio\2025\VENTAS 2025",
            )
            carpeta_ventas_2026 = st.text_input(
                "Carpeta Ventas 2026",
                value=r"C:\Users\pc\OneDrive\Escritorio\2026\LIBRO VENTAS",
            )
            carpeta_compras_2025 = st.text_input(
                "Carpeta Compras 2025",
                value=r"C:\Users\pc\OneDrive\Escritorio\2025\COMPRAS 2025",
            )
            carpeta_compras_2026 = st.text_input(
                "Carpeta Compras 2026",
                value=r"C:\Users\pc\OneDrive\Escritorio\2026\LIBRO COMPRA",
            )
            carpeta_rrhh_2025 = st.text_input(
                "Carpeta RRHH 2025",
                value=r"C:\Users\pc\OneDrive\Escritorio\2025\REMUNERACIONES 2025",
            )
            carpeta_rrhh_2026 = st.text_input(
                "Carpeta RRHH 2026",
                value=r"C:\Users\pc\OneDrive\Escritorio\2026\LIBRO REMUNERACIONES",
            )

    if st.button("🔄 Recargar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    umbral = st.slider("Umbral Pareto (%)", 50, 95, 80, 5) / 100


# ── Carga de datos ────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Cargando ventas...")
def get_ventas(c2025, c2026):
    return cargar_ventas([c2025, c2026])

@st.cache_data(show_spinner="Cargando compras...")
def get_compras(c2025, c2026):
    return cargar_compras([c2025, c2026])

@st.cache_data(show_spinner="Cargando RRHH...")
def get_rrhh(c2025, c2026):
    import pandas as pd
    frames = []
    for c in [c2025, c2026]:
        df = cargar_rrhh(c)
        if not df.empty:
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

df_ventas = get_ventas(carpeta_ventas_2025, carpeta_ventas_2026)
df_compras = get_compras(carpeta_compras_2025, carpeta_compras_2026)
df_rrhh = get_rrhh(carpeta_rrhh_2025, carpeta_rrhh_2026)

anios_v = sorted(df_ventas["anio"].unique().tolist()) if not df_ventas.empty else []
anios_c = sorted(df_compras["anio"].unique().tolist()) if not df_compras.empty else []
anios_r = sorted(df_rrhh["anio"].unique().tolist()) if not df_rrhh.empty else []
anios_todos = sorted(set(anios_v + anios_c + anios_r))

if not anios_todos:
    st.warning("No se encontraron archivos. Verifica las carpetas en el panel lateral.")
    st.stop()

with st.sidebar:
    anios_disp = [a for a in anios_todos if a >= 2025]
    anios_sel = st.multiselect("Años a comparar", anios_disp, default=anios_disp)

if not anios_sel:
    st.info("Selecciona al menos un año en el panel lateral.")
    st.stop()


# ── Helpers de visualización ──────────────────────────────────────────────────
def grafico_mensual(pivot: pd.DataFrame):
    fig = go.Figure()
    for i, anio in enumerate(sorted(pivot.columns)):
        fig.add_trace(go.Bar(
            name=str(anio),
            x=pivot.index.tolist(),
            y=pivot[anio].tolist(),
            marker_color=COLORES[i % len(COLORES)],
            text=[f"${v:,.0f}" for v in pivot[anio]],
            textposition="outside",
            textfont=dict(size=10),
        ))
    fig.update_layout(
        barmode="group",
        xaxis_title="Mes",
        yaxis_tickformat="$,.0f",
        legend_title="Año",
        height=400,
        margin=dict(t=20, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def grafico_barras_h(df_rank, entidad_col, chart_key, valor_col="monto_neto"):
    nombres = df_rank[entidad_col].tolist()[:25]
    montos = df_rank[valor_col].tolist()[:25]
    fig = go.Figure(go.Bar(
        x=montos, y=nombres, orientation="h",
        marker_color="#1f77b4",
        text=[f"${v:,.0f}" for v in montos],
        textposition="outside",
    ))
    fig.update_layout(
        yaxis=dict(autorange="reversed"),
        xaxis_tickformat="$,.0f",
        height=max(250, len(nombres) * 30),
        margin=dict(t=10, b=10, l=10, r=80),
    )
    st.plotly_chart(fig, use_container_width=True, key=chart_key)


def tabla_ranking(df_rank, entidad_col, label):
    t = df_rank[[entidad_col, "rut", "monto_neto", "pct"]].copy()
    t.columns = [label.capitalize(), "RUT", "Monto Neto", "% Total"]
    t["Monto Neto"] = t["Monto Neto"].map("${:,.0f}".format)
    t["% Total"] = t["% Total"].map("{:.1%}".format)
    st.dataframe(t, use_container_width=True, hide_index=True)


def _render_pareto_anio(df, anio, entidad_col, label, umbral, key):
    top, otros, total = ranking_pareto(df, [anio], entidad_col, umbral)
    st.markdown(f"**Top {label}s {anio} — {int(umbral*100)}% del total**")
    grafico_barras_h(top, entidad_col, chart_key=f"{key}_top_{anio}")
    tabla_ranking(top, entidad_col, label)
    monto_otros = otros["monto_neto"].sum()
    pct_otros = monto_otros / total if total > 0 else 0
    with st.expander(f"📦 Otros ({len(otros)} {label}s) — ${monto_otros:,.0f} ({pct_otros:.1%})"):
        if not otros.empty:
            grafico_barras_h(otros, entidad_col, chart_key=f"{key}_otros_{anio}")
            tabla_ranking(otros, entidad_col, label)


def render_pareto(df, anios, entidad_col, label, umbral, key):
    anios_ord = sorted(anios)
    if len(anios_ord) == 1:
        _render_pareto_anio(df, anios_ord[0], entidad_col, label, umbral, key)
    else:
        cols = st.columns(len(anios_ord))
        for col, a in zip(cols, anios_ord):
            with col:
                _render_pareto_anio(df, a, entidad_col, label, umbral, key)


def render_modulo(df, anios, entidad_col, label, umbral, key):
    datos = df[df["anio"].isin(anios)]
    anios_ord = sorted(anios)

    # Una fila de métricas por año
    for i, a in enumerate(anios_ord):
        d = datos[datos["anio"] == a]
        prev = datos[datos["anio"] == anios_ord[i-1]] if i > 0 else None
        total_a = d["monto_neto"].sum()
        prev_total = prev["monto_neto"].sum() if prev is not None else None
        delta = f"{((total_a - prev_total) / prev_total * 100):+.1f}%" if prev_total else None
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Total Neto {a}", f"${total_a:,.0f}", delta)
        c2.metric(f"{label.capitalize()}s únicos {a}", d["rut"].nunique())
        c3.metric(f"Docs {a}", len(d))

    st.subheader("Evolución mensual")
    pivot = resumen_mensual(df, anios)
    grafico_mensual(pivot)

    st.divider()
    st.subheader(f"Ranking por {label} — Pareto {int(umbral*100)}/{100-int(umbral*100)}")
    render_pareto(df, anios, entidad_col, label, umbral, key)


def render_resumen(df_v, df_c, df_r, anios):
    anios = sorted(anios)

    def _pivot_concepto(df, valor_col):
        """Retorna pivot mes x año para un concepto."""
        if df.empty:
            return pd.DataFrame()
        filtrado = df[df["anio"].isin(anios)]
        pivot = (
            filtrado.groupby(["mes", "anio"])[valor_col]
            .sum()
            .reset_index()
            .pivot(index="mes", columns="anio", values=valor_col)
            .fillna(0)
        )
        pivot.index = pivot.index.map(_nombre_mes)
        return pivot

    pv_v = _pivot_concepto(df_v, "monto_neto")
    pv_c = _pivot_concepto(df_c, "monto_neto")
    pv_r = _pivot_concepto(df_r, "costo_empresa")

    # Meses presentes en orden
    meses_idx = sorted(
        set(pv_v.index) | set(pv_c.index) | set(pv_r.index),
        key=lambda m: MESES.index(m) if m in MESES else 99,
    )

    def _alinear(pivot):
        return pivot.reindex(meses_idx).fillna(0) if not pivot.empty else pd.DataFrame(0, index=meses_idx, columns=anios)

    pv_v = _alinear(pv_v)
    pv_c = _alinear(pv_c)
    pv_r = _alinear(pv_r)

    def _variacion(pivot):
        """% variación entre último y penúltimo año."""
        if len(pivot.columns) < 2:
            return None
        a1, a2 = pivot.columns[-2], pivot.columns[-1]
        var = ((pivot[a2] - pivot[a1]) / pivot[a1].replace(0, float("nan"))) * 100
        return var

    def _tabla_concepto(titulo, pivot, color_neg_es_malo=True):
        st.markdown(f"**{titulo}**")
        tabla = pivot.copy()
        tabla.columns = [str(a) for a in tabla.columns]
        # Fila total
        total_row = tabla.sum().rename("TOTAL")
        tabla = pd.concat([tabla, total_row.to_frame().T])

        if len(pivot.columns) >= 2:
            a1, a2 = str(pivot.columns[-2]), str(pivot.columns[-1])
            v1 = tabla[a1].replace(0, float("nan"))
            tabla["Var %"] = ((tabla[a2] - tabla[a1]) / v1 * 100).round(1).map(
                lambda x: f"{x:+.1f}%" if pd.notna(x) else "—"
            )

        def _fmt_num(v):
            try:
                return f"${float(v):,.0f}"
            except Exception:
                return v

        def _color_var(val):
            try:
                n = float(str(val).replace("%", "").replace("+", ""))
                bueno = n >= 0 if color_neg_es_malo else n <= 0
                return "color: #198754" if bueno else "color: #dc3545"
            except Exception:
                return ""

        cols_num = [c for c in tabla.columns if c != "Var %"]
        tabla_fmt = tabla.copy()
        tabla_fmt[cols_num] = tabla_fmt[cols_num].map(_fmt_num)

        styled = tabla_fmt.style.set_properties(**{"text-align": "right"})
        if "Var %" in tabla_fmt.columns:
            styled = styled.map(_color_var, subset=["Var %"])
        styled = styled.set_table_styles([
            {"selector": "th", "props": [("text-align", "center"), ("background-color", "#f0f2f6")]},
            {"selector": "tr:last-child", "props": [("font-weight", "bold"), ("background-color", "#e8eaf6")]},
        ])
        st.dataframe(styled, use_container_width=True)

    # ── Tabla Resultado ────────────────────────────────────────────────────────
    pv_res = pd.DataFrame(index=meses_idx)
    for a in anios:
        v = pv_v[a] if a in pv_v.columns else 0
        c = pv_c[a] if a in pv_c.columns else 0
        r = pv_r[a] if a in pv_r.columns else 0
        pv_res[a] = v - c - r

    def _delta(nuevo, viejo):
        if viejo and viejo != 0:
            return f"{((nuevo - viejo) / abs(viejo)) * 100:+.1f}%"
        return None

    # Métricas por cada año seleccionado
    for i, a in enumerate(anios):
        ant = anios[i-1] if i > 0 else None
        tot_v   = pv_v[a].sum()   if a in pv_v.columns   else 0
        tot_c   = pv_c[a].sum()   if a in pv_c.columns   else 0
        tot_r   = pv_r[a].sum()   if a in pv_r.columns   else 0
        tot_res = pv_res[a].sum() if a in pv_res.columns else 0
        v_ant   = pv_v[ant].sum()   if ant and ant in pv_v.columns   else None
        c_ant   = pv_c[ant].sum()   if ant and ant in pv_c.columns   else None
        res_ant = pv_res[ant].sum() if ant and ant in pv_res.columns else None

        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"Ventas {a}",    f"${tot_v:,.0f}",   _delta(tot_v, v_ant))
        c2.metric(f"Compras {a}",   f"${tot_c:,.0f}",   _delta(tot_c, c_ant))
        c3.metric(f"RRHH {a}",      f"${tot_r:,.0f}")
        c4.metric(f"Resultado {a}", f"${tot_res:,.0f}", _delta(tot_res, res_ant))

    st.divider()

    # ── Tablas en una sola fila horizontal ───────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        _tabla_concepto("📈 Ventas", pv_v, color_neg_es_malo=False)
    with col2:
        _tabla_concepto("📉 Compras", pv_c, color_neg_es_malo=True)
    with col3:
        _tabla_concepto("👥 RRHH", pv_r, color_neg_es_malo=True)
    with col4:
        _tabla_concepto("💰 Resultado", pv_res, color_neg_es_malo=False)


def _nombre_mes(n):
    return MESES[n - 1] if 1 <= n <= 12 else str(n)


def render_rrhh(df, anios, umbral):
    datos = df[df["anio"].isin(anios)]
    anios_ord = sorted(anios)

    # Una fila de métricas por año
    for i, a in enumerate(anios_ord):
        d = datos[datos["anio"] == a]
        prev = datos[datos["anio"] == anios_ord[i-1]] if i > 0 else None
        costo_a = d["costo_empresa"].sum()
        prev_costo = prev["costo_empresa"].sum() if prev is not None else None
        delta = f"{((costo_a - prev_costo) / prev_costo * 100):+.1f}%" if prev_costo else None
        liq_a = d["liquido"].sum() if "liquido" in d.columns else 0
        emp_a = d["empleado"].nunique()
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Costo Empresa {a}", f"${costo_a:,.0f}", delta)
        c2.metric(f"Líquido Pagado {a}", f"${liq_a:,.0f}")
        c3.metric(f"Empleados únicos {a}", emp_a)

    # ── Evolución mensual ──────────────────────────────────────────────────────
    st.subheader("Evolución mensual — Costo Empresa")
    pivot = resumen_mensual_rrhh(df, anios)
    grafico_mensual(pivot)

    # ── Centro de costo ────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Costo por Centro de Costo")
    cc = resumen_por_centro_costo(df, anios)
    fig_cc = go.Figure(go.Bar(
        x=cc["costo_empresa"].tolist(),
        y=cc["centro_costo"].tolist(),
        orientation="h",
        marker_color="#2ca02c",
        text=[f"${v:,.0f}" for v in cc["costo_empresa"]],
        textposition="outside",
    ))
    fig_cc.update_layout(
        yaxis=dict(autorange="reversed"),
        xaxis_tickformat="$,.0f",
        height=max(200, len(cc) * 40),
        margin=dict(t=10, b=10),
    )
    st.plotly_chart(fig_cc, use_container_width=True)

    t = cc[["centro_costo", "costo_empresa", "liquido", "imponible"]].copy()
    t.columns = ["Centro Costo", "Costo Empresa", "Líquido", "Imponible"]
    for col in ["Costo Empresa", "Líquido", "Imponible"]:
        t[col] = t[col].map("${:,.0f}".format)
    st.dataframe(t, use_container_width=True, hide_index=True)

    # ── Ranking empleados Pareto ───────────────────────────────────────────────
    st.divider()
    st.subheader(f"Ranking Empleados — Pareto {int(umbral*100)}/{100-int(umbral*100)}")
    top, otros, total = ranking_empleados(df, anios, umbral)

    st.markdown(f"**Top empleados — {int(umbral*100)}% del costo**")
    grafico_barras_h(top, "empleado", chart_key="r_top", valor_col="costo_empresa")
    t2 = top[["empleado", "costo_empresa", "pct"]].copy()
    t2.columns = ["Empleado", "Costo Empresa", "% Total"]
    t2["Costo Empresa"] = t2["Costo Empresa"].map("${:,.0f}".format)
    t2["% Total"] = t2["% Total"].map("{:.1%}".format)
    st.dataframe(t2, use_container_width=True, hide_index=True)

    monto_otros = otros["costo_empresa"].sum()
    pct_otros = monto_otros / total if total > 0 else 0
    with st.expander(f"📦 Otros ({len(otros)} empleados) — ${monto_otros:,.0f} ({pct_otros:.1%})"):
        if not otros.empty:
            grafico_barras_h(otros, "empleado", chart_key="r_otros", valor_col="costo_empresa")
            t3 = otros[["empleado", "costo_empresa", "pct"]].copy()
            t3.columns = ["Empleado", "Costo Empresa", "% Total"]
            t3["Costo Empresa"] = t3["Costo Empresa"].map("${:,.0f}".format)
            t3["% Total"] = t3["% Total"].map("{:.1%}".format)
            st.dataframe(t3, use_container_width=True, hide_index=True)


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_res, tab_v, tab_c, tab_r = st.tabs(["📋 Resumen", "📈 Ventas", "📉 Compras", "👥 RRHH"])

with tab_res:
    render_resumen(df_ventas, df_compras, df_rrhh, anios_sel)

with tab_v:
    if df_ventas.empty:
        st.warning("No hay archivos de ventas en la carpeta indicada.")
    else:
        render_modulo(df_ventas, anios_sel, "cliente", "cliente", umbral, "v")

with tab_c:
    if df_compras.empty:
        st.warning("No hay archivos de compras en la carpeta indicada.")
    else:
        render_modulo(df_compras, anios_sel, "proveedor", "proveedor", umbral, "c")

with tab_r:
    if df_rrhh.empty:
        st.warning("No hay archivos de RRHH en la carpeta indicada.")
    else:
        render_rrhh(df_rrhh, anios_sel, umbral)
