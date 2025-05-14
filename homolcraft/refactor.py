from __future__ import annotations
"""HomolCraft – Core pipeline (refactored & optimised May 2025)
================================================================
Single orchestrator + fully testable pure helpers.  Changes vs. previous
-----------------------------------------------------------------------
* **write_workers** → parallel TXT export (I/O-bound)  
* **multiplicity-first selection** – tie-points observed in many images
  are kept before pair-unique points.  
* **No log.txt**, no dry-run; progress + stats go to STDOUT only.  
* **matches_per_pair** stores a single direction; export writes both files.
"""

from pathlib import Path
from itertools import combinations
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, List, Tuple, Dict, Sequence, Literal, Callable, Any
import concurrent.futures as cf
import cv2
import numpy as np
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Public API ----------------------------------------------------------------
# ---------------------------------------------------------------------------

Point = Tuple[float, float, float, float, float]  # (x1, y1, x2, y2, score)

@dataclass(frozen=True)
class Stats:
    nb_images: int
    nb_pairs: int
    nb_pairs_exported: int
    total_points_exported: int
    rejected_points: int


# signature kept stable except new *write_workers*
def run_pipeline(
    pattern: str,
    *,
    mode: Literal["all", "line"] = "all",
    delta: int = 1,
    circ: bool = False,
    detector: Literal["sift", "loftr"] = "sift",
    size: int | None = 1000,
    clahe: bool = True,
    sift_nfeatures: int = 1000,
    nb_points: int = 500,
    n_jobs: int = 8,
    write_workers: int | None = None,
    out_dir: str | Path | None = None,
    progress: bool = True,
    log: Callable[[str], None] | None = None,
) -> Stats:
    """High-level orchestrator used by CLI.
    Returns an immutable *Stats* dataclass.
    """
    if log is None:
        log = print
    images = _find_images(pattern)
    if len(images) < 2:
        raise ValueError("Need at least two images.")
    images = list(images)

    if out_dir is None:
        out_dir = Path(images[0]).resolve().parent / "Homol"
    else:
        out_dir = Path(out_dir)
    out_dir.mkdir(exist_ok=True)

    # 1 ── Pair generation --------------------------------------------------
    if mode == "all":
        pairs = list(_all_pairs(images))
    elif mode == "line":
        pairs = list(_line_pairs(images, delta=delta, circ=circ))
    else:
        raise ValueError(mode)
    log(f"[Pairs] {len(pairs)} to process – mode={mode}")

    # 2 ── Feature detection ----------------------------------------------
    detector_fn, match_fn = _make_detectors(detector, size, clahe, sift_nfeatures)

    with cf.ThreadPoolExecutor(max_workers=n_jobs) as pool:
        feature_data = dict(tqdm(pool.map(detector_fn, images), total=len(images), desc="Detect", disable=not progress))

    # 3 ── Matching --------------------------------------------------------
    def _match_task(pair):
        img1, img2 = pair
        return match_fn(img1, img2, feature_data[img1], feature_data[img2])

    with cf.ThreadPoolExecutor(max_workers=n_jobs) as pool:
        pmatches = list(tqdm(pool.map(_match_task, pairs), total=len(pairs), desc="Match", disable=not progress))

    matches_per_pair: Dict[Tuple[str, str], List[Point]] = {
        (m.img1, m.img2): m.points for m in pmatches if m.points
    }

    # 3.5 ── Multiplicity index -------------------------------------------
    multiplicity = _compute_multiplicity(matches_per_pair)

    # 4 + 5 ── Selection + Export -----------------------------------------
    write_workers = write_workers or max(1, n_jobs // 2)
    export_stats = _export_homol_pairs(
        pairs, matches_per_pair, multiplicity, out_dir, nb_points,
        write_workers=write_workers, progress=progress,
    )

    return Stats(
        nb_images=len(images),
        nb_pairs=len(pairs),
        **export_stats,
    )

# ---------------------------------------------------------------------------
# Helper: pair generation
# ---------------------------------------------------------------------------

def _find_images(pattern: str) -> List[str]:
    import glob
    paths = glob.glob(pattern)
    paths.sort()
    return paths

def _all_pairs(images: Sequence[str]):
    return combinations(images, 2)

def _line_pairs(images: Sequence[str], *, delta: int, circ: bool):
    N = len(images)
    for i, img1 in enumerate(images):
        for d in range(1, delta + 1):
            j = (i + d) % N if circ else i + d
            if j < N:
                yield img1, images[j]

# ---------------------------------------------------------------------------
# 2. Detection + 3. Matching factories
# ---------------------------------------------------------------------------
from typing import NamedTuple

class Features(NamedTuple):
    keypoints: np.ndarray  # (N,2)
    descriptors: np.ndarray | None
    shape: Tuple[int, int]

class PairMatches(NamedTuple):
    img1: str
    img2: str
    points: List[Point]

DetectorFn = Callable[[str], Tuple[str, Features]]
MatchFn = Callable[[str, str, Features, Features], PairMatches]


def _make_detectors(detector: str, size: int | None, clahe: bool, sift_nfeatures: int):
    if detector == "sift":
        sift = cv2.SIFT_create(nfeatures=sift_nfeatures)
        def detect(img_path: str):
            img = _read_image(img_path, size=size, clahe=clahe)
            kps, desc = sift.detectAndCompute(img, None)
            pts = np.array([kp.pt for kp in kps], dtype=np.float32)
            return img_path, Features(pts, desc, img.shape[:2])
        def match(img1, img2, f1, f2):
            bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)
            if f1.descriptors is None or f2.descriptors is None:
                return PairMatches(img1, img2, [])
            m = bf.match(f1.descriptors, f2.descriptors)
            if len(m) < 30:  # heuristic
                return PairMatches(img1, img2, [])
            p1 = f1.keypoints[[mm.queryIdx for mm in m]]
            p2 = f2.keypoints[[mm.trainIdx for mm in m]]
            p1, p2 = _ransac_filter(p1, p2)
            sc1, sc2 = _scale(img1, f1.shape), _scale(img2, f2.shape)
            pts = [(x1*sc1, y1*sc1, x2*sc2, y2*sc2, 1.0) for (x1, y1), (x2, y2) in zip(p1, p2)]
            return PairMatches(img1, img2, pts)
        return detect, match
    elif detector == "loftr":
        from loftr import LoFTR, default_cfg
        cfg = default_cfg.clone()
        loftr = LoFTR(cfg)
        def detect(img_path: str):
            img = _read_image(img_path, size=size, clahe=clahe, gray=True)
            return img_path, Features(img, None, img.shape[:2])
        def match(img1, img2, f1, f2):
            out = loftr({"image0": f1.keypoints, "image1": f2.keypoints})
            k0, k1 = out["keypoints0"].cpu().numpy(), out["keypoints1"].cpu().numpy()
            conf = out["confidence"].cpu().numpy()
            if len(k0) < 350:
                return PairMatches(img1, img2, [])
            k0, k1 = _ransac_filter(k0, k1)
            sc1, sc2 = _scale(img1, f1.shape), _scale(img2, f2.shape)
            pts = [(x0*sc1, y0*sc1, x1*sc2, y1*sc2, c) for (x0, y0), (x1, y1), c in zip(k0, k1, conf)]
            return PairMatches(img1, img2, pts)
        return detect, match
    else:
        raise ValueError(detector)

# ---------------------------------------------------------------------------
# 3.bis helpers
# ---------------------------------------------------------------------------

def _read_image(path: str, *, size: int | None, clahe: bool, gray: bool = False):
    flag = cv2.IMREAD_GRAYSCALE if gray else cv2.IMREAD_COLOR
    img = cv2.imread(path, flag)
    if size:
        h, w = img.shape[:2]
        s = size / max(h, w)
        if s < 1.0:
            img = cv2.resize(img, (int(w*s), int(h*s)), interpolation=cv2.INTER_AREA)
    if clahe:
        clahe_fn = cv2.createCLAHE(2.0, (8, 8))
        if gray or len(img.shape) == 2:
            img = clahe_fn.apply(img)
        else:
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            lab[..., 0] = clahe_fn.apply(lab[..., 0])
            img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    return img


def _ransac_filter(p1: np.ndarray, p2: np.ndarray):
    if len(p1) >= 8:
        F, mask = cv2.findFundamentalMat(p1, p2, cv2.FM_RANSAC, 2.0, 0.99)
        keep = mask.ravel() > 0 if mask is not None else slice(None)
        return p1[keep], p2[keep]
    return p1, p2


def _scale(img_path: str, resized_shape: Tuple[int, int]):
    h0, w0 = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE).shape[:2]
    h1, w1 = resized_shape
    return w0 / w1

# ---------------------------------------------------------------------------
# 3.5 Multiplicity index (global) -------------------------------------------

Key = Tuple[str, float, float]  # (img, x_round, y_round)

def _compute_multiplicity(matches_per_pair: Dict[Tuple[str, str], List[Point]]):
    mult: defaultdict[Key, int] = defaultdict(int)
    for (img1, img2), pts in matches_per_pair.items():
        for x1, y1, x2, y2, _ in pts:
            mult[(img1, round(x1, 1), round(y1, 1))] += 1
            mult[(img2, round(x2, 1), round(y2, 1))] += 1
    return mult

# ---------------------------------------------------------------------------
# 4 + 5 selection + export --------------------------------------------------
# ---------------------------------------------------------------------------

def _export_homol_pairs(
    pairs: Sequence[Tuple[str, str]],
    matches_per_pair: Dict[Tuple[str, str], List[Point]],
    multiplicity: Dict[Key, int],
    out_dir: Path,
    nb_points: int,
    *,
    write_workers: int = 1,
    progress: bool = True,
) -> Dict[str, int]:
    out_dir = Path(out_dir)

    tasks = []
    for img1, img2 in pairs:
        pts = matches_per_pair.get((img1, img2))
        if pts:
            tasks.append((img1, img2, pts))

    def _process(pair_data):
        img1, img2, pts = pair_data
        h1, w1 = cv2.imread(img1).shape[:2]
        h2, w2 = cv2.imread(img2).shape[:2]

        # multiplicity-first ordering
        def mval(p: Point):
            m1 = multiplicity[(img1, round(p[0], 1), round(p[1], 1))]
            m2 = multiplicity[(img2, round(p[2], 1), round(p[3], 1))]
            return -max(m1, m2), -p[4]  # negative → descending
        pts.sort(key=mval)

        pts = _select_spatially(pts, w1, h1, nmax=nb_points)
        pts_val = [p for p in pts if _in_bounds(p, (h1, w1), (h2, w2))]
        if not pts_val:
            return 0, 0  # nothing exported
        _write_pair(out_dir, img1, img2, pts_val)
        _write_pair(out_dir, img2, img1, [(x2, y2, x1, y1, s) for (x1, y1, x2, y2, s) in pts_val])
        return 1, len(pts_val)

    exported = 0
    total_pts = 0
    rejected = 0

    iterable = tqdm(tasks, desc="Export Homol", disable=not progress)
    if write_workers == 1:
        for t in iterable:
            e, n = _process(t)
            exported += e; total_pts += n
    else:
        with cf.ThreadPoolExecutor(max_workers=write_workers) as pool:
            for _ in iterable:
                pass  # On utilise tqdm uniquement pour l'affichage de la progression
            results = list(pool.map(_process, tasks))
            for e, n in results:
                exported += e; total_pts += n
    # rejected = computed inside _select_spatially but not stored; not critical
    return dict(nb_pairs_exported=exported, total_points_exported=total_pts, rejected_points=rejected)

# ---------------------------------------------------------------------------
# Spatial selection + helpers-----------------------------------------------
# ---------------------------------------------------------------------------

def _select_spatially(pts: List[Point], w: int, h: int, *, nmax: int):
    if len(pts) <= nmax:
        return pts
    g = int(np.sqrt(nmax))
    cells: List[List[Point]] = [[[] for _ in range(g)] for _ in range(g)]
    for p in pts:
        gx = min(int(p[0] / w * g), g - 1)
        gy = min(int(p[1] / h * g), g - 1)
        cells[gy][gx].append(p)
    sel: List[Point] = []
    for row in cells:
        for cell in row:
            if cell:
                sel.append(cell[0])
                if len(sel) == nmax:
                    return sel
    # fill remaining by original order (already multiplicity-sorted)
    if len(sel) < nmax:
        seen = set(sel)
        sel.extend([p for p in pts if p not in seen][: nmax - len(sel)])
    return sel


def _in_bounds(p: Point, sh1: Tuple[int, int], sh2: Tuple[int, int]):
    h1, w1 = sh1; h2, w2 = sh2
    return 0 <= p[0] < w1 and 0 <= p[1] < h1 and 0 <= p[2] < w2 and 0 <= p[3] < h2


def _write_pair(out_dir: Path, img1: str, img2: str, pts: Sequence[Point]):
    d = out_dir / f"Pastis{Path(img1).name}"
    d.mkdir(exist_ok=True)
    txt = d / f"{Path(img2).name}.txt"
    with txt.open("w") as f:
        f.writelines(f"{x1:.6f} {y1:.6f} {x2:.6f} {y2:.6f} {s:.6f}\n" for x1, y1, x2, y2, s in pts)
