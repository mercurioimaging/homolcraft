#!/usr/bin/env python3
"""
Script de vérification des dimensions d'images
Utile pour identifier les images avec des résolutions différentes
"""

import os
import glob
import cv2
from collections import defaultdict

def get_image_dimensions(image_path):
    """Récupère les dimensions d'une image"""
    try:
        img = cv2.imread(image_path)
        if img is not None:
            return img.shape[1], img.shape[0]  # width, height
    except:
        pass
    return None, None

def main():
    print("Vérification des dimensions de toutes les images...")
    print("=" * 60)
    
    # Récupérer toutes les images
    image_files = glob.glob("imgs/*.jpg")
    image_files.sort()
    
    dimensions_count = defaultdict(int)
    dimensions_info = defaultdict(list)
    
    for image_path in image_files:
        width, height = get_image_dimensions(image_path)
        if width is not None and height is not None:
            dim_key = f"{width}x{height}"
            dimensions_count[dim_key] += 1
            dimensions_info[dim_key].append(os.path.basename(image_path))
            print(f"📷 {os.path.basename(image_path)}: {width}x{height}")
        else:
            print(f"❌ {os.path.basename(image_path)}: Impossible de lire")
    
    print("\n" + "=" * 60)
    print("Résumé des dimensions :")
    for dim, count in sorted(dimensions_count.items()):
        print(f"  {dim}: {count} images")
        if count <= 5:  # Afficher les détails si peu d'images
            for img in dimensions_info[dim]:
                print(f"    - {img}")
    
    print(f"\nTotal: {len(image_files)} images analysées")

if __name__ == "__main__":
    main() 