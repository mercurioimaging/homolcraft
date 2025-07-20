from __future__ import annotations
"""
homolcraft.pipeline
-------------------
Orchestrateur DRY (avec popularité des points).
"""

from dataclasses import dataclass
from enum import Enum, auto
from glob import glob
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Sequence, Tuple, Any, Optional
import concurrent.futures as cf
import statistics as stats
import time
from functools import partial
import subprocess
import sys
import os

# Internes
from .io import write_homol, read_pairs_xml, write_pairs_xml
from .utils import log_section
from .core.detectors import get_detector
from .core.matchers import get_matcher
from .core.export import filter_matches, export_micmac_homol, Point

# ---------------------------------------------------------------------------
# Paramètres publics
# ---------------------------------------------------------------------------

class Mode(Enum):
    ALL      = auto()
    LINE     = auto()
    FILE     = auto()
    MULSCALE = auto()


@dataclass(frozen=True)
class Settings:
    pattern: str
    mode: Mode
    detect: str        = "sift"
    size: int | None   = 1500
    clahe: bool        = True
    sift_nfeat: int    = 10000
    nb_points: int     = 750
    nb_pts_min: int    = 30
    n_jobs: int        = 8
    # line
    delta: int         = 4
    circ: bool         = True
    # file / mulscale
    xml_path: Path | None = None
    # mulscale
    thresh_strategy: str = "auto"
    thresh_factor: float = 0.5
    thresh_fixed: int    = 50
    sift_nfeat_low: int  = 1000


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run(st: Settings) -> Dict[str, object]:
    tic = time.time()
    log = log_section("Pipeline")

    imgs  = _find_images(st.pattern)
    
    # Vérifier et normaliser les images si nécessaire
    _check_and_normalize_images(imgs)
    
    pairs = _pairs_from_mode(imgs, st)
    log(f"{len(imgs)} images · {len(pairs)} paires → mode {st.mode.name}")

    detect  = _factory_detector(st)
    matcher = _factory_matcher(st)

    feats = _par_map(detect, imgs, st.n_jobs, "Detect")

    # ---------- matching ----------------------------------------------------
    log("Matching…")
    match_dict: Dict[Tuple[str, str], List[Point]] = {
        pair: pts for pair, pts in
        _par_map(lambda ab: matcher(
            Path(ab[0]), Path(ab[1]), feats[ab[0]], feats[ab[1]]
        ), pairs, st.n_jobs, "Match").items()
        if pts
    }
    log(f"Pairs matchées : {len(match_dict)}")

    # ---------- mulscale première passe (brute) -----------------------------
    if st.mode is Mode.MULSCALE:
        xml_out, sel_pairs = _mulscale_coarse_pass(match_dict, st)
        log("Mulscale coarse pass terminée")

        # --------- seconde passe haute déf (Mode.FILE) ----------------------
        log("Passe haute résolution…")
        hi_st = Settings(
            **{**st.__dict__, "mode": Mode.FILE, "xml_path": xml_out,
               "sift_nfeat": st.sift_nfeat, "detect": st.detect}
        )
        high_stats = run(hi_st)   # récursion contrôlée
        return {
            "coarse": {"init": len(match_dict), "kept": len(sel_pairs)},
            "high":   high_stats,
            "elapsed_total": time.time() - tic
        }

    # ---------- filtrage + export (avec popularité) -------------------------
    occ = _compute_occurrences(match_dict)  # popularité globale
    export_stats = _export(match_dict, st, occ)
    export_stats["elapsed"] = time.time() - tic
    return export_stats


# ---------------------------------------------------------------------------
# Helpers paires
# ---------------------------------------------------------------------------

def _find_images(pattern: str) -> List[str]:
    imgs = sorted(glob(pattern))
    if not imgs:
        raise FileNotFoundError(pattern)
    return imgs


def _pairs_from_mode(imgs: Sequence[str], st: Settings) -> List[Tuple[str, str]]:
    if st.mode in {Mode.ALL, Mode.MULSCALE}:
        return [(a, b) for a, b in combinations(imgs, 2)]

    if st.mode is Mode.LINE:
        n = len(imgs)
        out = []
        for i, a in enumerate(imgs):
            for d in range(1, st.delta + 1):
                j = i + d
                if j < n:
                    out.append((a, imgs[j]))
                elif st.circ:
                    out.append((a, imgs[j % n]))
        return out

    if st.mode is Mode.FILE:
        if st.xml_path is None:
            raise ValueError("xml_path requis")
        cpls = read_pairs_xml(st.xml_path)
        m = {Path(p).name: p for p in imgs}
        return [(m[a], m[b]) for a, b in cpls if a in m and b in m]

    raise RuntimeError(st.mode)


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _factory_detector(st: Settings):
    sift_nf = st.sift_nfeat_low if st.mode is Mode.MULSCALE else st.sift_nfeat
    return get_detector(name=st.detect, resize_max=st.size,
                        clahe=st.clahe, sift_nfeatures=sift_nf)


def _factory_matcher(st: Settings):
    return get_matcher(name="flann" if st.detect == "sift" else "loftr",
                       nb_points=st.nb_points)


# ---------------------------------------------------------------------------
# Parallel map
# ---------------------------------------------------------------------------

def _par_map(fn, iterable, n_jobs: int, title: str):
    log = log_section(title)
    seq = list(iterable)
    if n_jobs <= 1:
        return {x: fn(x) for x in seq}

    with cf.ThreadPoolExecutor(max_workers=n_jobs) as ex:
        futs = {ex.submit(fn, x): x for x in seq}
        out = {}
        for f in cf.as_completed(futs):
            x = futs[f]
            try:
                out[x] = f.result()
            except Exception as e:
                log(f"⚠︎ {x}: {e}")
        return out


# ---------------------------------------------------------------------------
# Export avec popularité
# ---------------------------------------------------------------------------

def _compute_occurrences(matches: Dict[Tuple[str, str], List[Point]]):
    from collections import defaultdict
    occ: Dict[Tuple[str, int, int], int] = defaultdict(int)
    for (a, b), pts in matches.items():
        for x1, y1, x2, y2, _ in pts:
            occ[(a, round(x1), round(y1))] += 1
            occ[(b, round(x2), round(y2))] += 1
    return occ


def _export(matches: Dict[Tuple[str, str], List[Point]],
            st: Settings,
            occ) -> Dict[str, object]:
    img_dir = Path(next(iter(matches))[0]).parent if matches else Path(".")
    out_dir = img_dir / "Homol"
    out_dir.mkdir(exist_ok=True)

    kept, total_pts = 0, 0
    for (path_a, path_b), pts in matches.items(): # path_a, path_b sont les chemins complets
        # on prépare une version partielle de filter_matches avec les infos d'images
        # Note: filter_matches utilise les noms d'image, pas les chemins, pour OccMap.
        # Cela devrait être cohérent avec la façon dont OccMap est construit.
        # Si OccMap est indexé par les noms de base, alors Path(path_a).name est correct.
        fm = partial(_filter_with_occ, img1=Path(path_a).name, img2=Path(path_b).name, occ=occ,
                     max_pts=st.nb_points, min_pts=st.nb_pts_min)
        pts_sel = fm(pts)
        if not pts_sel:
            continue
        # Passer les chemins complets path_a, path_b en plus des noms de base
        export_micmac_homol(str(out_dir), 
                            path_a, path_b, 
                            Path(path_a).name, Path(path_b).name, 
                            pts_sel)
        kept += 1
        total_pts += len(pts_sel)

    return dict(
        kept_pairs=kept,
        total_pairs=len(matches),
        total_points_exported=total_pts,
        homol_dir=str(out_dir)
    )


def _filter_with_occ(points: List[Point], *,
                      img1: str, img2: str, occ,
                      max_pts: int, min_pts: int):
    # on réutilise filter_matches mais en lui donnant une clé de tri custom
    pts_sorted = sorted(
        points,
        key=lambda p: (p[4] / max(
            occ.get((img1, round(p[0]), round(p[1])), 1),
            occ.get((img2, round(p[2]), round(p[3])), 1)
        ))
    )
    pts_buf = pts_sorted[: max_pts * 2]
    # on appelle la version "occurrences=None" pour utiliser sampling
    return filter_matches(
        pts_buf,
        max_pts=max_pts,
        min_pts=min_pts,
        occurrences=None  # déjà triés par popularité
    )


# ---------------------------------------------------------------------------
# Mulscale coarse (brut)
# ---------------------------------------------------------------------------

def _mulscale_coarse_pass(matches, st: Settings):
    npts = [len(v) for v in matches.values()]
    thr = _threshold(npts, st)
    intra, inter = _split(matches)

    kept = {p: pts for p, pts in matches.items()
            if len(pts) >= (thr // 2 if p in inter else thr)}

    xml_out = st.xml_path or Path(_find_images(st.pattern)[0]).parent / "selected_pairs.xml"
    write_pairs_xml(xml_out, [(Path(a).name, Path(b).name) for a, b in kept])

    return xml_out, kept


def _threshold(vals, st: Settings):
    if st.thresh_strategy == "fixed":
        return st.thresh_fixed
    if not vals:
        return st.thresh_fixed
    if st.thresh_strategy == "mean":
        return int(stats.mean(vals) * st.thresh_factor)
    if st.thresh_strategy == "median":
        return int(stats.median(vals) * st.thresh_factor)
    # auto
    sd = stats.stdev(vals) if len(vals) > 1 else 0
    ref = stats.median(vals) if sd < .35 * stats.mean(vals) else stats.mean(vals)
    return max(5, int(ref * st.thresh_factor))


def _split(matches):
    intra, inter = set(), set()
    for a, b in matches:
        (intra if Path(a).parent.name == Path(b).parent.name else inter).add((a, b))
    return intra, inter


# ---------------------------------------------------------------------------
# Vérification et normalisation des images
# ---------------------------------------------------------------------------

def _check_and_normalize_images(images: List[str]) -> None:
    """Vérifie l'orientation et la résolution des images, normalise si nécessaire"""
    from PIL import Image, ImageOps
    
    log = log_section("Vérification images")
    
    if not images:
        return
    
    # Vérifier les dimensions et orientations
    dimensions = []
    orientations = []
    needs_normalization = False
    
    for img_path in images:
        try:
            # Vérifier avec PIL pour l'orientation
            pil_img = Image.open(img_path)
            pil_img_oriented = ImageOps.exif_transpose(pil_img)
            w, h = pil_img_oriented.size
            dimensions.append((w, h))
            
            # Vérifier si l'image est en portrait après correction EXIF
            if h > w:
                orientations.append("portrait")
                needs_normalization = True
            else:
                orientations.append("paysage")
                
        except Exception as e:
            log(f"⚠️ Impossible de vérifier {img_path}: {e}")
            continue
    
    if not dimensions:
        log("⚠️ Aucune image vérifiée")
        return
    
    # Vérifier la cohérence des dimensions
    unique_dims = set(dimensions)
    if len(unique_dims) > 1:
        log(f"⚠️ Images avec résolutions différentes: {unique_dims}")
        needs_normalization = True
    
    # Vérifier l'orientation
    unique_orientations = set(orientations)
    if len(unique_orientations) > 1 or "portrait" in orientations:
        log(f"⚠️ Images avec orientations différentes: {unique_orientations}")
        needs_normalization = True
    
    if needs_normalization:
        log("🔄 Normalisation des images avec fix_orientation...")
        try:
            # Construire le pattern pour toutes les images
            img_dir = os.path.dirname(images[0])
            img_ext = os.path.splitext(images[0])[1]
            pattern = os.path.join(img_dir, f"*{img_ext}")
            
            # Appeler fix_orientation
            script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "fix_orientation.py")
            result = subprocess.run([
                sys.executable, script_path, pattern
            ], capture_output=True, text=True, cwd=os.getcwd())
            
            if result.returncode == 0:
                log("✅ Images normalisées avec succès")
            else:
                log(f"❌ Erreur lors de la normalisation: {result.stderr}")
        except Exception as e:
            log(f"❌ Erreur lors de l'appel à fix_orientation: {e}")
    else:
        log("✅ Images déjà normalisées")
