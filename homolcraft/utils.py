from __future__ import annotations
"""
homolcraft.utils
----------------
Aide-mémoire partagé par la CLI et le pipeline.
"""

from datetime import datetime
from functools import lru_cache
from typing import Optional, Tuple
import os
import socket

try:
    import cv2  # OpenCV est recommandé pour get_image_size_cached
except ImportError:
    cv2 = None  # les appels lèveront une erreur explicite

__all__ = [
    # anciennes fonctions
    "get_ram_max_mb",
    "write_run_log",
    "estimate_homol_size",
    # nouvelles
    "get_image_size_cached",
    "log_section",
]

# ---------------------------------------------------------------------------
# Estimation de taille des fichiers Homol -----------------------------------
# ---------------------------------------------------------------------------

def estimate_homol_size(total_points: int) -> Tuple[float, str]:
    """Estime la taille approximative des fichiers Homol.

    Chaque point ≈ 40 octets (x1 y1 x2 y2 score).
    Retourne (taille en octets, chaîne formatée lisible).
    """
    bytes_per_point = 40
    total_bytes = total_points * bytes_per_point

    if total_bytes < 1024:
        return total_bytes, f"{total_bytes} octets"
    if total_bytes < 1024 ** 2:
        kb = total_bytes / 1024
        return total_bytes, f"{kb:.2f} Ko"
    mb = total_bytes / 1024 ** 2
    return total_bytes, f"{mb:.2f} Mo"

# ---------------------------------------------------------------------------
# Memory helper -------------------------------------------------------------
# ---------------------------------------------------------------------------

def get_ram_max_mb() -> Optional[float]:
    """Retourne la mémoire RSS courante en **Mo** ou *None* si indisponible."""
    try:
        import psutil  # type: ignore
        return psutil.Process().memory_info().rss / 1024 / 1024
    except Exception:
        try:
            import resource  # type: ignore
            ram = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # sur macOS/Linux ru_maxrss peut être en KiB ou octets
            return ram / 1024 if ram < 10**7 else ram / 1024 / 1024
        except Exception:
            return None

# ---------------------------------------------------------------------------
# Run-log helper ------------------------------------------------------------
# ---------------------------------------------------------------------------

def _write_header(
    f,
    *,
    algo_version: str,
    pattern: str,
    detect: str,
    size: int | None,
    clahe: bool,
    sift_nfeatures: int,
    nb_points: int,
    n_jobs: int,
    delta: int | None,
    circ: bool | None,
    mode: str = "all",
    nb_pts_mini: int = 25,
):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    f.write(f"[HomolCraft v{algo_version}] [{now}]\n")
    f.write(f"  Pattern           : {pattern}\n")
    f.write(f"  Mode              : {mode}\n")
    f.write(f"  Detector          : {detect}\n")
    f.write(f"  Size              : {size}\n")
    f.write(f"  CLAHE             : {clahe}\n")
    if detect == "sift":
        f.write(f"  SIFT nfeatures    : {sift_nfeatures}\n")
    f.write(f"  Nb points/pair    : {nb_points}\n")
    f.write(f"  Nb pts mini       : {nb_pts_mini}\n")
    f.write(f"  n_jobs            : {n_jobs}\n")
    if delta is not None:
        f.write(f"  Delta             : {delta}\n")
    if circ is not None:
        f.write(f"  Circular          : {circ}\n")


def write_run_log(
    stats,
    pattern,
    detect,
    size,
    clahe,
    sift_nfeatures,
    nb_points,
    n_jobs,
    algo_version="unknown",
    nb_pts_mini=25,
    mode="all",
    delta=None,
    circ=None,
    thresh_strategy=None,
    thresh_factor=None,
    thresh_fixed=None,
    sift_nfeat_low=None,
    size_low=None,
    pattern2=None,
    size_pattern2=None,
    sift_nfeat_pattern2=None,
):
    """Append un résumé d'exécution dans *homolcraft_run_log.txt*."""
    log_file = "homolcraft_run_log.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hostname = socket.gethostname()

    lines = [
        f"",
        f"==== HomolCraft run {timestamp} ====",
        f"Algorithm version: {algo_version}",
        f"Host: {hostname}",
        f"Pattern: {pattern}",
        "Parameters:",
        f"  - mode: {mode}",
        f"  - detector: {detect}",
        f"  - size: {size}",
        f"  - clahe: {clahe}",
        f"  - sift_nfeatures: {sift_nfeatures}",
        f"  - nb_points: {nb_points}",
        f"  - nb_pts_mini: {nb_pts_mini}",
        f"  - n_jobs: {n_jobs}",
    ]
    
    # Ajouter pattern2 si spécifié
    if pattern2 is not None:
        lines.append(f"  - pattern2: {pattern2}")
    
    # Ajouter size_pattern2 si spécifié
    if size_pattern2 is not None:
        lines.append(f"  - size_pattern2: {size_pattern2}")
    
    # Ajouter delta et circ seulement s'ils sont spécifiés (utile pour le mode line)
    if delta is not None:
        lines.append(f"  - delta: {delta}")
    if circ is not None:
        lines.append(f"  - circ: {circ}")
        
    # Ajouter paramètres spécifiques au mode mulscale
    if mode == "mulscale":
        if thresh_strategy is not None:
            lines.append(f"  - thresh_strategy: {thresh_strategy}")
        if thresh_factor is not None:
            lines.append(f"  - thresh_factor: {thresh_factor}")
        if thresh_fixed is not None:
            lines.append(f"  - thresh_fixed: {thresh_fixed}")
        if sift_nfeat_low is not None:
            lines.append(f"  - sift_nfeat_low: {sift_nfeat_low}")
        if size_low is not None:
            lines.append(f"  - size_low: {size_low}")

    # Ajout des stats
    lines.append("Stats:")
    
    # Gestion spéciale pour le mode mulscale avec statistiques structurées
    if isinstance(stats, dict) and "coarse_pass" in stats and "high_res_pass" in stats:
        # Stats de la passe basse résolution
        lines.append("  Passe rapide (basse résolution):")
        for k, v in stats["coarse_pass"].items():
            lines.append(f"    - {k}: {v:.3f}" if isinstance(v, float) else f"    - {k}: {v}")
        
        # Stats de la passe haute résolution
        lines.append("  Passe précise (haute résolution):")
        # Travailler sur une copie du dictionnaire pour éviter la modification pendant l'itération
        high_res = stats["high_res_pass"].copy()
        
        # Calculer la taille estimée Homol
        if "total_points_exported" in high_res:
            _, sz = estimate_homol_size(high_res["total_points_exported"])
            high_res["estimated_homol_size"] = sz
            
        # Afficher toutes les stats
        for k, v in high_res.items():
            lines.append(f"    - {k}: {v:.3f}" if isinstance(v, float) else f"    - {k}: {v}")
            
        # Temps total
        if "elapsed_total" in stats:
            lines.append(f"  - temps_total: {stats['elapsed_total']:.3f}s")
    
    # Format standard pour les autres modes
    elif isinstance(stats, dict):
        for k, v in stats.items():
            lines.append(f"  - {k}: {v:.3f}" if isinstance(v, float) else f"  - {k}: {v}")
        if "total_points_exported" in stats:
            _, sz = estimate_homol_size(stats["total_points_exported"])
            lines.append(f"  - estimated_homol_size: {sz}")
    else:
        for k in dir(stats):
            if not k.startswith("_"):
                v = getattr(stats, k)
                lines.append(f"  - {k}: {v:.3f}" if isinstance(v, float) else f"  - {k}: {v}")
                if k == "total_points_exported":
                    _, sz = estimate_homol_size(v)
                    lines.append(f"  - estimated_homol_size: {sz}")

    lines.append("")  # ligne vide

    with open(log_file, "a") as f:
        f.write("\n".join(lines))

# ---------------------------------------------------------------------------
# NOUVELLES FONCTIONS COMMUNES ---------------------------------------------
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def get_image_size_cached(path: str | os.PathLike) -> Tuple[int, int]:
    """Retourne *(h, w)* en lisant l'image une seule fois (cache mémoire)."""
    if cv2 is None:
        raise ImportError("OpenCV (cv2) est requis pour get_image_size_cached.")
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(path)
    h, w = img.shape[:2]
    return h, w


def log_section(title: str):
    """Fabrique une petite fonction logger :

    >>> log = log_section("Detect")
    >>> log("image 42 traitée")
    [Detect   ] 12:34:56 – image 42 traitée
    """
    pad = max(8, len(title) + 1)

    def _log(msg: str):
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{title:<{pad}}] {now} – {msg}")

    return _log
