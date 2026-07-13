import pandas as pd
from pathlib import Path
import re

MESES_NOMBRE = {
    "ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12,
}

# Nombres completos de los meses (para FEBRERO2025, REM ABRIL 2025, etc.)
MESES_FULL = {
    "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6,
    "JULIO": 7, "AGOSTO": 8, "SEPTIEMBRE": 9, "SETIEMBRE": 9, "OCTUBRE": 10,
    "NOVIEMBRE": 11, "DICIEMBRE": 12,
}

# Columnas del Excel de remuneraciones que nos interesan
COLS_BASE = {
    # Identificación
    "EMPLEADO":                                          "empleado",
    "CENTRO COSTO":                                      "centro_costo",
    "ISAPRE NOMBRE":                                     "isapre_nombre",
    "AFP NOMBRE":                                        "afp_nombre",
    "PORCENTAJE AFP":                                    "porcentaje_afp",
    # Asistencia
    "HORAS EXTRAS 50":                                   "horas_extras_50",
    "DIAS NO TRABAJADOS":                                "dias_no_trabajados",
    "DIAS DE AUSENCIA":                                  "dias_ausencia",
    "DIAS DE LICENCIA":                                  "dias_licencia",
    "HORAS NO TRABAJADAS":                               "horas_no_trabajadas",
    # Haberes imponibles
    "SUELDO BASE":                                       "sueldo_base",
    "GRATIFICACION LEGAL":                               "gratificacion",
    "BONOS":                                             "bonos",
    "BONO DE PRODUCCION":                                "bono_produccion",
    "BONO COMERCIAL":                                    "bono_comercial",
    "OTROS BONOS":                                       "otros_bonos",
    "AGUINALDO":                                         "aguinaldo",
    "HORAS EXTRAS":                                      "horas_extras",
    "COMISIONES POR VENTA":                              "comisiones",
    "VALOR HORAS NO TRABAJADAS":                         "valor_horas_no_trabajadas",
    "AJUSTE LEY DE PROTECCION AL EMPLEO":                "ajuste_ley_empleo",
    # Haberes no imponibles
    "NO IMPONIBLE":                                      "no_imponible",
    "MOVILIZACION":                                      "movilizacion",
    "COLACION":                                          "colacion",
    "ASIGNACION FAMILIAR":                               "asig_familiar",
    "ASIGNACION FAMILIAR RETROACTIVA":                   "asig_familiar_retro",
    "FINIQUITOS":                                        "finiquitos",
    # Bases de cálculo
    "RENTA AFECTA":                                      "renta_afecta",
    "RENTA IMPONIBLE AFP E ISAPRE":                      "renta_imponible",
    "RENTA IMPONIBLE SEGURO DE CESANTIA":                "renta_imponible_sc",
    "IMPONIBLE":                                         "imponible",
    # Descuentos trabajador
    "DESCUENTOS LEGALES":                                "desc_legales",
    "SALUD":                                             "desc_salud",
    "AFP":                                               "desc_afp",
    "ADICIONAL ISAPRE":                                  "desc_adicional_isapre",
    "IMPUESTO UNICO":                                    "impuesto_unico",
    "SEGURO DE CESANTIA TRABAJADOR":                     "sc_trabajador",
    "ANTICIPOS":                                         "anticipos",
    "APV INDIVIDUAL":                                    "apv",
    "COTIZACIONES VOLUNTARIAS":                          "cot_voluntarias",
    "PRESTAMOS CCAF":                                    "prestamos_ccaf",
    "LEASING CCAF":                                      "leasing_ccaf",
    "DESCUENTO DENTAL CCAF":                             "dental_ccaf",
    "SEGURO DE VIDA CCAF":                               "seguro_vida_ccaf",
    "OTROS DESCUENTOS CCAF":                             "otros_desc_ccaf",
    "PRESTAMOS":                                         "prestamos",
    "PRESTAMOS EMPRESA":                                 "prestamos_empresa",
    # Aportes empresa
    "SEGURO DE CESANTIA EMPRESA":                        "sc_empresa",
    "MUTUAL DE SEGURIDAD":                               "mutual",
    "SIS EMPRESA":                                       "sis",
    "ADICIONAL AFP EMPRESA":                             "afp_adicional",
    "COTIZACION RENTABILIDAD PROTEGIDA":                 "cot_rent_protegida",
    "COTIZACION ESPERANZA DE VIDA":                      "cot_esperanza_vida",
    # Resultado
    "LIQUIDO A PAGAR":                                   "liquido",
}

# Grupos de columnas para la vista de detalle
GRUPOS_DETALLE = {
    "👤 Identificación": ["isapre_nombre", "afp_nombre", "porcentaje_afp", "centro_costo"],
    "📅 Asistencia": ["dias_no_trabajados", "dias_ausencia", "dias_licencia", "horas_extras_50", "horas_no_trabajadas"],
    "💰 Haberes Imponibles": ["sueldo_base", "gratificacion", "bonos", "bono_produccion", "bono_comercial",
                               "otros_bonos", "aguinaldo", "horas_extras", "comisiones",
                               "valor_horas_no_trabajadas", "ajuste_ley_empleo"],
    "🚌 Haberes No Imponibles": ["movilizacion", "colacion", "asig_familiar", "asig_familiar_retro", "finiquitos"],
    "📊 Bases de Cálculo": ["renta_afecta", "renta_imponible", "renta_imponible_sc", "imponible"],
    "➖ Descuentos Trabajador": ["desc_salud", "desc_afp", "desc_adicional_isapre", "impuesto_unico",
                                  "sc_trabajador", "anticipos", "apv", "cot_voluntarias",
                                  "prestamos_ccaf", "leasing_ccaf", "dental_ccaf", "seguro_vida_ccaf",
                                  "otros_desc_ccaf", "prestamos", "prestamos_empresa"],
    "🏢 Aportes Empresa": ["sc_empresa", "mutual", "sis", "afp_adicional", "cot_rent_protegida", "cot_esperanza_vida"],
}

LABELS_COLS = {
    "isapre_nombre": "Isapre", "afp_nombre": "AFP", "porcentaje_afp": "% AFP", "centro_costo": "Centro Costo",
    "dias_no_trabajados": "Días no trab.", "dias_ausencia": "Días ausencia", "dias_licencia": "Días licencia",
    "horas_extras_50": "HH.EE. 50%", "horas_no_trabajadas": "Horas no trab.",
    "sueldo_base": "Sueldo Base", "gratificacion": "Gratificación", "bonos": "Bonos",
    "bono_produccion": "Bono Producción", "bono_comercial": "Bono Comercial", "otros_bonos": "Otros Bonos",
    "aguinaldo": "Aguinaldo", "horas_extras": "Horas Extras", "comisiones": "Comisiones",
    "valor_horas_no_trabajadas": "Valor HH no trab.", "ajuste_ley_empleo": "Ajuste Ley Empleo",
    "movilizacion": "Movilización", "colacion": "Colación", "asig_familiar": "Asig. Familiar",
    "asig_familiar_retro": "Asig. Familiar Retro", "finiquitos": "Finiquitos",
    "renta_afecta": "Renta Afecta", "renta_imponible": "Renta Imponible AFP/Isapre",
    "renta_imponible_sc": "Renta Imponible SC", "imponible": "Imponible",
    "desc_salud": "Salud", "desc_afp": "AFP", "desc_adicional_isapre": "Adicional Isapre",
    "impuesto_unico": "Impuesto Único", "sc_trabajador": "SC Trabajador",
    "anticipos": "Anticipos", "apv": "APV", "cot_voluntarias": "Cot. Voluntarias",
    "prestamos_ccaf": "Préstamos CCAF", "leasing_ccaf": "Leasing CCAF", "dental_ccaf": "Dental CCAF",
    "seguro_vida_ccaf": "Seguro Vida CCAF", "otros_desc_ccaf": "Otros Desc. CCAF",
    "prestamos": "Préstamos", "prestamos_empresa": "Préstamos Empresa",
    "sc_empresa": "SC Empresa", "mutual": "Mutual de Seguridad", "sis": "SIS",
    "afp_adicional": "AFP Adicional", "cot_rent_protegida": "Cot. Rent. Protegida",
    "cot_esperanza_vida": "Cot. Esperanza Vida",
    "liquido": "Líquido a Pagar",
}

COLS_NUMERICAS_DETALLE = [
    "horas_extras_50", "dias_no_trabajados", "dias_ausencia", "dias_licencia", "horas_no_trabajadas",
    "sueldo_base", "gratificacion", "bonos", "bono_produccion", "bono_comercial", "otros_bonos",
    "aguinaldo", "horas_extras", "comisiones", "valor_horas_no_trabajadas", "ajuste_ley_empleo",
    "movilizacion", "colacion", "asig_familiar", "asig_familiar_retro", "finiquitos",
    "renta_afecta", "renta_imponible", "renta_imponible_sc", "imponible",
    "desc_legales", "desc_salud", "desc_afp", "desc_adicional_isapre", "impuesto_unico",
    "sc_trabajador", "anticipos", "apv", "cot_voluntarias",
    "prestamos_ccaf", "leasing_ccaf", "dental_ccaf", "seguro_vida_ccaf", "otros_desc_ccaf",
    "prestamos", "prestamos_empresa",
    "sc_empresa", "mutual", "sis", "afp_adicional", "cot_rent_protegida", "cot_esperanza_vida",
    "liquido",
]

# Columnas que suman como subtotal en cada grupo (solo las monetarias, no días/horas)
COLS_SUBTOTAL = {
    "💰 Haberes Imponibles": ["sueldo_base", "gratificacion", "bonos", "bono_produccion", "bono_comercial",
                               "otros_bonos", "aguinaldo", "horas_extras", "comisiones",
                               "valor_horas_no_trabajadas", "ajuste_ley_empleo"],
    "🚌 Haberes No Imponibles": ["movilizacion", "colacion", "asig_familiar", "asig_familiar_retro", "finiquitos"],
    "➖ Descuentos Trabajador": ["desc_salud", "desc_afp", "desc_adicional_isapre", "impuesto_unico",
                                  "sc_trabajador", "anticipos", "apv", "cot_voluntarias",
                                  "prestamos_ccaf", "leasing_ccaf", "dental_ccaf", "seguro_vida_ccaf",
                                  "otros_desc_ccaf", "prestamos", "prestamos_empresa"],
    "🏢 Aportes Empresa": ["sc_empresa", "mutual", "sis", "afp_adicional", "cot_rent_protegida", "cot_esperanza_vida"],
}

def _normalizar_nombre(s: str) -> str:
    """Mayúsculas, sin acentos, solo letras/números/espacios."""
    s = str(s).upper()
    for a, b in (("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U"), ("Ñ", "N")):
        s = s.replace(a, b)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _mes_anio_desde_nombre(nombre: str, carpeta: str = ""):
    """Extrae (mes, anio) desde nombres variados de remuneraciones.

    Soporta: FEB2025, ENE25, 04 REM ABR, REM ABRIL 2025, ABRIL2025,
    01ENE26, y archivos sin año en el nombre (toma el año de la carpeta)."""
    # Quitar la extensión antes de normalizar
    base = re.sub(r"\.[A-Za-z0-9]+$", "", nombre)
    n = _normalizar_nombre(base)

    mes = None
    # 1) Nombre completo del mes (ABRIL, FEBRERO, ...)
    for nom, num in MESES_FULL.items():
        if nom in n:
            mes = num
            break
    # 2) Abreviatura de 3 letras (no precedida por otra letra: ABR, ENE25, 04ENE)
    if mes is None:
        for ab, num in MESES_NOMBRE.items():
            if re.search(rf"(?<![A-Z]){ab}", n):
                mes = num
                break
    # 3) Número de mes al inicio del nombre (04 REM ...)
    if mes is None:
        m_num = re.match(r"(\d{1,2})\b", n)
        if m_num and 1 <= int(m_num.group(1)) <= 12:
            mes = int(m_num.group(1))

    # Año: 4 dígitos en el nombre tiene prioridad
    anio = None
    m_anio = re.search(r"(20\d{2})", n)
    if m_anio:
        anio = int(m_anio.group(1))
    else:
        # 2 dígitos pegados/junto a un token de mes  →  ENE25, ABR 25
        m2 = re.search(r"[A-Z]{3,}\s*'?(\d{2})(?!\d)", n)
        if m2:
            anio = 2000 + int(m2.group(1))
    # Sin año en el nombre → tomarlo de la ruta de la carpeta (repo: rrhh/2025)
    if anio is None:
        m_carp = re.search(r"(20\d{2})", carpeta)
        if m_carp:
            anio = int(m_carp.group(1))

    if mes and anio and 2000 <= anio <= 2100:
        return mes, anio
    return None, None


def _norm_col(s) -> str:
    """Normaliza un nombre de columna para emparejar: borra TODO lo no alfanumérico.
    Así 'LÍQUIDO A PAGAR', 'L�QUIDO A PAGAR' (encoding roto) y 'LIQUIDOAPAGAR'
    convergen al mismo valor, igualando acentos, espacios dobles y mojibake."""
    return re.sub(r"[^A-Z0-9]", "", str(s).upper())


def _leer_excel_sii(path) -> pd.DataFrame:
    """Lee un Excel de remuneraciones detectando automáticamente la fila de encabezado."""
    probe = pd.read_excel(path, header=None, dtype=str, nrows=25)
    header_row = 0
    for i, row in probe.iterrows():
        vals = [_norm_col(v) for v in row.dropna()]
        # La fila de encabezado contiene la columna EMPLEADO
        if any(v == "EMPLEADO" or v.startswith("EMPLEADO") or "EMPLEADO" in v.split() for v in vals):
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


# Mapa de columnas normalizadas → destino (se calcula una vez)
# Normalizamos las claves de COLS_BASE quitando acentos antes de _norm_col
def _norm_key(s: str) -> str:
    s = s.upper()
    for a, b in (("Á","A"),("É","E"),("Í","I"),("Ó","O"),("Ú","U"),("Ñ","N")):
        s = s.replace(a, b)
    return re.sub(r"[^A-Z0-9]", "", s)

_COLS_NORM = {_norm_key(k): v for k, v in COLS_BASE.items()}


COLS_TEXTO = {"empleado", "centro_costo", "isapre_nombre", "afp_nombre"}


def _procesar_archivo_rrhh(path, mes: int, anio: int) -> pd.DataFrame:
    """Lee y normaliza un único Excel de remuneraciones. Lanza excepción si falla la lectura."""
    raw = _leer_excel_sii(path)

    # Mapeo flexible por nombre de columna normalizado (acentos/espacios/encoding)
    cols_map = {}
    for c in raw.columns:
        dest = _COLS_NORM.get(_norm_col(c))
        if dest and dest not in cols_map.values():
            cols_map[c] = dest

    df = raw[list(cols_map.keys())].rename(columns=cols_map)

    # Limpiar numéricos / texto
    for col in df.columns:
        if col not in COLS_TEXTO:
            df[col] = _limpiar_num(df[col])

    # Eliminar filas sin empleado (totales, vacías)
    if "empleado" in df.columns:
        df = df[df["empleado"].notna() & (df["empleado"].astype(str).str.strip() != "")]

    # costo_empresa = Renta Imponible AFP e Isapre + aportes empresa
    aportes_cols = ["sc_empresa", "mutual", "sis", "afp_adicional", "cot_rent_protegida", "cot_esperanza_vida"]
    base = df["renta_imponible"] if "renta_imponible" in df.columns else (
           df["imponible"]       if "imponible"       in df.columns else pd.Series(0, index=df.index))
    aportes = sum(df[c] for c in aportes_cols if c in df.columns)
    df["costo_empresa"] = base + aportes

    df["mes"] = mes
    df["anio"] = anio
    return df


def cargar_rrhh(carpeta: str) -> pd.DataFrame:
    frames = []
    for f in sorted(Path(carpeta).glob("*.xlsx")):
        mes, anio = _mes_anio_desde_nombre(f.name, str(f.parent))
        if not mes or not anio:
            continue
        try:
            df = _procesar_archivo_rrhh(f, mes, anio)
        except Exception:
            continue
        if not df.empty:
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def diagnostico_rrhh(carpetas: list) -> pd.DataFrame:
    """Devuelve un detalle por archivo: si se detectó mes/año, filas y costo total.
    Útil para entender por qué un mes aparece en 0."""
    filas = []
    for c in carpetas:
        for f in sorted(Path(c).glob("*.xlsx")):
            mes, anio = _mes_anio_desde_nombre(f.name, str(f.parent))
            info = {
                "archivo": f.name,
                "mes": mes if mes else "—",
                "anio": anio if anio else "—",
                "filas": 0,
                "costo_empresa": 0,
                "estado": "",
            }
            if not mes or not anio:
                info["estado"] = "❌ no se detectó mes/año del nombre"
                filas.append(info)
                continue
            try:
                df = _procesar_archivo_rrhh(f, mes, anio)
                info["filas"] = len(df)
                info["costo_empresa"] = float(df["costo_empresa"].sum()) if not df.empty else 0
                if info["costo_empresa"] == 0:
                    info["estado"] = "⚠️ cargó pero costo = 0 (revisar columnas)"
                else:
                    info["estado"] = "✅ ok"
            except Exception as e:
                info["estado"] = f"❌ error: {type(e).__name__}"
            filas.append(info)
    return pd.DataFrame(filas)


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
