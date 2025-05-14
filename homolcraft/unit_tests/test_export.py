import os
from homolcraft.core.export import export_micmac_homol

def test_export_micmac_homol(tmp_path):
    base = tmp_path / "Homol"
    img1 = "imgA.jpg"
    img2 = "imgB.jpg"
    points = [(1,2,3,4,1.0)]
    export_micmac_homol(str(base), img1, img2, points)
    out_path = base / f"Pastis{img1}" / f"{img2}.txt"
    assert out_path.exists()
    content = out_path.read_text()
    assert "1.000000 2.000000 3.000000 4.000000 1.000000" in content 