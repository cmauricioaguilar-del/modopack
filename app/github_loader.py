"""Lee archivos CSV/Excel desde el repo privado modopack-datos en GitHub."""
import io
import os
import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = "cmauricioaguilar-del/modopack-datos"
BRANCH = "main"
BASE_URL = f"https://api.github.com/repos/{REPO}/contents"


def _headers():
    return {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3.raw"}


def listar_archivos(carpeta_repo: str) -> list[str]:
    """Retorna lista de paths de archivos en una carpeta del repo."""
    url = f"{BASE_URL}/{carpeta_repo}?ref={BRANCH}"
    r = requests.get(url, headers=_headers(), timeout=30)
    if r.status_code != 200:
        return []
    return [f["path"] for f in r.json() if f["type"] == "file"]


def descargar(path_repo: str) -> bytes:
    """Descarga el contenido raw de un archivo del repo."""
    url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{path_repo}"
    r = requests.get(url, headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.content


def csv_bytes_a_df(contenido: bytes, **kwargs):
    import pandas as pd
    return pd.read_csv(io.BytesIO(contenido), **kwargs)


def excel_bytes_a_df(contenido: bytes, **kwargs):
    import pandas as pd
    return pd.read_excel(io.BytesIO(contenido), **kwargs)
