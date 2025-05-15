"""
Exécute la CLI quand on fait  `python -m homolcraft …`
"""
from .cli import cli
from . import ALGO_VERSION

if __name__ == "__main__":
    cli()
