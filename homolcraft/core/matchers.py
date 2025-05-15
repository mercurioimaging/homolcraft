from __future__ import annotations
"""
homolcraft.core.matchers
------------------------
Mise en correspondance SIFT + RANSAC.
"""

from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

Point = Tuple[float, float, float, float, float]  # (x1, y1, x2, y2, score)


# ---------------------------------------------------------------------------
# Lowe ratio + SIFT ----------------------------------------------------------
# ---------------------------------------------------------------------------

def _match_sift(desc1, desc2, ratio: float = 0.75):
    bf = cv2.BFMatcher()
    matches = bf.knnMatch(desc1, desc2, k=2)
    return [m for m, n in matches if m.distance < ratio * n.distance]


# ---------------------------------------------------------------------------
# Factory pour le pipeline ---------------------------------------------------
# ---------------------------------------------------------------------------

def get_matcher(*, name: str = "flann", nb_points: int = 750,
                use_ransac: bool = True, ransac_thresh: float = 4.0):
    """
    Retourne une fonction :
        matcher(pathA, pathB, featA, featB) -> List[Point]
    qui inclut (optionnellement) un filtrage RANSAC.
    """
    name = name.lower()
    if name not in {"flann", "sift"}:
        raise ValueError(f"Matcher inconnu : {name!r}")

    def _matcher(
        path_a: Path | str,
        path_b: Path | str,
        feat_a,
        feat_b,
    ) -> List[Point]:
        kA, dA = feat_a
        kB, dB = feat_b
        if dA is None or dB is None or len(dA) == 0 or len(dB) == 0:
            return []

        # 1) Lowe ratio-test
        good = _match_sift(dA, dB)
        if len(good) < 8:                       # homographie < 4, essentielle < 5
            return []

        # 2) Homographie RANSAC pour éliminer les outliers
        if use_ransac and len(good) >= 8:
            ptsA = np.float32([kA[m.queryIdx].pt for m in good])
            ptsB = np.float32([kB[m.trainIdx].pt for m in good])
            H, mask = cv2.findHomography(ptsA, ptsB, cv2.RANSAC, ransac_thresh)
            if H is None:
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
            pts.append((x1, y1, x2, y2, float(m.distance)))

        pts.sort(key=lambda p: p[4])           # score ascendant
        return pts[:nb_points]

    return _matcher
