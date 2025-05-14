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

## [1.2.1] - 2025-05-15
### Correctif
- Correction critique : en mode "line", seuls les fichiers Homol correspondant aux vrais voisins (selon delta et circ) sont écrits dans chaque dossier PastisXXX. Plus de propagation de fichiers non voisins (ex : IMG_0065.JPG.txt partout).
- Compatibilité stricte Micmac assurée pour la structure Homol. 

## [1.3.0] - 2025-05-15
### Refactorisation
- Factorisation de la génération des paires : fonctions utilitaires `all_pairs` (toutes paires) et `line_pairs` (voisins, delta, circ).
- Correction du mode `all` : il ne dépend plus de `delta`/`circ` et traite bien toutes les paires possibles.
- Préparation à la mutualisation du pipeline principal pour les futurs modes (ex : mulscale). 

## [1.3.1] - 2025-05-15
### Refactorisation & Améliorations
- Centralisation et DRY complet du logging (run_log et log.txt) : une seule fonction pour tous les modes.
- Ajout et correction des indicateurs dans les logs : nombre d'images, nombre de paires, nombre de paires exportées, RAM max (psutil ou resource), temps moyen par paire, paires/sec.
- Correction de l'affichage des stats (plus de '?').
- Décorateur commun pour les options CLI partagées (plus de duplication entre all/line).
- Refactorisation du calcul des stats (fonction compute_stats).
- Alternative à psutil pour la RAM max (module resource sur macOS/Linux). 

## [1.3.2] - 2025-05-14
### Correction de performance et robustesse
- Suppression de la double boucle de sélection spatiale par paire (phase post-matching) qui causait un ralentissement majeur.
- Optimisation de la structure de la sélection spatiale : un seul passage, plus de recalcul inutile.
- Progress bar explicite pour la phase de sélection spatiale et d'écriture Homol.
- Correction du compteur de paires exportées (stats) : le nombre affiché reflète désormais la réalité.
- Maintien de la compatibilité Micmac (symétrie d'écriture). 

## [1.4.0] - YYYY-MM-DD
### Added
- Integration of a major refactoring of the core pipeline (`homolcraft/refactor.py`).
- The `run_pipeline` function is now the central orchestrator for all processing modes (`all`, `line`).
- Clear 5-stage pipeline: pair generation, feature detection, matching, spatial selection, and MicMac Homol export.
- Each stage is a pure function, facilitating unit testing and maintenance.
- Improved progress display with `tqdm` for each significant step.
- Stricter `_in_bounds()` filter for homologous points, and reporting of rejected points in statistics.

### Changed
- CLI commands `all` and `line` in `__main__.py` now delegate their core logic to `run_pipeline`.
- Simplified logic in `__main__.py` by removing duplicated code for detection, matching, selection, and export, now handled by the refactored pipeline.
- Updated logging to reflect the new pipeline structure and include statistics on rejected points.
- `ALGO_VERSION` updated to `1.4.0`.

### Removed
- Old SIFT/LoFTR detection and matching logic from `__main__.py` commands.
- Functions `select_spatially`, `all_pairs`, `line_pairs` (module-level versions), `finalize`, `compute_stats`, `export_homol_pairs` from `__main__.py` as their responsibilities are now covered by the new pipeline or re-implemented locally if still needed (e.g., `get_ram_max_mb`).
- Temporary `*.npy` file storage for matches is no longer used by the new pipeline. 

## [1.4.1] - 2025-06-05
### Fixed
- Corrected a `TypeError` in CLI option handling (`_add_opts` in `__main__.py`) that prevented the program from running. 

## [1.4.2] - 2025-06-05
### Fixed
- Corrected an `AttributeError: 'function' object has no attribute 'params'` in CLI option handling (`_add_opts` in `__main__.py`). Options are now correctly added using the `__click_params__` attribute of the decorated function, ensuring compatibility with Click's command creation process. 

## [2.0.0] - 2025-06-05
### Major Refactoring & Enhancements
- **Core Pipeline Rearchitected (`homolcraft/refactor.py`):**
    - Introduction of `run_pipeline()` as the central orchestrator, unifying logic for all processing modes.
    - Clear 5-stage pipeline:
        1.  Pair generation (`_all_pairs`, `_line_pairs`)
        2.  Feature detection (SIFT, LoFTR via `_make_detectors`)
        3.  Matching (including RANSAC filtering)
        4.  Multiplicity-first spatial selection (`_compute_multiplicity`, `_select_spatially`)
        5.  Optimized MicMac Homol export (`_export_homol_pairs`)
    - Each stage is designed as a pure function where possible, improving testability and maintainability.
- **Multiplicity-based Point Prioritization:**
    - Tie-points observed in multiple images are now globally scored and prioritized *before* grid-based spatial selection, ensuring the most robust points are selected.
- **Optimized Homol Export:**
    - Parallelized I/O for writing Homol files using `ThreadPoolExecutor` (controlled by `write_workers` in `run_pipeline`).
    - Symmetric writing (e.g., `img1/img2.txt` and `img2/img1.txt`) is handled efficiently within a single processing step for each pair.
- **Simplified Logging:**
    - Standard output (`stdout`) is now the primary channel for progress and informational messages.
    - `homolcraft_run_log.txt` (via `homolcraft.utils.write_run_log`) receives a concise summary of each run, including key statistics. The verbose `log.txt` has been removed.
- **Streamlined CLI (`homolcraft/__main__.py`):**
    - `COMMON_OPTS` and a generic `_run()` function reduce redundancy between `all` and `line` commands.
    - No more `--test` flag; the core logic is robust.
    - Explicit short aliases for CLI options to prevent conflicts (e.g., `-t/--detect`, `-s/--size`, `-p/--nb-points`, `-j/--n-jobs`).
- **Bug Fixes:**
    - Resolved `TypeError: Name 'd' defined twice` by assigning explicit, unique short aliases to CLI options. `--detect` is now `-t`, allowing `--delta` to use `-d` without collision.
    - Fixed previous `TypeError` and `AttributeError` issues related to `click` option handling in `_add_opts`.

### Changed
- `ALGO_VERSION` updated to `2.0.0`.

### Removed
- Redundant logic in `__main__.py` now handled by `run_pipeline`.
- Old ad-hoc selection and export mechanisms.
- `log.txt` file. 

## [2.0.1] - 2025-06-05
### Fixed
- Correction d'une erreur `ValueError: too many values to unpack (expected 2)` dans `_export_homol_pairs` de `homolcraft/refactor.py` lors de l'utilisation de `write_workers > 1`. Le problème était lié à une tentative incorrecte de déballer les éléments de l'itérateur `tqdm` qui retournait des tuples à 3 éléments et non des paires. 