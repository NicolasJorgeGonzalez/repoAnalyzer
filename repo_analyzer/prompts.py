"""Prompts and prompt builders for Gemini repository analysis."""

from __future__ import annotations

from repo_analyzer.scanner import RepoStats

SYSTEM_PROMPT: str = """\
Eres un arquitecto de software senior y revisor de código de élite con amplia experiencia en múltiples lenguajes, frameworks y patrones de diseño modernos.
Tu misión es analizar el repositorio de código proporcionado y generar un informe arquitectónico exhaustivo, profesional y accionable.

El informe debe estar formateado en Markdown claro y contener obligatoriamente las siguientes secciones:

# 1. Resumen Ejecutivo y Arquitectura
- Visión general del propósito y capacidades del proyecto.
- Stack tecnológico detectado (lenguajes, frameworks, herramientas de build y librerías clave).
- Patrones arquitectónicos identificados (ej. modular, hexagonal, MVC, microservicios, monolito, etc.).
- Estructura modular y flujo de datos principal.

# 2. Evaluación de Salud del Código y Buenas Prácticas
- Organización y estructura de directorios.
- Separación de responsabilidades y cohesión modular.
- Gestión de dependencias y configuración.
- Calidad y consistencia en el estilo, tipado y documentación.

# 3. Puntos de Dolor y Deuda Técnica
- Posibles cuellos de botella de rendimiento o escalabilidad.
- Riesgos de seguridad, robustez o manejo inadecuado de errores/excepciones.
- Acoplamiento excesivo, duplicación de código o antipatrones observados.
- Cobertura de pruebas o brechas en la estrategia de testing.

# 4. Propuestas Concretas de Refactorización y Mejora
- Recomendaciones prácticas, priorizadas (Alta / Media / Baja) y accionables.
- Ejemplos concretos de cómo refactorizar o reestructurar componentes críticos.
- Próximos pasos sugeridos para modernizar o robustecer el codebase.

Sé preciso, técnico, constructivo y fundamenta tus observaciones con base en los archivos y estructura provistos.
"""


def _format_size(size_bytes: int) -> str:
    """Format bytes into a human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _get_syntax_tag(filename: str) -> str:
    """Get appropriate markdown code fence tag based on file extension or name."""
    lower = filename.lower()
    if lower.endswith(".py"):
        return "python"
    if lower.endswith((".js", ".mjs", ".cjs")):
        return "javascript"
    if lower.endswith((".ts", ".tsx")):
        return "typescript"
    if lower.endswith(".json"):
        return "json"
    if lower.endswith(".toml"):
        return "toml"
    if lower.endswith((".yaml", ".yml")):
        return "yaml"
    if lower.endswith(".md"):
        return "markdown"
    if lower.endswith(".go"):
        return "go"
    if lower.endswith(".rs"):
        return "rust"
    if lower.endswith((".c", ".h")):
        return "c"
    if lower.endswith((".cpp", ".hpp", ".cc")):
        return "cpp"
    if lower.endswith(".java"):
        return "java"
    if lower.endswith(".sh"):
        return "bash"
    if lower.endswith(".sql"):
        return "sql"
    if lower.endswith(".html"):
        return "html"
    if lower.endswith(".css"):
        return "css"
    if lower.endswith(".xml"):
        return "xml"
    if "dockerfile" in lower:
        return "dockerfile"
    if "makefile" in lower:
        return "makefile"
    return ""


def build_analysis_prompt(
    repo_name: str,
    tree_str: str,
    stats: RepoStats,
    key_files: dict[str, str],
) -> str:
    """Build a structured analysis prompt for Gemini.

    Args:
        repo_name: Name of the repository or root directory.
        tree_str: Plain text representation of the file tree.
        stats: RepoStats object containing aggregated repository statistics.
        key_files: Dictionary mapping relative file paths to their content.

    Returns:
        Formatted prompt string ready for LLM generation.
    """
    # Format extension statistics breakdown
    top_extensions = sorted(
        stats.extension_counts.items(),
        key=lambda item: item[1],
        reverse=True,
    )
    ext_lines: list[str] = []
    for ext, count in top_extensions:
        size = stats.extension_sizes.get(ext, 0)
        lines = stats.extension_lines.get(ext, 0)
        ext_lines.append(f"- `{ext}`: {count} archivo(s), {lines:,} líneas ({_format_size(size)})")

    extensions_summary = "\n".join(ext_lines) if ext_lines else "- No se detectaron archivos."

    # Format key files content
    key_files_blocks: list[str] = []
    if key_files:
        for file_path, content in key_files.items():
            syntax = _get_syntax_tag(file_path)
            key_files_blocks.append(
                f"### Archivo: `{file_path}`\n```{syntax}\n{content}\n```"
            )
        key_files_formatted = "\n\n".join(key_files_blocks)
    else:
        key_files_formatted = "*(No se extrajeron archivos clave de texto)*"

    prompt = f"""\
# Información del Repositorio para Análisis: `{repo_name}`

## 1. Estadísticas Generales del Repositorio
- **Nombre:** {repo_name}
- **Total de Archivos:** {stats.total_files} ({stats.text_files_count} de texto, {stats.binary_files_count} binarios)
- **Total de Directorios:** {stats.total_dirs}
- **Líneas de Código Totales (archivos de texto):** {stats.total_lines:,}
- **Tamaño Total:** {_format_size(stats.total_size_bytes)}
- **Archivos omitidos por tamaño:** {stats.skipped_large_files_count}

### Desglose por Extensión:
{extensions_summary}

---

## 2. Estructura de Directorios y Archivos
```
{tree_str.strip()}
```

---

## 3. Contenido de Archivos Clave y de Configuración
A continuación se presenta el contenido extraído de los archivos clave y representativos del proyecto:

{key_files_formatted}

---

## Instrucciones Finales
Con base en la estructura, métricas y contenido de los archivos provistos, elabora el informe arquitectónico siguiendo la estructura requerida por el System Prompt.
"""
    return prompt
