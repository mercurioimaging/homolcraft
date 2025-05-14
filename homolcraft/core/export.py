import os

def export_micmac_homol(base_dir, img1, img2, points):
    # base_dir: dossier Homol
    # img1, img2: noms des images
    # points: liste de tuples (x1, y1, x2, y2, score)
    d1 = os.path.join(base_dir, f"Pastis{img1}")
    os.makedirs(d1, exist_ok=True)
    out_path = os.path.join(d1, f"{img2}.txt")
    with open(out_path, 'w') as f:
        for pt in points:
            f.write(f"{pt[0]:.6f} {pt[1]:.6f} {pt[2]:.6f} {pt[3]:.6f} {pt[4]:.6f}\n") 