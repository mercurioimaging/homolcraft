import cv2
import numpy as np
from PIL import Image, ImageOps

def apply_clahe(img, clip_limit=2.0, tile_grid_size=(8,8)):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

def read_image(path, size=None, clahe=False):
    # Lire avec Pillow et appliquer l'orientation EXIF
    try:
        pil_img = Image.open(path)
        pil_img_oriented = ImageOps.exif_transpose(pil_img)
    except Exception as e:
        raise FileNotFoundError(f"Impossible de lire l'image avec Pillow : {path} - Erreur: {e}")

    # Convertir l'image Pillow orientée (RGB) en image OpenCV (BGR)
    # np.array(pil_img_oriented) donne un array HxWxC (RGB)
    cv_img_oriented_rgb = np.array(pil_img_oriented)
    if len(cv_img_oriented_rgb.shape) == 2: # Greyscale image
        img_bgr = cv2.cvtColor(cv_img_oriented_rgb, cv2.COLOR_GRAY2BGR)
    elif cv_img_oriented_rgb.shape[2] == 4: # RGBA image
        img_bgr = cv2.cvtColor(cv_img_oriented_rgb, cv2.COLOR_RGBA2BGR)
    else: # RGB image
        img_bgr = cv2.cvtColor(cv_img_oriented_rgb, cv2.COLOR_RGB2BGR)
    
    # Les dimensions originales sont celles de l'image orientée logiquement
    # pil_img_oriented.size est (width, height)
    w_orig, h_orig = pil_img_oriented.size
    original_shape = (h_orig, w_orig) # Stocké comme (height, width) pour cohérence interne
    scale_factor = 1.0

    # Le reste du redimensionnement et CLAHE se fait sur img_bgr
    img_to_process = img_bgr.copy() # Travailler sur une copie pour éviter des side effects

    if size is not None:
        # S'assurer que size est un entier
        size = int(size)
        # Utiliser h_orig, w_orig (logiques) pour calculer le scale_factor
        scale_factor = size / max(h_orig, w_orig)
        # Redimensionner en utilisant les dimensions logiques multipliées par le scale_factor
        # pour que les keypoints soient détectés sur une image proportionnelle aux dimensions logiques.
        target_w = int(w_orig * scale_factor)
        target_h = int(h_orig * scale_factor)
        img_to_process = cv2.resize(img_to_process, (target_w, target_h))
    
    if clahe:
        img_to_process = apply_clahe(img_to_process)
    return img_to_process, original_shape, scale_factor

def write_micmac_txt(path, points):
    # points : liste de tuples (x1, y1, x2, y2, score)
    with open(path, 'w') as f:
        for pt in points:
            f.write(f"{pt[0]:.6f} {pt[1]:.6f} {pt[2]:.6f} {pt[3]:.6f} {pt[4]:.6f}\n") 