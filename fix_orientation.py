#!/usr/bin/env python3
import os
import glob
import sys
from PIL import Image, ImageOps

def fix_image_orientation(image_path):
    """
    Ouvre une image, s'assure qu'elle est physiquement en orientation paysage
    (en la pivotant de 90° si nécessaire après correction EXIF initiale),
    et la réenregistre avec un tag EXIF d'orientation normal (1).
    Les autres tags EXIF sont préservés autant que possible.
    """
    try:
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
        print(f"Traitement de {os.path.basename(image_path)}: {'; '.join(actions_taken)}")

    except FileNotFoundError:
        print(f"Erreur : Image non trouvée à {image_path}")
    except Exception as e:
        print(f"Impossible de traiter {image_path} : {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_orientation.py \"images_pattern/*.jpg\"")
        sys.exit(1)

    image_pattern = sys.argv[1]
    image_paths = glob.glob(image_pattern)

    if not image_paths:
        print(f"Aucune image trouvée correspondant au pattern : {image_pattern}")
        sys.exit(1)

    print(f"Début du traitement de {len(image_paths)} image(s) pour normalisation en paysage...")
    for path in image_paths:
        fix_image_orientation(path)

    print("\nTraitement de normalisation d'orientation terminé.") 