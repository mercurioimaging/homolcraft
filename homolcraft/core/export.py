from __future__ import annotations
"""
homolcraft.core.export
----------------------
• Écriture MicMac « Pastis »
• Filtrage avancé :
      - score Lowe
      - popularité (occurrence inter-images)
      - échantillonnage spatial 4×4
"""

import os
from typing import List, Tuple, Dict, DefaultDict
from collections import defaultdict
from homolcraft.core import IMAGE_PROCESSING_INFO # Import du dictionnaire global depuis homolcraft.core

Point = Tuple[float, float, float, float, float]  # (x1, y1, x2, y2, score)
OccMap = Dict[Tuple[str, int, int], int]          # (img, x, y) -> count


# ---------------------------------------------------------------------------
# MicMac I/O ----------------------------------------------------------------
# ---------------------------------------------------------------------------

def export_micmac_homol(base_dir: str, 
                        path1_full: str, path2_full: str,
                        img1_name: str, img2_name: str,
                        points: List[Point]) -> None:
    """Écrit les deux fichiers Pastis (symétriques).
    
    path1_full, path2_full: Chemins complets vers les fichiers images originaux.
    img1_name, img2_name: Noms de base des images (ex: image.jpg).
    """
    d1 = os.path.join(base_dir, f"Pastis{img1_name}")
    d2 = os.path.join(base_dir, f"Pastis{img2_name}")
    os.makedirs(d1, exist_ok=True)
    os.makedirs(d2, exist_ok=True)

    # Récupérer les informations de traitement pour chaque image
    info1 = IMAGE_PROCESSING_INFO.get(path1_full)
    info2 = IMAGE_PROCESSING_INFO.get(path2_full)

    if not info1 or not info2:
        # Fallback ou erreur si les infos ne sont pas trouvées (ne devrait pas arriver)
        # Pour l'instant, on écrit sans scaling si info non trouvée, mais un warning serait bien
        print(f"Warning: Processing info not found for {path1_full} or {path2_full}. Points might not be scaled.")
        scale1, orig_shape1_wh = 1.0, None 
        scale2, orig_shape2_wh = 1.0, None
    else:
        scale1 = info1["scale_factor"]
        # original_shape est (h, w), on veut (w, h) pour la vérification des limites
        orig_shape1_wh = (info1["original_shape"][1], info1["original_shape"][0]) 
        
        scale2 = info2["scale_factor"]
        orig_shape2_wh = (info2["original_shape"][1], info2["original_shape"][0])

    _write_one(os.path.join(d1, f"{img2_name}.txt"), points, 
               scale1, orig_shape1_wh, 
               scale2, orig_shape2_wh)
    
    # Pour le fichier symétrique, les rôles de (scale1, shape1) et (scale2, shape2) sont inversés
    # car les points (x2,y2) deviennent (x1',y1') et (x1,y1) deviennent (x2',y2')
    sym_points = [(x2, y2, x1, y1, s) for x1, y1, x2, y2, s in points]
    _write_one(os.path.join(d2, f"{img1_name}.txt"), sym_points,
               scale2, orig_shape2_wh,  # scale pour les premiers points (originellement x2,y2)
               scale1, orig_shape1_wh)  # scale pour les seconds points (originellement x1,y1)


def _write_one(path: str, pts: List[Point], 
               sc1: float, shape1_wh: Tuple[int, int] | None,
               sc2: float, shape2_wh: Tuple[int, int] | None) -> None:
    with open(path, "w") as f:
        for x1_res, y1_res, x2_res, y2_res, score in pts:
            # Remise à l'échelle vers les coordonnées originales
            # Attention: si sc1 ou sc2 est 0 (ne devrait pas arriver si size > 0), cela causerait ZeroDivisionError
            # Cependant, scale_factor est size / max(h_orig, w_orig), donc positif si size > 0.
            # Si scale_factor est 1.0 (pas de redimensionnement ou info manquante), pas de changement.
            x1_orig = x1_res / sc1 if sc1 != 0 else x1_res
            y1_orig = y1_res / sc1 if sc1 != 0 else y1_res
            x2_orig = x2_res / sc2 if sc2 != 0 else x2_res
            y2_orig = y2_res / sc2 if sc2 != 0 else y2_res

            # Vérification des limites des points dans les images originales
            # 0 ≤ x < largeur et 0 ≤ y < hauteur
            # Initialiser la validité à False. Un point n'est valide que si les dimensions sont connues ET qu'il est dedans.
            valid_pt1 = False
            if shape1_wh: # shape1_wh is (width, height)
                if (0 <= x1_orig < shape1_wh[0] and 0 <= y1_orig < shape1_wh[1]):
                    valid_pt1 = True
            
            valid_pt2 = False
            if shape2_wh: # shape2_wh is (width, height)
                if (0 <= x2_orig < shape2_wh[0] and 0 <= y2_orig < shape2_wh[1]):
                    valid_pt2 = True
            
            if valid_pt1 and valid_pt2:
                f.write(f"{x1_orig:.6f} {y1_orig:.6f} {x2_orig:.6f} {y2_orig:.6f} {score:.6f}\n")


# ---------------------------------------------------------------------------
# Filtrage -------------------------------------------------------------------
# ---------------------------------------------------------------------------

def _spatial_sample(points: List[Point], max_pts: int,
                    grid: int = 4) -> List[Point]:
    """Répartit les points dans une grille *grid×grid* côté image A."""
    bins: DefaultDict[Tuple[int, int], List[Point]] = defaultdict(list)

    w = max(max(p[0], p[2]) for p in points)
    h = max(max(p[1], p[3]) for p in points)

    for p in points:
        col = int(p[0] / (w + 1e-6) * grid)
        row = int(p[1] / (h + 1e-6) * grid)
        bins[(col, row)].append(p)

    selected: List[Point] = []
    cells = [(c, r) if r % 2 == 0 else (grid - 1 - c, r)
             for r in range(grid) for c in range(grid)]

    while len(selected) < max_pts and bins:
        for cell in cells:
            if cell in bins and bins[cell]:
                selected.append(bins[cell].pop(0))
                if len(selected) >= max_pts:
                    break
            if cell in bins and not bins[cell]:
                del bins[cell]
        if not bins:
            break
    return selected


def _popularity_key(p: Point, img1: str, img2: str, occ: OccMap) -> float:
    """Combine le score Lowe et la popularité (>=1). Plus petit est meilleur."""
    x1, y1, x2, y2, score = p
    w1 = occ.get((img1, round(x1), round(y1)), 1)
    w2 = occ.get((img2, round(x2), round(y2)), 1)
    pop = max(w1, w2)              # popularité du point (max des deux vues)
    return score / pop             # score pondéré (plus petit = meilleur)


def filter_matches(points: List[Point], *,
                   max_pts: int = 750,
                   min_pts: int = 30,
                   occurrences: OccMap | None = None) -> List[Point]:
    """
    1. Trie par (score Lowe / popularité) si `occurrences` fourni,
       sinon par score Lowe.
    2. Découpe un petit buffer (×2) pour le sampling spatial.
    3. Échantillonnage spatial 4×4.
    4. Renvoie [] si < min_pts, sinon au plus max_pts points.
    """
    if len(points) < min_pts:
        return []

    if occurrences is None:
        points_sorted = sorted(points, key=lambda p: p[4])
    else:
        # On a besoin du nom de l'image A/B pour la popularité ; on les
        # passera plus tard via `functools.partial`.
        raise RuntimeError("filter_matches doit être partiellement appliquée "
                           "avec les noms d'image quand occurrences est fourni.")

    pts_buf = points_sorted[: max_pts * 2]          # buffer
    pts_final = _spatial_sample(pts_buf, max_pts)

    return pts_final if len(pts_final) >= min_pts else []
