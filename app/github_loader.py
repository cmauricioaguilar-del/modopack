"""
Descarga archivos desde modopack-datos en GitHub a un directorio fijo en disco.
La descarga solo ocurre si el caché en disco no existe o si limpiar_cache() fue llamado.
Se activa únicamente cuando la app corre en Railway.
"""
import os
import shutil
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = "cmauricioaguilar-del/modopack-datos"
BRANCH = "main"
API_BASE = f"https://api.github.com/repos/{REPO}/contents"

EN_RAILWAY = bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"))

# Directorio fijo en disco — compartido entre todos los workers del proceso Railway.
# Persiste mientras el contenedor esté vivo (horas/días); solo se borra con limpiar_cache().
CACHE_BASE = Path("/tmp/modopack_cache")

# Índice en memoria: evita stat() al disco en cada llamada dentro del mismo worker.
_cache_dirs: dict[str, str] = {}

# Caché de DataFrames: compartido entre sesiones del mismo proceso.
# Se llena la primera vez que se leen datos y se borra solo con limpiar_cache().
_df_cache: dict = {}


# ── Helpers GitHub ───────────────────────────────────────────────────────────

def _headers():
    return {"Authorization": f"token {GITHUB_TOKEN}"}


def _listar(carpeta: str) -> list[dict]:
    r = requests.get(f"{API_BASE}/{carpeta}?ref={BRANCH}", headers=_headers(), timeout=30)
    if r.status_code != 200:
        return []
    return [f for f in r.json() if isinstance(f, dict) and f.get("type") == "file"]


def _descargar_archivo(path_repo: str) -> bytes | None:
    r = requests.get(
        f"{API_BASE}/{path_repo}",
        params={"ref": BRANCH},
        headers={**_headers(), "Accept": "application/vnd.github.raw"},
        timeout=60,
    )
    return r.content if r.status_code == 200 else None


def _descargar_carpeta(carpeta_repo: str, destino: Path):
    """Descarga en paralelo todos los archivos de una carpeta del repo."""
    destino.mkdir(parents=True, exist_ok=True)
    archivos = _listar(carpeta_repo)
    if not archivos:
        return

    def _bajar(f):
        contenido = _descargar_archivo(f["path"])
        if contenido is not None:
            (destino / f["name"]).write_bytes(contenido)

    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(_bajar, archivos))


# ── Estado del caché ─────────────────────────────────────────────────────────

def cache_disponible() -> bool:
    """True si el caché en disco existe y tiene al menos una subcarpeta con archivos."""
    if not CACHE_BASE.exists():
        return False
    return any(
        child.is_dir() and any(child.iterdir())
        for child in CACHE_BASE.iterdir()
    )


# ── Caché de DataFrames (módulo) ──────────────────────────────────────────────

def df_cache_get() -> dict:
    return _df_cache


def df_cache_set(key: str, value) -> None:
    _df_cache[key] = value


def df_cache_clear() -> None:
    _df_cache.clear()


# ── Caché de carpetas locales ────────────────────────────────────────────────

def obtener_carpeta(carpeta_repo: str) -> str:
    """Retorna path local con los archivos descargados.

    Prioridad:
    1. Índice en memoria (_cache_dirs)  — sin I/O
    2. Directorio en disco (CACHE_BASE) — sin descarga
    3. Descarga desde GitHub            — solo si no hay caché
    """
    if carpeta_repo in _cache_dirs:
        return _cache_dirs[carpeta_repo]

    disco = CACHE_BASE / carpeta_repo.replace("/", "_")
    if disco.exists() and any(disco.iterdir()):
        _cache_dirs[carpeta_repo] = str(disco)
        return str(disco)

    disco.mkdir(parents=True, exist_ok=True)
    _descargar_carpeta(carpeta_repo, disco)
    _cache_dirs[carpeta_repo] = str(disco)
    return str(disco)


def limpiar_cache():
    """Borra caché en disco, en memoria y DataFrames para forzar re-descarga desde GitHub."""
    _cache_dirs.clear()
    _df_cache.clear()
    shutil.rmtree(CACHE_BASE, ignore_errors=True)


def limpiar_cache_carpeta(carpeta_repo: str):
    """Borra solo la carpeta de una carpeta específica del repo."""
    _cache_dirs.pop(carpeta_repo, None)
    _df_cache.clear()
    shutil.rmtree(CACHE_BASE / carpeta_repo.replace("/", "_"), ignore_errors=True)


# ── Detección de destino ─────────────────────────────────────────────────────

def detectar_destino(nombre: str) -> str | None:
    """Detecta la carpeta destino en el repo según el nombre del archivo."""
    import re
    n = nombre.upper()
    if "RCV_VENTA_" in n and n.endswith(".CSV"):
        anio = nombre[-10:-4][:4]
        return f"ventas/{anio}"
    if "RCV_RESUMEN_VENTA_" in n and n.endswith(".CSV"):
        anio = nombre[-10:-4][:4]
        return f"ventas/{anio}"
    if "RCV_COMPRA_REGISTRO_" in n and n.endswith(".CSV"):
        anio = nombre[-10:-4][:4]
        return f"compras/{anio}"
    _nn = n.replace(" ", "_")
    if (_nn in ("DEUDAS.XLSX", "POR_COBRAR.XLSX")
            or ("POR_COBRAR" in _nn and _nn.endswith(".XLSX"))
            or ("DEUDAS" in _nn and _nn.endswith(".XLSX") and "RCV" not in _nn)):
        return "flujos"
    if n.endswith(".XLSX"):
        m = re.search(r"(20\d{2})", nombre)
        anio = m.group(1) if m else "2026"
        return f"rrhh/{anio}"
    return None


# ── Subir / borrar ───────────────────────────────────────────────────────────

def subir_archivo(nombre: str, contenido_bytes: bytes) -> tuple[bool, str]:
    """Sube o reemplaza un archivo en modopack-datos. Retorna (ok, mensaje)."""
    import base64 as _b64
    nombre = nombre.replace(" ", "_")
    carpeta = detectar_destino(nombre)
    if not carpeta:
        return False, f"No se pudo detectar el tipo de archivo: {nombre}"

    if carpeta == "flujos":
        _nn = nombre.upper()
        if "POR_COBRAR" in _nn:
            nombre = "POR_COBRAR.xlsx"
        elif "DEUDAS" in _nn:
            nombre = "DEUDAS.xlsx"

    path_repo = f"{carpeta}/{nombre}"
    url = f"https://api.github.com/repos/{REPO}/contents/{path_repo}"

    r = requests.get(url, headers=_headers(), timeout=15)
    sha = r.json().get("sha") if r.status_code == 200 else None

    payload = {
        "message": f"update {nombre}",
        "content": _b64.b64encode(contenido_bytes).decode(),
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha

    r = requests.put(url, headers=_headers(), json=payload, timeout=30)
    if r.status_code in (200, 201):
        accion = "actualizado" if sha else "agregado"
        return True, f"✅ {nombre} {accion} en `{carpeta}/`"
    return False, f"❌ Error subiendo {nombre}: {r.json().get('message', '')}"


def borrar_archivo(path_repo: str, sha: str) -> tuple[bool, str]:
    """Borra un archivo de modopack-datos. Retorna (ok, mensaje)."""
    nombre = path_repo.split("/")[-1]
    url = f"https://api.github.com/repos/{REPO}/contents/{path_repo}"
    payload = {
        "message": f"delete {nombre}",
        "sha": sha,
        "branch": BRANCH,
    }
    r = requests.delete(url, headers=_headers(), json=payload, timeout=15)
    if r.status_code == 200:
        return True, f"✅ {nombre} eliminado de `{'/'.join(path_repo.split('/')[:-1])}/`"
    return False, f"❌ Error al eliminar {nombre}: {r.json().get('message', '')}"


# ── Listado de archivos ───────────────────────────────────────────────────────

def listar_archivos_carpeta(carpeta: str) -> list[dict]:
    return [{"name": f["name"], "path": f["path"], "sha": f["sha"]}
            for f in _listar(carpeta)]


def listar_flujos() -> list[str]:
    return [f["name"] for f in _listar("flujos")]


# ── Flujos ────────────────────────────────────────────────────────────────────

def obtener_archivo_flujos(nombre: str) -> bytes | None:
    """Descarga un archivo de la carpeta flujos/."""
    result = _descargar_archivo(f"flujos/{nombre}")
    if result is None:
        alt = nombre.replace("_", " ") if "_" in nombre else nombre.replace(" ", "_")
        if alt != nombre:
            result = _descargar_archivo(f"flujos/{alt}")
    return result


# ── Config flujos ─────────────────────────────────────────────────────────────

def leer_config_flujos() -> dict:
    import json
    contenido = _descargar_archivo("config/flujos.json")
    if contenido:
        try:
            return json.loads(contenido)
        except Exception:
            pass
    return {"gerencia_puede_ver": False}


def guardar_config_flujos(config: dict) -> bool:
    import json
    import base64 as _b64
    path_repo = "config/flujos.json"
    url = f"https://api.github.com/repos/{REPO}/contents/{path_repo}"
    r = requests.get(url, headers=_headers(), timeout=15)
    sha = r.json().get("sha") if r.status_code == 200 else None
    payload = {
        "message": "update flujos config",
        "content": _b64.b64encode(json.dumps(config).encode()).decode(),
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=_headers(), json=payload, timeout=30)
    return r.status_code in (200, 201)


# ── Bootstrap Railway ─────────────────────────────────────────────────────────

def carpetas_railway() -> dict:
    """Retorna paths locales de todas las carpetas (descarga en paralelo si es necesario)."""
    keys  = ["ventas_2025", "ventas_2026", "compras_2025", "compras_2026", "rrhh_2025", "rrhh_2026"]
    repos = ["ventas/2025", "ventas/2026", "compras/2025", "compras/2026", "rrhh/2025", "rrhh/2026"]
    resultado = {}
    from concurrent.futures import as_completed
    with ThreadPoolExecutor(max_workers=6) as executor:
        futuros = {executor.submit(obtener_carpeta, r): k for k, r in zip(keys, repos)}
        for futuro in as_completed(futuros):
            k = futuros[futuro]
            try:
                resultado[k] = futuro.result()
            except Exception:
                resultado[k] = ""
    return resultado
