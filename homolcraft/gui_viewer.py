import os
import sys
import cv2
import numpy as np
import matplotlib.pyplot as plt

def read_tie_points(img1, img2, homol_dir="tests/Homol"):
    base1 = os.path.basename(img1)
    base2 = os.path.basename(img2)
    tie_path = os.path.join(homol_dir, f"Pastis{base1}", f"{base2}.txt")
    if not os.path.exists(tie_path):
        return None
    pts = []
    with open(tie_path, "r") as f:
        for line in f:
            vals = list(map(float, line.strip().split()))
            if len(vals) >= 4:
                pts.append(vals[:4])
    return np.array(pts) if pts else None

def resize(img, h):
    scale = h / img.shape[0]
    return cv2.resize(img, (int(img.shape[1]*scale), h)), scale

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Visualise les points homologues entre deux images")
    parser.add_argument("image1")
    parser.add_argument("image2")
    parser.add_argument("--homol-dir", default="Homol", help="Dossier Homol (défaut: Homol)")
    args = parser.parse_args()
    img_path1 = args.image1
    img_path2 = args.image2
    if not (os.path.exists(img_path1) and os.path.exists(img_path2)):
        print("Erreur : une des images n'existe pas.")
        sys.exit(1)
    img1 = cv2.cvtColor(cv2.imread(img_path1), cv2.COLOR_BGR2RGB)
    img2 = cv2.cvtColor(cv2.imread(img_path2), cv2.COLOR_BGR2RGB)
    h1, w1 = img1.shape[:2]
    h2, w2 = img2.shape[:2]
    max_h = max(h1, h2)
    img1_resized, scale1 = resize(img1, max_h)
    img2_resized, scale2 = resize(img2, max_h)
    concat = np.hstack([img1_resized, img2_resized])
    pts = read_tie_points(img_path1, img_path2, homol_dir=args.homol_dir)
    if pts is None:
        # essayer dans l'autre sens
        pts = read_tie_points(img_path2, img_path1, homol_dir=args.homol_dir)
        if pts is not None:
            pts = pts[:, [2, 3, 0, 1]]  # inverser les colonnes
    if pts is None:
        print("Aucun tie point trouvé.")
        sys.exit(1)
    print(f"{len(pts)} points homologues trouvés.")
    plt.figure(figsize=(15, 8))
    plt.imshow(concat)
    for x1, y1, x2, y2 in pts:
        x1s, y1s = x1 * scale1, y1 * scale1
        x2s, y2s = x2 * scale2, y2 * scale2
        plt.plot([x1s, x2s + img1_resized.shape[1]], [y1s, y2s], 'y-', alpha=0.5)
        plt.plot(x1s, y1s, 'ro', markersize=4)
        plt.plot(x2s + img1_resized.shape[1], y2s, 'bo', markersize=4)
    plt.axis('off')
    plt.show()

if __name__ == "__main__":
    main()
