# Plan de Desarrollo: Repo Analyzer CLI

Implementación de una herramienta de línea de comandos (CLI) en Python que explora un proyecto local, analiza la estructura del codebase y genera propuestas de refactorización y resúmenes arquitectónicos mediante la API de Gemini (`google-genai`).

## User Review Required

> [!IMPORTANT]
> - **Autenticación con Gemini:** La herramienta requerirá la variable de entorno `GEMINI_API_KEY` (o argumento `--api-key`) para el comando `analyze`. Si no está configurada, mostrará un mensaje descriptivo y amigable en terminal usando `Rich`.
> - **Modelo LLM por defecto:** Según la especificación, se configurará `gemini-3.8-flash` (o `gemini-2.5-flash` como fallback en caso de disponibilidad según la clave de API).
> - **Filtro de archivos para el LLM:** Para respetar la restricción de evitar archivos binarios o excesivamente pesados, se implementará un umbral de tamaño máximo por archivo (ej. 100 KB) y una lista de extensiones/patrones ignorados por defecto además de `.gitignore`.

## Proposed Architecture & Directory Structure

```
repoAnalyzerCli/
├── pyproject.toml               # Configuración de paquete y dependencias
├── repo_analyzer/
│   ├── __init__.py              # Metadatos del paquete
│   ├── __main__.py              # Permite ejecutar con: python -m repo_analyzer
│   ├── cli.py                   # Definición de comandos Typer (scan, analyze)
│   ├── config.py                # Configuración, API keys y constantes
│   ├── scanner.py               # Exploración del repo, .gitignore y detección de binarios/pesados
│   ├── tree.py                  # Renderizado del árbol y tablas estadísticas con Rich
│   ├── llm_client.py            # Integración con google-genai y manejo de excepciones
│   └── prompts.py               # Plantillas y construcción del prompt contextual para Gemini
└── tests/
    ├── __init__.py
    ├── test_scanner.py          # Pruebas del explorador de archivos e ignores
    └── test_cli.py              # Pruebas de los comandos Typer con CliRunner
```

---

## Proposed Changes

### Core Scanner & Ignore Engine

#### [NEW] [config.py](file:///home/nicolas/Documentos/repoAnalyzerCli/repo_analyzer/config.py)
- Constantes por defecto: carpetas a ignorar (`.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `dist`, `build`, etc.).
- Extensiones binarias comunes (`.png`, `.jpg`, `.pdf`, `.zip`, `.exe`, `.pyc`, `.wasm`, etc.).
- Límites de tamaño por archivo (ej. 100 KB) y límite de contexto total a enviar al LLM.
- Modelo por defecto: `gemini-3.8-flash`.

#### [NEW] [scanner.py](file:///home/nicolas/Documentos/repoAnalyzerCli/repo_analyzer/scanner.py)
- Recorrido recursivo del directorio respetando reglas de `.gitignore` (soporte para patrones estándar `fnmatch` / glob).
- Detección estricta de binarios (por extensión y detección de bytes nulos/no decodificables en UTF-8).
- Cálculo de estadísticas: cantidad de archivos por extensión, tamaños, conteo de líneas de código.
- Selección inteligente de archivos clave para el análisis (manifestos como `pyproject.toml`, `package.json`, archivos de entrada `main.py`, `index.js`, etc.).

---

### Rich Visualizations & Formatting

#### [NEW] [tree.py](file:///home/nicolas/Documentos/repoAnalyzerCli/repo_analyzer/tree.py)
- Generación del árbol visual usando `rich.tree.Tree` con colores diferenciados para carpetas y tipos de archivo.
- Generación de tablas estadísticas con `rich.table.Table` mostrando extensión, cantidad de archivos y porcentaje/tamaño.
- Renderizado de reportes Markdown generados por el LLM usando `rich.markdown.Markdown` con paneles y estilos consistentes.

---

### LLM Integration & Prompt Engineering

#### [NEW] [prompts.py](file:///home/nicolas/Documentos/repoAnalyzerCli/repo_analyzer/prompts.py)
- Diseño del System Prompt enfocado en análisis de arquitectura de software, patrones de diseño, mantenibilidad y oportunidades de refactorización.
- Construcción del User Prompt con la estructura del árbol, estadísticas del proyecto, archivos de configuración/dependencias y muestras clave de código.

#### [NEW] [llm_client.py](file:///home/nicolas/Documentos/repoAnalyzerCli/repo_analyzer/llm_client.py)
- Cliente que interactúa con `google.genai.Client`.
- Manejo robusto y elegante de excepciones:
  - Clave de API no encontrada o inválida.
  - Errores de conexión o timeout.
  - Límites de cuota o rate limit.
  - Respuestas vacías o bloqueadas por seguridad.

---

### CLI Interface & Execution Entrypoints

#### [NEW] [cli.py](file:///home/nicolas/Documentos/repoAnalyzerCli/repo_analyzer/cli.py)
- Implementación de Typer CLI:
  - `scan <path>`:
    - Opciones: `--max-depth`, `--show-hidden`, `--only-stats`.
    - Muestra árbol estilizado y tabla estadística.
  - `analyze <path>`:
    - Opciones: `--output <file.md>` (para guardar el reporte en disco opcionalmente), `--model <model_name>`, `--api-key <key>`.
    - Muestra `rich.status.Status` (spinner animado) mientras Gemini procesa el análisis.
    - Imprime el reporte formateado en terminal y guarda en archivo si se especifica.

#### [NEW] [__main__.py](file:///home/nicolas/Documentos/repoAnalyzerCli/repo_analyzer/__main__.py)
- Punto de entrada para ejecutar `python -m repo_analyzer`.

#### [NEW] [pyproject.toml](file:///home/nicolas/Documentos/repoAnalyzerCli/pyproject.toml)
- Metadatos del proyecto, configuración de dependencias y entrypoint de consola `repo-analyzer = "repo_analyzer.cli:app"`.

---

### Testing & Verification

#### [NEW] [tests/test_scanner.py](file:///home/nicolas/Documentos/repoAnalyzerCli/tests/test_scanner.py)
- Pruebas unitarias para:
  - Ignorar carpetas `.git`, `.venv`, etc.
  - Respetar reglas de `.gitignore`.
  - Detección de binarios y archivos pesados.
  - Conteo de extensiones y estadísticas.

#### [NEW] [tests/test_cli.py](file:///home/nicolas/Documentos/repoAnalyzerCli/tests/test_cli.py)
- Pruebas de integración del CLI usando `typer.testing.CliRunner`:
  - Ejecución de `scan` sobre directorios de prueba.
  - Verificación del manejo de errores cuando no hay API Key en `analyze`.

---

## Verification Plan

### Automated Tests
Ejecutar la suite de pruebas unitarias y de integración con el intérprete de `.venv`:
```bash
.venv/bin/python -m unittest discover tests -v
```

### Manual Verification
1. **Comando `scan`**:
   ```bash
   .venv/bin/python -m repo_analyzer scan .
   ```
   - Verificar que no incluya `.venv` ni `.git`.
   - Verificar la salida visual del árbol con Rich y la tabla de resumen de extensiones.

2. **Comando `analyze` sin API Key**:
   ```bash
   GEMINI_API_KEY="" .venv/bin/python -m repo_analyzer analyze .
   ```
   - Verificar que maneje el error elegantemente con un panel de advertencia en Rich en vez de un traceback feo.

3. **Comando `analyze` con API Key (o mock)**:
   ```bash
   .venv/bin/python -m repo_analyzer analyze . --output reporte.md
   ```
   - Verificar el spinner de carga de Rich, la salida en Markdown en terminal y la persistencia en `reporte.md`.
