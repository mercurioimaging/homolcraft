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
        nb_points=750, nb_pts_min=30, n_jobs=8, size_pattern2=None,
        xfeat_max_kpts=8192, xfeat_ransac_thresh=5.0, dust3r_conf=1.5, dust3r_refine=2000,
        lowe_ratio=0.75, ransac_thresh=4.0,
    )
    for k, default in reversed(list(opts.items())):
        fn = click.option(f"--{k.replace('_','-')}", default=default)(fn)
    fn = click.option("--ransac-model", default="homography",
                      type=click.Choice(["homography", "fundamental"]),
                      help="Modèle du RANSAC (SIFT/FLANN) : homographie (défaut, scène plane) ou matrice fondamentale (3D)")(fn)
    fn = click.option("--dedup/--no-dedup", default=False,
                      help="Un point image n'est utilisé qu'une fois par paire (meilleur match gardé)")(fn)
    fn = click.option("--min-disp", default=0.0, type=float,
                      help="Supprime les matchs dont le déplacement (px pleine résolution) est < min-disp "
                           "(points fixes : fond, table). 0 = désactivé ; usage : 3.0. Appliqué avant RANSAC et --nb-points")(fn)
    fn = click.option("--cache/--no-cache", "use_cache", default=True,
                      help="Cache SIFT disque (sift_cache/). --no-cache : ni lecture, ni écriture, dossier non créé")(fn)
    fn = click.option("--use-masq/--no-use-masq", default=False,
                      help="SIFT ne détecte que dans <image>_Masq.tif (masque MicMac, à côté de l'image ; 255 = zone utile). Sans effet pour LoFTR")(fn)
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
    for _k in ('use_masq', 'use_cache', 'xfeat_max_kpts', 'xfeat_ransac_thresh', 'dust3r_conf', 'dust3r_refine', 'lowe_ratio', 'ransac_thresh', 'ransac_model'):
        log_params.pop(_k, None)
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
        if 'size_low' not in log_params:
            log_params['size_low'] = st.size_low
    write_run_log(stats=stats, algo_version=ALGO_VERSION, mode=mode.name.lower(), **log_params)
    click.echo(f"\n✓ Terminé : {stats}")

# Les quatre commandes ↓ : aucune répétition de code.
@cli.command()
@common_opts
@click.argument("pattern")
@click.option("--pattern2", default=None, type=str, help="Second pattern pour matching croisé")
@click.option("--sift-nfeat-pattern2", default=None, type=int, help="Nombre de features SIFT pour pattern2")
def all(pattern, pattern2, sift_nfeat_pattern2, **kw):
    _launch(Mode.ALL, pattern=pattern, pattern2=pattern2, sift_nfeat_pattern2=sift_nfeat_pattern2, **kw)

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
@click.option("--pattern2", default=None, type=str, help="Second pattern pour matching croisé")
@click.option("--xml-path", type=click.Path(), default=None)
@click.option("--thresh-strategy",
              type=click.Choice(["auto", "mean", "median", "fixed"]),
              default="auto")
@click.option("--thresh-factor", default=.5, type=float)
@click.option("--thresh-fixed", default=50, type=int)
@click.option("--sift-nfeat-low", default=500, type=int, 
              help="Nombre de points SIFT à détecter pour la passe rapide (la passe haute résolution utilisera --sift-nfeat)")
@click.option("--size-low", default=None, type=int,
              help="Taille max (px) pour la passe rapide ; par défaut = --size")
def mulscale(pattern, pattern2, **kw):
    """
    Traitement en deux passes (rapide puis précise) pour optimiser le calcul des points homologues.
    
    1. Passe rapide (basse résolution) : utilise --sift-nfeat-low pour détecter moins de points
    2. Passe précise (haute résolution) : utilise --sift-nfeat uniquement sur les paires pertinentes
    
    Les points homologues finaux sont écrits dans le dossier Homol.
    """
    # Convertir xml_path en Path si présent
    if kw.get('xml_path'):
        kw['xml_path'] = Path(kw['xml_path'])
    _launch(Mode.MULSCALE, pattern=pattern, pattern2=pattern2, **kw)
