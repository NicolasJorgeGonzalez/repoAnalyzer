# Repo Analyzer CLI 🔍🚀

**Repo Analyzer CLI** es una herramienta de línea de comandos para explorar, mapear y auditar repositorios de código de forma rápida e intuitiva. Combina un escáner de archivos inteligente y configurable con el poder de los modelos **Google Gemini** para ofrecer diagnósticos arquitectónicos y de salud de código en segundos.

---

## 📋 Tabla de Contenidos

- [Características Principales](#-características-principales)
- [Tecnologías Utilizadas](#-tecnologías-utilizadas)
- [Requisitos Previos](#-requisitos-previos)
- [Instalación y Configuración](#-instalación-y-configuración)
- [Guía de Uso y Comandos](#-guía-de-uso-y-comandos)
  - [1. Escaneo de repositorios (`scan`)](#1-escaneo-de-repositorios-scan)
  - [2. Análisis arquitectónico con Gemini (`analyze`)](#2-análisis-arquitectónico-con-gemini-analyze)
- [Detalles Técnicos y Filtrado](#-detalles-técnicos-y-filtrado)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Ejecución de Pruebas](#-ejecución-de-pruebas)
- [Licencia](#-licencia)

---

## ✨ Características Principales

- 🌳 **Árbol Visual Jerárquico**: Muestra la estructura de directorios con iconos y colores temáticos según el tipo de archivo (código, configuración, documentación o binarios) junto a sus tamaños formateados.
- 📊 **Métricas y Estadísticas Claras**: Calcula automáticamente el total de archivos, carpetas, líneas de código (LoC), tamaño total y distribución porcentual por extensión en tablas formateadas con [Rich](https://github.com/Textualize/rich).
- 🧠 **Auditoría de Código con Gemini**: Analiza la arquitectura, patrones de diseño, fortalezas, deuda técnica y riesgos de seguridad utilizando el SDK oficial `google-genai` con el modelo `gemini-3.8-flash`.
- 🛡️ **Respeto Nativo a `.gitignore`**: Motor propio de evaluación de patrones glob de Git (soporta comodines `*`, `**`, anclajes, negaciones `!` y carpetas). Ignora directorios como `.git`, `node_modules`, `.venv`, `__pycache__` por defecto.
- ⚡ **Filtrado Inteligente de Binarios y Archivos Grandes**: Detección de binarios por extensión, presencia de bytes nulos (`\x00`) e incompatibilidad UTF-8. Omite automáticamente archivos individuales de más de 100 KB para evitar ruido.
- 💰 **Presupuesto Seguro de Contexto**: Prioriza la lectura de archivos clave (manifiestos de dependencias, especificaciones, documentación y entrypoints) con un límite máximo estricto de 500 KB para proteger las cuotas y la ventana de contexto de la API.
- 📝 **Exportación a Markdown**: Permite visualizar reportes directamente en la terminal con renderizado estilizado o guardarlos en archivos `.md` para documentación de equipo o pull requests.

---

## 🛠 Tecnologías Utilizadas

- **[Python](https://www.python.org/)** `>= 3.10` (compatible y probado con Python 3.14).
- **[Typer](https://typer.tiangolo.com/)**: Construcción de interfaces de línea de comandos robustas y tipadas.
- **[Rich](https://rich.readthedocs.io/)**: Visualización enriquecida en terminal (árboles, tablas, paneles, colores y spinners animados).
- **[Google GenAI SDK (`google-genai`)](https://github.com/google-gemini/google-genai)**: SDK oficial de Google para comunicarse con los modelos Gemini (por defecto: `gemini-3.8-flash`).

---

## 📦 Requisitos Previos

1. **Python**: Versión **3.10 o superior** instalada en el sistema (verificable con `python3 --version`).
2. **Clave de API de Google Gemini**: Se obtiene de forma gratuita e inmediata en [Google AI Studio](https://aistudio.google.com/).

---

## 🚀 Instalación y Configuración

### 1. Clonar el repositorio

```bash
git clone https://github.com/NicolasJorgeGonzalez/repoAnalyzerCli.git
cd repoAnalyzerCli
```

### 2. Crear y activar el entorno virtual

En Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

En Windows:
```cmd
python -m venv .venv
.venv\Scripts\activate
```

### 3. Instalar dependencias

Instala el paquete en modo editable:
```bash
pip install -e .
```

> **Nota:** También puedes ejecutar los comandos directamente usando el intérprete de Python mediante `python -m repo_analyzer`.

### 4. Configurar la clave de API de Gemini

Define la variable de entorno con tu clave generada en Google AI Studio:

```bash
export GEMINI_API_KEY="tu_api_key_aqui"
```

*(En Windows PowerShell: `$env:GEMINI_API_KEY="tu_api_key_aqui"`)*

> **Tip:** También puedes pasar la clave directamente en el comando `analyze` mediante el flag `--api-key` / `-k`.

---

## 📖 Guía de Uso y Comandos

Una vez instalado, el comando principal `repo-analyzer` estará disponible globalmente en tu entorno.

```bash
repo-analyzer --help
```

```text
 Usage: repo-analyzer [OPTIONS] COMMAND [ARGS]...

 CLI tool to explore repositories and analyze architecture with Gemini.

╭─ Options ────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                      │
╰──────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────╮
│ scan     Escanear un repositorio local y mostrar estructura y    │
│          métricas.                                               │
│ analyze  Analiza la arquitectura y salud de código de un         │
│          repositorio usando Gemini.                              │
╰──────────────────────────────────────────────────────────────────╯
```

---

### 1. Escaneo de repositorios (`scan`)

Inspecciona el directorio indicado, muestra el árbol de archivos coloreado, un panel resumen de métricas y una tabla con la distribución por extensiones.

```bash
repo-analyzer scan [RUTA] [OPCIONES]
```

#### Opciones y flags:

| Flag | Tipo / Valor | Descripción |
|---|---|---|
| `[RUTA]` | Argumento posicional | Ruta al directorio a escanear (por defecto: `.` directorio actual). |
| `-d`, `--max-depth` | Entero (`int`) | Límite de niveles de profundidad a recorrer en el árbol de directorios. |
| `-s`, `--only-stats` | Bandera (`bool`) | Oculta el árbol jerárquico y muestra únicamente el resumen y la tabla de estadísticas. |
| `--no-gitignore` | Bandera (`bool`) | Desactiva el filtrado de archivos y carpetas según reglas de `.gitignore`. |

#### Ejemplos de uso:

- **Escanear el directorio actual:**
  ```bash
  repo-analyzer scan
  ```

- **Limitar la profundidad del árbol a 2 niveles:**
  ```bash
  repo-analyzer scan --max-depth 2
  ```

- **Escanear otro proyecto mostrando solo las estadísticas:**
  ```bash
  repo-analyzer scan /ruta/a/mi-proyecto --only-stats
  ```

- **Escanear incluyendo archivos normalmente ignorados por `.gitignore`:**
  ```bash
  repo-analyzer scan . --no-gitignore
  ```

#### Ejemplo de salida visual:

```text
📁 repoAnalyzerCli
├── 📁 repo_analyzer
│   ├── 📄 __init__.py (52 B)
│   ├── 📄 __main__.py (132 B)
│   ├── 📄 cli.py (8.3 KB)
│   ├── 📄 config.py (2.4 KB)
│   ├── 📄 llm_client.py (5.2 KB)
│   ├── 📄 prompts.py (6.0 KB)
│   ├── 📄 scanner.py (16.1 KB)
│   └── 📄 tree.py (10.9 KB)
├── 📁 tests
│   ├── 📄 __init__.py (0 B)
│   ├── 📄 test_cli.py (8.7 KB)
│   ├── 📄 test_llm_client.py (5.4 KB)
│   ├── 📄 test_prompts.py (4.4 KB)
│   ├── 📄 test_scanner.py (14.0 KB)
│   └── 📄 test_tree.py (10.6 KB)
├── 📄 AGENT.md (929 B)
├── 📄 pyproject.toml (503 B)
└── 📄 README.md (6.5 KB)

╭─ Resumen del Repositorio ─╮
│ • Total de archivos: 17   │
│ • Total de carpetas: 3    │
│ • Líneas de código: 2,750 │
│ • Tamaño total: 98.2 KB   │
│ • Archivos ignorados: 5   │
╰───────────────────────────╯

                       Estadísticas por Extensión / Tipo                        
╭────────────────┬──────────┬─────────────┬──────────────────┬─────────────────╮
│ Extensión/Tipo │ Archivos │ % del total │ Tamaño formatead │ Líneas de códig │
├────────────────┼──────────┼─────────────┼──────────────────┼─────────────────┤
│ .py            │       14 │       82.4% │          92.2 KB │           2,665 │
│ .md            │        2 │       11.8% │           5.5 KB │              63 │
│ .toml          │        1 │        5.9% │            503 B │              22 │
├────────────────┼──────────┼─────────────┼──────────────────┼─────────────────┤
│ Total          │       17 │      100.0% │          98.2 KB │           2,750 │
╰────────────────┴──────────┴─────────────┴──────────────────┴─────────────────╯
```

---

### 2. Análisis arquitectónico con Gemini (`analyze`)

Realiza un escaneo de la estructura, extrae el contenido de los archivos clave dentro de un presupuesto seguro y consulta a **Gemini** para emitir un informe arquitectónico exhaustivo dividido en 5 secciones:
1. **Resumen Ejecutivo**: Propósito del proyecto, tecnologías y nivel de madurez.
2. **Estructura y Arquitectura**: Patrón de diseño, responsabilidades de módulos y flujo de datos.
3. **Puntos Fuertes**: Buenas prácticas de modularidad, tipado y diseño identificadas.
4. **Áreas de Mejora y Riesgos**: Deuda técnica, acoplamiento, dependencias y riesgos de seguridad.
5. **Recomendaciones Prácticas**: Hoja de ruta priorizada con acciones de refactorización o mejoras inmediatas.

```bash
repo-analyzer analyze [RUTA] [OPCIONES]
```

#### Opciones y flags:

| Flag | Tipo / Valor | Por defecto | Descripción |
|---|---|---|---|
| `[RUTA]` | Argumento posicional | `.` | Directorio del proyecto a analizar. |
| `-o`, `--output` | Ruta (`Path`) | `None` | Ruta de archivo donde se guardará el reporte Markdown generado (ej. `reporte.md`). |
| `-m`, `--model` | Texto (`str`) | `gemini-3.8-flash` | Modelo de Google Gemini a utilizar. |
| `-k`, `--api-key` | Texto (`str`) | Variable de entorno | Clave de API de Gemini (si no está definida en `GEMINI_API_KEY`). |
| `-d`, `--max-depth` | Entero (`int`) | `None` | Límite de profundidad al escanear directorios para el contexto. |
| `--no-gitignore` | Bandera (`bool`) | `False` | Ignorar reglas de `.gitignore` al compilar contexto. |

#### Ejemplos de uso:

- **Análisis directo con salida formateada en terminal:**
  ```bash
  repo-analyzer analyze
  ```

- **Guardar el reporte Markdown generado en un archivo:**
  ```bash
  repo-analyzer analyze . --output reporte_arquitectura.md
  # O de forma abreviada:
  repo-analyzer analyze -o reporte.md
  ```

- **Pasar la clave de API explícitamente y usar un modelo específico:**
  ```bash
  repo-analyzer analyze /ruta/a/proyecto -k "AIzaSy..." -m gemini-3.8-flash -o auditoria.md
  ```

- **Analizar un subdirectorio limitando la profundidad:**
  ```bash
  repo-analyzer analyze ./src --max-depth 3 -o reporte-src.md
  ```

---

## 🔬 Detalles Técnicos y Filtrado

Para garantizar un funcionamiento ágil, seguro y sin costos imprevistos de API, Repo Analyzer CLI incorpora varias capas de protección:

1. **Priorización de Archivos Clave**:
   - Manifiestos: `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `pom.xml`, `requirements.txt`, `Dockerfile`, etc.
   - Documentación y especificaciones: `README.md`, `ARCHITECTURE.md`, `spec.md`.
   - Entrypoints: `main.py`, `app.py`, `cli.py`, `index.js`, `index.ts`, `main.go`, `main.rs`, etc.
2. **Presupuesto de Contexto**:
   - Archivos individuales > **100 KB** son excluidos del envío al LLM.
   - Presupuesto global total acumulado: máximo **500 KB** de contenido fuente enviado en el prompt.
3. **Detección de Binarios**:
   - Extensiones no legibles conocidas (`.png`, `.exe`, `.zip`, `.pyc`, `.sqlite`, `.wasm`, etc.).
   - Muestreo de los primeros 8 KB: detección de byte nulo (`\x00`) o error de decodificación UTF-8.
4. **Mapeo Robusto de Errores de API**:
   - Validación clara de clave de API ausente con sugerencias de configuración.
   - Manejo amigable ante errores de red, cuotas excedidas (`429 Resource Exhausted`) o contenido bloqueado por políticas de seguridad.

---

## 📁 Estructura del Proyecto

```text
repoAnalyzerCli/
├── repo_analyzer/              # Paquete principal
│   ├── __init__.py             # Versión y metadatos del paquete
│   ├── __main__.py             # Punto de entrada para ejecución `python -m repo_analyzer`
│   ├── cli.py                  # Definición de comandos Typer (`scan`, `analyze`) e interfaz CLI
│   ├── config.py               # Constantes de configuración, extensiones binarias y límites
│   ├── llm_client.py           # Cliente adaptador oficial del SDK `google-genai` para Gemini
│   ├── prompts.py              # Plantillas de prompt del sistema y usuario para el análisis
│   ├── scanner.py              # Motor de escaneo, parser de .gitignore, filtros y estadísticas
│   └── tree.py                 # Generador de árboles Rich, colores de extensiones y tablas
├── tests/                      # Suite de pruebas unitarias (69 pruebas)
│   ├── test_cli.py             # Tests de comandos CLI y control de errores con CliRunner
│   ├── test_llm_client.py      # Tests unitarios del cliente Gemini y mapeo de excepciones
│   ├── test_prompts.py         # Tests de ensamblado de prompts y formato de archivos
│   ├── test_scanner.py         # Tests de reglas .gitignore, binarios, límites y estadísticas
│   └── test_tree.py            # Tests de renderizado de árbol visual y tablas estadísticas
├── pyproject.toml              # Definición del proyecto, dependencias y script de consola
├── AGENT.md                    # Directivas y contexto de desarrollo para agentes
└── README.md                   # Documentación oficial y guía de uso
```

---

## 🧪 Ejecución de Pruebas

El proyecto cuenta con una cobertura completa de **69 pruebas unitarias** que verifican el escáner, los filtros de tamaño, el parseo de patrones `.gitignore`, el renderizado en Rich, el cliente Gemini (con simulación y manejo de fallos) y los comandos Typer.

Para ejecutar la suite de pruebas:

```bash
python -m unittest discover tests -v
```

Ejemplo de ejecución exitosa:
```text
Ran 69 tests in 0.589s

OK
```

---

## 📄 Licencia

Distribuido bajo la licencia de código abierto según los términos del repositorio. ¡Contribuciones, sugerencias e issues son bienvenidos!
