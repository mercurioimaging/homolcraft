import click, glob, os, shutil, time
from pathlib import Path
from datetime import datetime
from homolcraft.refactor import run_pipeline  # the file updated in the canvas
from homolcraft.utils import get_ram_max_mb, write_run_log

ALGO_VERSION = "2.0.1"

# ---------------------------------------------------------------------------
# Shared CLI options ---------------------------------------------------------
# ---------------------------------------------------------------------------

COMMON_OPTS = [
    click.Option(["--size"], type=int, default=1000, help="Taille max du plus grand côté"),
    click.Option(["--detect"], type=click.Choice(["sift", "loftr"]), default="sift", help="Type de détecteur"),
    click.Option(["--clahe"], is_flag=True, default=True, help="Appliquer CLAHE"),
    click.Option(["--sift-nfeatures"], type=int, default=1000),
    click.Option(["--nb-points"], type=int, default=500, help="Nombre de points homologues par paire"),
    click.Option(["--n-jobs"], type=int, default=8, help="Nombre de processus parallèles"),
]


def _add_opts(fn):
    if not hasattr(fn, '__click_params__'):
        fn.__click_params__ = []
    for opt in reversed(COMMON_OPTS):
        fn.__click_params__.insert(0, opt)
    return fn

# ---------------------------------------------------------------------------
# Generic runner -------------------------------------------------------------
# ---------------------------------------------------------------------------

def _run(pattern: str, *, mode: str, delta: int | None = None, circ: bool = False, **kw):
    t0 = time.time()
    imgs = sorted(glob.glob(pattern))
    if not imgs:
        raise click.ClickException("Aucune image trouvée pour le pattern donné.")
    img_dir = Path(imgs[0]).parent
    out_dir = img_dir / "Homol"

    if out_dir.exists():
        shutil.move(out_dir, img_dir / "Homol_bkp")
    out_dir.mkdir()

    def log(msg):
        ts = datetime.now().strftime("%H:%M:%S")
        click.echo(f"[{ts}] {msg}")

    stats = run_pipeline(
        pattern=pattern,
        mode=mode,
        delta=delta or 1,
        circ=circ,
        detector=kw["detect"],
        size=kw["size"],
        clahe=kw["clahe"],
        sift_nfeatures=kw["sift_nfeatures"],
        nb_points=kw["nb_points"],
        n_jobs=kw["n_jobs"],
        write_workers=max(1, kw["n_jobs"] // 2),
        out_dir=out_dir,
        log=log,
    )

    elapsed = time.time() - t0
    ram = get_ram_max_mb()
    final_stats = {
        **stats.__dict__,
        "elapsed_sec": elapsed,
        "ram_max_mb": ram,
        "time_per_pair": elapsed / stats.nb_pairs if stats.nb_pairs else 0,
        "pairs_per_sec": stats.nb_pairs / elapsed if elapsed else 0,
    }

    # Summary to STDOUT -----------------------------------------------------
    click.echo("\n=== Résumé ===")
    for k, v in final_stats.items():
        click.echo(f"- {k}: {v}")

    write_run_log(final_stats, pattern, kw["detect"], kw["size"], kw["clahe"],
                  kw["sift_nfeatures"], kw["nb_points"], kw["n_jobs"], delta, circ)

    click.echo(f"\nTerminé en {elapsed:.1f}s → résultats dans {out_dir}/")

# ---------------------------------------------------------------------------
# CLI commands ---------------------------------------------------------------
# ---------------------------------------------------------------------------
@click.group(help="HomolCraft « 1‑clic » – Générateur de points homologues MicMac")
def cli():
    pass

@cli.command()
@click.argument("pattern")
@_add_opts
def all(pattern, **kw):
    """Calcul pour toutes les paires possibles."""
    _run(pattern, mode="all", **kw)

@cli.command()
@click.argument("pattern")
@click.option("--delta", type=int, default=1)
@click.option("--circ", is_flag=True, default=False)
@_add_opts
def line(pattern, delta, circ, **kw):
    """Calcul restreint aux voisins (linéaire ou circulaire)."""
    _run(pattern, mode="line", delta=delta, circ=circ, **kw)

# TODO: mulscale / file modes reuse the same _run() when implemented.

if __name__ == "__main__":
    cli()
