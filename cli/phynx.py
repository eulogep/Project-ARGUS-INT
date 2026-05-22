#!/usr/bin/env python3
"""
PHYNX CLI — Interface en ligne de commande
cli/phynx.py

Usage :
  phynx investigate email john.doe@example.com --depth 3
  phynx investigate username johndoe --depth 2
  phynx graph export <investigation_id> --format gexf
  phynx modules list
  phynx status <investigation_id>
"""
import typer
import httpx
import json
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import print as rprint
from typing import Optional
from enum import Enum

app = typer.Typer(
    name="phynx",
    help="🔍 PHYNX — Framework OSINT Full-Spectrum",
    rich_markup_mode="rich"
)
investigate_app = typer.Typer(help="Lancer des investigations OSINT")
graph_app = typer.Typer(help="Gestion du graphe de liens")
modules_app = typer.Typer(help="Gestion des modules")

app.add_typer(investigate_app, name="investigate")
app.add_typer(graph_app, name="graph")
app.add_typer(modules_app, name="modules")

console = Console()

API_URL = "http://localhost:8000"


class TargetType(str, Enum):
    email = "email"
    username = "username"
    domain = "domain"
    ip = "ip"
    phone = "phone"
    wallet = "wallet"
    image = "image"


class ExportFormat(str, Enum):
    json = "json"
    gexf = "gexf"
    csv = "csv"
    pdf = "pdf"


# ──────────────────────────────────────────────────────────────
#  phynx investigate <type> <target>
# ──────────────────────────────────────────────────────────────

@investigate_app.command("run")
def run_investigation(
    target_type: TargetType = typer.Argument(..., help="Type de cible"),
    target: str = typer.Argument(..., help="Valeur de la cible"),
    depth: int = typer.Option(1, "--depth", "-d", min=1, max=5, help="Profondeur d'investigation (1-5)"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Suivre la progression en temps réel"),
    api_url: str = typer.Option(API_URL, "--api", help="URL de l'API PHYNX"),
):
    """Lance une investigation OSINT asynchrone."""

    console.print(Panel(
        f"[bold cyan]🎯 Cible :[/] {target}\n"
        f"[bold cyan]📋 Type  :[/] {target_type.value}\n"
        f"[bold cyan]🔍 Profondeur :[/] {depth}",
        title="[bold]PHYNX Investigation[/]",
        border_style="cyan"
    ))

    with httpx.Client(timeout=30.0) as client:
        try:
            response = client.post(
                f"{api_url}/api/v1/investigations",
                json={
                    "target": target,
                    "target_type": target_type.value,
                    "depth": depth
                }
            )
            response.raise_for_status()
            data = response.json()

            investigation_id = data["investigation_id"]
            console.print(f"[green]✅ Investigation lancée[/] — ID: [bold]{investigation_id}[/]")

            if watch:
                _watch_investigation(client, api_url, investigation_id)
            else:
                console.print(f"\n[dim]Pour suivre la progression :[/]")
                console.print(f"  phynx status {investigation_id}")

        except httpx.ConnectError:
            console.print("[red]❌ Impossible de se connecter à l'API PHYNX.[/]")
            console.print(f"[dim]Vérifiez que l'API tourne sur {api_url}[/]")
            raise typer.Exit(1)


def _watch_investigation(client: httpx.Client, api_url: str, investigation_id: str):
    """Polling du statut avec affichage temps réel."""
    import time

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Collecte en cours...", total=None)

        while True:
            time.sleep(3)
            try:
                resp = client.get(f"{api_url}/api/v1/investigations/{investigation_id}")
                data = resp.json()
                status = data.get("status", "PENDING")
                count = data.get("result_count", 0)

                progress.update(task, description=f"[cyan]{status}[/] — {count} résultats collectés")

                if status in ("COMPLETED", "FAILED"):
                    break

            except Exception:
                break

    # Afficher le résumé final
    _show_status(client, api_url, investigation_id)


# ──────────────────────────────────────────────────────────────
#  phynx status <investigation_id>
# ──────────────────────────────────────────────────────────────

@app.command("status")
def status(
    investigation_id: str = typer.Argument(..., help="ID de l'investigation"),
    api_url: str = typer.Option(API_URL, "--api", help="URL de l'API"),
):
    """Affiche le statut d'une investigation."""
    with httpx.Client(timeout=10.0) as client:
        _show_status(client, api_url, investigation_id)


def _show_status(client: httpx.Client, api_url: str, investigation_id: str):
    try:
        resp = client.get(f"{api_url}/api/v1/investigations/{investigation_id}")
        data = resp.json()

        status_colors = {
            "PENDING": "yellow",
            "COLLECTING": "blue",
            "CORRELATING": "cyan",
            "COMPLETED": "green",
            "FAILED": "red",
        }
        color = status_colors.get(data.get("status", ""), "white")

        console.print(Panel(
            f"[bold]Statut :[/] [{color}]{data.get('status')}[/]\n"
            f"[bold]Résultats :[/] {data.get('result_count', 0)}\n"
            f"[bold]Message :[/] {data.get('message', '-')}",
            title=f"Investigation [dim]{investigation_id[:8]}...[/]",
            border_style=color
        ))

        if data.get("llm_summary"):
            console.print(Panel(
                data["llm_summary"],
                title="[bold cyan]🤖 Analyse LLM Locale[/]",
                border_style="cyan"
            ))

    except Exception as e:
        console.print(f"[red]Erreur : {e}[/]")


# ──────────────────────────────────────────────────────────────
#  phynx graph export <investigation_id>
# ──────────────────────────────────────────────────────────────

@graph_app.command("export")
def export_graph(
    investigation_id: str = typer.Argument(...),
    format: ExportFormat = typer.Option(ExportFormat.json, "--format", "-f"),
    output: str = typer.Option("./graph_export", "--output", "-o"),
    api_url: str = typer.Option(API_URL, "--api"),
):
    """Exporte le graphe d'une investigation."""
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{api_url}/api/v1/graph/{investigation_id}",
            params={"format": format.value}
        )
        resp.raise_for_status()

        filename = f"{output}.{format.value}"
        with open(filename, "w", encoding="utf-8") as f:
            if format == ExportFormat.json:
                json.dump(resp.json(), f, ensure_ascii=False, indent=2)
            else:
                f.write(resp.text)

        console.print(f"[green]✅ Graphe exporté :[/] {filename}")
        data = resp.json()
        console.print(
            f"   Nœuds : [bold]{len(data.get('nodes', []))}[/] | "
            f"Relations : [bold]{len(data.get('edges', []))}[/]"
        )


# ──────────────────────────────────────────────────────────────
#  phynx modules list
# ──────────────────────────────────────────────────────────────

@modules_app.command("list")
def list_modules(
    api_url: str = typer.Option(API_URL, "--api"),
):
    """Liste tous les modules disponibles."""
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(f"{api_url}/api/v1/modules")
        modules = resp.json()

    table = Table(title="Modules PHYNX", show_header=True, header_style="bold cyan")
    table.add_column("Nom", style="bold")
    table.add_column("Version")
    table.add_column("État")
    table.add_column("Types de cibles")
    table.add_column("Queue")

    for m in modules:
        status_str = "[green]✅ Actif[/]" if m.get("enabled") else "[red]❌ Désactivé[/]"
        table.add_row(
            m["name"],
            m.get("version", "-"),
            status_str,
            ", ".join(m.get("target_types", [])),
            m.get("queue", "-")
        )

    console.print(table)


if __name__ == "__main__":
    app()
