import os
from homolcraft.utils import find_images

def test_find_images(tmp_path):
    # Création de fichiers factices
    (tmp_path / "img1.jpg").write_text("")
    (tmp_path / "img2.jpg").write_text("")
    (tmp_path / "notimg.txt").write_text("")
    imgs = find_images(str(tmp_path / "*.jpg"))
    assert len(imgs) == 2
    assert any("img1.jpg" in img for img in imgs)
    assert any("img2.jpg" in img for img in imgs) 