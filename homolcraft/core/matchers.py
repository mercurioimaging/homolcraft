from __future__ import annotations
"""
homolcraft.core.matchers
------------------------
Fonctions de mise en correspondance et factory get_matcher().
"""

from pathlib import Path
from typing import List, Tuple, Dict

import cv2

Point = Tuple[float, float, float, float, float]  # (x1, y1, x2, y2, score)


# ---------------------------------------------------------------------------
# Bas niveau — déjà présent --------------------------------------------------
# ---------------------------------------------------------------------------

def match_sift(desc1, desc2, ratio: float = 0.75):
    bf = cv2.BFMatcher()
    matches = bf.knnMatch(desc1, desc2, k=2)
    good = [m for m, n in matches if m.distance < ratio * n.distance]
    return good


# ---------------------------------------------------------------------------
# Factory pour le pipeline ---------------------------------------------------
# ---------------------------------------------------------------------------

def get_matcher(*, name: str = "flann", nb_points: int = 750):
    """
    Retourne une fonction
        matcher(pathA, pathB, featA, featB) -> List[Point]
    compatible pipeline.
    """
    name = name.lower()

    if name in {"flann", "sift"}:
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

            good = match_sift(dA, dB)
            pts: List[Point] = []
            for m in good:
                idx1 = m.queryIdx
                idx2 = m.trainIdx
                x1, y1 = kA[idx1].pt
                x2, y2 = kB[idx2].pt
                pts.append((x1, y1, x2, y2, float(m.distance)))

            # tri croissant (meilleure distance d'abord) + limite nb_points
            pts.sort(key=lambda p: p[4])
            return pts[:nb_points]

        return _matcher

    raise ValueError(f"Matcher inconnu : {name!r}")
