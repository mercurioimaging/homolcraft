from __future__ import annotations
"""
homolcraft.core.matchers
------------------------
Mise en correspondance SIFT + RANSAC.
"""

from pathlib import Path
from typing import List, Tuple
import sys, time
import threading

import cv2
import numpy as np

Point = Tuple[float, float, float, float, float]  # (x1, y1, x2, y2, score)

try:
    from vismatch import available_models as _VISMATCH_MODELS
except ImportError:
    _VISMATCH_MODELS = []

_VISMATCH_ALIASES = {"xfeat": "xfeat-star"}
_VISMATCH_CACHE: dict[str, object] = {}
_VISMATCH_LOCK = threading.Lock()
_VISMATCH_INFER_LOCK = threading.Lock()

# Cache global pour LoFTR (kornia)
_LOFTR_CACHE = None
_LOFTR_LOCK = threading.Lock()


def is_vismatch_model(name: str) -> bool:
    model = _VISMATCH_ALIASES.get(name.lower(), name.lower())
    return model in _VISMATCH_MODELS


def vismatch_model_name(name: str) -> str:
    return _VISMATCH_ALIASES.get(name.lower(), name.lower())


def _pad_to_multiple(img: np.ndarray, multiple: int = 8) -> np.ndarray:
    """Pad image (right/bottom) so dimensions are multiples of `multiple`."""
    h, w = img.shape[:2]
    pad_h = (multiple - h % multiple) % multiple
    pad_w = (multiple - w % multiple) % multiple
    if pad_h > 0 or pad_w > 0:
        img = np.pad(img, ((0, pad_h), (0, pad_w)), mode="reflect")
    return img


def _log(msg: str) -> None:
    """Print avec flush immédiat (utile en multithread / piping)."""
    print(msg, flush=True)


# ---------------------------------------------------------------------------
# Lowe ratio + SIFT ----------------------------------------------------------
# ---------------------------------------------------------------------------

def _match_sift(desc1, desc2, ratio: float = 0.75):
    bf = cv2.BFMatcher()
    matches = bf.knnMatch(desc1, desc2, k=2)
    return [m for m, n in matches if m.distance < ratio * n.distance]


def _match_flann(desc1, desc2, ratio: float = 0.75):
    FLANN_INDEX_KDTREE = 1
    flann = cv2.FlannBasedMatcher(
        {"algorithm": FLANN_INDEX_KDTREE, "trees": 5},
        {"checks": 50},
    )
    matches = flann.knnMatch(desc1.astype(np.float32), desc2.astype(np.float32), k=2)
    return [m for m, n in matches if m.distance < ratio * n.distance]


def _scale_of(path) -> float:
    """Facteur d'échelle (image réduite / pleine résolution) d'une image."""
    from . import IMAGE_PROCESSING_INFO
    info = IMAGE_PROCESSING_INFO.get(str(path)) or {}
    sc = info.get("scale_factor", 1.0)
    return sc if sc else 1.0


def _fixed_mask(ptsA, ptsB, sc_a: float, sc_b: float, min_disp: float):
    """True pour les matchs à garder : déplacement (px pleine résolution) >= min_disp."""
    a = np.asarray(ptsA, dtype=np.float64) / sc_a
    b = np.asarray(ptsB, dtype=np.float64) / sc_b
    return np.hypot(*(a - b).T) >= min_disp


def _dedup_matches(good):
    """Garde le meilleur match (distance min) par point image A et par point image B."""
    best_q, best_t = {}, {}
    for i, m in enumerate(good):
        if m.queryIdx not in best_q or m.distance < good[best_q[m.queryIdx]].distance:
            best_q[m.queryIdx] = i
        if m.trainIdx not in best_t or m.distance < good[best_t[m.trainIdx]].distance:
            best_t[m.trainIdx] = i
    keep = set(best_q.values()) & set(best_t.values())
    return [m for i, m in enumerate(good) if i in keep]


# ---------------------------------------------------------------------------
# Factory pour le pipeline ---------------------------------------------------
# ---------------------------------------------------------------------------

def get_matcher(*, name: str = "flann", nb_points: int = 750,
                use_ransac: bool = True, ransac_thresh: float = 4.0,
                resize_max_a: int = 800, resize_max_b: int | None = None,
                device: str | None = None,
                xfeat_max_kpts: int = 8192,
                xfeat_ransac_thresh: float = 5.0,
                min_disp: float = 0.0, dedup: bool = False,
                lowe_ratio: float = 0.75, ransac_model: str = "homography",
                stats: dict | None = None):
    """
    Retourne une fonction :
        matcher(pathA, pathB, featA, featB) -> List[Point]
    qui inclut (optionnellement) un filtrage RANSAC.

    min_disp : rejette les matchs dont les deux positions sont à moins de
        min_disp px (pleine résolution) — points fixes (fond, table). Appliqué
        AVANT RANSAC et AVANT le plafonnement nb_points.
    dedup : un point image n'est utilisé qu'une fois par paire (meilleur match).
    stats : dict rempli {(pathA, pathB): {"fixed": n, "dup": n}}.

    resize_max_a / resize_max_b : taille max (en px) pour les deux images
        en entrée de LoFTR. Si resize_max_b est None, on utilise resize_max_a
        pour les deux.
    """
    import torch as _torch
    name = name.lower()
    if name not in {"flann", "sift", "loftr"} and not is_vismatch_model(name):
        raise ValueError(f"Matcher inconnu : {name!r}")
    if resize_max_b is None:
        resize_max_b = resize_max_a
    if device is None:
        device = "mps" if _torch.backends.mps.is_available() else "cpu"

    def _rec(path_a, path_b, key, n):
        if stats is not None and n:
            d = stats.setdefault((str(path_a), str(path_b)), {"fixed": 0, "dup": 0})
            d[key] += n

    def _matcher(
        path_a: Path | str,
        path_b: Path | str,
        feat_a,
        feat_b,
    ) -> List[Point]:
        if is_vismatch_model(name):
            from .io import read_image as _read_image

            model_name = vismatch_model_name(name)
            tag = f"[{model_name}] {Path(path_a).name} ↔ {Path(path_b).name}"
            t0 = time.time()

            try:
                img1_bgr, _, _ = _read_image(str(path_a), size=resize_max_a, clahe=False)
                img2_bgr, _, _ = _read_image(str(path_b), size=resize_max_b, clahe=False)
            except Exception as e:
                _log(f"{tag}: lecture image échouée: {e}")
                return []

            h1, w1 = img1_bgr.shape[:2]
            h2, w2 = img2_bgr.shape[:2]
            t_read = time.time() - t0
            _log(f"{tag}: matching ({w1}×{h1} / {w2}×{h2})…")

            cache_key = f"{model_name}:{device}:{xfeat_max_kpts}:{xfeat_ransac_thresh}"
            if cache_key not in _VISMATCH_CACHE:
                with _VISMATCH_LOCK:
                    if cache_key not in _VISMATCH_CACHE:
                        _log(f"[vismatch] Chargement du modèle {model_name}…")
                        from vismatch import get_matcher as _vm_get_matcher
                        _VISMATCH_CACHE[cache_key] = _vm_get_matcher(
                            model_name,
                            device=device,
                            max_num_keypoints=xfeat_max_kpts,
                            ransac_reproj_thresh=xfeat_ransac_thresh,
                        )
            vm = _VISMATCH_CACHE[cache_key]

            try:
                def _bgr_to_tensor(bgr):
                    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
                    return _torch.from_numpy(rgb).permute(2, 0, 1)

                t_match = time.time()
                with _VISMATCH_INFER_LOCK:
                    result = vm(_bgr_to_tensor(img1_bgr), _bgr_to_tensor(img2_bgr))
                dt_match = time.time() - t_match

                kp0 = result["inlier_kpts0"]
                kp1 = result["inlier_kpts1"]
                mkpts0 = kp0.cpu().numpy() if hasattr(kp0, "cpu") else np.asarray(kp0)
                mkpts1 = kp1.cpu().numpy() if hasattr(kp1, "cpu") else np.asarray(kp1)
                n_in = len(mkpts0)

                if min_disp > 0 and n_in:
                    keep = _fixed_mask(mkpts0, mkpts1, _scale_of(path_a), _scale_of(path_b), min_disp)
                    _rec(path_a, path_b, "fixed", int((~keep).sum()))
                    mkpts0, mkpts1 = mkpts0[keep], mkpts1[keep]
                    n_in = len(mkpts0)

                if n_in < 8:
                    _log(f"{tag}: {n_in} inliers (< 8, skip)")
                    return []

                dt_total = time.time() - t0
                _log(
                    f"{tag}: {result['num_inliers']} inliers "
                    f"[lecture {t_read:.1f}s · match {dt_match:.1f}s · total {dt_total:.1f}s]"
                )

                pts: List[Point] = [
                    (float(x1), float(y1), float(x2), float(y2), 0.0)
                    for (x1, y1), (x2, y2) in zip(mkpts0, mkpts1)
                ]
                return pts[:nb_points]

            except Exception as e:
                _log(f"{tag}: erreur {type(e).__name__}: {e}")
                return []

        elif name == "loftr":
            # LoFTR : matching direct entre images
            from .detectors import LoFTRDetector
            from .io import read_image

            tag = f"[LoFTR] {Path(path_a).name} ↔ {Path(path_b).name}"
            t0 = time.time()

            try:
                img1_bgr, _, _ = read_image(str(path_a), size=resize_max_a, clahe=False)
                img2_bgr, _, _ = read_image(str(path_b), size=resize_max_b, clahe=False)
            except Exception as e:
                _log(f"{tag}: lecture image échouée: {e}")
                return []

            img1_resized = cv2.cvtColor(img1_bgr, cv2.COLOR_BGR2GRAY)
            img2_resized = cv2.cvtColor(img2_bgr, cv2.COLOR_BGR2GRAY)
            # LoFTR requiert des dimensions multiples de 8
            img1_resized = _pad_to_multiple(img1_resized, 8)
            img2_resized = _pad_to_multiple(img2_resized, 8)
            t_read = time.time() - t0

            global _LOFTR_CACHE
            if _LOFTR_CACHE is None:
                with _LOFTR_LOCK:
                    if _LOFTR_CACHE is None:
                        _log("[LoFTR] Chargement du modèle (première fois)…")
                        t_model = time.time()
                        _LOFTR_CACHE = LoFTRDetector()
                        _log(f"[LoFTR] Modèle chargé en {time.time() - t_model:.1f}s")

            h1, w1 = img1_resized.shape[:2]
            h2, w2 = img2_resized.shape[:2]
            _log(f"{tag}: matching ({w1}×{h1} / {w2}×{h2})…")

            try:
                t_match = time.time()
                mkpts0, mkpts1 = _LOFTR_CACHE.match_images(img1_resized, img2_resized)
                dt_match = time.time() - t_match
                n_raw = len(mkpts0)

                if n_raw == 0:
                    _log(f"{tag}: 0 point brut ({dt_match:.1f}s)")
                    return []

                mkpts0 = np.asarray(mkpts0, dtype=np.float32)
                mkpts1 = np.asarray(mkpts1, dtype=np.float32)

                valid = (
                    (mkpts0[:, 0] >= 0) & (mkpts0[:, 1] >= 0) &
                    (mkpts1[:, 0] >= 0) & (mkpts1[:, 1] >= 0) &
                    (mkpts0[:, 0] < 10000) & (mkpts0[:, 1] < 10000) &
                    (mkpts1[:, 0] < 10000) & (mkpts1[:, 1] < 10000)
                )
                mkpts0, mkpts1 = mkpts0[valid], mkpts1[valid]
                if min_disp > 0 and len(mkpts0):
                    keep = _fixed_mask(mkpts0, mkpts1, _scale_of(path_a), _scale_of(path_b), min_disp)
                    _rec(path_a, path_b, "fixed", int((~keep).sum()))
                    mkpts0, mkpts1 = mkpts0[keep], mkpts1[keep]
                n_valid = len(mkpts0)

                if n_valid < 8:
                    _log(f"{tag}: {n_raw} brut → {n_valid} valides (< 8, skip)")
                    return []

                if use_ransac:
                    t_rsc = time.time()
                    F, mask = cv2.findFundamentalMat(
                        mkpts0, mkpts1, cv2.USAC_MAGSAC,
                        ransac_thresh, 0.999, 100000,
                    )
                    dt_rsc = time.time() - t_rsc
                    if F is None or mask is None:
                        _log(f"{tag}: RANSAC échec ({dt_rsc:.2f}s)")
                        return []
                    inliers = mask.ravel().astype(bool)
                    n_in = int(inliers.sum())
                    mkpts0, mkpts1 = mkpts0[inliers], mkpts1[inliers]
                    if n_in < 8:
                        _log(f"{tag}: {n_valid} → {n_in} inliers (< 8, skip)")
                        return []
                    n_out = n_valid - n_in
                    pct = 100.0 * n_in / n_valid
                    dt_total = time.time() - t0
                    _log(
                        f"{tag}: {n_raw} brut → {n_in} inliers "
                        f"({n_out} outliers rejetés, {pct:.0f}% gardés) "
                        f"[lecture {t_read:.1f}s · LoFTR {dt_match:.1f}s · RANSAC {dt_rsc:.2f}s · total {dt_total:.1f}s]"
                    )
                else:
                    dt_total = time.time() - t0
                    _log(f"{tag}: {n_raw} brut → {n_valid} valides "
                         f"[lecture {t_read:.1f}s · LoFTR {dt_match:.1f}s · total {dt_total:.1f}s]")

                pts: List[Point] = [
                    (float(x1), float(y1), float(x2), float(y2), 0.0)
                    for (x1, y1), (x2, y2) in zip(mkpts0, mkpts1)
                ]
                return pts[:nb_points]

            except Exception as e:
                _log(f"{tag}: erreur {type(e).__name__}: {e}")
                return []
        
        else:
            # Matchers classiques (FLANN/SIFT)
            kA, dA = feat_a
            kB, dB = feat_b
            if dA is None or dB is None or len(dA) == 0 or len(dB) == 0:
                return []

            # 1) Lowe ratio-test
            good = (_match_flann(dA, dB, lowe_ratio) if name == "flann"
                    else _match_sift(dA, dB, lowe_ratio))
            # 1b) Points fixes (même position image) et doublons : AVANT RANSAC,
            #     sinon un fond immobile (H = identité) capte le consensus.
            if min_disp > 0 and good:
                pa = np.float32([kA[m.queryIdx].pt for m in good])
                pb = np.float32([kB[m.trainIdx].pt for m in good])
                keep = _fixed_mask(pa, pb, _scale_of(path_a), _scale_of(path_b), min_disp)
                _rec(path_a, path_b, "fixed", int((~keep).sum()))
                good = [m for m, k in zip(good, keep) if k]
            if dedup and good:
                n0 = len(good)
                good = _dedup_matches(good)
                _rec(path_a, path_b, "dup", n0 - len(good))

            if len(good) < 8:                       # homographie < 4, essentielle < 5
                return []

            # 2) Homographie RANSAC pour éliminer les outliers
            if use_ransac and len(good) >= 8:
                ptsA = np.float32([kA[m.queryIdx].pt for m in good])
                ptsB = np.float32([kB[m.trainIdx].pt for m in good])
                if ransac_model == "fundamental":
                    H, mask = cv2.findFundamentalMat(ptsA, ptsB, cv2.FM_RANSAC, ransac_thresh, 0.999)
                else:
                    H, mask = cv2.findHomography(ptsA, ptsB, cv2.RANSAC, ransac_thresh)
                if H is None or mask is None:
                    return []
                inliers = mask.ravel() == 1
                good = [m for m, keep in zip(good, inliers) if keep]

            if len(good) < 4:                      # gardons au moins 4 inliers
                return []

            # 3) Conversion en liste Point + tri sur la distance (qualité)
            pts: List[Point] = []
            for m in good:
                x1, y1 = kA[m.queryIdx].pt
                x2, y2 = kB[m.trainIdx].pt
                
                # Validation des coordonnées : éviter les valeurs négatives ou trop grandes
                if (x1 >= 0 and y1 >= 0 and x2 >= 0 and y2 >= 0 and 
                    x1 < 10000 and y1 < 10000 and x2 < 10000 and y2 < 10000):
                    pts.append((x1, y1, x2, y2, float(m.distance)))

            pts.sort(key=lambda p: p[4])           # score ascendant
            return pts[:nb_points]

    return _matcher
