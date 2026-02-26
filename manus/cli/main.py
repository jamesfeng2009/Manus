"""CLI interface for Manus."""

import asyncio
import sys
from typing import Optional

import typer

app = typer.Typer(help="Manus - AI Agent CLI")

from manus.agents import SimpleAgentTeam
from manus.config import get_config
from manus.models import get_model_factory
from manus.tasks import get_task_manager


@app.command()
def interact(
    model: str = typer.Option("gpt-4o", help="Model to use"),
    system_prompt: Optional[str] = typer.Option(None, help="System prompt"),
):
    """Start interactive chat session."""
    typer.echo(f"Starting interactive session with {model}")
    typer.echo("Press Ctrl+C to exit\n")

    team = SimpleAgentTeam()

    async def chat_loop():
        messages = []
        while True:
            try:
                user_input = typer.prompt("You")
                if not user_input.strip():
                    continue

                if user_input.lower() in ["exit", "quit"]:
                    break

                result = await team.execute("interactive", user_input)
                typer.echo(f"\nAssistant: {result.final_response}\n")

            except KeyboardInterrupt:
                break
            except Exception as e:
                typer.echo(f"Error: {e}", err=True)

    asyncio.run(chat_loop())
    typer.echo("\nGoodbye!")


@app.command()
def run(
    task: str = typer.Argument(..., help="Task description"),
    model: str = typer.Option("gpt-4o", help="Model to use"),
    save: bool = typer.Option(True, help="Save task output"),
):
    """Run a single task."""
    typer.echo(f"Running task: {task}")

    team = SimpleAgentTeam()

    async def execute_task():
        result = await team.execute("cli", task)
        return result

    result = asyncio.run(execute_task())

    typer.echo(f"\nStatus: {result.status.value}")
    typer.echo(f"Duration: {result.duration:.2f}s")
    typer.echo(f"\nResult:\n{result.final_response}")

    if save:
        tm = get_task_manager()
        task_obj = tm.create_task(task)
        tm.update_task(
            task_obj.task_id,
            status=result.status.value,
            result={"response": result.final_response},
        )
        typer.echo(f"\nTask saved: {task_obj.task_id}")


@app.command()
def tasks(
    list_all: bool = typer.Option(False, "--all", help="List all tasks"),
    status_filter: Optional[str] = typer.Option(None, help="Filter by status"),
):
    """List tasks."""
    tm = get_task_manager()

    if list_all:
        all_tasks = tm.list_tasks(limit=100)
    else:
        pending = tm.list_tasks(status="pending", limit=10)
        running = tm.list_tasks(status="running", limit=10)
        all_tasks = pending + running

    if status_filter:
        all_tasks = [t for t in all_tasks if t.status.value == status_filter]

    if not all_tasks:
        typer.echo("No tasks found")
        return

    typer.echo(f"{'Task ID':<25} {'Status':<12} {'Created':<20}")
    typer.echo("-" * 60)
    for t in all_tasks:
        typer.echo(f"{t.task_id:<25} {t.status.value:<12} {t.created_at.strftime('%Y-%m-%d %H:%M'):<20}")


@app.command()
def models():
    """List available models."""
    factory = get_model_factory()
    config = get_config()

    typer.echo(f"Default model: {config.defaults.default_model}\n")
    typer.echo("Available models:")
    for model in factory.list_available_models():
        typer.echo(f"  - {model}")


@app.command()
def config_show():
    """Show current configuration."""
    config = get_config()

    typer.echo("Configuration:")
    typer.echo(f"  Default model: {config.defaults.default_model}")
    typer.echo(f"  Temperature: {config.defaults.temperature}")
    typer.echo(f"  Max tokens: {config.defaults.max_tokens}")
    typer.echo(f"  Planner model: {config.defaults.planner_model}")
    typer.echo(f"  Executor model: {config.defaults.executor_model}")
    typer.echo(f"  Verifier model: {config.defaults.verifier_model}")

    typer.echo("\nProviders:")
    for p in config.models:
        typer.echo(f"  {p.provider}: {len(p.models)} models")


if __name__ == "__main__":
    app()
