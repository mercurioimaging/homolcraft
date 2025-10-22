from __future__ import annotations
"""
homolcraft.core.detectors
-------------------------
Wrappe OpenCV-SIFT et (optionnellement) LoFTR,
et fournit une *factory* : get_detector().
Le détecteur retourné lit l’image (resize + CLAHE),
puis renvoie (keypoints, descriptors).
"""

from pathlib import Path
from typing import Tuple, List, Any

import cv2
import numpy as np

from .io import read_image   # même dossier « core »
from homolcraft.core import IMAGE_PROCESSING_INFO # Import du dictionnaire depuis homolcraft.core

# ---------------------------------------------------------------------------
# Classes de bas niveau déjà présentes --------------------------------------
# ---------------------------------------------------------------------------

class SIFTDetector:
    def __init__(self, nfeatures: int = 0):
        self.detector = cv2.SIFT_create(nfeatures=nfeatures)

    def detect_and_compute(self, gray: np.ndarray):
        return self.detector.detectAndCompute(gray, None)


class AKAZEDetector:
    def __init__(self, max_keypoints: int = 2000, threshold: float = 0.001):
        self.detector = cv2.AKAZE_create(threshold=threshold)
        self.max_keypoints = max_keypoints

    def detect_and_compute(self, gray: np.ndarray):
        kps, desc = self.detector.detectAndCompute(gray, None)
        if kps is not None and len(kps) > self.max_keypoints:
            # Trie par réponse et ne garde que les meilleurs
            idx = np.argsort([-kp.response for kp in kps])[:self.max_keypoints]
            kps = [kps[i] for i in idx]
            desc = desc[idx]
        return kps, desc


class ORBDetector:
    def __init__(self, nfeatures: int = 10000):
        self.detector = cv2.ORB_create(nfeatures=nfeatures)

    def detect_and_compute(self, gray: np.ndarray):
        return self.detector.detectAndCompute(gray, None)


class LoFTRDetector:
    """Détecteur LoFTR pour matching deep learning."""
    def __init__(self, device: str = "cpu", weights: str = "outdoor"):
        from kornia.feature import LoFTR
        import torch
        self.loftr = LoFTR(pretrained=weights).to(device)
        self.device = device

    def detect_and_compute(self, gray: np.ndarray):
        """LoFTR ne fait pas de détection séparée, retourne None pour compatibilité."""
        return None, None

    def match_images(self, img1: np.ndarray, img2: np.ndarray):
        """Matching direct entre deux images avec LoFTR."""
        import torch
        
        # Conversion en tenseur torch, normalisé [0,1], batché, float32
        if isinstance(img1, np.ndarray):
            img1 = torch.from_numpy(img1).float() / 255.0
        if isinstance(img2, np.ndarray):
            img2 = torch.from_numpy(img2).float() / 255.0
        if img1.ndim == 2:
            img1 = img1.unsqueeze(0)
        if img2.ndim == 2:
            img2 = img2.unsqueeze(0)
        if img1.ndim == 3:
            img1 = img1.unsqueeze(0)
        if img2.ndim == 3:
            img2 = img2.unsqueeze(0)
        
        inp = {'image0': img1, 'image1': img2}
        with torch.no_grad():
            out = self.loftr(inp)
        mkpts0 = out['keypoints0'].cpu().numpy()
        mkpts1 = out['keypoints1'].cpu().numpy()
        return mkpts0, mkpts1


# ---------------------------------------------------------------------------
# Helpers internes ----------------------------------------------------------
# ---------------------------------------------------------------------------

def _preprocess(path: str | Path, resize_max: int | None, clahe: bool):
    """Lit, redimensionne et applique éventuellement un CLAHE, retourne l’image *grise*."""
    img_color, original_shape, scale_factor = read_image(str(path), size=resize_max, clahe=clahe)
    gray = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)
    
    # Store processing info
    IMAGE_PROCESSING_INFO[str(path)] = {
        "original_shape": original_shape, # (h_orig, w_orig)
        "scale_factor": scale_factor,
        "resized_shape": gray.shape # (h_resized, w_resized)
    }
    return gray


# ---------------------------------------------------------------------------
# Factory publique ----------------------------------------------------------
# ---------------------------------------------------------------------------

def get_detector(
    *,
    name: str = "sift",
    resize_max: int | None = 1500,
    clahe: bool = True,
    sift_nfeatures: int = 4_000,
):
    """
    Retourne une fonction ``detect(path) -> (keypoints, descriptors)``
    conforme aux attentes du pipeline.
    """
    name = name.lower()

    if name == "sift":
        sift = SIFTDetector(nfeatures=sift_nfeatures)

        def _detect(path: str | Path):
            gray = _preprocess(path, resize_max, clahe)
            kpts, desc = sift.detect_and_compute(gray)
            return kpts, desc

        return _detect

    elif name == "akaze":
        akaze = AKAZEDetector(max_keypoints=sift_nfeatures)

        def _detect(path: str | Path):
            gray = _preprocess(path, resize_max, clahe)
            kpts, desc = akaze.detect_and_compute(gray)
            return kpts, desc

        return _detect

    elif name == "orb":
        orb = ORBDetector(nfeatures=sift_nfeatures)

        def _detect(path: str | Path):
            gray = _preprocess(path, resize_max, clahe)
            kpts, desc = orb.detect_and_compute(gray)
            return kpts, desc

        return _detect

    elif name == "loftr":
        loftr = LoFTRDetector()

        def _detect(path: str | Path):
            # LoFTR ne fait pas de détection séparée
            return None, None

        return _detect

    raise ValueError(f"Detector inconnu : {name!r}")
