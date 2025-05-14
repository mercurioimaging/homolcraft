import click
import numpy as np
import time
from itertools import combinations

ALGO_VERSION = "1.3.1"

@click.group()
def cli():
    """HomolCraft : Générateur de points homologues compatibles Micmac."""
    pass

def common_options(func):
    options = [
        click.option('--size', type=int, default=1000, help="Taille d'image (optionnel)"),
        click.option('--detect', type=click.Choice(['sift', 'loftr']), default='sift', help='Détecteur à utiliser'),
        click.option('--clahe', is_flag=True, default=True, help='Appliquer un filtre CLAHE avant détection'),
        click.option('--sift-nfeatures', type=int, default=2000, help='Nombre de points SIFT (défaut 2000)'),
        click.option('--nb-points', type=int, default=500, help='Nombre de points max à garder par paire (défaut 500)'),
        click.option('--n-jobs', type=int, default=8, help='Nombre de processus pour la parallélisation (défaut 8)'),
        click.option('--test', is_flag=True, default=False, help='Dry-run : génère un fichier de test des paires sans calculer les points'),
    ]
    for opt in reversed(options):
        func = opt(func)
    return func

@cli.command()
@click.argument('pattern')
@common_options
def all(pattern, size, detect, clahe, sift_nfeatures, nb_points, n_jobs, test):
    """Calcul pour toutes les paires possibles."""
    import time
    from homolcraft.utils import find_images
    from homolcraft.core.pairs import all_pairs as core_all_pairs
    from homolcraft.core.detectors import SIFTDetector, LoFTRDetector
    from homolcraft.core.matchers import match_sift
    from homolcraft.core.io import read_image
    from homolcraft.core.export import export_micmac_homol
    import os
    from tqdm import tqdm
    import torch
    import cv2
    import numpy as np
    from datetime import datetime
    import json
    import shutil
    import concurrent.futures
    try:
        import psutil
        psutil_available = True
    except ImportError:
        psutil_available = False

    def log(msg, logf=None):
        ts = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        line = f"{ts} {msg}"
        print(line)
        if logf:
            print(line, file=logf)
            logf.flush()

    t0 = time.time()
    images = find_images(pattern)
    if len(images) < 2:
        click.echo("Moins de 2 images trouvées.")
        return
    pairs = core_all_pairs(images)
    img_dir = os.path.dirname(os.path.abspath(images[0]))
    out_dir = os.path.join(img_dir, "Homol")
    # Sauvegarde Homol existant
    if os.path.exists(out_dir):
        bkp_dir = out_dir + "_bkp"
        if os.path.exists(bkp_dir):
            shutil.rmtree(bkp_dir)
        shutil.move(out_dir, bkp_dir)
    os.makedirs(out_dir, exist_ok=True)

    log_path = os.path.join(out_dir, "log.txt")
    logf = open(log_path, "w")
    log(f"--- Lancement homolcraft {ALGO_VERSION} ---", logf)
    log(f"Pattern utilisé : {pattern}", logf)
    log(f"Détecteur : {detect}", logf)
    log(f"Taille demandée : {size}", logf)
    log(f"CLAHE : {clahe}", logf)
    if detect == "sift":
        log(f"SIFT nfeatures : {sift_nfeatures}", logf)
    log(f"Nombre d'images : {len(images)}", logf)
    log(f"Nombre de paires : {len(pairs)}", logf)
    log(f"Parallélisation : {n_jobs} processus", logf)

    stats = {"total_pairs": len(pairs), "pairs_done": 0, "total_matches": 0, "per_pair": []}

    # Initialisation des timers pour éviter les erreurs si non utilisés
    detection_t0 = detection_t1 = 0.0

    detection_t0 = time.time()
    if detect == "sift":
        detector = SIFTDetector(nfeatures=sift_nfeatures)
        def sift_worker(img):
            im = read_image(img, size, clahe=clahe)
            kps, desc = detector.detect_and_compute(im)
            return (img, (kps, desc, im.shape))
        sift_data = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_jobs) as executor:
            for img, res in tqdm(executor.map(sift_worker, images), total=len(images), desc="SIFT détecteurs"):
                sift_data[img] = res
        # Stockage temporaire des matches
        tmp_dir = os.path.join(img_dir, "tmp_homolcraft")
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        os.makedirs(tmp_dir, exist_ok=True)
        matches_per_pair = {}
        def match_worker(pair):
            img1, img2 = pair
            kps1, desc1, shape1 = sift_data[img1]
            kps2, desc2, shape2 = sift_data[img2]
            orig1 = cv2.imread(img1, cv2.IMREAD_COLOR)
            orig2 = cv2.imread(img2, cv2.IMREAD_COLOR)
            h1o, w1o = orig1.shape[:2]
            h2o, w2o = orig2.shape[:2]
            h1, w1 = shape1[:2]
            h2, w2 = shape2[:2]
            scale1 = w1o / w1
            scale2 = w2o / w2
            if desc1 is None or desc2 is None:
                return (pair, [])
            matches = match_sift(desc1, desc2)
            if len(matches) < 30:
                return (pair, [])
            pts1 = np.float32([kps1[m.queryIdx].pt for m in matches])
            pts2 = np.float32([kps2[m.trainIdx].pt for m in matches])
            if len(pts1) >= 8:
                F, mask = cv2.findFundamentalMat(pts1, pts2, cv2.FM_RANSAC, 2.0, 0.99)
                inlier_matches = [m for m, inl in zip(matches, mask.ravel()) if inl]
            else:
                inlier_matches = matches
            points = []
            points_inv = []
            for m in inlier_matches:
                pt1 = kps1[m.queryIdx].pt
                pt2 = kps2[m.trainIdx].pt
                x1, y1 = pt1[0]*scale1, pt1[1]*scale1
                x2, y2 = pt2[0]*scale2, pt2[1]*scale2
                points.append((x1, y1, x2, y2, 1.0, m.queryIdx, m.trainIdx))
                points_inv.append((x2, y2, x1, y1, 1.0, m.trainIdx, m.queryIdx))
            # Sauvegarde temporaire dans les deux sens
            d1 = os.path.join(tmp_dir, f"Pastis{os.path.basename(img1)}")
            os.makedirs(d1, exist_ok=True)
            out_path = os.path.join(d1, f"{os.path.basename(img2)}.npy")
            np.save(out_path, np.array(points))
            d2 = os.path.join(tmp_dir, f"Pastis{os.path.basename(img2)}")
            os.makedirs(d2, exist_ok=True)
            out_path_inv = os.path.join(d2, f"{os.path.basename(img1)}.npy")
            np.save(out_path_inv, np.array(points_inv))
            return (pair, points)
        # Parallélisation du matching
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_jobs) as executor:
            results = list(tqdm(executor.map(match_worker, pairs), total=len(pairs), desc="SIFT matches brut"))
        for (img1, img2), points in results:
            if points:
                matches_per_pair[(img1, img2)] = points
                matches_per_pair[(img2, img1)] = [(x2, y2, x1, y1, s, idx2, idx1) for (x1, y1, x2, y2, s, idx1, idx2) in points]
        # Indexation des tie points par image
        from collections import defaultdict
        point_index = defaultdict(lambda: defaultdict(list))  # img -> (x,y arrondi) -> [(autre_img, x2, y2)]
        for (img1, img2), points in matches_per_pair.items():
            for x1, y1, x2, y2, s, idx1, idx2 in points:
                key1 = (round(x1,1), round(y1,1))  # tolérance 0.1 pixel
                key2 = (round(x2,1), round(y2,1))
                point_index[img1][key1].append((img2, x2, y2))
                point_index[img2][key2].append((img1, x1, y1))
        # --- Nouvelle sélection par paire ---
        from collections import defaultdict
        final_points = defaultdict(lambda: defaultdict(list))  # img -> img2 -> [x1, y1, x2, y2, 1.0]
        #print("[CHECKPOINT] Début de la sélection spatiale par paire Homol")
        for img1, img2 in tqdm(pairs, desc="Sélection spatiale par paire"):
            # On récupère tous les tie points entre img1 et img2 (triples+ puis doubles)
            key_img2 = os.path.basename(img2)
            # On cherche d'abord les points triples+ (présents sur >=3 images)
            triples_pts = []
            doubles_pts = []
            # On parcourt tous les tie points indexés pour img1
            for (x, y), lst in point_index[img1].items():
                imgset = set([img2b for img2b, _, _ in lst])
                # On cherche si img2 fait partie de la liste
                for img2b, x2, y2 in lst:
                    if os.path.basename(img2b) == key_img2:
                        if len(imgset) >= 3:
                            triples_pts.append((x, y, x2, y2, 1.0))
                        elif len(imgset) == 2:
                            doubles_pts.append((x, y, x2, y2, 1.0))
            # On priorise les triples, puis on complète avec les doubles
            all_pts = triples_pts.copy()
            if len(all_pts) < nb_points:
                all_pts += doubles_pts[:nb_points-len(all_pts)]
            # Sélection spatiale
            orig = cv2.imread(img1, cv2.IMREAD_COLOR)
            h1o, w1o = orig.shape[:2]
            if len(all_pts) > nb_points:
                all_pts = select_spatially(all_pts, w1o, h1o, nmax=nb_points)
            # On écrit le résultat dans final_points
            final_points[img1][key_img2] = all_pts
            #print(f"[DEBUG] {os.path.basename(img1)} -> {key_img2} : {len(all_pts)} tie points sélectionnés (triples+ et doubles)")
        #print("[CHECKPOINT] Fin de la sélection spatiale par paire Homol")
        detection_t1 = time.time()
        log(f"[STATS] Détection SIFT : {detection_t1-detection_t0:.1f} sec", logf)
        matching_t0 = time.time()
        # --- Boucle d'écriture finale Homol (symétrique Micmac, uniquement pour les vrais voisins) ---
        for img1, img2 in pairs:
            key1 = os.path.basename(img1)
            key2 = os.path.basename(img2)
            pts = final_points[img1][key2] if key2 in final_points[img1] else []
            if pts:
                # Ecriture img1 -> img2
                d1 = os.path.join(out_dir, f"Pastis{key1}")
                os.makedirs(d1, exist_ok=True)
                out_path = os.path.join(d1, f"{key2}.txt")
                with open(out_path, 'w') as f:
                    for pt in pts:
                        f.write(f"{pt[0]:.6f} {pt[1]:.6f} {pt[2]:.6f} {pt[3]:.6f} {pt[4]:.6f}\n")
                # Ecriture img2 -> img1 (symétrique)
                d2 = os.path.join(out_dir, f"Pastis{key2}")
                os.makedirs(d2, exist_ok=True)
                out_path_inv = os.path.join(d2, f"{key1}.txt")
                with open(out_path_inv, 'w') as f:
                    for pt in pts:
                        f.write(f"{pt[2]:.6f} {pt[3]:.6f} {pt[0]:.6f} {pt[1]:.6f} {pt[4]:.6f}\n")
        matching_t1 = time.time()
        log(f"[STATS] Matching SIFT : {matching_t1-matching_t0:.1f} sec", logf)
        selection_t0 = time.time()
        # --- Nouvelle sélection par paire ---
        #print("[CHECKPOINT] Début de la sélection spatiale par paire Homol")
        for img1, img2 in tqdm(pairs, desc="Sélection spatiale par paire"):
            # ... code inchangé ...
            final_points[img1][key_img2] = all_pts
            #print(f"[DEBUG] {os.path.basename(img1)} -> {key_img2} : {len(all_pts)} tie points sélectionnés (triples+ et doubles)")
        #print("[CHECKPOINT] Fin de la sélection spatiale par paire Homol")
        selection_t1 = time.time()
        log(f"[STATS] Sélection spatiale : {selection_t1-selection_t0:.1f} sec", logf)
        ecriture_t0 = time.time()
        ecriture_t1 = time.time()
        log(f"[STATS] Ecriture Homol : {ecriture_t1-ecriture_t0:.1f} sec", logf)
        print("[CHECKPOINT] Fin de la boucle d'écriture finale Homol")
        print(f"[tmp_homolcraft] Dossier temporaire conservé ici : {tmp_dir}")
        # Suppression du dossier temporaire à la fin
        if os.path.exists(tmp_dir):
            import shutil
            shutil.rmtree(tmp_dir)
        if test:
            # Dry-run : on écrit la liste des paires dans un fichier JSON
            out = {"images": images, "pairs": [(os.path.basename(a), os.path.basename(b)) for a, b in pairs]}
            with open("homolcraft_test_pairs.json", "w") as f:
                json.dump(out, f, indent=2)
            click.echo(f"[TEST] Dry-run : {len(pairs)} paires générées. Voir homolcraft_test_pairs.json.")
            return
        return finalize(stats, out_dir, t0, pattern, size, detect, clahe, sift_nfeatures, nb_points, n_jobs, logf, log)
    elif detect == "loftr":
        detector = LoFTRDetector(device="cpu")
    else:
        click.echo(f"Détecteur inconnu : {detect}")
        logf.close()
        return

    stats = {"total_pairs": len(pairs), "pairs_done": 0, "total_matches": 0, "per_pair": []}

    pbar = tqdm(pairs, desc="Paires")
    for img1, img2 in pbar:
        if detect == "sift":
            kps1, desc1, shape1 = sift_data[img1]
            kps2, desc2, shape2 = sift_data[img2]
            orig1 = cv2.imread(img1, cv2.IMREAD_COLOR)
            orig2 = cv2.imread(img2, cv2.IMREAD_COLOR)
            h1o, w1o = orig1.shape[:2]
            h2o, w2o = orig2.shape[:2]
            h1, w1 = shape1[:2]
            h2, w2 = shape2[:2]
            scale1 = w1o / w1
            scale2 = w2o / w2
            if desc1 is None or desc2 is None:
                continue
            matches = match_sift(desc1, desc2)
            if len(matches) < 30:
                msg = f"{os.path.basename(img1)} - {os.path.basename(img2)} SIFT : {len(matches)} matches < 30, ignoré"
                log(msg, logf)
                continue
            pts1 = np.float32([kps1[m.queryIdx].pt for m in matches])
            pts2 = np.float32([kps2[m.trainIdx].pt for m in matches])
            if len(pts1) >= 8:
                F, mask = cv2.findFundamentalMat(pts1, pts2, cv2.FM_RANSAC, 2.0, 0.99)
                inlier_matches = [m for m, inl in zip(matches, mask.ravel()) if inl]
            else:
                inlier_matches = matches
            points = []
            for m in inlier_matches:
                pt1 = kps1[m.queryIdx].pt
                pt2 = kps2[m.trainIdx].pt
                x1, y1 = pt1[0]*scale1, pt1[1]*scale1
                x2, y2 = pt2[0]*scale2, pt2[1]*scale2
                points.append((x1, y1, x2, y2, 1.0))
            if len(points) > nb_points:
                points = select_spatially(points, w1o, h1o, nmax=nb_points)
            msg = f"{os.path.basename(img1)} - {os.path.basename(img2)} SIFT : {len(matches)} matches, {len(inlier_matches)} inliers, {len(points)} exportés"
            log(msg, logf)
        elif detect == "loftr":
            im1 = read_image(img1, size, clahe=clahe)
            im2 = read_image(img2, size, clahe=clahe)
            orig1 = cv2.imread(img1, cv2.IMREAD_COLOR)
            orig2 = cv2.imread(img2, cv2.IMREAD_COLOR)
            h1o, w1o = orig1.shape[:2]
            h2o, w2o = orig2.shape[:2]
            h1, w1 = im1.shape[:2]
            h2, w2 = im2.shape[:2]
            scale1 = w1o / w1
            scale2 = w2o / w2
            def to_tensor(img):
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                t = torch.from_numpy(gray).float() / 255.0
                t = t.unsqueeze(0).unsqueeze(0)
                return t
            t1 = to_tensor(im1)
            t2 = to_tensor(im2)
            out = detector.detect_and_compute(t1, t2)
            mkpts0 = out["keypoints0"].cpu().numpy() if "keypoints0" in out else np.zeros((0,2))
            mkpts1 = out["keypoints1"].cpu().numpy() if "keypoints1" in out else np.zeros((0,2))
            n_matches = len(mkpts0)
            conf = out["confidence"].cpu().numpy() if "confidence" in out else np.ones(len(mkpts0))
            if n_matches < 350:
                msg = f"{os.path.basename(img1)} - {os.path.basename(img2)} LoFTR : {n_matches} matches < 350, ignoré"
                log(msg, logf)
                continue
            if n_matches >= 8:
                F, mask = cv2.findFundamentalMat(mkpts0, mkpts1, cv2.FM_RANSAC, 1.0, 0.999)
                inlier_mask = mask.ravel().astype(bool)
                mkpts0_inl = mkpts0[inlier_mask]
                mkpts1_inl = mkpts1[inlier_mask]
                conf_inl = conf[inlier_mask] if len(conf) == len(mkpts0) else np.ones(len(mkpts0_inl))
            else:
                mkpts0_inl = mkpts0
                mkpts1_inl = mkpts1
                conf_inl = conf if len(conf) == len(mkpts0) else np.ones(len(mkpts0))
            points = []
            for i, (pt0, pt1) in enumerate(zip(mkpts0_inl, mkpts1_inl)):
                x1, y1 = pt0[0]*scale1, pt0[1]*scale1
                x2, y2 = pt1[0]*scale2, pt1[1]*scale2
                score = conf_inl[i] if i < len(conf_inl) else 1.0
                points.append((x1, y1, x2, y2, float(score)))
            if len(points) > nb_points:
                points = select_spatially(points, w1o, h1o, nmax=nb_points, scores=np.array([p[4] for p in points]))
            msg = f"{os.path.basename(img1)} - {os.path.basename(img2)} LoFTR : {n_matches} matches, {len(mkpts0_inl)} inliers, {len(points)} exportés"
            log(msg, logf)
            export_micmac_homol(out_dir, os.path.basename(img1), os.path.basename(img2), points)
            points_inv = [(x2, y2, x1, y1, s) for (x1, y1, x2, y2, s) in points]
            export_micmac_homol(out_dir, os.path.basename(img2), os.path.basename(img1), points_inv)
            stats["pairs_done"] += 1
            stats["total_matches"] += len(points)
            stats["per_pair"].append({"img1": img1, "img2": img2, "matches": len(points)})
        else:
            points = []
        export_micmac_homol(out_dir, os.path.basename(img1), os.path.basename(img2), points)
        points_inv = [(x2, y2, x1, y1, s) for (x1, y1, x2, y2, s) in points]
        export_micmac_homol(out_dir, os.path.basename(img2), os.path.basename(img1), points_inv)
        stats["pairs_done"] += 1
        stats["total_matches"] += len(points)
        stats["per_pair"].append({"img1": img1, "img2": img2, "matches": len(points)})
    t1 = time.time()
    stats["elapsed_sec"] = t1-t0
    # Mesure RAM max
    if psutil_available:
        process = psutil.Process()
        mem_info = process.memory_info()
        ram_max_mb = mem_info.rss / 1024 / 1024
        stats["ram_max_mb"] = ram_max_mb
    else:
        stats["ram_max_mb"] = None
    # Calcul du vrai total matches exportés
    total_matches = 0
    for img1 in final_points:
        for img2 in final_points[img1]:
            total_matches += len(final_points[img1][img2])
    stats["total_matches"] = total_matches
    # Indicateurs de performance
    stats["nb_images"] = len(images)
    stats["nb_paires"] = len(pairs)
    stats["time_per_pair"] = stats["elapsed_sec"] / stats["nb_paires"] if stats["nb_paires"] else 0
    stats["pairs_per_sec"] = stats["nb_paires"] / stats["elapsed_sec"] if stats["elapsed_sec"] else 0
    log(f"--- Fin pipeline ---", logf)
    log(f"Temps total : {stats['elapsed_sec']:.1f} sec", logf)
    log(f"Nombre d'images : {stats['nb_images']}", logf)
    log(f"Nombre de paires : {stats['nb_paires']}", logf)
    log(f"Total matches exportés : {stats['total_matches']}", logf)
    log(f"Temps moyen par paire : {stats['time_per_pair']:.3f} sec", logf)
    log(f"Paires/sec : {stats['pairs_per_sec']:.2f}", logf)
    if stats["ram_max_mb"] is not None:
        log(f"RAM max utilisée : {stats['ram_max_mb']:.1f} Mo", logf)
    else:
        log(f"RAM max : psutil non disponible", logf)
    logf.close()
    write_run_log(stats, pattern, detect, size, clahe, sift_nfeatures, nb_points, n_jobs)
    click.echo(f"Terminé. Résultats dans {out_dir}/")

@cli.command()
@click.argument('pattern')
@common_options
@click.option('--delta', type=int, default=1, help='Nombre de voisins à considérer (défaut 1)')
@click.option('--circ', is_flag=True, default=False, help='Activer le mode circulaire (matcher les premières et dernières images)')
def line(pattern, size, detect, clahe, sift_nfeatures, nb_points, n_jobs, test, delta, circ):
    """Calcul restreint aux paires voisines (structure linéaire ou circulaire)."""
    import time
    from homolcraft.utils import find_images
    from homolcraft.core.detectors import SIFTDetector, LoFTRDetector
    from homolcraft.core.matchers import match_sift
    from homolcraft.core.io import read_image
    from homolcraft.core.export import export_micmac_homol
    import os
    from tqdm import tqdm
    import torch
    import cv2
    import numpy as np
    from datetime import datetime
    import shutil
    import concurrent.futures
    import json

    def log(msg, logf=None):
        ts = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        line = f"{ts} {msg}"
        print(line)
        if logf:
            print(line, file=logf)
            logf.flush()

    t0 = time.time()
    images = find_images(pattern)
    if len(images) < 2:
        click.echo("Moins de 2 images trouvées.")
        return
    N = len(images)
    pairs = line_pairs(images, delta=delta, circ=circ)
    img_dir = os.path.dirname(os.path.abspath(images[0]))
    out_dir = os.path.join(img_dir, "Homol")
    # Sauvegarde Homol existant
    if os.path.exists(out_dir):
        bkp_dir = out_dir + "_bkp"
        if os.path.exists(bkp_dir):
            shutil.rmtree(bkp_dir)
        shutil.move(out_dir, bkp_dir)
    os.makedirs(out_dir, exist_ok=True)

    log_path = os.path.join(out_dir, "log.txt")
    logf = open(log_path, "w")
    log(f"--- Lancement pipeline (mode LINE) ---", logf)
    log(f"Version algo : {ALGO_VERSION}", logf)
    log(f"Pattern utilisé : {pattern}", logf)
    log(f"Détecteur : {detect}", logf)
    log(f"Taille demandée : {size}", logf)
    log(f"CLAHE : {clahe}", logf)
    log(f"Delta : {delta}", logf)
    log(f"Circulaire : {circ}", logf)
    if detect == "sift":
        log(f"SIFT nfeatures : {sift_nfeatures}", logf)
    log(f"Nombre d'images : {len(images)}", logf)
    log(f"Nombre de paires : {len(pairs)}", logf)
    log(f"Parallélisation : {n_jobs} processus", logf)

    # Pipeline identique au mode all, mais sur la liste pairs
    stats = {"total_pairs": len(pairs), "pairs_done": 0, "total_matches": 0, "per_pair": []}
    detection_t0 = detection_t1 = 0.0
    detection_t0 = time.time()
    if detect == "sift":
        detector = SIFTDetector(nfeatures=sift_nfeatures)
        def sift_worker(img):
            im = read_image(img, size, clahe=clahe)
            kps, desc = detector.detect_and_compute(im)
            return (img, (kps, desc, im.shape))
        sift_data = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_jobs) as executor:
            for img, res in tqdm(executor.map(sift_worker, images), total=len(images), desc="SIFT détecteurs"):
                sift_data[img] = res
        # Stockage temporaire des matches
        tmp_dir = os.path.join(img_dir, "tmp_homolcraft")
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        os.makedirs(tmp_dir, exist_ok=True)
        matches_per_pair = {}
        def match_worker(pair):
            img1, img2 = pair
            kps1, desc1, shape1 = sift_data[img1]
            kps2, desc2, shape2 = sift_data[img2]
            orig1 = cv2.imread(img1, cv2.IMREAD_COLOR)
            orig2 = cv2.imread(img2, cv2.IMREAD_COLOR)
            h1o, w1o = orig1.shape[:2]
            h2o, w2o = orig2.shape[:2]
            h1, w1 = shape1[:2]
            h2, w2 = shape2[:2]
            scale1 = w1o / w1
            scale2 = w2o / w2
            if desc1 is None or desc2 is None:
                return (pair, [])
            matches = match_sift(desc1, desc2)
            if len(matches) < 30:
                return (pair, [])
            pts1 = np.float32([kps1[m.queryIdx].pt for m in matches])
            pts2 = np.float32([kps2[m.trainIdx].pt for m in matches])
            if len(pts1) >= 8:
                F, mask = cv2.findFundamentalMat(pts1, pts2, cv2.FM_RANSAC, 2.0, 0.99)
                inlier_matches = [m for m, inl in zip(matches, mask.ravel()) if inl]
            else:
                inlier_matches = matches
            points = []
            points_inv = []
            for m in inlier_matches:
                pt1 = kps1[m.queryIdx].pt
                pt2 = kps2[m.trainIdx].pt
                x1, y1 = pt1[0]*scale1, pt1[1]*scale1
                x2, y2 = pt2[0]*scale2, pt2[1]*scale2
                points.append((x1, y1, x2, y2, 1.0, m.queryIdx, m.trainIdx))
                points_inv.append((x2, y2, x1, y1, 1.0, m.trainIdx, m.queryIdx))
            # Sauvegarde temporaire dans les deux sens
            d1 = os.path.join(tmp_dir, f"Pastis{os.path.basename(img1)}")
            os.makedirs(d1, exist_ok=True)
            out_path = os.path.join(d1, f"{os.path.basename(img2)}.npy")
            np.save(out_path, np.array(points))
            d2 = os.path.join(tmp_dir, f"Pastis{os.path.basename(img2)}")
            os.makedirs(d2, exist_ok=True)
            out_path_inv = os.path.join(d2, f"{os.path.basename(img1)}.npy")
            np.save(out_path_inv, np.array(points_inv))
            return (pair, points)
        # Parallélisation du matching
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_jobs) as executor:
            results = list(tqdm(executor.map(match_worker, pairs), total=len(pairs), desc="SIFT matches brut"))
        for (img1, img2), points in results:
            if points:
                matches_per_pair[(img1, img2)] = points
                matches_per_pair[(img2, img1)] = [(x2, y2, x1, y1, s, idx2, idx1) for (x1, y1, x2, y2, s, idx1, idx2) in points]
        # Indexation des tie points par image
        from collections import defaultdict
        point_index = defaultdict(lambda: defaultdict(list))  # img -> (x,y arrondi) -> [(autre_img, x2, y2)]
        for (img1, img2), points in matches_per_pair.items():
            for x1, y1, x2, y2, s, idx1, idx2 in points:
                key1 = (round(x1,1), round(y1,1))  # tolérance 0.1 pixel
                key2 = (round(x2,1), round(y2,1))
                point_index[img1][key1].append((img2, x2, y2))
                point_index[img2][key2].append((img1, x1, y1))
        # --- Nouvelle sélection par paire ---
        from collections import defaultdict
        final_points = defaultdict(lambda: defaultdict(list))  # img -> img2 -> [x1, y1, x2, y2, 1.0]
        for img1, img2 in tqdm(pairs, desc="Sélection spatiale par paire"):
            key_img2 = os.path.basename(img2)
            triples_pts = []
            doubles_pts = []
            for (x, y), lst in point_index[img1].items():
                imgset = set([img2b for img2b, _, _ in lst])
                for img2b, x2, y2 in lst:
                    if os.path.basename(img2b) == key_img2:
                        if len(imgset) >= 3:
                            triples_pts.append((x, y, x2, y2, 1.0))
                        elif len(imgset) == 2:
                            doubles_pts.append((x, y, x2, y2, 1.0))
            all_pts = triples_pts.copy()
            if len(all_pts) < nb_points:
                all_pts += doubles_pts[:nb_points-len(all_pts)]
            orig = cv2.imread(img1, cv2.IMREAD_COLOR)
            h1o, w1o = orig.shape[:2]
            if len(all_pts) > nb_points:
                all_pts = select_spatially(all_pts, w1o, h1o, nmax=nb_points)
            final_points[img1][key_img2] = all_pts
        detection_t1 = time.time()
        log(f"[STATS] Détection SIFT : {detection_t1-detection_t0:.1f} sec", logf)
        matching_t0 = time.time()
        # --- Boucle d'écriture finale Homol (symétrique Micmac, uniquement pour les vrais voisins) ---
        for img1, img2 in pairs:
            key1 = os.path.basename(img1)
            key2 = os.path.basename(img2)
            pts = final_points[img1][key2] if key2 in final_points[img1] else []
            if pts:
                # Ecriture img1 -> img2
                d1 = os.path.join(out_dir, f"Pastis{key1}")
                os.makedirs(d1, exist_ok=True)
                out_path = os.path.join(d1, f"{key2}.txt")
                with open(out_path, 'w') as f:
                    for pt in pts:
                        f.write(f"{pt[0]:.6f} {pt[1]:.6f} {pt[2]:.6f} {pt[3]:.6f} {pt[4]:.6f}\n")
                # Ecriture img2 -> img1 (symétrique)
                d2 = os.path.join(out_dir, f"Pastis{key2}")
                os.makedirs(d2, exist_ok=True)
                out_path_inv = os.path.join(d2, f"{key1}.txt")
                with open(out_path_inv, 'w') as f:
                    for pt in pts:
                        f.write(f"{pt[2]:.6f} {pt[3]:.6f} {pt[0]:.6f} {pt[1]:.6f} {pt[4]:.6f}\n")
        matching_t1 = time.time()
        log(f"[STATS] Matching SIFT : {matching_t1-matching_t0:.1f} sec", logf)
        selection_t0 = time.time()
        for img1, img2 in tqdm(pairs, desc="Sélection spatiale par paire"):
            final_points[img1][key_img2] = all_pts
        selection_t1 = time.time()
        log(f"[STATS] Sélection spatiale : {selection_t1-selection_t0:.1f} sec", logf)
        ecriture_t0 = time.time()
        ecriture_t1 = time.time()
        log(f"[STATS] Ecriture Homol : {ecriture_t1-ecriture_t0:.1f} sec", logf)
        print("[CHECKPOINT] Fin de la boucle d'écriture finale Homol")
        print(f"[tmp_homolcraft] Dossier temporaire conservé ici : {tmp_dir}")
        # Suppression du dossier temporaire à la fin
        if os.path.exists(tmp_dir):
            import shutil
            shutil.rmtree(tmp_dir)
        if test:
            out = {"images": images, "pairs": [(os.path.basename(a), os.path.basename(b)) for a, b in pairs]}
            with open("homolcraft_test_pairs.json", "w") as f:
                json.dump(out, f, indent=2)
            click.echo(f"[TEST] Dry-run : {len(pairs)} paires générées. Voir homolcraft_test_pairs.json.")
            return
        return finalize(stats, out_dir, t0, pattern, size, detect, clahe, sift_nfeatures, nb_points, n_jobs, logf, log)
    elif detect == "loftr":
        detector = LoFTRDetector(device="cpu")
    else:
        click.echo(f"Détecteur inconnu : {detect}")
        logf.close()
        return

    stats = {"total_pairs": len(pairs), "pairs_done": 0, "total_matches": 0, "per_pair": []}
    pbar = tqdm(pairs, desc="Paires")
    for img1, img2 in pbar:
        if detect == "sift":
            kps1, desc1, shape1 = sift_data[img1]
            kps2, desc2, shape2 = sift_data[img2]
            orig1 = cv2.imread(img1, cv2.IMREAD_COLOR)
            orig2 = cv2.imread(img2, cv2.IMREAD_COLOR)
            h1o, w1o = orig1.shape[:2]
            h2o, w2o = orig2.shape[:2]
            h1, w1 = shape1[:2]
            h2, w2 = shape2[:2]
            scale1 = w1o / w1
            scale2 = w2o / w2
            if desc1 is None or desc2 is None:
                continue
            matches = match_sift(desc1, desc2)
            if len(matches) < 30:
                msg = f"{os.path.basename(img1)} - {os.path.basename(img2)} SIFT : {len(matches)} matches < 30, ignoré"
                log(msg, logf)
                continue
            pts1 = np.float32([kps1[m.queryIdx].pt for m in matches])
            pts2 = np.float32([kps2[m.trainIdx].pt for m in matches])
            if len(pts1) >= 8:
                F, mask = cv2.findFundamentalMat(pts1, pts2, cv2.FM_RANSAC, 2.0, 0.99)
                inlier_matches = [m for m, inl in zip(matches, mask.ravel()) if inl]
            else:
                inlier_matches = matches
            points = []
            for m in inlier_matches:
                pt1 = kps1[m.queryIdx].pt
                pt2 = kps2[m.trainIdx].pt
                x1, y1 = pt1[0]*scale1, pt1[1]*scale1
                x2, y2 = pt2[0]*scale2, pt2[1]*scale2
                points.append((x1, y1, x2, y2, 1.0))
            if len(points) > nb_points:
                points = select_spatially(points, w1o, h1o, nmax=nb_points)
            msg = f"{os.path.basename(img1)} - {os.path.basename(img2)} SIFT : {len(matches)} matches, {len(inlier_matches)} inliers, {len(points)} exportés"
            log(msg, logf)
        elif detect == "loftr":
            im1 = read_image(img1, size, clahe=clahe)
            im2 = read_image(img2, size, clahe=clahe)
            orig1 = cv2.imread(img1, cv2.IMREAD_COLOR)
            orig2 = cv2.imread(img2, cv2.IMREAD_COLOR)
            h1o, w1o = orig1.shape[:2]
            h2o, w2o = orig2.shape[:2]
            h1, w1 = im1.shape[:2]
            h2, w2 = im2.shape[:2]
            scale1 = w1o / w1
            scale2 = w2o / w2
            def to_tensor(img):
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                t = torch.from_numpy(gray).float() / 255.0
                t = t.unsqueeze(0).unsqueeze(0)
                return t
            t1 = to_tensor(im1)
            t2 = to_tensor(im2)
            out = detector.detect_and_compute(t1, t2)
            mkpts0 = out["keypoints0"].cpu().numpy() if "keypoints0" in out else np.zeros((0,2))
            mkpts1 = out["keypoints1"].cpu().numpy() if "keypoints1" in out else np.zeros((0,2))
            n_matches = len(mkpts0)
            conf = out["confidence"].cpu().numpy() if "confidence" in out else np.ones(len(mkpts0))
            if n_matches < 350:
                msg = f"{os.path.basename(img1)} - {os.path.basename(img2)} LoFTR : {n_matches} matches < 350, ignoré"
                log(msg, logf)
                continue
            if n_matches >= 8:
                F, mask = cv2.findFundamentalMat(mkpts0, mkpts1, cv2.FM_RANSAC, 1.0, 0.999)
                inlier_mask = mask.ravel().astype(bool)
                mkpts0_inl = mkpts0[inlier_mask]
                mkpts1_inl = mkpts1[inlier_mask]
                conf_inl = conf[inlier_mask] if len(conf) == len(mkpts0) else np.ones(len(mkpts0_inl))
            else:
                mkpts0_inl = mkpts0
                mkpts1_inl = mkpts1
                conf_inl = conf if len(conf) == len(mkpts0) else np.ones(len(mkpts0))
            points = []
            for i, (pt0, pt1) in enumerate(zip(mkpts0_inl, mkpts1_inl)):
                x1, y1 = pt0[0]*scale1, pt0[1]*scale1
                x2, y2 = pt1[0]*scale2, pt1[1]*scale2
                score = conf_inl[i] if i < len(conf_inl) else 1.0
                points.append((x1, y1, x2, y2, float(score)))
            if len(points) > nb_points:
                points = select_spatially(points, w1o, h1o, nmax=nb_points, scores=np.array([p[4] for p in points]))
            msg = f"{os.path.basename(img1)} - {os.path.basename(img2)} LoFTR : {n_matches} matches, {len(mkpts0_inl)} inliers, {len(points)} exportés"
            log(msg, logf)
            export_micmac_homol(out_dir, os.path.basename(img1), os.path.basename(img2), points)
            points_inv = [(x2, y2, x1, y1, s) for (x1, y1, x2, y2, s) in points]
            export_micmac_homol(out_dir, os.path.basename(img2), os.path.basename(img1), points_inv)
            stats["pairs_done"] += 1
            stats["total_matches"] += len(points)
            stats["per_pair"].append({"img1": img1, "img2": img2, "matches": len(points)})
        else:
            points = []
        export_micmac_homol(out_dir, os.path.basename(img1), os.path.basename(img2), points)
        points_inv = [(x2, y2, x1, y1, s) for (x1, y1, x2, y2, s) in points]
        export_micmac_homol(out_dir, os.path.basename(img2), os.path.basename(img1), points_inv)
        stats["pairs_done"] += 1
        stats["total_matches"] += len(points)
        stats["per_pair"].append({"img1": img1, "img2": img2, "matches": len(points)})
    t1 = time.time()
    stats["elapsed_sec"] = t1-t0
    stats["params"] = {"pattern": pattern, "size": size, "detect": detect, "clahe": clahe, "sift_nfeatures": sift_nfeatures, "delta": delta, "circ": circ}
    stats["datetime"] = datetime.now().isoformat()
    log(f"--- Fin pipeline ---", logf)
    log(f"Temps total : {stats['elapsed_sec']:.1f} sec", logf)
    log(f"Total paires traitées : {stats['pairs_done']}", logf)
    log(f"Total matches : {stats['total_matches']}", logf)
    logf.close()
    write_run_log(stats, pattern, detect, size, clahe, sift_nfeatures, nb_points, n_jobs, delta, circ)
    click.echo(f"Terminé. Résultats dans {out_dir}/")

@cli.command()
@click.argument('pattern')
@click.option('--size-low', type=int)
@click.option('--size', type=int)
@click.option('--nb-min-pt', type=int, default=5)
def mulscale(pattern, size_low, size, nb_min_pt):
    """Approche multirésolution."""
    click.echo(f"Mode MULSCALE | Pattern: {pattern} | Size low: {size_low} | Size: {size} | Nb min pt: {nb_min_pt}")
    # TODO: Appeler la logique core

@cli.command()
@click.argument('file')
@click.option('--size', type=int)
def file(file, size):
    """Calcul sur des paires listées dans un fichier."""
    click.echo(f"Mode FILE | Fichier: {file} | Size: {size}")
    # TODO: Appeler la logique core

def select_spatially(points, w, h, nmax=200, scores=None):
    """
    Sélectionne jusqu'à nmax points bien répartis sur l'image (grille spatiale),
    en gardant les meilleurs par score si fourni.
    """
    grid_size = int(np.sqrt(nmax))
    grid = [[[] for _ in range(grid_size)] for _ in range(grid_size)]
    for i, pt in enumerate(points):
        x, y = pt[0], pt[1]
        gx = min(int(x / w * grid_size), grid_size-1)
        gy = min(int(y / h * grid_size), grid_size-1)
        grid[gy][gx].append((i, pt))
    selected = []
    for row in grid:
        for cell in row:
            if not cell:
                continue
            if scores is not None:
                cell = sorted(cell, key=lambda x: -scores[x[0]])
            selected.append(cell[0][1])
    if len(selected) < nmax:
        rest = [pt for i, pt in enumerate(points) if pt not in selected]
        selected += rest[:nmax-len(selected)]
    return selected[:nmax]

def finalize(stats, out_dir, t0, pattern, size, detect, clahe, sift_nfeatures, nb_points, n_jobs, logf, log):
    from datetime import datetime
    import json
    import time
    t1 = time.time()
    stats["elapsed_sec"] = t1-t0
    stats["params"] = {"pattern": pattern, "size": size, "detect": detect, "clahe": clahe, "sift_nfeatures": sift_nfeatures, "nb_points": nb_points, "n_jobs": n_jobs}
    stats["datetime"] = datetime.now().isoformat()
    log(f"--- Fin pipeline ---", logf)
    log(f"Temps total : {stats['elapsed_sec']:.1f} sec", logf)
    log(f"Total paires traitées : {stats['pairs_done']}", logf)
    log(f"Total matches : {stats['total_matches']}", logf)
    logf.close()
    write_run_log(stats, pattern, detect, size, clahe, sift_nfeatures, nb_points, n_jobs)
    click.echo(f"Terminé. Résultats dans {out_dir}/")

def all_pairs(images):
    """Retourne toutes les paires possibles d'images (img1, img2) avec img1 != img2."""
    from itertools import combinations
    return list(combinations(images, 2))

def line_pairs(images, delta=1, circ=False):
    """Retourne les paires voisines (avant/après, delta, circ)."""
    N = len(images)
    pairs_done = set()
    pairs = []
    for i, img1 in enumerate(images):
        for d in range(1, delta+1):
            # Voisin aval
            j_plus = (i + d) % N if circ else i + d
            if (circ or j_plus < N) and j_plus != i:
                key = tuple(sorted((i, j_plus)))
                if key not in pairs_done:
                    pairs.append((img1, images[j_plus]))
                    pairs_done.add(key)
            # Voisin amont
            j_minus = (i - d) % N if circ else i - d
            if (circ or j_minus >= 0) and j_minus != i:
                key = tuple(sorted((i, j_minus)))
                if key not in pairs_done:
                    pairs.append((img1, images[j_minus]))
                    pairs_done.add(key)
    return pairs

def write_log_header(f, pattern, detect, size, clahe, sift_nfeatures, nb_points, n_jobs, delta=None, circ=None):
    from datetime import datetime
    f.write(f"[HomolCraft - Version : {ALGO_VERSION}] ")
    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]
")
    f.write(f"  Pattern : {pattern}\n  Detecteur : {detect}\n  Taille : {size}\n  CLAHE : {clahe}\n  SIFT nfeatures : {sift_nfeatures if detect=='sift' else '-'}\n")
    f.write(f"  Nb points : {nb_points}\n  n_jobs : {n_jobs}\n")
    if delta is not None:
        f.write(f"  Delta : {delta}\n")
    if circ is not None:
        f.write(f"  Circulaire : {circ}\n")

def write_run_log(stats, pattern, detect, size, clahe, sift_nfeatures, nb_points, n_jobs, delta=None, circ=None):
    from datetime import datetime
    with open("homolcraft_run_log.txt", "a") as f:
        write_log_header(f, pattern, detect, size, clahe, sift_nfeatures, nb_points, n_jobs, delta, circ)
        f.write(f"  Nb images : {stats.get('nb_images','?')}\n  Nb paires : {stats.get('nb_paires','?')}\n  Nb paires exportées : {stats.get('nb_paires_exportees','?')}\n")
        f.write(f"  Temps total : {stats.get('elapsed_sec',0):.1f} sec\n")
        f.write(f"  Total matches exportés : {stats.get('total_matches','?')}\n")
        f.write(f"  Temps moyen par paire : {stats.get('time_per_pair',0):.3f} sec\n")
        f.write(f"  Paires/sec : {stats.get('pairs_per_sec',0):.2f}\n")
        if stats.get("ram_max_mb") is not None:
            f.write(f"  RAM max utilisée : {stats.get('ram_max_mb',0):.1f} Mo\n")
        else:
            f.write(f"  RAM max : psutil/resource non disponible\n")
        f.write("\n")

def compute_stats(images, pairs, final_points, t0, t1, ram_max_mb=None):
    """Calcule toutes les stats de run pour le logging et le reporting."""
    stats = {}
    stats["elapsed_sec"] = t1 - t0
    stats["nb_images"] = len(images)
    stats["nb_paires"] = len(pairs)
    stats["nb_paires_exportees"] = len(pairs)
    # Total matches exportés (somme sur toutes les paires)
    total_matches = 0
    for img1 in final_points:
        for img2 in final_points[img1]:
            total_matches += len(final_points[img1][img2])
    stats["total_matches"] = total_matches
    stats["time_per_pair"] = stats["elapsed_sec"] / stats["nb_paires"] if stats["nb_paires"] else 0
    stats["pairs_per_sec"] = stats["nb_paires"] / stats["elapsed_sec"] if stats["elapsed_sec"] else 0
    stats["ram_max_mb"] = ram_max_mb
    return stats

def get_ram_max_mb():
    try:
        import psutil
        process = psutil.Process()
        mem_info = process.memory_info()
        return mem_info.rss / 1024 / 1024
    except ImportError:
        try:
            import resource
            ram = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # Sur macOS/Linux, ru_maxrss est en Ko ou en octets selon la plateforme
            if ram > 10**7:  # probablement octets
                return ram / 1024 / 1024
            else:  # probablement Ko
                return ram / 1024
        except ImportError:
            return None

if __name__ == '__main__':
    cli() 