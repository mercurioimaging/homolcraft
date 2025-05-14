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
    if len(sys.argv) != 3:
        print("Usage : python gui_viewer.py image1.jpg image2.jpg")
        sys.exit(1)
    img_path1 = sys.argv[1]
    img_path2 = sys.argv[2]
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
    pts = read_tie_points(img_path1, img_path2)
    if pts is None:
        print("Aucun tie point trouvé.")
        sys.exit(1)
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
