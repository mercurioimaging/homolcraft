#!/usr/bin/env python3
"""
Démonstration du préprocessing d'images
"""

import os
import sys
from image_preprocessing import fix_image_orientation, process_images

def demo_single_image():
    """Démonstration avec une seule image"""
    print("=== Démonstration - Image unique ===")
    
    # Exemple d'utilisation avec une image
    image_path = "exemple.jpg"  # Remplacer par un vrai chemin
    
    if os.path.exists(image_path):
        success, message = fix_image_orientation(image_path, backup=True)
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")
    else:
        print(f"⚠️ Image d'exemple non trouvée: {image_path}")

def demo_multiple_images():
    """Démonstration avec plusieurs images"""
    print("\n=== Démonstration - Images multiples ===")
    
    # Exemple avec un pattern
    import glob
    image_pattern = "images/*.jpg"  # Remplacer par un vrai pattern
    image_paths = glob.glob(image_pattern)
    
    if image_paths:
        print(f"Traitement de {len(image_paths)} images...")
        success_count, error_count = process_images(image_paths, backup=True, verbose=True)
        print(f"Résultats: {success_count} succès, {error_count} erreurs")
    else:
        print(f"⚠️ Aucune image trouvée avec le pattern: {image_pattern}")

if __name__ == "__main__":
    print("🔄 Démonstration du préprocessing d'images")
    print("=" * 50)
    
    demo_single_image()
    demo_multiple_images()
    
    print("\n📖 Utilisation:")
    print("   python image_preprocessing.py \"images/*.jpg\"")
    print("   python image_preprocessing.py image1.jpg image2.jpg --no-backup")
    print("   python image_preprocessing.py \"*.JPG\" --quiet")
