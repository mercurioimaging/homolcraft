from __future__ import annotations
"""homolcraft.utils
Shared helpers for CLI & pipeline.
"""

from datetime import datetime
from typing import Optional

__all__ = ["get_ram_max_mb", "write_run_log"]

# ---------------------------------------------------------------------------
# Memory helper -------------------------------------------------------------
# ---------------------------------------------------------------------------

def get_ram_max_mb() -> Optional[float]:
    """Return current RSS in **megabytes** or *None* if unavailable."""
    try:
        import psutil  # type: ignore
        return psutil.Process().memory_info().rss / 1024 / 1024
    except Exception:
        try:
            import resource  # type: ignore
            ram = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # On macOS/Linux ru_maxrss may be in KiB or bytes
            return ram / 1024 if ram < 10 ** 7 else ram / 1024 / 1024
        except Exception:
            return None

# ---------------------------------------------------------------------------
# Run‑log helper ------------------------------------------------------------
# ---------------------------------------------------------------------------

def _write_header(f, *, algo_version: str, pattern: str, detect: str, size: int | None,
                  clahe: bool, sift_nfeatures: int, nb_points: int, n_jobs: int,
                  delta: int | None, circ: bool | None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    f.write(f"[HomolCraft v{algo_version}] [{now}]\n")
    f.write(f"  Pattern           : {pattern}\n")
    f.write(f"  Detector          : {detect}\n")
    f.write(f"  Size              : {size}\n")
    f.write(f"  CLAHE             : {clahe}\n")
    if detect == "sift":
        f.write(f"  SIFT nfeatures    : {sift_nfeatures}\n")
    f.write(f"  Nb points/pair    : {nb_points}\n")
    f.write(f"  n_jobs            : {n_jobs}\n")
    if delta is not None:
        f.write(f"  Delta             : {delta}\n")
    if circ is not None:
        f.write(f"  Circular          : {circ}\n")


def write_run_log(stats: dict, pattern: str, detect: str, size: int | None, clahe: bool,
                  sift_nfeatures: int, nb_points: int, n_jobs: int,
                  delta: int | None = None, circ: bool | None = None,
                  algo_version: str = "unknown") -> None:
    """Append a concise summary of *stats* to *homolcraft_run_log.txt* in CWD."""
    with open("homolcraft_run_log.txt", "a", encoding="utf-8") as f:
        _write_header(
            f,
            algo_version=algo_version,
            pattern=pattern,
            detect=detect,
            size=size,
            clahe=clahe,
            sift_nfeatures=sift_nfeatures,
            nb_points=nb_points,
            n_jobs=n_jobs,
            delta=delta,
            circ=circ,
        )
        ordered_keys = [
            "nb_images", "nb_pairs", "nb_pairs_exported", "total_points_exported",
            "rejected_points", "elapsed_sec", "ram_max_mb", "time_per_pair", "pairs_per_sec",
        ]
        for key in ordered_keys:
            if key in stats:
                f.write(f"  {key:<22}: {stats[key]}\n")
        f.write("\n")
