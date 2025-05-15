import click
from enum import Enum
from pathlib import Path
from homolcraft.pipeline import Settings, Mode, run
from homolcraft import ALGO_VERSION
from .utils import write_run_log

# ------------------------------------------------------------------
# Générateur d'options DRY -----------------------------------------
# ------------------------------------------------------------------
def common_opts(fn):
    """Injecte toutes les options communes en une seule fois."""
    opts = dict(
        size=1500, detect="sift", clahe=True, sift_nfeat=4000,
        nb_points=750, nb_pts_min=30, n_jobs=8,
    )
    for k, default in reversed(list(opts.items())):
        fn = click.option(f"--{k.replace('_','-')}", default=default)(fn)
    return fn

@click.group()
def cli():
    """HomolCraft – CLI unifiée"""

def _launch(mode: Mode, **kw):
    st = Settings(mode=mode, **kw)
    stats = run(st)
    # Écrire dans le log avec la version
    # Ajuster les paramètres pour write_run_log
    log_params = kw.copy()
    if 'sift_nfeat' in log_params:
        log_params['sift_nfeatures'] = log_params.pop('sift_nfeat')
    if 'nb_pts_min' in log_params:
        log_params['nb_pts_mini'] = log_params.pop('nb_pts_min')
    write_run_log(stats=stats, algo_version=ALGO_VERSION, mode=mode.name.lower(), **log_params)
    click.echo(f"\n✓ Terminé : {stats}")

# Les quatre commandes ↓ : aucune répétition de code.
@cli.command()
@common_opts
@click.argument("pattern")
def all(pattern, **kw):
    _launch(Mode.ALL, pattern=pattern, **kw)

@cli.command()
@common_opts
@click.argument("pattern")
@click.option("--delta", default=1, type=int)
@click.option("--circ/--no-circ", default=False)
def line(pattern, delta, circ, **kw):
    _launch(Mode.LINE, pattern=pattern, delta=delta, circ=circ, **kw)

@cli.command()
@common_opts
@click.argument("pattern")
@click.argument("xml_path", type=click.Path(exists=True))
def file(pattern, xml_path, **kw):
    _launch(Mode.FILE, pattern=pattern, xml_path=Path(xml_path), **kw)

@cli.command()
@common_opts
@click.argument("pattern")
@click.option("--xml-path", type=click.Path(), default=None)
@click.option("--thresh-strategy",
              type=click.Choice(["auto", "mean", "median", "fixed"]),
              default="auto")
@click.option("--thresh-factor", default=.5, type=float)
@click.option("--thresh-fixed", default=50, type=int)
def mulscale(pattern, **kw):
    _launch(Mode.MULSCALE, pattern=pattern, **kw)
