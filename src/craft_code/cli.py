import typer
import tomllib
from craft_code.config.loader import load_config, save_config

app = typer.Typer(
    name="craft-code",
    help="Craft Code. A local LLM-powered assistant that can explore, " \
            "analyze, and modify your codebase through structured tool calls. " \
            "Chat with your codebase — locally and privately.",
    invoke_without_command=True,
)


def version_callback(value: bool):
    if value:
        with open("pyproject.toml", "rb") as f:
            pyproject = tomllib.load(f)
            version = pyproject["project"]["version"]
        typer.echo(version)
        raise typer.Exit()


@app.callback()
def main_callback(
    version: bool = typer.Option(
        None,
        "--version", "-v",
        help="Show craft-code version and exit.",
        callback=version_callback,
        is_eager=True
    )
):
    """Craft Code CLI entry point."""
    from craft_code.ui.app import CraftCodeApp
    app_instance = CraftCodeApp(workspace=".")
    app_instance.run()


@app.command("configure")
def configure():
    """Interactive configuration wizard for Craft Code."""
    typer.echo("🛠️  Craft Code configuration\n")

    current = load_config()
    provider = typer.prompt(
        "Select provider [lm_studio / ollama / openai]",
        default="lm_studio"
    )

    if provider not in current["models"]:
        typer.echo(f"❌ Unknown provider: {provider}")
        raise typer.Exit(code=1)

    model_cfg = current["models"][provider]
    base_url = typer.prompt("Base URL", default=model_cfg["base_url"])
    model = typer.prompt("Model name", default=model_cfg["model"])

    api_key = model_cfg.get("api_key", "")
    if provider == "openai":
        api_key = typer.prompt("OpenAI API key (starts with sk-...)", default=api_key, hide_input=True)
    elif provider in {"lm_studio", "ollama"}:
        typer.echo("Local mode detected — API key not required.")
        api_key = api_key or provider

    current["provider"] = provider
    current["models"][provider]["base_url"] = base_url
    current["models"][provider]["model"] = model
    current["models"][provider]["api_key"] = api_key

    save_config(current)
    typer.echo("✅ Configuration updated successfully!")


def main():
    app()


if __name__ == "__main__":
    main()
