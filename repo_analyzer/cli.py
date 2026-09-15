"""CLI entrypoint for Repo Analyzer."""

import typer

app = typer.Typer(
    name="repo-analyzer",
    help="CLI tool to explore repositories and analyze architecture with Gemini.",
)
