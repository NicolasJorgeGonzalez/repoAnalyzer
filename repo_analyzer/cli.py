"""CLI entrypoint and Typer commands for Repo Analyzer."""

from __future__ import annotations

from pathlib import Path
import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from repo_analyzer.config import DEFAULT_MODEL
from repo_analyzer.llm_client import GeminiAnalyzer, LLMAnalysisError, MissingApiKeyError
from repo_analyzer.prompts import SYSTEM_PROMPT, build_analysis_prompt
from repo_analyzer.scanner import get_key_files_content, scan_repository
from repo_analyzer.tree import create_rich_tree, create_stats_table, format_tree_as_text

app = typer.Typer(
    name="repo-analyzer",
    help="CLI tool to explore repositories and analyze architecture with Gemini.",
    no_args_is_help=True,
)
console = Console()


@app.command("scan")
def scan(
    path: Path = typer.Argument(
        Path("."),
        help="Ruta al directorio o repositorio a escanear.",
    ),
    max_depth: int | None = typer.Option(
        None,
        "--max-depth",
        "-d",
        help="Límite de profundidad para el escaneo de subdirectorios.",
    ),
    no_gitignore: bool = typer.Option(
        False,
        "--no-gitignore",
        help="Ignorar reglas de .gitignore durante el escaneo.",
    ),
    only_stats: bool = typer.Option(
        False,
        "--only-stats",
        "-s",
        help="Mostrar únicamente la tabla de resumen estadístico.",
    ),
) -> None:
    """Escanea la estructura de un repositorio e imprime su árbol y estadísticas."""
    target_path = path.resolve()
    if not target_path.exists():
        console.print(
            Panel(
                f"[bold red]Ruta inexistente:[/bold red] '{target_path}' no existe.",
                title="[bold red]Error[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)
    if not target_path.is_dir():
        console.print(
            Panel(
                f"[bold red]Ruta inválida:[/bold red] '{target_path}' no es un directorio.",
                title="[bold red]Error[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    try:
        files, stats, tree_dict = scan_repository(
            path=target_path,
            max_depth=max_depth,
            respect_gitignore=not no_gitignore,
        )
    except Exception as e:
        console.print(
            Panel(
                f"[bold red]Error durante el escaneo:[/bold red] {e}",
                title="[bold red]Error de Escaneo[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    if not only_stats:
        console.print()
        console.print(create_rich_tree(tree_dict))
        console.print()

    console.print(create_stats_table(stats))


@app.command("analyze")
def analyze(
    path: Path = typer.Argument(
        Path("."),
        help="Ruta al repositorio a analizar.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Ruta de archivo para guardar el reporte Markdown generado (ej. reporte.md).",
    ),
    model: str = typer.Option(
        DEFAULT_MODEL,
        "--model",
        "-m",
        help="Modelo de Gemini a utilizar para el análisis.",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="Clave de API de Gemini (por defecto se lee de la variable GEMINI_API_KEY).",
    ),
    max_depth: int | None = typer.Option(
        None,
        "--max-depth",
        "-d",
        help="Límite de profundidad para el escaneo de directorios.",
    ),
    no_gitignore: bool = typer.Option(
        False,
        "--no-gitignore",
        help="Ignorar archivos y reglas de .gitignore durante el escaneo.",
    ),
) -> None:
    """Analiza la arquitectura y salud de código de un repositorio usando Gemini."""
    target_path = path.resolve()
    if not target_path.exists():
        console.print(
            Panel(
                f"[bold red]Ruta inexistente:[/bold red] La ruta '{path}' no existe.",
                title="[bold red]Error[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)
    if not target_path.is_dir():
        console.print(
            Panel(
                f"[bold red]Ruta inválida:[/bold red] La ruta '{path}' no es un directorio.",
                title="[bold red]Error[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    # 1. Initialize analyzer client & check API key
    try:
        analyzer = GeminiAnalyzer(api_key=api_key, model_name=model)
    except MissingApiKeyError as e:
        console.print(
            Panel(
                f"[bold yellow]Configuración requerida:[/bold yellow]\n{e}\n\n"
                "[dim]Ejemplo:[/dim] export GEMINI_API_KEY=\"tu-api-key\"\n"
                "[dim]O mediante opción:[/dim] repo-analyzer analyze . --api-key \"tu-api-key\"",
                title="[bold red]Falta Gemini API Key[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(
            Panel(
                f"[bold red]Error al inicializar el cliente de Gemini:[/bold red] {e}",
                title="[bold red]Error de Inicialización[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    # 2. Scan repository & gather content
    try:
        files, stats, tree_dict = scan_repository(
            path=target_path,
            max_depth=max_depth,
            respect_gitignore=not no_gitignore,
        )
        key_files = get_key_files_content(files, root_path=target_path)
        tree_str = format_tree_as_text(tree_dict)
        prompt = build_analysis_prompt(
            repo_name=target_path.name,
            tree_str=tree_str,
            stats=stats,
            key_files=key_files,
        )
    except Exception as e:
        console.print(
            Panel(
                f"[bold red]Error al preparar datos del repositorio:[/bold red] {e}",
                title="[bold red]Error de Preparación[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    # 3. Call Gemini with animated spinner
    try:
        with console.status("[bold cyan]Analizando repositorio con Gemini...[/bold cyan]", spinner="dots"):
            report_md = analyzer.analyze_codebase(prompt=prompt, system_instruction=SYSTEM_PROMPT)
    except LLMAnalysisError as e:
        console.print(
            Panel(
                f"[bold red]No fue posible completar el análisis:[/bold red]\n{e}",
                title="[bold red]Fallo de Análisis con Gemini[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(
            Panel(
                f"[bold red]Error inesperado durante la llamada a Gemini:[/bold red]\n{e}",
                title="[bold red]Error Inesperado[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    # 4. Render markdown report to terminal
    console.print()
    console.print(
        Panel(
            Markdown(report_md),
            title=f"[bold green]Reporte Arquitectónico: {target_path.name}[/bold green]",
            subtitle=f"[dim]Modelo: {model}[/dim]",
            border_style="green",
            padding=(1, 2),
        )
    )

    # 5. Save report to disk if requested
    if output is not None:
        try:
            output_path = Path(output)
            if output_path.parent:
                output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report_md, encoding="utf-8")
            console.print(
                f"\n[bold green]✓[/bold green] Reporte guardado exitosamente en: [bold cyan]{output_path}[/bold cyan]"
            )
        except OSError as e:
            console.print(
                Panel(
                    f"[bold red]No se pudo guardar el archivo de reporte:[/bold red] {e}",
                    title="[bold red]Error al Guardar[/bold red]",
                    border_style="red",
                )
            )
            raise typer.Exit(code=1)
