import numpy as np
import os

tmp_dir = "tests/tmp_homolcraft/PastisPXL_20250416_071451624.jpg"
for fname in sorted(os.listdir(tmp_dir)):
    if fname.endswith(".npy"):
        arr = np.load(os.path.join(tmp_dir, fname))
        print(f"{fname}: {arr.shape[0]} tie points")
        if arr.shape[0] > 0:
            print("  Exemple:", arr[0])