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

# Cache global pour LoFTR (éviter de recharger le modèle)
_LOFTR_CACHE = None


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
    if name not in {"flann", "sift", "loftr"}:
        raise ValueError(f"Matcher inconnu : {name!r}")

    def _matcher(
        path_a: Path | str,
        path_b: Path | str,
        feat_a,
        feat_b,
    ) -> List[Point]:
        if name == "loftr":
            # LoFTR : matching direct entre images
            from .detectors import LoFTRDetector
            import cv2
            
            # Charger les images en niveaux de gris
            img1 = cv2.imread(str(path_a), cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(str(path_b), cv2.IMREAD_GRAYSCALE)
            if img1 is None or img2 is None:
                return []
            
            # Redimensionner pour LoFTR : Ori max 2000px, RTI max 500px
            def resize_maxdim(img, maxdim):
                h, w = img.shape[:2]
                scale = min(maxdim / max(h, w), 1.0)
                if scale < 1.0:
                    new_w, new_h = int(w * scale), int(h * scale)
                    img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                return img
            
            # Ori (img1) : max 800px, RTI (img2) : max 500px
            img1_resized = resize_maxdim(img1, 800)
            img2_resized = resize_maxdim(img2, 500)
            
            # Stocker les informations de traitement pour l'export (comme _preprocess)
            from . import IMAGE_PROCESSING_INFO
            
            # Calculer les facteurs d'échelle comme read_image
            h1_orig, w1_orig = img1.shape[:2]
            h2_orig, w2_orig = img2.shape[:2]
            
            scale1 = 800 / max(h1_orig, w1_orig)  # Comme read_image
            scale2 = 500 / max(h2_orig, w2_orig)  # Comme read_image
            
            # Stocker dans IMAGE_PROCESSING_INFO (exactement comme _preprocess)
            IMAGE_PROCESSING_INFO[str(path_a)] = {
                "original_shape": (h1_orig, w1_orig),
                "scale_factor": scale1,
                "resized_shape": img1_resized.shape[:2]
            }
            IMAGE_PROCESSING_INFO[str(path_b)] = {
                "original_shape": (h2_orig, w2_orig),
                "scale_factor": scale2,
                "resized_shape": img2_resized.shape[:2]
            }
            
            # Matching LoFTR avec cache global
            global _LOFTR_CACHE
            if _LOFTR_CACHE is None:
                print(f"LoFTR: Chargement du modèle (première fois)...")
                _LOFTR_CACHE = LoFTRDetector()
                print(f"LoFTR: Modèle chargé")
            
            print(f"LoFTR: Matching entre images {img1_resized.shape} et {img2_resized.shape}...")
            try:
                mkpts0, mkpts1 = _LOFTR_CACHE.match_images(img1_resized, img2_resized)
                print(f"LoFTR: {len(mkpts0)} points trouvés")
                
                if len(mkpts0) == 0:
                    return []
                
                # Conversion en liste Point avec filtrage par homothétie
                pts: List[Point] = []
                scales = []
                
                # Calculer les homothéties pour tous les points
                for i in range(len(mkpts0)):
                    # Utiliser directement les coordonnées de LoFTR (l'export s'occupera de la remise à l'échelle)
                    x1, y1 = mkpts0[i]
                    x2, y2 = mkpts1[i]
                    
                    # Validation des coordonnées
                    if (x1 >= 0 and y1 >= 0 and x2 >= 0 and y2 >= 0 and 
                        x1 < 10000 and y1 < 10000 and x2 < 10000 and y2 < 10000):
                        
                        # Calculer l'homothétie (distance entre points)
                        dist1 = np.sqrt((x1 - 0)**2 + (y1 - 0)**2)  # Distance depuis origine
                        dist2 = np.sqrt((x2 - 0)**2 + (y2 - 0)**2)
                        
                        if dist1 > 0 and dist2 > 0:
                            scale = dist2 / dist1
                            scales.append(scale)
                            pts.append((float(x1), float(y1), float(x2), float(y2), float(scale)))
                
                if len(scales) < 3:
                    return pts[:nb_points]
                
                # Calculer la médiane des homothéties (plus robuste que la moyenne)
                scales_array = np.array(scales)
                median_scale = np.median(scales_array)
                mad = np.median(np.abs(scales_array - median_scale))  # Median Absolute Deviation
                
                # Filtrer les points avec homothétie aberrante (écart > 2*MAD)
                filtered_pts = []
                for pt in pts:
                    scale = pt[4]  # Le scale est stocké dans le score
                    if abs(scale - median_scale) <= 2.0 * mad:
                        filtered_pts.append(pt)
                
                print(f"LoFTR: {len(pts)} points → {len(filtered_pts)} après filtrage homothétie")
                return filtered_pts[:nb_points]
                
            except Exception as e:
                print(f"LoFTR error: {e}")
                return []
        
        else:
            # Matchers classiques (FLANN/SIFT)
            import cv2  # Import cv2 pour les matchers classiques
            kA, dA = feat_a
            kB, dB = feat_b
            if dA is None or dB is None or len(dA) == 0 or len(dB) == 0:
                return []

            # 1) Lowe ratio-test
            good = _match_flann(dA, dB) if name == "flann" else _match_sift(dA, dB)
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
                
                # Validation des coordonnées : éviter les valeurs négatives ou trop grandes
                if (x1 >= 0 and y1 >= 0 and x2 >= 0 and y2 >= 0 and 
                    x1 < 10000 and y1 < 10000 and x2 < 10000 and y2 < 10000):
                    pts.append((x1, y1, x2, y2, float(m.distance)))

            pts.sort(key=lambda p: p[4])           # score ascendant
            return pts[:nb_points]

    return _matcher
