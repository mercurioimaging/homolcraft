import glob

def find_images(pattern):
    return sorted(glob.glob(pattern)) 