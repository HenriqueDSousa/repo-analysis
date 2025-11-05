import typer
from miner import miner

app = typer.Typer(help="Ferramenta de Mineração de Repositórios")

app.add_typer(miner.app, help="Análise de Código com MI")

if __name__ == "__main__":
    app()
