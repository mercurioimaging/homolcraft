#!/usr/bin/env python3
"""
Script de vérification des points homologues
Vérifie tous les fichiers Homol pour détecter les points hors limites
"""

import os
import glob
import cv2

def get_image_dimensions(image_path):
    """Récupère les dimensions d'une image"""
    try:
        img = cv2.imread(image_path)
        if img is not None:
            return img.shape[1], img.shape[0]  # width, height
    except:
        pass
    return None, None

def check_homol_files():
    """Vérifie tous les fichiers Homol pour des points hors limites"""
    print("Vérification finale des points homologues...")
    print("=" * 60)
    
    # Récupérer toutes les images pour créer un dictionnaire des dimensions
    image_files = glob.glob("imgs/*.jpg")
    image_dimensions = {}
    
    for image_path in image_files:
        width, height = get_image_dimensions(image_path)
        if width is not None and height is not None:
            image_dimensions[os.path.basename(image_path)] = (width, height)
    
    print(f"📊 {len(image_dimensions)} images avec dimensions connues")
    
    # Vérifier tous les fichiers Homol
    homol_files = glob.glob("imgs/Homol/**/*.txt", recursive=True)
    total_points = 0
    problematic_points = 0
    problematic_files = []
    
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
                
                file_problems = 0
                file_points = 0
                
                try:
                    with open(homol_file, 'r') as f:
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if not line:
                                continue
                                
                            parts = line.split()
                            if len(parts) >= 4:
                                try:
                                    x1, y1, x2, y2 = float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])
                                    file_points += 1
                                    
                                    # Vérifier les limites pour chaque image
                                    if (x1 < 0 or x1 >= width1 or y1 < 0 or y1 >= height1 or
                                        x2 < 0 or x2 >= width2 or y2 < 0 or y2 >= height2):
                                        file_problems += 1
                                        if file_problems <= 3:  # Limiter l'affichage
                                            print(f"❌ {homol_file}:{line_num} - Point hors limites: ({x1:.1f}, {y1:.1f}) -> ({x2:.1f}, {y2:.1f})")
                                            print(f"    Limites: {img1_name}({width1}x{height1}) et {img2_name}({width2}x{height2})")
                                        
                                except ValueError:
                                    pass
                except:
                    pass
                
                if file_problems > 0:
                    problematic_files.append((homol_file, file_problems))
                    problematic_points += file_problems
                
                total_points += file_points
    
    print("\n" + "=" * 60)
    print("Résumé de la vérification :")
    print(f"📁 Fichiers Homol analysés : {len(homol_files)}")
    print(f"📊 Points totaux : {total_points}")
    print(f"❌ Points problématiques : {problematic_points}")
    print(f"📁 Fichiers avec problèmes : {len(problematic_files)}")
    
    if problematic_points == 0:
        print("\n✅ Aucun point hors limites détecté !")
    else:
        print(f"\n❌ {problematic_points} points hors limites dans {len(problematic_files)} fichiers")
        for file_path, count in problematic_files[:5]:  # Afficher les 5 premiers
            print(f"  - {file_path}: {count} points problématiques")

if __name__ == "__main__":
    check_homol_files() 