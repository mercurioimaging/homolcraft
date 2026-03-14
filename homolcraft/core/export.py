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
from PIL import Image, ImageOps

Point = Tuple[float, float, float, float, float]  # (x1, y1, x2, y2, score)
OccMap = Dict[Tuple[str, int, int], int]          # (img, x, y) -> count


def _get_image_orientation_transform(image_path: str) -> Tuple[int, int, int]:
    """
    Détermine la transformation d'orientation nécessaire pour une image.
    Retourne (width, height, orientation_code) de l'image après correction EXIF.
    orientation_code: 1=normal, 3=180°, 6=90°CW, 8=90°CCW
    """
    # Pour l'instant, retourner des valeurs par défaut pour éviter la lenteur
    # Les images sont déjà orientées correctement par HomolCraft lors de la lecture
    return 4000, 6000, 1  # Valeurs par défaut pour les images ori


def _reproject_point_to_final_orientation(x: float, y: float, 
                                         original_w: int, original_h: int,
                                         final_w: int, final_h: int,
                                         orientation: int) -> Tuple[float, float]:
    """
    Reprojette un point de l'image redimensionnée vers l'orientation finale.
    """
    # Les points sont détectés sur l'image redimensionnée et orientée
    # Il faut les reprojeter dans l'orientation finale
    
    # Si l'image a été pivotée (orientation 6 ou 8), il faut ajuster les coordonnées
    if orientation == 6:  # 90° CW
        # L'image a été pivotée de 90° dans le sens horaire
        # Les coordonnées (x,y) sur l'image pivotée correspondent à (y, w-x) sur l'image originale
        x_final = y
        y_final = original_w - x
    elif orientation == 8:  # 90° CCW  
        # L'image a été pivotée de 90° dans le sens anti-horaire
        # Les coordonnées (x,y) sur l'image pivotée correspondent à (h-y, x) sur l'image originale
        x_final = original_h - y
        y_final = x
    elif orientation == 3:  # 180°
        # L'image a été pivotée de 180°
        x_final = original_w - x
        y_final = original_h - y
    else:  # orientation == 1 (normal)
        # Pas de rotation, coordonnées inchangées
        x_final = x
        y_final = y
    
    return x_final, y_final


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
        print(f"Warning: Processing info not found for {path1_full} or {path2_full}. Using default validation.")
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
               scale1, orig_shape1_wh)   # scale pour les seconds points (originellement x1,y1)


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
            

            # Les images sont déjà correctement orientées par HomolCraft lors de la lecture
            # Pas besoin de reprojection supplémentaire

            # DEBUG: Afficher les dimensions pour diagnostiquer
            if shape1_wh is None or shape2_wh is None:
                print(f"DEBUG: shape1_wh={shape1_wh}, shape2_wh={shape2_wh}")
                print(f"DEBUG: Point problématique: ({x1_orig:.2f}, {y1_orig:.2f}) -> ({x2_orig:.2f}, {y2_orig:.2f})")
            
            # Vérification des limites des points dans les images finales
            # 0 ≤ x < largeur et 0 ≤ y < hauteur
            valid_pt1 = False
            valid_pt2 = False
            
            if shape1_wh: # shape1_wh is (width, height)
                # Validation : point doit être dans les dimensions de l'image
                if (0 <= x1_orig < shape1_wh[0] and 0 <= y1_orig < shape1_wh[1]):
                    valid_pt1 = True
                else:
                    print(f"DEBUG: Point 1 rejeté: ({x1_orig:.2f}, {y1_orig:.2f}) limites: {shape1_wh} (width={shape1_wh[0]}, height={shape1_wh[1]})")
            else:
                # Si les dimensions ne sont pas connues, on applique une validation par défaut
                if (0 <= x1_orig < 10000 and 0 <= y1_orig < 10000):
                    valid_pt1 = True
            
            if shape2_wh: # shape2_wh is (width, height)
                # Validation : point doit être dans les dimensions de l'image
                if (0 <= x2_orig < shape2_wh[0] and 0 <= y2_orig < shape2_wh[1]):
                    valid_pt2 = True
                else:
                    print(f"DEBUG: Point 2 rejeté: ({x2_orig:.2f}, {y2_orig:.2f}) limites: {shape2_wh} (width={shape2_wh[0]}, height={shape2_wh[1]})")
            else:
                # Si les dimensions ne sont pas connues, on applique une validation par défaut
                if (0 <= x2_orig < 10000 and 0 <= y2_orig < 10000):
                    valid_pt2 = True
            
            if valid_pt1 and valid_pt2:
                f.write(f"{x1_orig:.3f} {y1_orig:.3f} {x2_orig:.3f} {y2_orig:.3f}\n")


# ---------------------------------------------------------------------------
# Filtrage -------------------------------------------------------------------
# ---------------------------------------------------------------------------

def _spatial_sample(points: List[Point], max_pts: int,
                    grid: int = 4,
                    img_w: float | None = None,
                    img_h: float | None = None) -> List[Point]:
    """Répartit les points dans une grille *grid×grid* côté image A.

    Reçoit TOUS les points matchés (pas de pré-filtrage par score global).
    Dans chaque cellule, les points sont triés par score Lowe (ascendant =
    meilleur en premier), puis on pioche en round-robin entre cellules.

    img_w / img_h : dimensions réelles de l'image A. Si non fournis, on se
    rabat sur le max des coordonnées matchées.
    """
    bins: DefaultDict[Tuple[int, int], List[Point]] = defaultdict(list)

    w = img_w if img_w is not None else max(p[0] for p in points)
    h = img_h if img_h is not None else max(p[1] for p in points)

    for p in points:
        col = min(int(p[0] / (w + 1e-6) * grid), grid - 1)
        row = min(int(p[1] / (h + 1e-6) * grid), grid - 1)
        bins[(col, row)].append(p)

    # Trier chaque cellule par score (meilleur = plus petit score Lowe)
    for cell in bins:
        bins[cell].sort(key=lambda p: p[4])

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
                   occurrences: OccMap | None = None,
                   img_w: float | None = None,
                   img_h: float | None = None) -> List[Point]:
    """
    Échantillonnage spatial 4×4 sur TOUS les points matchés.
    Le tri par score se fait à l'intérieur de chaque cellule, pas globalement,
    pour éviter que les zones texturées monopolisent le budget.
    """
    if len(points) < min_pts:
        return []

    if occurrences is not None:
        raise RuntimeError("filter_matches doit être partiellement appliquée "
                           "avec les noms d'image quand occurrences est fourni.")

    pts_final = _spatial_sample(points, max_pts, img_w=img_w, img_h=img_h)

    return pts_final if len(pts_final) >= min_pts else []
