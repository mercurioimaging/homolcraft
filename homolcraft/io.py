from pathlib import Path
import xml.etree.ElementTree as ET
import cv2, numpy as np
from typing import Dict, List, Sequence, Tuple

Point = Tuple[float, float, float, float, float]

# ------------------------------------------------------------------
# HOMOL I/O ---------------------------------------------------------
# ------------------------------------------------------------------
def write_homol(out_dir: Path, img1: str, img2: str,
                pts: Sequence[Point]) -> None:
    """Écrit *les deux fichiers* Pastis en une seule fonction."""
    if not pts:
        return
    _write_one(out_dir, img1, img2, pts)
    _write_one(out_dir, img2, img1,
               [(x2, y2, x1, y1, s) for (x1, y1, x2, y2, s) in pts])

def _write_one(out_dir: Path, src: str, dst: str,
               pts: Sequence[Point]) -> None:
    d = out_dir / f"Pastis{Path(src).name}"
    d.mkdir(parents=True, exist_ok=True)
    txt = d / f"{Path(dst).name}.txt"
    txt.write_text(
        "".join(f"{x1:.4f} {y1:.4f} {x2:.4f} {y2:.4f} {s:.4f}\n"
                for x1, y1, x2, y2, s in pts)
    )

# ------------------------------------------------------------------
# XML SauvegardeNamedRel I/O ---------------------------------------
# ------------------------------------------------------------------
def read_pairs_xml(path: str | Path) -> List[Tuple[str, str]]:
    tree = ET.parse(str(path))
    return [tuple(c.text.split()) for c in tree.findall("Cple")]

def write_pairs_xml(path: str | Path,
                    pairs: Sequence[Tuple[str, str]]) -> None:
    import xml.dom.minidom as md
    root = ET.Element("SauvegardeNamedRel")
    for a, b in pairs:
        ET.SubElement(root, "Cple").text = f"{a} {b}"
    path = Path(path)
    path.write_text(md.parseString(ET.tostring(root)).toprettyxml("  "))
