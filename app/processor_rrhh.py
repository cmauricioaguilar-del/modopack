import pandas as pd
from pathlib import Path
import re

MESES_NOMBRE = {
    "ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12,
}

# Columnas del Excel de remuneraciones que nos interesan
COLS_BASE = {
    "EMPLEADO":                          "empleado",
    "CENTRO COSTO":                       "centro_costo",
    "RENTA IMPONIBLE AFP E ISAPRE":       "renta_imponible",
    "IMPONIBLE":                          "imponible",
    "SUELDO BASE":                        "sueldo_base",
    "GRATIFICACIÓN LEGAL":           "gratificacion",
    "BONOS":                              "bonos",
    "NO IMPONIBLE":                       "no_imponible",
    "MOVILIZACIÓN":                  "movilizacion",
    "COLACIÓN":                      "colacion",
    "LÍQUIDO A PAGAR":               "liquido",
    "SEGURO DE CESANTÍA EMPRESA":    "sc_empresa",
    "MUTUAL DE SEGURIDAD":                "mutual",
    "SIS EMPRESA":                        "sis",
    "ADICIONAL AFP EMPRESA":              "afp_adicional",
}

# Fallback para columnas con encoding roto (latin-1 mal interpretado)
COLS_FALLBACK = {
    "GRATIFICACI� N LEGAL":     "gratificacion",
    "NO IMPONIBLE":                  "no_imponible",
    "MOVILIZACI� N":            "movilizacion",
    "COLACI� N":                "colacion",
    "L� QUIDO A PAGAR":        "liquido",
    "SEGURO DE CESANT� A EMPRESA": "sc_empresa",
}


def _mes_anio_desde_nombre(nombre: str, carpeta: str = ""):
    """Extrae (mes, anio) desde nombres variados de remuneraciones."""
    n = nombre.upper()

    # Caso 1: mes + año 4 dígitos  →  FEB2025
    m = re.search(r"([A-Z]{3})(\d{4})", n)
    if m:
        mes = MESES_NOMBRE.get(m.group(1))
        anio = int(m.group(2))
        if mes and 2000 <= anio <= 2100:
            return mes, anio

    # Caso 2: mes + año 2 dígitos  →  ENE25  (no seguido de otro dígito)
    m = re.search(r"([A-Z]{3})(\d{2})(?!\d)", n)
    if m:
        mes = MESES_NOMBRE.get(m.group(1))
        anio = 2000 + int(m.group(2))
        if mes:
            return mes, anio

    # Caso 3: sin año en el nombre  →  04 REM ABR.xlsx
    # Intenta obtener el mes del número inicial y el año de la carpeta
    m_num = re.search(r"^(\d{2})", nombre)
    m_anio_carpeta = re.search(r"(20\d{2})", carpeta)
    if m_num and m_anio_carpeta:
        num = int(m_num.group(1))
        if 1 <= num <= 12:
            return num, int(m_anio_carpeta.group(1))

    # Caso 4: nombre tipo 01ENE26 (dígitos + mes + año 2d)
    m = re.search(r"\d{2}([A-Z]{3})(\d{2})", n)
    if m:
        mes = MESES_NOMBRE.get(m.group(1))
        anio = 2000 + int(m.group(2))
        if mes:
            return mes, anio

    return None, None


def _leer_excel_sii(path) -> pd.DataFrame:
    """Lee un Excel de remuneraciones detectando automáticamente la fila de encabezado."""
    probe = pd.read_excel(path, header=None, dtype=str, nrows=15)
    header_row = 0
    for i, row in probe.iterrows():
        vals = [str(v).upper().strip() for v in row.dropna()]
        if "EMPLEADO" in vals:
            header_row = i
            break
    raw = pd.read_excel(path, header=header_row, dtype=str)
    raw.columns = [str(c).strip().upper() if not isinstance(c, float) else f"_COL_{i}"
                   for i, c in enumerate(raw.columns)]
    return raw


def _limpiar_num(serie: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(serie):
        return serie.fillna(0)
    return pd.to_numeric(serie, errors="coerce").fillna(0)


def cargar_rrhh(carpeta: str) -> pd.DataFrame:
    archivos = sorted(Path(carpeta).glob("*.xlsx"))
    frames = []

    for f in archivos:
        mes, anio = _mes_anio_desde_nombre(f.name, str(f.parent))
        if not mes or not anio:
            continue
        try:
            raw = _leer_excel_sii(f)
        except Exception:
            continue

        # Mapeo flexible: busca columna original en COLS_BASE (ignorando encoding)
        cols_map = {}
        for col_orig, col_dest in COLS_BASE.items():
            # Coincidencia exacta primero
            if col_orig.upper() in raw.columns:
                cols_map[col_orig.upper()] = col_dest
                continue
            # Búsqueda por similitud (ignora chars especiales)
            key_clean = re.sub(r"[^A-Z ]", "", col_orig.upper())
            for c in raw.columns:
                c_clean = re.sub(r"[^A-Z ]", "", c.upper())
                if key_clean == c_clean and c not in cols_map:
                    cols_map[c] = col_dest
                    break

        df = raw[list(cols_map.keys())].rename(columns=cols_map)

        # Limpiar numéricos
        for col in df.columns:
            if col not in ("empleado", "centro_costo"):
                df[col] = _limpiar_num(df[col])

        # Eliminar filas sin empleado (totales, vacías)
        if "empleado" in df.columns:
            df = df[df["empleado"].notna() & (df["empleado"].str.strip() != "")]

        # costo_empresa = suma directa de RENTA IMPONIBLE AFP E ISAPRE
        if "renta_imponible" in df.columns:
            df["costo_empresa"] = df["renta_imponible"]
        elif "imponible" in df.columns:
            df["costo_empresa"] = df["imponible"]
        else:
            df["costo_empresa"] = 0

        df["mes"] = mes
        df["anio"] = anio
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def resumen_mensual_rrhh(df: pd.DataFrame, anios: list) -> pd.DataFrame:
    filtrado = df[df["anio"].isin(anios)]
    pivot = (
        filtrado.groupby(["anio", "mes"])["costo_empresa"]
        .sum()
        .reset_index()
        .pivot(index="mes", columns="anio", values="costo_empresa")
        .fillna(0)
    )
    from processor import _nombre_mes
    pivot.index = pivot.index.map(_nombre_mes)
    return pivot


def ranking_empleados(df: pd.DataFrame, anios: list, umbral: float = 0.80):
    filtrado = df[df["anio"].isin(anios)]
    agrupado = (
        filtrado.groupby("empleado")["costo_empresa"]
        .sum()
        .reset_index()
        .sort_values("costo_empresa", ascending=False)
        .reset_index(drop=True)
    )
    total = agrupado["costo_empresa"].sum()
    agrupado["acumulado"] = agrupado["costo_empresa"].cumsum()
    agrupado["pct_acumulado"] = agrupado["acumulado"] / total if total > 0 else 0
    agrupado["pct"] = agrupado["costo_empresa"] / total if total > 0 else 0

    corte = agrupado["pct_acumulado"].searchsorted(umbral)
    corte = min(corte + 1, len(agrupado))

    return agrupado.iloc[:corte].copy(), agrupado.iloc[corte:].copy(), total


def resumen_por_centro_costo(df: pd.DataFrame, anios: list) -> pd.DataFrame:
    filtrado = df[df["anio"].isin(anios)]
    return (
        filtrado.groupby("centro_costo")[["costo_empresa", "liquido", "imponible"]]
        .sum()
        .sort_values("costo_empresa", ascending=False)
        .reset_index()
    )
