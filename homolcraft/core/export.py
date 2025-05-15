from __future__ import annotations
"""
homolcraft.core.export
----------------------
Fonctions d'écriture et de filtrage pour les fichiers Homol MicMac.
"""

import os
from typing import List, Tuple

Point = Tuple[float, float, float, float, float]  # (x1, y1, x2, y2, score)


# ---------------------------------------------------------------------------
# Écriture MicMac « Pastis » -------------------------------------------------
# ---------------------------------------------------------------------------

def export_micmac_homol(base_dir: str, img1: str, img2: str, points: List[Point]):
    """Écrit les deux fichiers .txt nécessaires à MicMac."""
    # Fichier A→B
    d1 = os.path.join(base_dir, f"Pastis{img1}")
    os.makedirs(d1, exist_ok=True)
    _write_one(os.path.join(d1, f"{img2}.txt"), points)

    # Fichier symétrique B→A
    d2 = os.path.join(base_dir, f"Pastis{img2}")
    os.makedirs(d2, exist_ok=True)
    sym = [(x2, y2, x1, y1, s) for x1, y1, x2, y2, s in points]
    _write_one(os.path.join(d2, f"{img1}.txt"), sym)


def _write_one(path: str, points: List[Point]):
    with open(path, "w") as f:
        for x1, y1, x2, y2, s in points:
            f.write(f"{x1:.6f} {y1:.6f} {x2:.6f} {y2:.6f} {s:.6f}\n")


# ---------------------------------------------------------------------------
# Filtrage avant export ------------------------------------------------------
# ---------------------------------------------------------------------------

def filter_matches(
    points: List[Point],
    *,
    max_pts: int = 750,
    min_pts: int = 30,
) -> List[Point]:
    """
    • trie les points par score croissant  
    • en garde au plus *max_pts*  
    • renvoie [] si moins de *min_pts* points
    """
    if len(points) < min_pts:
        return []

    pts_sorted = sorted(points, key=lambda p: p[4])
    return pts_sorted[:max_pts]
