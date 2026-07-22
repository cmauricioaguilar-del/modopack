"""
Parser para archivos de Flujos: Cuentas por Cobrar (POR_COBRAR.xlsx) y
Cuentas por Pagar (DEUDAS.xlsx).

Las filas resumen (NUM FACTURA == '---') se ignoran; los totales se calculan
sumando las facturas individuales.
"""
import io
import pandas as pd

TRAMOS      = ["sin_vencer", "d30", "d60", "d90", "mas90"]
TRAMOS_LABEL = ["Sin Vencer", "30 días", "60 días", "90 días", "Más 90"]

_COLS_COBRAR = [
    "cliente", "rut", "comuna", "ciudad", "vendedor",
    "num_factura", "emision", "vencimiento",
    "sin_vencer", "d30", "d60", "d90", "mas90",
]
_COLS_DEUDAS = [
    "proveedor",
    "num_factura", "emision", "vencimiento",
    "sin_vencer", "d30", "d60", "d90", "mas90",
]


def _parse(data, col_names: list[str]) -> pd.DataFrame:
    if data is None:
        return pd.DataFrame()
    if isinstance(data, bytes):
        df = pd.read_excel(io.BytesIO(data), header=0)
    else:
        df = pd.read_excel(data, header=0)

    n = len(col_names)
    if len(df.columns) < n:
        # El archivo tiene menos columnas de las esperadas — no se puede mapear
        import sys
        print(
            f"[flujos] columnas insuficientes: se esperaban {n}, "
            f"el archivo tiene {len(df.columns)}. Columnas: {list(df.columns)}",
            file=sys.stderr,
        )
        return pd.DataFrame()

    # Si hay columnas extra (ej: totales al final), tomar solo las primeras N
    df = df.iloc[:, :n].copy()
    df.columns = col_names
    entidad_col = col_names[0]

    # Descartar filas resumen (NUM FACTURA == '---') y filas vacías
    df = df[~df["num_factura"].astype(str).isin(["---", "nan", "NUM FACTURA", "None"])]
    df = df[df[entidad_col].notna()]

    for col in ["emision", "vencimiento"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in TRAMOS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df.reset_index(drop=True)


def cargar_por_cobrar(data) -> pd.DataFrame:
    """data: bytes (GitHub) o path (local)."""
    return _parse(data, _COLS_COBRAR)


def cargar_deudas(data) -> pd.DataFrame:
    """data: bytes (GitHub) o path (local)."""
    return _parse(data, _COLS_DEUDAS)
