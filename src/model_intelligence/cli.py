from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from model_intelligence.collectors import arena, models_dev, openrouter
from model_intelligence.http import ConditionalHttpClient
from model_intelligence.snapshots import SnapshotOutcome, SnapshotStore

app = typer.Typer(no_args_is_help=True, help="Collect and inspect model-intelligence sources.")
collect_app = typer.Typer(no_args_is_help=True, help="Run source collectors.")
app.add_typer(collect_app, name="collect")
console = Console()

Collector = Callable[[ConditionalHttpClient, SnapshotStore], Awaitable[SnapshotOutcome]]


async def _run(name: str, collector: Collector, root: Path) -> SnapshotOutcome:
    store = SnapshotStore(root)
    async with ConditionalHttpClient() as client:
        outcome = await collector(client, store)
    _print_outcome(name, outcome)
    return outcome


def _print_outcome(name: str, outcome: SnapshotOutcome) -> None:
    table = Table(title=name)
    table.add_column("changed")
    table.add_column("304")
    table.add_column("sha256")
    table.add_column("body")
    table.add_row(
        str(outcome.changed),
        str(outcome.not_modified),
        outcome.body_sha256 or "-",
        str(outcome.body_path or "-"),
    )
    console.print(table)


@collect_app.command("models-dev")
def collect_models_dev(
    root: Path = typer.Option(Path("var"), help="Runtime snapshot/state root."),
) -> None:
    asyncio.run(_run("models.dev", models_dev.collect, root))


@collect_app.command("openrouter-models")
def collect_openrouter_models(
    root: Path = typer.Option(Path("var"), help="Runtime snapshot/state root."),
) -> None:
    asyncio.run(_run("OpenRouter models", openrouter.collect_models, root))


@collect_app.command("arena-manifest")
def collect_arena_manifest(
    root: Path = typer.Option(Path("var"), help="Runtime snapshot/state root."),
) -> None:
    asyncio.run(_run("Arena HF parquet manifest", arena.collect_manifest, root))


@collect_app.command("bootstrap")
def collect_bootstrap(
    root: Path = typer.Option(Path("var"), help="Runtime snapshot/state root."),
) -> None:
    async def run_all() -> None:
        store = SnapshotStore(root)
        async with ConditionalHttpClient() as client:
            jobs: list[tuple[str, Collector]] = [
                ("models.dev", models_dev.collect),
                ("OpenRouter models", openrouter.collect_models),
                ("Arena HF parquet manifest", arena.collect_manifest),
            ]
            for name, collector in jobs:
                outcome = await collector(client, store)
                _print_outcome(name, outcome)

    asyncio.run(run_all())


if __name__ == "__main__":
    app()
