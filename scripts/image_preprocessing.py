#!/usr/bin/env python3
"""
Script de préprocessing d'images pour la normalisation d'orientation
Extrait de HomolCraft pour utilisation autonome
"""

import os
import glob
import sys
import argparse
from PIL import Image, ImageOps
from typing import List, Tuple, Optional

def fix_image_orientation(image_path: str, backup: bool = True) -> Tuple[bool, str]:
    """
    Ouvre une image, s'assure qu'elle est physiquement en orientation paysage
    (en la pivotant de 90° si nécessaire après correction EXIF initiale),
    et la réenregistre avec un tag EXIF d'orientation normal (1).
    Les autres tags EXIF sont préservés autant que possible.
    
    Args:
        image_path: Chemin vers l'image à traiter
        backup: Si True, crée une sauvegarde avant modification
        
    Returns:
        Tuple[bool, str]: (succès, message de statut)
    """
    try:
        # Créer une sauvegarde si demandé
        if backup and os.path.exists(image_path):
            backup_path = f"{image_path}.backup"
            if not os.path.exists(backup_path):
                import shutil
                shutil.copy2(image_path, backup_path)
        
        img = Image.open(image_path)
        
        # 1. Appliquer la transposition EXIF initiale pour orienter les pixels selon l'EXIF.
        img_oriented_by_exif = ImageOps.exif_transpose(img)
        
        final_img_pixels = img_oriented_by_exif
        w, h = final_img_pixels.size
        actions_taken = ["Pixels orientés selon EXIF initial"] 

        # 2. Si l'image (après correction EXIF) est en portrait, la pivoter pour être paysage.
        if h > w:
            # Rotation anti-horaire de 90 degrés pour passer de portrait à paysage.
            # expand=True ajuste la taille de l'image pour contenir toute l'image pivotée.
            final_img_pixels = final_img_pixels.rotate(90, expand=True)
            actions_taken.append("Pivotée de 90° pour format paysage")

        # 3. Préparer l'EXIF pour la sauvegarde : garantir Orientation = 1 (Normal).
        new_exif_bytes = None
        original_exif_data = img.info.get('exif')

        if original_exif_data:
            try:
                exif = Image.Exif()
                exif.load(original_exif_data) # Charger l'EXIF original
                
                exif[274] = 1  # Tag ID pour Orientation (0x0112), mettre à Normal (1)
                
                # Supprimer les tags de dimensions EXIF qui pourraient être incorrects après rotation.
                # Tag ID 0xA002: PixelXDimension, Tag ID 0xA003: PixelYDimension.
                if 0xA002 in exif: del exif[0xA002]
                if 0xA003 in exif: del exif[0xA003]
                
                new_exif_bytes = exif.tobytes()
                actions_taken.append("EXIF d'orientation mis à jour (Normal), tags de dimensions EXIF supprimés, autres tags préservés")
            except Exception as e_exif_update:
                actions_taken.append(f"AVERTISSEMENT: Impossible de mettre à jour l'EXIF existant ({e_exif_update}). Sauvegarde avec EXIF minimal d'orientation.")
                # Créer un EXIF minimal si la mise à jour de l'existant a échoué
                exif = Image.Exif()
                exif[274] = 1 # Normal
                new_exif_bytes = exif.tobytes()
        else: # Pas d'EXIF original, créer un EXIF minimal
            exif = Image.Exif()
            exif[274] = 1 # Normal
            new_exif_bytes = exif.tobytes()
            actions_taken.append("EXIF d'orientation créé (Normal)")

        # 4. Sauvegarder l'image avec les pixels finaux et l'EXIF préparé.
        final_img_pixels.save(image_path, exif=new_exif_bytes)
        message = f"Traitement de {os.path.basename(image_path)}: {'; '.join(actions_taken)}"
        return True, message

    except FileNotFoundError:
        return False, f"Erreur : Image non trouvée à {image_path}"
    except Exception as e:
        return False, f"Impossible de traiter {image_path} : {e}"

def process_images(image_paths: List[str], backup: bool = True, verbose: bool = True) -> Tuple[int, int]:
    """
    Traite une liste d'images pour normaliser leur orientation.
    
    Args:
        image_paths: Liste des chemins d'images à traiter
        backup: Si True, crée des sauvegardes avant modification
        verbose: Si True, affiche les messages de progression
        
    Returns:
        Tuple[int, int]: (nombre de succès, nombre d'erreurs)
    """
    success_count = 0
    error_count = 0
    
    for image_path in image_paths:
        success, message = fix_image_orientation(image_path, backup)
        
        if success:
            success_count += 1
            if verbose:
                print(f"✅ {message}")
        else:
            error_count += 1
            if verbose:
                print(f"❌ {message}")
    
    return success_count, error_count

def main():
    parser = argparse.ArgumentParser(
        description="Préprocessing d'images pour normalisation d'orientation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  python image_preprocessing.py "images/*.jpg"
  python image_preprocessing.py "images/*.JPG" --no-backup
  python image_preprocessing.py image1.jpg image2.jpg --quiet
        """
    )
    
    parser.add_argument(
        "images",
        nargs="+",
        help="Images à traiter (patterns glob ou chemins individuels)"
    )
    
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Ne pas créer de sauvegardes avant modification"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Mode silencieux (pas de messages de progression)"
    )
    
    args = parser.parse_args()
    
    # Développer les patterns glob
    image_paths = []
    for pattern in args.images:
        if "*" in pattern or "?" in pattern:
            # Pattern glob
            expanded = glob.glob(pattern)
            if not expanded:
                print(f"⚠️ Aucune image trouvée correspondant au pattern : {pattern}")
            else:
                image_paths.extend(expanded)
        else:
            # Chemin individuel
            if os.path.exists(pattern):
                image_paths.append(pattern)
            else:
                print(f"⚠️ Image non trouvée : {pattern}")
    
    if not image_paths:
        print("❌ Aucune image à traiter")
        sys.exit(1)
    
    if not args.quiet:
        print(f"🔄 Début du traitement de {len(image_paths)} image(s) pour normalisation en paysage...")
        if not args.no_backup:
            print("📁 Les sauvegardes seront créées avec l'extension .backup")
    
    success_count, error_count = process_images(
        image_paths, 
        backup=not args.no_backup, 
        verbose=not args.quiet
    )
    
    if not args.quiet:
        print(f"\n📊 Résultats:")
        print(f"   ✅ Succès: {success_count}")
        print(f"   ❌ Erreurs: {error_count}")
        print(f"   📁 Sauvegardes: {'Activées' if not args.no_backup else 'Désactivées'}")
    
    if error_count > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
