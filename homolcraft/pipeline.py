from __future__ import annotations
"""
homolcraft.pipeline
-------------------
Orchestrateur DRY : gère la détection, le matching, l'export Homol
et les quatre modes « all », « line », « file » et « mulscale ».
"""

from dataclasses import dataclass
from enum import Enum, auto
from functools import partial
from glob import glob
from itertools import combinations, islice
from pathlib import Path
from typing import Dict, List, Sequence, Tuple
import concurrent.futures as cf
import statistics as stats
import time

# Dépendances internes
from .io import write_homol, read_pairs_xml, write_pairs_xml
from .utils import get_image_size_cached, log_section

# Dépendances « core » (détection, matching, export)
from .core.detectors import get_detector          # type: ignore
from .core.matchers  import get_matcher           # type: ignore
from .core.export    import filter_matches        # type: ignore


Point = Tuple[float, float, float, float, float]   # (x1, y1, x2, y2, score)


# ===========================================================================
# PARAMÉTRAGE PUBLIC
# ===========================================================================

class Mode(Enum):
    ALL       = auto()
    LINE      = auto()
    FILE      = auto()
    MULSCALE  = auto()


@dataclass(frozen=True)
class Settings:
    # ==== généraux =========================================================
    pattern: str                     # glob motif des images
    mode: Mode
    detect: str       = "sift"     # "sift" | "loftr" | autre…
    size: int | None    = 1500       # resize max côté long
    clahe: bool         = True
    sift_nfeat: int     = 4000
    nb_points: int      = 750
    nb_pts_min: int     = 30
    n_jobs: int         = 8

    # ==== mode LINE ========================================================
    delta: int          = 1
    circ: bool          = False

    # ==== mode FILE / MULSCALE ============================================
    xml_path: Path | None = None     # couples pré-définis (entrée / sortie)

    # ==== thresold MULSCALE ==============================================
    thresh_strategy: str  = "auto"   # auto | mean | median | fixed
    thresh_factor: float  = 0.5
    thresh_fixed: int     = 50


# ===========================================================================
# FONCTION PRINCIPALE
# ===========================================================================

def run(settings: Settings) -> Dict[str, object]:
    """
    Point d'entrée unique depuis la CLI.
    Retourne un dictionnaire de statistiques d'exécution.
    """
    tic = time.time()
    logger = log_section("Pipeline")

    imgs  = _find_images(settings.pattern)
    pairs = _pairs_from_mode(imgs, settings)
    logger(f"{len(imgs)} images · {len(pairs)} paires → mode {settings.mode.name}")

    # --- usines détecteur + matcher ---------------------------------------
    detect  = _factory_detector(settings)
    matcher = _factory_matcher(settings)

    # --- détection ---------------------------------------------------------
    logger("Détection…")
    feats = _par_map(detect, imgs, settings.n_jobs, title="Detect")

    # --- matching ----------------------------------------------------------
    logger("Matching…")
    m_per_pair = {}
    match_results = _par_map(
        lambda ab: matcher(
            Path(ab[0]), Path(ab[1]), feats[ab[0]], feats[ab[1]]
        ),
        pairs,
        settings.n_jobs,
        title="Match",
    )
    
    # Filtrer les résultats non vides
    for pair, pts in match_results.items():
        if pts:
            m_per_pair[pair] = pts
            
    logger(f"Pairs matchées : {len(m_per_pair)}")

    # --- export / mulscale -------------------------------------------------
    if settings.mode is Mode.MULSCALE:
        stats_mul = _mulscale_coarse_pass(m_per_pair, settings, tic)
        logger("Mulscale coarse pass terminée")
        return stats_mul

    stats_export = _export(m_per_pair, settings)
    stats_export["elapsed"] = time.time() - tic
    logger("Export terminé")
    return stats_export


# ===========================================================================
# HELPERS – PAIRS
# ===========================================================================

def _find_images(pattern: str) -> List[str]:
    """Liste triée des images correspondant au motif glob."""
    imgs = sorted(glob(pattern))
    if not imgs:
        raise FileNotFoundError(f"Aucune image ne correspond à {pattern!r}")
    return imgs


def _pairs_from_mode(imgs: Sequence[str], st: Settings) -> List[Tuple[str, str]]:
    """Génère les couples selon le mode choisi."""
    if st.mode is Mode.ALL or st.mode is Mode.MULSCALE:
        return [(a, b) for a, b in combinations(imgs, 2)]

    if st.mode is Mode.LINE:
        n = len(imgs)
        pairs = []
        for i, a in enumerate(imgs):
            for d in range(1, st.delta + 1):
                j = i + d
                if j < n:
                    pairs.append((a, imgs[j]))
                elif st.circ:
                    pairs.append((a, imgs[(j) % n]))
        return pairs

    if st.mode is Mode.FILE:
        if st.xml_path is None:
            raise ValueError("xml_path requis en mode FILE")
        cpls = read_pairs_xml(st.xml_path)
        return [(str(Path(a)), str(Path(b))) for a, b in cpls]

    raise RuntimeError(f"Mode inconnu : {st.mode}")


# ===========================================================================
# HELPERS – FACTORIES DETECT / MATCH
# ===========================================================================

def _factory_detector(st: Settings):
    """
    Retourne une fonction : path -> features
    NB : la détection est pure : pas de dépendance au pair.
    """
    detect = get_detector(
        name=st.detect,
        resize_max=st.size,
        clahe=st.clahe,
        sift_nfeatures=st.sift_nfeat,
    )
    return detect


def _factory_matcher(st: Settings):
    """Retourne une fonction : (pathA, pathB, featA, featB) -> List[Point]."""
    matcher = get_matcher(
        name="flann" if st.detect == "sift" else "loftr",
        nb_points=st.nb_points,
    )
    return matcher


# ===========================================================================
# HELPERS – PARALLEL MAP
# ===========================================================================

def _par_map(
    fn, iterable, n_jobs: int, title: str = ""
) -> Dict[object, object]:
    """
    Applique `fn` à chaque élément de `iterable` avec ThreadPool.
    Retourne un dictionnaire {élément: résultat}.
    """
    log = log_section(title)
    it = list(iterable)
    if n_jobs <= 1:
        return {x: fn(x) for x in it}

    with cf.ThreadPoolExecutor(max_workers=n_jobs) as ex:
        futures = {ex.submit(fn, x): x for x in it}
        results = {}
        for fut in cf.as_completed(futures):
            x = futures[fut]
            try:
                res = fut.result()
                results[x] = res
            except Exception as e:
                log(f"⚠︎ Erreur avec {x}: {e}")
        return results


# ===========================================================================
# EXPORT HOMOL
# ===========================================================================

def _export(
    matches_per_pair: Dict[Tuple[str, str], List[Point]],
    st: Settings,
) -> Dict[str, object]:
    """
    Filtre, écrit les Homol et renvoie quelques stats.
    """
    out_dir = Path("Homol")
    out_dir.mkdir(exist_ok=True)

    total_pts, kept_pairs = 0, 0
    for (a, b), pts in matches_per_pair.items():
        pts_sel = filter_matches(pts, max_pts=st.nb_points, min_pts=st.nb_pts_min)
        if not pts_sel:
            continue
        write_homol(out_dir, a, b, pts_sel)
        kept_pairs += 1
        total_pts += len(pts_sel)

    return dict(
        kept_pairs=kept_pairs,
        total_pairs=len(matches_per_pair),
        total_points_exported=total_pts,
        nb_images=len({p for ab in matches_per_pair for p in ab}),
    )


# ===========================================================================
# MULSCALE – COARSE PASS
# ===========================================================================

def _mulscale_coarse_pass(
    matches: Dict[Tuple[str, str], List[Point]],
    st: Settings,
    tic: float,
) -> Dict[str, object]:
    """
    Premier passage basse def. Sélectionne les couples « fiables »,
    écrit un XML, et retourne des stats. Le XML servira de base
    pour la passe haute def (à exécuter ensuite par l'utilisateur).
    """
    # ------------------------------------------------ seuil dynamique
    npts = [len(v) for v in matches.values()]
    thr = _compute_threshold(npts, st.thresh_strategy, st.thresh_factor, st.thresh_fixed)

    # ------------------------------------------------ split intra/inter
    intra, inter = _split_intra_inter(matches)

    selected = {
        p: pts
        for p, pts in matches.items()
        if len(pts) >= (thr // 2 if p in inter else thr)
    }

    xml_out = st.xml_path or Path("selected_pairs.xml")
    write_pairs_xml(
        xml_out,
        [(Path(a).name, Path(b).name) for a, b in selected.keys()],
    )

    return dict(
        nb_pairs_init=len(matches),
        nb_pairs_kept=len(selected),
        threshold=thr,
        intra_pairs=len(intra),
        inter_pairs=len(inter),
        xml_file=str(xml_out),
        elapsed=time.time() - tic,
    )


def _compute_threshold(
    values: Sequence[int], strategy: str, factor: float, fixed: int
) -> int:
    if strategy == "fixed":
        return fixed
    if not values:
        return fixed
    if strategy == "mean":
        return int(stats.mean(values) * factor)
    if strategy == "median":
        return int(stats.median(values) * factor)
    # auto : médiane si dispersion faible sinon moyenne
    stdev = stats.stdev(values) if len(values) > 1 else 0
    ref = stats.median(values) if stdev < 0.35 * stats.mean(values) else stats.mean(values)
    return max(5, int(ref * factor))


def _split_intra_inter(matches: Dict[Tuple[str, str], List[Point]]):
    """Sépare les couples intra-groupe vs inter-groupe (d'après le nom du dossier parent)."""
    intra, inter = set(), set()
    for a, b in matches:
        grp_a = Path(a).parent.name
        grp_b = Path(b).parent.name
        (intra if grp_a == grp_b else inter).add((a, b))
    return intra, inter
