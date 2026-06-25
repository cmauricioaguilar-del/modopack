import pandas as pd
from pathlib import Path


VENTAS_COLS = {
    "Fecha Docto": "fecha",
    "Rut cliente": "rut",
    "Razon Social": "cliente",
    "Monto Neto": "monto_neto",
    "Monto total": "monto_total",
    "Tipo Doc": "tipo_doc",
}

COMPRAS_COLS = {
    "Fecha Docto": "fecha",
    "RUT Proveedor": "rut",
    "Razon Social": "proveedor",
    "Monto Neto": "monto_neto",
    "Tipo Doc": "tipo_doc",
}

# Documentos que suman (facturas)
TIPOS_VENTA_POSITIVOS = {33, 34, 56}
# Documentos que restan (NC, ND)
TIPOS_VENTA_NEGATIVOS = {61, 55}

TIPOS_COMPRA_POSITIVOS = {33, 34, 46, 56, 914}  # 914 = DIN (declaración de ingreso, importaciones)
TIPOS_COMPRA_NEGATIVOS = {61, 55}

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def _leer_csv_sii(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", encoding="latin-1", dtype=str, index_col=False, skip_blank_lines=True)


def _limpiar_monto(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(
        serie.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
        errors="coerce",
    ).fillna(0)


def _procesar(archivos, cols_map, tipos_positivos, tipos_negativos) -> pd.DataFrame:
    frames = []
    for f in archivos:
        try:
            df = _leer_csv_sii(f)
            df.columns = df.columns.str.strip()
            frames.append(df)
        except Exception:
            continue

    if not frames:
        return pd.DataFrame()

    raw = pd.concat(frames, ignore_index=True)
    raw.columns = raw.columns.str.strip()

    cols_presentes = {k: v for k, v in cols_map.items() if k in raw.columns}
    df = raw[list(cols_presentes.keys())].rename(columns=cols_presentes)

    df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True, errors="coerce")
    df["monto_neto"] = _limpiar_monto(df["monto_neto"])
    if "monto_total" in df.columns:
        df["monto_total"] = _limpiar_monto(df["monto_total"])
    df["tipo_doc"] = pd.to_numeric(df["tipo_doc"], errors="coerce")

    todos_validos = tipos_positivos | tipos_negativos
    df = df[df["tipo_doc"].isin(todos_validos)].copy()

    # NC y ND restan — invertir signo
    mask_neg = df["tipo_doc"].isin(tipos_negativos)
    df.loc[mask_neg, "monto_neto"] *= -1
    if "monto_total" in df.columns:
        df.loc[mask_neg, "monto_total"] *= -1

    df = df.dropna(subset=["fecha"])
    df["anio"] = df["fecha"].dt.year
    df["mes"] = df["fecha"].dt.month

    return df.reset_index(drop=True)


def _cargar_resumenes_48(carpetas: list) -> pd.DataFrame:
    """Lee RCV_RESUMEN_VENTA_*.csv y extrae el monto neto del tipo 48 por mes/año."""
    filas = []
    for c in carpetas:
        for f in sorted(Path(c).glob("RCV_RESUMEN_VENTA_*.csv")):
            # Extraer año y mes del nombre: RCV_RESUMEN_VENTA_XXXXXXX_YYYYMM.csv
            m = __import__("re").search(r"(\d{6})\.csv$", f.name)
            if not m:
                continue
            anio, mes = int(m.group(1)[:4]), int(m.group(1)[4:])
            try:
                df = pd.read_csv(f, sep=";", encoding="latin-1", dtype=str,
                                 index_col=False, skip_blank_lines=True)
                df.columns = df.columns.str.strip()
                # Buscar fila tipo 48 (contiene "48" en columna Tipo Documento)
                col_tipo = df.columns[0]
                fila48 = df[df[col_tipo].str.contains(r"\(48\)", na=False)]
                if fila48.empty:
                    continue
                neto = _limpiar_monto(fila48["Monto Neto"]).iloc[0]
                filas.append({
                    "fecha": None, "rut": "boletas-48",
                    "cliente": "Boletas / Comprobantes (48)",
                    "monto_neto": neto, "tipo_doc": 48,
                    "anio": anio, "mes": mes,
                })
            except Exception:
                continue
    if not filas:
        return pd.DataFrame()
    return pd.DataFrame(filas)


def cargar_ventas(carpetas: list) -> pd.DataFrame:
    archivos = []
    for c in carpetas:
        archivos += sorted(Path(c).glob("RCV_VENTA_*.csv"))
    df_det = _procesar(archivos, VENTAS_COLS, TIPOS_VENTA_POSITIVOS, TIPOS_VENTA_NEGATIVOS)
    df_48 = _cargar_resumenes_48(carpetas)
    if df_48.empty:
        return df_det
    return pd.concat([df_det, df_48], ignore_index=True)


def cargar_compras(carpetas: list) -> pd.DataFrame:
    archivos = []
    for c in carpetas:
        archivos += sorted(Path(c).glob("RCV_COMPRA_REGISTRO_*.csv"))
    return _procesar(archivos, COMPRAS_COLS, TIPOS_COMPRA_POSITIVOS, TIPOS_COMPRA_NEGATIVOS)


def resumen_mensual(df: pd.DataFrame, anios: list) -> pd.DataFrame:
    filtrado = df[df["anio"].isin(anios)]
    pivot = (
        filtrado.groupby(["anio", "mes"])["monto_neto"]
        .sum()
        .reset_index()
        .pivot(index="mes", columns="anio", values="monto_neto")
        .fillna(0)
    )
    pivot.index = pivot.index.map(_nombre_mes)
    return pivot


def ranking_pareto(df: pd.DataFrame, anios: list, entidad_col: str, umbral: float = 0.80):
    """Retorna (top_df, otros_df, total)."""
    filtrado = df[df["anio"].isin(anios)]
    agrupado = (
        filtrado.groupby([entidad_col, "rut"])["monto_neto"]
        .sum()
        .reset_index()
        .sort_values("monto_neto", ascending=False)
        .reset_index(drop=True)
    )
    total = agrupado["monto_neto"].sum()
    agrupado["acumulado"] = agrupado["monto_neto"].cumsum()
    agrupado["pct_acumulado"] = agrupado["acumulado"] / total if total > 0 else 0
    agrupado["pct"] = agrupado["monto_neto"] / total if total > 0 else 0

    corte = agrupado["pct_acumulado"].searchsorted(umbral)
    corte = min(corte + 1, len(agrupado))

    top = agrupado.iloc[:corte].copy()
    otros = agrupado.iloc[corte:].copy()

    return top, otros, total


def _nombre_mes(n: int) -> str:
    return MESES[n - 1] if 1 <= n <= 12 else str(n)
