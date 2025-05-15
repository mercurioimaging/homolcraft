"""
HomolCraft - Outil de visualisation des statistiques de paires
==============================================================
Script autonome pour analyser et visualiser les statistiques des paires 
d'images générées par HomolCraft en mode mulscale.
"""

import sys
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import json

def read_matches_stats(xml_path):
    """Analyse le fichier XML pour extraire les statistiques de matches."""
    # Pour l'instant, cette fonction est un placeholder
    # Dans une version future, on pourrait stocker les statistiques de matches 
    # directement dans le fichier XML
    
    # Lisons au moins le nombre de paires dans le XML
    tree = ET.parse(xml_path)
    root = tree.getroot()
    pairs = [cple.text.strip() for cple in root.findall('Cple')]
    
    return {
        "nb_pairs": len(pairs),
        "pairs": pairs,
        "message": f"Le fichier XML contient {len(pairs)} paires, mais pas d'informations de statistiques."
    }

def plot_distribution(stats, output=None, display=True):
    """Génère un histogramme de la distribution des matches."""
    
    if 'match_values' in stats:
        # Format idéal si on avait les valeurs réelles des matches
        match_values = stats['match_values']
        
        plt.figure(figsize=(10, 6))
        plt.hist(match_values, bins=30, alpha=0.7, color='skyblue')
        plt.axvline(np.mean(match_values), color='red', linestyle='dashed', 
                   linewidth=1, label=f'Moyenne: {np.mean(match_values):.1f}')
        
        # Ajouter médiane
        median = np.median(match_values)
        plt.axvline(median, color='green', linestyle='dashed', 
                   linewidth=1, label=f'Médiane: {median:.1f}')
        
        plt.xlabel('Nombre de matches')
        plt.ylabel('Nombre de paires')
        plt.title('Distribution du nombre de matches par paire')
        plt.grid(True, alpha=0.3)
        plt.legend()
    else:
        # Si on n'a pas les valeurs, on affiche un simple graphique du nombre de paires
        plt.figure(figsize=(8, 6))
        plt.bar(['Paires sélectionnées'], [stats['nb_pairs']], color='skyblue')
        plt.title(f'Nombre de paires sélectionnées: {stats["nb_pairs"]}')
        plt.ylabel('Nombre de paires')
        plt.grid(axis='y', alpha=0.3)
    
    # Sauvegarder ou afficher
    if output:
        plt.savefig(output)
        return f"Graphique enregistré dans {output}"
    elif display:
        plt.show()
        return "Graphique affiché"
    else:
        return "Aucune action spécifiée pour le graphique"

def analyze_pairs(xml_path, output_path=None, display=True):
    """Analyse complète des paires d'un fichier XML."""
    if not Path(xml_path).exists():
        return f"Erreur: Le fichier {xml_path} n'existe pas."
    
    try:
        stats = read_matches_stats(xml_path)
        result = plot_distribution(stats, output_path, display)
        return f"Analyse terminée. {stats.get('message', '')} {result}"
    except Exception as e:
        return f"Erreur lors de l'analyse: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description="Visualisation des statistiques de paires HomolCraft")
    parser.add_argument("xml_path", help="Chemin du fichier XML à analyser")
    parser.add_argument("--output", "-o", help="Chemin de sortie pour le graphique")
    parser.add_argument("--no-display", action="store_true", help="Ne pas afficher le graphique")
    
    args = parser.parse_args()
    
    result = analyze_pairs(args.xml_path, args.output, not args.no_display)
    print(result)

if __name__ == "__main__":
    main() 