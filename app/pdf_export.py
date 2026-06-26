"""Generación de PDFs en formato horizontal (landscape A4) por pestaña."""
import io
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from processor import ranking_pareto, resumen_mensual
from processor_rrhh import (
    ranking_empleados, resumen_mensual_rrhh, resumen_por_centro_costo,
)

PAGE_W, PAGE_H = landscape(A4)
MARGIN = 1.2 * cm
USABLE_W = PAGE_W - 2 * MARGIN
# Padding aplicado a cada celda de tablas exteriores (izq + der)
_CELL_PAD = 8

COLORES = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

_STYLES = getSampleStyleSheet()
_H2 = ParagraphStyle("h2", fontSize=9, fontName="Helvetica-Bold", spaceBefore=4, spaceAfter=2)


def _nombre_mes(n):
    return MESES[n - 1] if 1 <= n <= 12 else str(n)


def _fig_bytes(fig, w=800, h=250):
    try:
        raw = fig.to_image(format="png", width=w, height=h, scale=2)
        return io.BytesIO(raw)
    except Exception:
        return None


def _new_doc(buf, title=""):
    return SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
        title=title,
    )


def _header(titulo_tab):
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    data = [["Control de Gestión · Modopack", titulo_tab, fecha]]
    t = Table(data, colWidths=[USABLE_W * 0.4, USABLE_W * 0.4, USABLE_W * 0.2])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a6b8a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("LEFTPADDING", (0, 0), (-1, 0), 8),
        ("RIGHTPADDING", (0, 0), (-1, 0), 8),
    ]))
    return [t, Spacer(1, 0.3 * cm)]


def _metricas(items):
    """items: list of (label, value) tuples."""
    n = len(items)
    cw = [USABLE_W / n] * n
    t = Table([[i[0] for i in items], [i[1] for i in items]], colWidths=cw)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f2f6")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 11),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
    ]))
    return t


def _df_table(df, font_size=7, header_bg="#1a6b8a", col_widths=None, total_width=None):
    headers = list(df.columns)
    data = [headers] + [list(r) for r in df.itertuples(index=False)]
    n = len(headers)
    if col_widths is None:
        w = total_width or USABLE_W
        col_widths = [w / n] * n
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_bg)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), font_size),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), font_size),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
    ]
    if len(data) > 1 and str(data[-1][0]).upper() == "TOTAL":
        style += [
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8eaf6")),
        ]
    t.setStyle(TableStyle(style))
    return t


def _grafico_fig(pivot):
    fig = go.Figure()
    for i, anio in enumerate(sorted(pivot.columns)):
        fig.add_trace(go.Bar(
            name=str(anio),
            x=pivot.index.tolist(),
            y=pivot[anio].tolist(),
            marker_color=COLORES[i % len(COLORES)],
            text=[f"${v:,.0f}" for v in pivot[anio]],
            textposition="outside",
            textfont=dict(size=8),
        ))
    fig.update_layout(
        barmode="group",
        yaxis_tickformat="$,.0f",
        legend_title="Año",
        height=280,
        margin=dict(t=10, b=30, l=70, r=10),
        font=dict(size=9),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return fig


def _add_chart(elems, fig):
    # Render at double resolution for sharpness; display at USABLE_W x 180 pt
    img_io = _fig_bytes(fig, w=int(USABLE_W * 2), h=360)
    if img_io:
        elems.append(Image(img_io, width=USABLE_W, height=180))
    elems.append(Spacer(1, 0.2 * cm))


def _pivot_concepto(df, valor_col, anios):
    if df.empty:
        return pd.DataFrame()
    filtrado = df[df["anio"].isin(anios)]
    pivot = (
        filtrado.groupby(["mes", "anio"])[valor_col]
        .sum().reset_index()
        .pivot(index="mes", columns="anio", values=valor_col)
        .fillna(0)
    )
    pivot.index = pivot.index.map(_nombre_mes)
    return pivot


def _tabla_concepto_df(pivot, anios):
    tabla = pivot.copy()
    tabla.columns = [str(a) for a in tabla.columns]
    total_row = tabla.sum().rename("TOTAL")
    tabla = pd.concat([tabla, total_row.to_frame().T])
    if len(anios) >= 2:
        a1, a2 = str(anios[-2]), str(anios[-1])
        if a1 in tabla.columns and a2 in tabla.columns:
            v1 = tabla[a1].replace(0, float("nan"))
            tabla["Var %"] = ((tabla[a2] - tabla[a1]) / v1 * 100).round(1).map(
                lambda x: f"{x:+.1f}%" if pd.notna(x) else "—"
            )
    for col in [c for c in tabla.columns if c != "Var %"]:
        tabla[col] = tabla[col].map(lambda v: f"${float(v):,.0f}" if pd.notna(v) else "—")
    tabla.insert(0, "Mes", tabla.index)
    return tabla.reset_index(drop=True)


def _concepto_col_widths(df, inner_w):
    """Col widths for a concepto table, summing to inner_w."""
    n = len(df.columns)
    mes_w = inner_w * 0.28
    rest_w = (inner_w - mes_w) / (n - 1) if n > 1 else inner_w
    return [mes_w] + [rest_w] * (n - 1)


def _outer_table(rows_of_cells, col_widths):
    """Build a multi-column outer Table. Cells must be plain lists, not KeepTogether."""
    t = Table(rows_of_cells, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


# ── PDF Resumen ────────────────────────────────────────────────────────────────

def generar_pdf_resumen(df_v, df_c, df_r, anios, rol="admin"):
    buf = io.BytesIO()
    doc = _new_doc(buf, "Resumen")
    anios = sorted(anios)

    pv_v = _pivot_concepto(df_v, "monto_neto", anios)
    pv_c = _pivot_concepto(df_c, "monto_neto", anios)
    pv_r = _pivot_concepto(df_r, "costo_empresa", anios) if (rol == "admin" and not df_r.empty) else pd.DataFrame()

    all_idx = set(pv_v.index) | set(pv_c.index)
    if not pv_r.empty:
        all_idx |= set(pv_r.index)
    meses_idx = sorted(all_idx, key=lambda m: MESES.index(m) if m in MESES else 99)

    def _al(pivot):
        return pivot.reindex(meses_idx).fillna(0) if not pivot.empty else pd.DataFrame(0, index=meses_idx, columns=anios)

    pv_v = _al(pv_v)
    pv_c = _al(pv_c)
    if rol == "admin":
        pv_r = _al(pv_r)

    elems = _header("Resumen")

    # Métricas
    items = []
    for a in anios:
        tot_v = pv_v[a].sum() if a in pv_v.columns else 0
        tot_c = pv_c[a].sum() if a in pv_c.columns else 0
        items += [(f"Ventas {a}", f"${tot_v:,.0f}"), (f"Compras {a}", f"${tot_c:,.0f}")]
        if rol == "admin":
            tot_r = pv_r[a].sum() if a in pv_r.columns else 0
            tot_res = tot_v - tot_c - tot_r
            items += [(f"RRHH {a}", f"${tot_r:,.0f}"), (f"Resultado {a}", f"${tot_res:,.0f}")]
    elems.append(_metricas(items))
    elems.append(Spacer(1, 0.4 * cm))

    ventas_df = _tabla_concepto_df(pv_v, anios)
    compras_df = _tabla_concepto_df(pv_c, anios)

    if rol == "admin":
        pv_res = pd.DataFrame(index=meses_idx)
        for a in anios:
            v = pv_v[a] if a in pv_v.columns else 0
            c = pv_c[a] if a in pv_c.columns else 0
            r = pv_r[a] if a in pv_r.columns else 0
            pv_res[a] = v - c - r
        rrhh_df = _tabla_concepto_df(pv_r, anios)
        res_df = _tabla_concepto_df(pv_res, anios)

        cw = USABLE_W / 4
        inner_w = cw - _CELL_PAD
        # Plain lists in cells — NO KeepTogether (causes unbounded height in reportlab)
        outer = _outer_table([[
            [Paragraph("📈 Ventas", _H2), _df_table(ventas_df, font_size=6, col_widths=_concepto_col_widths(ventas_df, inner_w))],
            [Paragraph("📉 Compras", _H2), _df_table(compras_df, font_size=6, col_widths=_concepto_col_widths(compras_df, inner_w))],
            [Paragraph("👥 RRHH", _H2), _df_table(rrhh_df, font_size=6, col_widths=_concepto_col_widths(rrhh_df, inner_w))],
            [Paragraph("💰 Resultado", _H2), _df_table(res_df, font_size=6, col_widths=_concepto_col_widths(res_df, inner_w))],
        ]], [cw] * 4)
    else:
        cw = USABLE_W / 2
        inner_w = cw - _CELL_PAD
        outer = _outer_table([[
            [Paragraph("📈 Ventas", _H2), _df_table(ventas_df, font_size=7, col_widths=_concepto_col_widths(ventas_df, inner_w))],
            [Paragraph("📉 Compras", _H2), _df_table(compras_df, font_size=7, col_widths=_concepto_col_widths(compras_df, inner_w))],
        ]], [cw] * 2)

    elems.append(outer)
    doc.build(elems)
    buf.seek(0)
    return buf.read()


# ── PDF Ventas ─────────────────────────────────────────────────────────────────

def generar_pdf_ventas(df, anios, umbral=0.80):
    buf = io.BytesIO()
    doc = _new_doc(buf, "Ventas")
    anios = sorted(anios)
    datos = df[df["anio"].isin(anios)]

    elems = _header("Ventas")

    items = []
    for a in anios:
        d = datos[datos["anio"] == a]
        items += [
            (f"Total Neto {a}", f"${d['monto_neto'].sum():,.0f}"),
            (f"Clientes únicos {a}", str(d["rut"].nunique())),
            (f"Documentos {a}", str(len(d))),
        ]
    elems.append(_metricas(items))
    elems.append(Spacer(1, 0.3 * cm))

    elems.append(Paragraph("Evolución Mensual", _H2))
    pivot = resumen_mensual(df, anios)
    _add_chart(elems, _grafico_fig(pivot))

    elems.append(Paragraph(f"Ranking Clientes — Pareto {int(umbral*100)}/{100-int(umbral*100)}", _H2))
    n = len(anios)
    cw = USABLE_W / n
    inner_w = cw - _CELL_PAD
    cols = []
    for a in anios:
        top, _, _ = ranking_pareto(df, [a], "cliente", umbral)
        t = top[["cliente", "rut", "monto_neto", "pct"]].head(15).copy()
        t.columns = ["Cliente", "RUT", "Monto Neto", "% Total"]
        t["Monto Neto"] = t["Monto Neto"].map("${:,.0f}".format)
        t["% Total"] = t["% Total"].map("{:.1%}".format)
        cols.append([
            Paragraph(f"Top Clientes {a}", _H2),
            _df_table(t, font_size=6, col_widths=[inner_w*0.45, inner_w*0.20, inner_w*0.21, inner_w*0.14]),
        ])
    elems.append(_outer_table([cols], [cw] * n))

    doc.build(elems)
    buf.seek(0)
    return buf.read()


# ── PDF Compras ────────────────────────────────────────────────────────────────

def generar_pdf_compras(df, anios, umbral=0.80):
    buf = io.BytesIO()
    doc = _new_doc(buf, "Compras")
    anios = sorted(anios)
    datos = df[df["anio"].isin(anios)]

    elems = _header("Compras")

    items = []
    for a in anios:
        d = datos[datos["anio"] == a]
        items += [
            (f"Total Neto {a}", f"${d['monto_neto'].sum():,.0f}"),
            (f"Proveedores únicos {a}", str(d["rut"].nunique())),
            (f"Documentos {a}", str(len(d))),
        ]
    elems.append(_metricas(items))
    elems.append(Spacer(1, 0.3 * cm))

    elems.append(Paragraph("Evolución Mensual", _H2))
    pivot = resumen_mensual(df, anios)
    _add_chart(elems, _grafico_fig(pivot))

    elems.append(Paragraph(f"Ranking Proveedores — Pareto {int(umbral*100)}/{100-int(umbral*100)}", _H2))
    n = len(anios)
    cw = USABLE_W / n
    inner_w = cw - _CELL_PAD
    cols = []
    for a in anios:
        top, _, _ = ranking_pareto(df, [a], "proveedor", umbral)
        t = top[["proveedor", "rut", "monto_neto", "pct"]].head(15).copy()
        t.columns = ["Proveedor", "RUT", "Monto Neto", "% Total"]
        t["Monto Neto"] = t["Monto Neto"].map("${:,.0f}".format)
        t["% Total"] = t["% Total"].map("{:.1%}".format)
        cols.append([
            Paragraph(f"Top Proveedores {a}", _H2),
            _df_table(t, font_size=6, col_widths=[inner_w*0.45, inner_w*0.20, inner_w*0.21, inner_w*0.14]),
        ])
    elems.append(_outer_table([cols], [cw] * n))

    doc.build(elems)
    buf.seek(0)
    return buf.read()


# ── PDF RRHH ──────────────────────────────────────────────────────────────────

def generar_pdf_rrhh(df, anios, umbral=0.80):
    buf = io.BytesIO()
    doc = _new_doc(buf, "RRHH")
    anios = sorted(anios)
    datos = df[df["anio"].isin(anios)]

    elems = _header("RRHH — Remuneraciones")

    items = []
    for a in anios:
        d = datos[datos["anio"] == a]
        liq = d["liquido"].sum() if "liquido" in d.columns else 0
        items += [
            (f"Costo Empresa {a}", f"${d['costo_empresa'].sum():,.0f}"),
            (f"Líquido Pagado {a}", f"${liq:,.0f}"),
            (f"Empleados únicos {a}", str(d["empleado"].nunique())),
        ]
    elems.append(_metricas(items))
    elems.append(Spacer(1, 0.3 * cm))

    elems.append(Paragraph("Evolución Mensual — Costo Empresa", _H2))
    pivot = resumen_mensual_rrhh(df, anios)
    _add_chart(elems, _grafico_fig(pivot))

    cw_l = USABLE_W * 0.45
    cw_r = USABLE_W * 0.55
    inner_l = cw_l - _CELL_PAD
    inner_r = cw_r - _CELL_PAD

    cc = resumen_por_centro_costo(df, anios)
    t_cc = cc[["centro_costo", "costo_empresa", "liquido", "imponible"]].copy()
    t_cc.columns = ["Centro Costo", "Costo Empresa", "Líquido", "Imponible"]
    for col in ["Costo Empresa", "Líquido", "Imponible"]:
        t_cc[col] = t_cc[col].map("${:,.0f}".format)

    top, _, _ = ranking_empleados(df, anios, umbral)
    t_emp = top[["empleado", "costo_empresa", "pct"]].head(20).copy()
    t_emp.columns = ["Empleado", "Costo Empresa", "% Total"]
    t_emp["Costo Empresa"] = t_emp["Costo Empresa"].map("${:,.0f}".format)
    t_emp["% Total"] = t_emp["% Total"].map("{:.1%}".format)

    elems.append(_outer_table([[
        [Paragraph("Costo por Centro de Costo", _H2),
         _df_table(t_cc, font_size=7, col_widths=[inner_l*0.4, inner_l*0.2, inner_l*0.2, inner_l*0.2])],
        [Paragraph(f"Ranking Empleados — Pareto {int(umbral*100)}/{100-int(umbral*100)}", _H2),
         _df_table(t_emp, font_size=7, col_widths=[inner_r*0.55, inner_r*0.30, inner_r*0.15])],
    ]], [cw_l, cw_r]))

    doc.build(elems)
    buf.seek(0)
    return buf.read()
