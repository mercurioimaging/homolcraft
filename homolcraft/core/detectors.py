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
from typing import Tuple, List

import cv2
import numpy as np

from .io import read_image   # même dossier « core »

# ---------------------------------------------------------------------------
# Classes de bas niveau déjà présentes --------------------------------------
# ---------------------------------------------------------------------------

class SIFTDetector:
    def __init__(self, nfeatures: int = 0):
        self.detector = cv2.SIFT_create(nfeatures=nfeatures)

    def detect_and_compute(self, gray: np.ndarray):
        return self.detector.detectAndCompute(gray, None)


class LoFTRDetector:
    """Présent pour référence ; non intégrée au pipeline DRY."""
    def __init__(self, device: str = "cpu"):
        from kornia.feature import LoFTR
        import torch
        self.matcher = LoFTR(pretrained="outdoor").to(device)
        self.device = device

    # API différente ; pas utilisée ici
    # def detect_and_compute(self, image0, image1): ...


# ---------------------------------------------------------------------------
# Helpers internes ----------------------------------------------------------
# ---------------------------------------------------------------------------

def _preprocess(path: str | Path, resize_max: int | None, clahe: bool):
    """Lit, redimensionne et applique éventuellement un CLAHE, retourne l’image *grise*."""
    img = read_image(str(path), size=resize_max, clahe=clahe)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
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

    raise ValueError(f"Detector inconnu : {name!r}")
