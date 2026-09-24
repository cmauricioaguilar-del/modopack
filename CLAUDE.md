# Modopack — Memoria General del Proyecto

Este archivo es leído automáticamente al inicio de cada sesión de Claude Code,
independiente de la rama. Contiene las reglas de trabajo para este proyecto.

---

## Stack

- **App**: Streamlit 1.37.0 desplegada en Railway (auto-deploy desde `main`)
- **Datos**: archivos Excel/CSV en el repo `cmauricioaguilar-del/modopack-datos` (rama `main`)
- **Procesadores**: `processor.py` (ventas/compras), `processor_rrhh.py` (RRHH), `processor_flujos.py` (flujos)
- **Loader**: `github_loader.py` — descarga archivos desde GitHub vía API autenticada

## Arquitectura de datos (actualizada)

```
GitHub (modopack-datos)
  → github_loader.obtener_carpeta()
  → /tmp/modopack_cache/<carpeta>/   ← caché en disco, persiste mientras vive el contenedor
  → _df_cache (dict a nivel módulo)  ← DataFrames en memoria, persiste entre sesiones del proceso
  → main.py (df_ventas, df_compras, df_rrhh)
```

### Caché en tres niveles (`github_loader.py`)

1. **Memoria** (`_cache_dirs` dict de módulo): evita stat() al disco en cada rerun
2. **Disco** (`/tmp/modopack_cache/`): directorio fijo compartido entre todos los workers del contenedor Railway
3. **GitHub API**: solo se consulta si el caché en disco no existe o fue borrado

### Cuándo se actualiza el caché

- **Solo** cuando el admin sube un archivo nuevo vía uploader → `limpiar_cache()` borra disco + `_df_cache`
- **Solo** cuando el admin presiona "Recargar datos" → ídem
- **Nunca** de forma automática ni por tiempo (aplicación batch, no polling)

### Funciones clave de `github_loader.py`

| Función | Qué hace |
|---|---|
| `cache_disponible()` | True si `/tmp/modopack_cache/` existe con al menos una subcarpeta con archivos |
| `obtener_carpeta(carpeta_repo)` | 3-tier lookup: memoria → disco → GitHub |
| `df_cache_get()` | Retorna el dict `_df_cache` (DataFrames cargados) |
| `df_cache_set(key, value)` | Guarda un DataFrame en `_df_cache` |
| `limpiar_cache()` | Borra disco + `_df_cache` + índice en memoria |
| `limpiar_cache_carpeta(carpeta)` | Borra solo una carpeta específica |
| `carpetas_railway()` | Descarga las 6 carpetas en paralelo si no están en caché |

### Carga de datos en `main.py`

- **Railway**: usa `df_cache_get()`/`df_cache_set()` — carga DataFrames solo si `_df_cache` está vacío
- **Local**: usa `@st.cache_data` con los paths como clave
- El spinner "📡 Descargando desde GitHub" solo aparece cuando `not cache_disponible()` (primera carga)
- `get_flujos()` sigue usando `@st.cache_data` (necesario para `get_flujos.clear()`)

## Estructura del repo `modopack-datos`

```
ventas/
  2025/  → RCV_VENTA_*.csv, RCV_RESUMEN_VENTA_*.csv
  2026/  → ídem
compras/
  2025/  → RCV_COMPRA_REGISTRO_*.csv
  2026/  → ídem
rrhh/
  2025/  → archivos .xlsx de remuneraciones
  2026/  → ídem
flujos/  → POR_COBRAR.xlsx, DEUDAS.xlsx
config/  → flujos.json
```

### Tipos SII importantes

- **Tipo 33** (factura): viene de `RCV_VENTA_*` detail — es la mayor parte de las ventas
- **Tipo 48** (boleta electrónica): viene de `RCV_RESUMEN_VENTA_*` — solo Monto Neto col
- **Tipo 61** (nota de crédito): negativo, viene de `RCV_VENTA_*`
- **Nomenclatura de archivos**: `RCV_VENTA_<RUT>_<AAAAMM>.csv`, `RCV_RESUMEN_VENTA_<RUT>_<AAAAMM>.csv`

## Configuración de producción Railway

### `.streamlit/config.toml` (creado Sep 2026)

```toml
[server]
headless = true
enableCORS = false
enableWebsocketCompression = false
fileWatcherType = "none"   # CRÍTICO: evita reruns por escrituras en /tmp/modopack_cache/

[browser]
gatherUsageStats = false
```

### `requirements.txt`

`watchdog` fue eliminado (Sep 2026). Causaba reruns periódicos cada ~10s al detectar
escrituras en `/tmp/modopack_cache/`. Con `fileWatcherType = "none"` no se necesita.

### `nixpacks.toml` / `Procfile`

```
streamlit run app/main.py --server.port $PORT --server.address 0.0.0.0
```

## Reglas de ejecución — CRÍTICO

**Nunca ejecutar cambios en el código sin que el usuario escriba explícitamente la orden.**

- Preguntar "¿Ejecuto?" y no recibir respuesta no es una orden.
- Que el usuario confirme que el diagnóstico es correcto no es una orden.
- Que el usuario diga "sí" a una pregunta de diseño o enfoque no es una orden de ejecución.
- La única orden válida es una instrucción explícita del usuario: "ejecuta", "hazlo", "adelante", "dale", etc.
- En caso de duda, preguntar. Nunca asumir.

---

## Reglas de trabajo obligatorias

### Antes de cualquier cambio

1. **Leer TODOS los archivos involucrados** — no solo el que tiene el síntoma visible.
   Para cambios en `main.py` que toquen datos o rendimiento, siempre leer también:
   `github_loader.py`, `processor_flujos.py`, `processor_rrhh.py`, `processor.py`.

2. **No proponer ni ejecutar cambios sin haber leído el flujo completo** de extremo a extremo.

3. **Diagnosticar antes de actuar**: si hay un error, leer el traceback completo y los archivos
   relevantes antes de proponer una solución. No asumir la causa.

### Streamlit — restricciones conocidas

- **`st.expander` no puede anidarse dentro de otro `st.expander`** → usar markdown con estilo.
- **`st.cache_resource`** comparte el mismo objeto entre sesiones → cualquier mutación in-place corrompe el caché. Usar siempre `st.cache_data`.
- **Código fuera de funciones en `main.py`** se re-ejecuta en cada rerun. Cualquier llamada HTTP en ese nivel causa lentitud en cada interacción.
- **`[data-testid="stStatusWidget"]`** oculto vía CSS — era molesto en producción (mostraba RUNNING/CONNECTING).
- **`fileWatcherType = "none"`** es obligatorio — sin esto, watchdog reinicia el proceso al escribir en `/tmp/`.

### Git

- Rama de producción: `main` (Railway auto-despliega desde aquí, ~2-3 min)
- No hacer force-push a `main` sin confirmación explícita
- Cada commit debe describir el "por qué", no solo el "qué"

## Contexto de negocio

- **Empresa**: Modopack
- **Usuario principal**: administrador (Mauricio)
- **Otros roles**: gerencia (acceso limitado, sin flujos a menos que admin lo habilite)
- **Datos sensibles**: remuneraciones, ventas, compras — no exponer en logs ni commits
- **Moneda**: pesos chilenos (CLP)
- **Idioma de la app**: español
- **Modelo de actualización**: **batch** — la app NO debe ir a buscar datos ni actualizarse sola.
  Solo se actualiza cuando Mauricio sube archivos nuevos o presiona "Recargar datos".
