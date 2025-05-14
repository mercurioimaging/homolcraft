import cv2
import numpy as np

def apply_clahe(img, clip_limit=2.0, tile_grid_size=(8,8)):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

def read_image(path, size=None, clahe=False):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Image non trouvée : {path}")
    if size is not None:
        h, w = img.shape[:2]
        scale = size / max(h, w)
        img = cv2.resize(img, (int(w*scale), int(h*scale)))
    if clahe:
        img = apply_clahe(img)
    return img

def write_micmac_txt(path, points):
    # points : liste de tuples (x1, y1, x2, y2, score)
    with open(path, 'w') as f:
        for pt in points:
            f.write(f"{pt[0]:.6f} {pt[1]:.6f} {pt[2]:.6f} {pt[3]:.6f} {pt[4]:.6f}\n") 