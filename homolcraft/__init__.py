"""
Paquet homolcraft
-----------------
Expose l'API publique :

    >>> from homolcraft import run, Settings, Mode
"""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    __version__ = _pkg_version("homolcraft")     # version du paquet installé
except PackageNotFoundError:                     # développement hors-paquet
    __version__ = "0.0.0.dev0"

# Version courante de l'algorithme HomolCraft
ALGO_VERSION = "3.2.3"

# API publique
from .pipeline import Settings, Mode, run

# Compat descendante : ancien nom de fonction
from .pipeline import run as run_pipeline

__all__: list[str] = [
    "Settings",
    "Mode",
    "run",
    "run_pipeline",
    "__version__",
    "ALGO_VERSION",
]
