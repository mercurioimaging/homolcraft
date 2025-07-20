#!/usr/bin/env python3
"""
Script de correction des points homologues hors limites
Supprime automatiquement les points avec des coordonnées invalides
"""

import os
import glob
import cv2
from typing import List, Tuple

def get_image_dimensions(image_path):
    """Récupère les dimensions d'une image"""
    try:
        img = cv2.imread(image_path)
        if img is not None:
            return img.shape[1], img.shape[0]  # width, height
    except:
        pass
    return None, None

def is_point_in_bounds(x: float, y: float, max_width: int, max_height: int) -> bool:
    """Vérifie si un point est dans les limites de l'image"""
    return 0 <= x < max_width and 0 <= y < max_height

def fix_homol_file(filepath: str, max_width: int, max_height: int) -> int:
    """Corrige un fichier Homol en supprimant les points hors limites"""
    fixed_lines = []
    removed_count = 0
    
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        x1, y1, x2, y2 = float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])
                        
                        # Vérifier que les deux points sont dans les limites
                        if (is_point_in_bounds(x1, y1, max_width, max_height) and 
                            is_point_in_bounds(x2, y2, max_width, max_height)):
                            fixed_lines.append(line)
                        else:
                            removed_count += 1
                    except ValueError:
                        # Garder les lignes mal formatées (ne devrait pas arriver)
                        fixed_lines.append(line)
                else:
                    # Garder les lignes avec moins de 4 colonnes
                    fixed_lines.append(line)
    except:
        return 0
    
    # Réécrire le fichier avec les lignes corrigées
    try:
        with open(filepath, 'w') as f:
            for line in fixed_lines:
                f.write(line + '\n')
    except:
        return 0
    
    return removed_count

def main():
    print("Correction des points homologues hors limites...")
    print("=" * 60)
    
    # Récupérer toutes les images pour créer un dictionnaire des dimensions
    image_files = glob.glob("imgs/*.jpg")
    image_dimensions = {}
    
    for image_path in image_files:
        width, height = get_image_dimensions(image_path)
        if width is not None and height is not None:
            image_dimensions[os.path.basename(image_path)] = (width, height)
    
    print(f"📊 {len(image_dimensions)} images avec dimensions connues")
    
    # Corriger tous les fichiers Homol
    homol_files = glob.glob("imgs/Homol/**/*.txt", recursive=True)
    total_removed = 0
    files_processed = 0
    
    for homol_file in homol_files:
        # Extraire les noms d'images du chemin du fichier
        # Format: imgs/Homol/PastisIMG1/IMG2.txt
        path_parts = homol_file.split('/')
        if len(path_parts) >= 4:
            img1_name = path_parts[2].replace('Pastis', '')
            img2_name = path_parts[3].replace('.txt', '')
            
            # Récupérer les dimensions des deux images
            dim1 = image_dimensions.get(img1_name)
            dim2 = image_dimensions.get(img2_name)
            
            if dim1 and dim2:
                width1, height1 = dim1
                width2, height2 = dim2
                
                # Corriger le fichier en utilisant les dimensions de la première image
                # (les points x1,y1 correspondent à img1)
                removed = fix_homol_file(homol_file, width1, height1)
                
                if removed > 0:
                    print(f"🔧 {homol_file}: {removed} points supprimés")
                    total_removed += removed
                
                files_processed += 1
    
    print("\n" + "=" * 60)
    print("Résumé de la correction :")
    print(f"📁 Fichiers traités : {files_processed}")
    print(f"❌ Points supprimés : {total_removed}")
    
    if total_removed == 0:
        print("\n✅ Aucun point hors limites trouvé !")
    else:
        print(f"\n✅ {total_removed} points hors limites supprimés avec succès")

if __name__ == "__main__":
    main() 