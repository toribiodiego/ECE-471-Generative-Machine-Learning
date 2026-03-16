"""Unit tests for media_processing module."""

import numpy as np
from PIL import Image

from src.utils.media_processing import (
    encode_image_from_array,
    get_blank_image,
    resize_frame,
)


class TestEncodeImageFromArray:
    """Tests for encode_image_from_array function."""

    def test_encode_rgb_image(self):
        """Test encoding a simple RGB image to JPEG."""
        # Create a 100x100 red image
        arr = np.zeros((100, 100, 3), dtype=np.uint8)
        arr[:, :, 0] = 255  # Red channel

        result = encode_image_from_array(arr)

        assert "mime_type" in result
        assert result["mime_type"] == "image/jpeg"
        assert "data" in result
        assert isinstance(result["data"], bytes)
        assert len(result["data"]) > 0

    def test_encode_different_dimensions(self):
        """Test encoding images of different sizes."""
        for h, w in [(480, 640), (720, 1280), (100, 100)]:
            arr = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
            result = encode_image_from_array(arr)

            assert result["mime_type"] == "image/jpeg"
            assert len(result["data"]) > 0

    def test_encode_blank_image(self):
        """Test encoding a blank (all zeros) image."""
        arr = np.zeros((480, 640, 3), dtype=np.uint8)
        result = encode_image_from_array(arr)

        assert result["mime_type"] == "image/jpeg"
        assert len(result["data"]) > 0

    def test_encode_preserves_data_format(self):
        """Test that encoded data is valid JPEG."""
        arr = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        result = encode_image_from_array(arr)

        # JPEG files start with FF D8 FF
        assert result["data"][:3] == b'\xff\xd8\xff'


class TestGetBlankImage:
    """Tests for get_blank_image function."""

    def test_get_blank_image_default_dimensions(self):
        """Test creating blank image with default dimensions."""
        img = get_blank_image()

        assert isinstance(img, Image.Image)
        assert img.size == (640, 480)  # PIL uses (width, height)
        assert img.mode == "RGB"

    def test_get_blank_image_custom_dimensions(self):
        """Test creating blank image with custom dimensions."""
        img = get_blank_image([720, 1280, 3])

        assert isinstance(img, Image.Image)
        assert img.size == (1280, 720)
        assert img.mode == "RGB"

    def test_get_blank_image_is_black(self):
        """Test that blank image is all black (zeros)."""
        img = get_blank_image([100, 100, 3])
        arr = np.array(img)

        assert np.all(arr == 0)

    def test_get_blank_image_different_sizes(self):
        """Test creating blank images of various sizes."""
        for h, w in [(480, 640), (720, 1280), (200, 300)]:
            img = get_blank_image([h, w, 3])
            assert img.size == (w, h)


class TestResizeFrame:
    """Tests for resize_frame function."""

    def test_resize_frame_large_image(self):
        """Test resizing a large image to fit within max size."""
        img = Image.new('RGB', (2048, 1536))
        result = resize_frame(img, (1024, 1024))

        assert result is img  # Should modify in-place
        assert img.size[0] <= 1024
        assert img.size[1] <= 1024

    def test_resize_frame_preserves_aspect_ratio(self):
        """Test that resizing preserves aspect ratio."""
        # Create 2:1 aspect ratio image
        img = Image.new('RGB', (2000, 1000))
        original_ratio = img.size[0] / img.size[1]

        resize_frame(img, (1024, 1024))

        new_ratio = img.size[0] / img.size[1]
        assert abs(original_ratio - new_ratio) < 0.01  # Allow small floating point error

    def test_resize_frame_already_small(self):
        """Test that images smaller than max size are not upscaled."""
        img = Image.new('RGB', (640, 480))
        original_size = img.size

        resize_frame(img, (1024, 1024))

        # PIL thumbnail doesn't upscale, so size should remain the same
        assert img.size == original_size

    def test_resize_frame_exact_width(self):
        """Test resizing when width exactly matches max width."""
        img = Image.new('RGB', (1024, 500))
        resize_frame(img, (1024, 1024))

        assert img.size[0] <= 1024
        assert img.size[1] <= 1024

    def test_resize_frame_exact_height(self):
        """Test resizing when height exactly matches max height."""
        img = Image.new('RGB', (500, 1024))
        resize_frame(img, (1024, 1024))

        assert img.size[0] <= 1024
        assert img.size[1] <= 1024

    def test_resize_frame_tall_image(self):
        """Test resizing a tall (portrait) image."""
        img = Image.new('RGB', (800, 2000))
        resize_frame(img, (1024, 1024))

        assert img.size[0] <= 1024
        assert img.size[1] <= 1024
        # Height should be the limiting factor
        assert img.size[1] == 1024

    def test_resize_frame_wide_image(self):
        """Test resizing a wide (landscape) image."""
        img = Image.new('RGB', (2000, 800))
        resize_frame(img, (1024, 1024))

        assert img.size[0] <= 1024
        assert img.size[1] <= 1024
        # Width should be the limiting factor
        assert img.size[0] == 1024


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_encode_blank_image(self):
        """Test encoding a blank image generated by get_blank_image."""
        blank = get_blank_image([480, 640, 3])
        arr = np.array(blank)
        result = encode_image_from_array(arr)

        assert result["mime_type"] == "image/jpeg"
        assert len(result["data"]) > 0

    def test_resize_then_encode(self):
        """Test resizing an image and then encoding it."""
        img = Image.new('RGB', (2048, 1536), color=(255, 0, 0))
        resize_frame(img, (1024, 1024))
        arr = np.array(img)
        result = encode_image_from_array(arr)

        assert result["mime_type"] == "image/jpeg"
        assert len(result["data"]) > 0
        assert arr.shape[0] <= 1024
        assert arr.shape[1] <= 1024
