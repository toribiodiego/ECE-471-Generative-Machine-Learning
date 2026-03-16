"""Media processing utilities for image and audio handling.

This module provides functions for encoding images, generating placeholders,
and resizing video frames for the Agnus application.
"""

from io import BytesIO
from typing import Dict, List, Tuple, Any

import numpy as np
from PIL import Image


def encode_image_from_array(arr: np.ndarray) -> Dict[str, Any]:
    """Convert a numpy array to a JPEG-encoded blob.

    Takes a numpy array representing an image and encodes it as a JPEG
    in memory, returning a dictionary with MIME type and binary data
    suitable for streaming to the Gemini API.

    Args:
        arr: Numpy array representing an image (height, width, channels).
             Expected to be in RGB format with dtype uint8.

    Returns:
        Dictionary with keys:
            - mime_type: String "image/jpeg"
            - data: Bytes containing the JPEG-encoded image

    Example:
        >>> import numpy as np
        >>> frame = np.zeros((480, 640, 3), dtype=np.uint8)
        >>> blob = encode_image_from_array(frame)
        >>> blob['mime_type']
        'image/jpeg'
    """
    with BytesIO() as out:
        Image.fromarray(arr).save(out, "JPEG")
        return {"mime_type": "image/jpeg", "data": out.getvalue()}


def get_blank_image(dimensions: List[int] = None) -> Image.Image:
    """Generate a blank (black) image as a placeholder.

    Creates a PIL Image filled with zeros (black pixels) with the
    specified dimensions. Useful as a placeholder when no camera
    frame is available.

    Args:
        dimensions: List [height, width, channels] for the image.
                   Defaults to [480, 640, 3] if not provided.

    Returns:
        PIL Image object containing a black image.

    Example:
        >>> blank = get_blank_image([480, 640, 3])
        >>> blank.size
        (640, 480)
    """
    if dimensions is None:
        dimensions = [480, 640, 3]

    h, w, channels = dimensions
    arr = np.zeros((h, w, channels), dtype=np.uint8)
    return Image.fromarray(arr)


def resize_frame(frame: Image.Image, max_size: Tuple[int, int]) -> Image.Image:
    """Resize a frame to fit within maximum dimensions while preserving aspect ratio.

    Uses PIL's thumbnail method to resize the image in-place to fit within
    the specified maximum width and height, maintaining the original aspect
    ratio.

    Args:
        frame: PIL Image to resize.
        max_size: Tuple (max_width, max_height) for the thumbnail.

    Returns:
        The same PIL Image object, resized in-place.

    Example:
        >>> from PIL import Image
        >>> img = Image.new('RGB', (2048, 1536))
        >>> resized = resize_frame(img, (1024, 1024))
        >>> resized.size[0] <= 1024 and resized.size[1] <= 1024
        True
    """
    frame.thumbnail(max_size)
    return frame
