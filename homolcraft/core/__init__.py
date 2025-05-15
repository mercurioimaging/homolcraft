from typing import Dict, Any

# Global dictionary to store image processing information
# Key: image_path (str)
# Value: {"original_shape": (h_orig, w_orig), "scale_factor": scale, "resized_shape": (h_resized, w_resized)}
IMAGE_PROCESSING_INFO: Dict[str, Dict[str, Any]] = {} 