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
    # Supprimer xml_path des paramètres de log pour le mode mulscale
    if mode == Mode.MULSCALE and 'xml_path' in log_params:
        log_params.pop('xml_path')
    # S'assurer que les paramètres spécifiques au mulscale sont présents
    if mode == Mode.MULSCALE:
        if 'thresh_strategy' not in log_params:
            log_params['thresh_strategy'] = st.thresh_strategy
        if 'thresh_factor' not in log_params:
            log_params['thresh_factor'] = st.thresh_factor
        if 'thresh_fixed' not in log_params:
            log_params['thresh_fixed'] = st.thresh_fixed
        if 'sift_nfeat_low' not in log_params:
            log_params['sift_nfeat_low'] = st.sift_nfeat_low
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
@click.option("--sift-nfeat-low", default=500, type=int, 
              help="Nombre de points SIFT à détecter pour la passe rapide (la passe haute résolution utilisera --sift-nfeat)")
def mulscale(pattern, **kw):
    """
    Traitement en deux passes (rapide puis précise) pour optimiser le calcul des points homologues.
    
    1. Passe rapide (basse résolution) : utilise --sift-nfeat-low pour détecter moins de points
    2. Passe précise (haute résolution) : utilise --sift-nfeat uniquement sur les paires pertinentes
    
    Les points homologues finaux sont écrits dans le dossier Homol.
    """
    # Convertir xml_path en Path si présent
    if kw.get('xml_path'):
        kw['xml_path'] = Path(kw['xml_path'])
    _launch(Mode.MULSCALE, pattern=pattern, **kw)
