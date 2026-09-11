# Modopack — Memoria General del Proyecto

Este archivo es leído automáticamente al inicio de cada sesión de Claude Code,
independiente de la rama. Contiene las reglas de trabajo para este proyecto.

---

## Stack

- **App**: Streamlit desplegada en Railway (auto-deploy desde `main`)
- **Datos**: archivos Excel/CSV almacenados en el repo `cmauricioaguilar-del/modopack-datos` en GitHub
- **Procesadores**: `processor.py` (ventas/compras), `processor_rrhh.py` (RRHH), `processor_flujos.py` (flujos)
- **Loader**: `github_loader.py` — descarga archivos desde GitHub vía API autenticada

## Arquitectura de datos

```
GitHub (modopack-datos) → github_loader.py → carpetas temporales → processors → DataFrames → main.py
```

- `carpetas_railway()` devuelve rutas locales de archivos descargados. Se cachea en `st.session_state` para no re-evaluar en cada rerun.
- `leer_config_flujos()` hace HTTP a GitHub. Se cachea en `st.session_state`.
- Las funciones `get_ventas`, `get_compras`, `get_rrhh`, `get_flujos` usan `@st.cache_data` (sin TTL).
- El caché se limpia solo cuando el admin sube archivos nuevos o presiona "Recargar datos".

## Reglas de ejecución — CRÍTICO

**Nunca ejecutar cambios en el código sin que el usuario escriba explícitamente la orden.**

- Preguntar "¿Ejecuto?" y no recibir respuesta no es una orden.
- Que el usuario confirme que el diagnóstico es correcto no es una orden.
- Que el usuario diga "sí" a una pregunta de diseño o enfoque no es una orden de ejecución.
- La única orden válida es una instrucción explícita del usuario: "ejecuta", "hazlo", "adelante", "sí, hazlo", etc.
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

- **`st.expander` no puede anidarse dentro de otro `st.expander`** → usar markdown con estilo como encabezado de sección.
- **`st.cache_resource`** comparte el mismo objeto entre sesiones → cualquier mutación in-place corrompe el caché para todos los usuarios. Usar siempre `st.cache_data`.
- **Código fuera de funciones en `main.py`** se re-ejecuta en cada rerun de Streamlit. Cualquier llamada HTTP en ese nivel causa lentitud en cada interacción del usuario.

### Git

- Rama de producción: `main` (Railway auto-despliega desde aquí)
- No hacer force-push a `main` sin confirmación explícita del usuario
- Cada commit debe describir el "por qué", no solo el "qué"

## Contexto de negocio

- **Empresa**: Modopack
- **Usuario principal**: administrador (Mauricio)
- **Otros roles**: gerencia (acceso limitado, sin flujos a menos que admin lo habilite)
- **Datos sensibles**: remuneraciones, ventas, compras — no exponer en logs ni commits
- **Moneda**: pesos chilenos (CLP), formato `$1.234.567`
- **Idioma de la app**: español
