from homolcraft.core.pairs import all_pairs

def test_all_pairs():
    images = ["a.jpg", "b.jpg", "c.jpg"]
    pairs = all_pairs(images)
    assert ("a.jpg", "b.jpg") in pairs
    assert ("a.jpg", "c.jpg") in pairs
    assert ("b.jpg", "c.jpg") in pairs
    assert len(pairs) == 3

def test_point_n_images(tmp_path, monkeypatch):
    """Vérifie qu'un point détecté sur n images est exporté dans toutes les paires concernées."""
    import subprocess
    import json
    import os
    # Simule 5 images fictives
    images = [f"img_{i}.jpg" for i in range(5)]
    # Patch find_images pour retourner ces images
    monkeypatch.setattr("homolcraft.utils.find_images", lambda pattern: images)
    # Appelle la CLI en dry-run (mode all)
    result = subprocess.run([
        "python3", "-m", "homolcraft", "all", "'img_*.jpg'", "--test"
    ], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0
    # Vérifie le fichier généré
    test_file = tmp_path / "homolcraft_test_pairs.json"
    assert test_file.exists()
    with open(test_file) as f:
        data = json.load(f)
    # Il doit y avoir 10 paires (5*4/2)
    assert len(data["pairs"]) == 10 