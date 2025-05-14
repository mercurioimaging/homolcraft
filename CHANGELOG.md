# Changelog HomolCraft

## [1.1.0] - 2025-05-14
### Ajouts
- Versionning majeur.mineur.révision ajouté (ALGO_VERSION)
- Logs détaillés par étape (détection, matching, sélection spatiale, écriture) dans le run_log
- Écriture systématique des deux fichiers Homol pour chaque paire (img1->img2 et img2->img1)
- Optimisation du matching : chaque paire n'est matchée qu'une seule fois (img1 < img2)

### Modifications
- Sélection spatiale améliorée pour garantir une bonne répartition des tie points
- Complétion automatique avec des doubles si pas assez de triples

### Corrections
- Correction du bug de shadowing de variable `images`
- Correction de l'accès aux dimensions originales pour le tri spatial

---

## [1.0.0] - 2025-05-10
- Première version stable du pipeline SIFT/LoFTR avec visualisation matplotlib 

## [1.2.0] - 2025-05-15
### Ajouts
- Mode "Line" : calcul restreint aux paires d'images voisines selon l'ordre des fichiers, avec paramètre `delta` et option `--circ` pour l'acquisition circulaire.
- Option CLI : `homolcraft line <pattern> --delta N [--circ]`.
- Documentation et exemples d'utilisation mis à jour (README).
- Export et logs détaillés identiques au mode all, compatible Micmac. 