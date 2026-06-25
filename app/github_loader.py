"""
Descarga archivos desde modopack-datos en GitHub a carpetas temporales.
Se activa solo cuando la app corre en Railway (variable RAILWAY_ENVIRONMENT presente).
"""
import io
import os
import tempfile
import requests
from pathlib import Path

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = "cmauricioaguilar-del/modopack-datos"
BRANCH = "main"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"
API_BASE = f"https://api.github.com/repos/{REPO}/contents"

EN_RAILWAY = bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"))


def _headers():
    return {"Authorization": f"token {GITHUB_TOKEN}"}


def _listar(carpeta: str) -> list[dict]:
    r = requests.get(f"{API_BASE}/{carpeta}?ref={BRANCH}", headers=_headers(), timeout=30)
    if r.status_code != 200:
        return []
    return [f for f in r.json() if isinstance(f, dict) and f.get("type") == "file"]


def _descargar_carpeta(carpeta_repo: str, destino: Path):
    """Descarga todos los archivos de una carpeta del repo a un directorio local."""
    destino.mkdir(parents=True, exist_ok=True)
    archivos = _listar(carpeta_repo)
    for f in archivos:
        url = f"{RAW_BASE}/{f['path']}"
        r = requests.get(url, headers=_headers(), timeout=60)
        if r.status_code == 200:
            (destino / f["name"]).write_bytes(r.content)


_cache_dirs: dict[str, str] = {}


def obtener_carpeta(carpeta_repo: str) -> str:
    """Retorna path local con los archivos descargados (con cache en memoria)."""
    if carpeta_repo in _cache_dirs:
        return _cache_dirs[carpeta_repo]
    tmp = Path(tempfile.mkdtemp())
    _descargar_carpeta(carpeta_repo, tmp)
    _cache_dirs[carpeta_repo] = str(tmp)
    return str(tmp)


def carpetas_railway() -> dict:
    """Retorna dict con todas las carpetas descargadas desde GitHub."""
    return {
        "ventas_2025":  obtener_carpeta("ventas/2025"),
        "ventas_2026":  obtener_carpeta("ventas/2026"),
        "compras_2025": obtener_carpeta("compras/2025"),
        "compras_2026": obtener_carpeta("compras/2026"),
        "rrhh_2025":    obtener_carpeta("rrhh/2025"),
        "rrhh_2026":    obtener_carpeta("rrhh/2026"),
    }
