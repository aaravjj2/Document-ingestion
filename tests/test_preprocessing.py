"""Tests for image preprocessing service."""

import numpy as np
import pytest

from src.services.preprocessing import ImagePreprocessor


class TestImagePreprocessor:
    """Tests for ImagePreprocessor class."""

    @pytest.fixture
    def preprocessor(self):
        """Create preprocessor instance."""
        return ImagePreprocessor()

    @pytest.fixture
    def sample_color_image(self):
        """Create a sample color image."""
        # Create 100x100 BGR image with some variation
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:50, :, 0] = 255  # Blue in top half
        img[50:, :, 2] = 255  # Red in bottom half
        return img

    @pytest.fixture
    def sample_grayscale_image(self):
        """Create a sample grayscale image."""
        return np.random.randint(0, 255, (100, 100), dtype=np.uint8)

    def test_to_grayscale_from_color(self, preprocessor, sample_color_image):
        """Test grayscale conversion from color image."""
        result = preprocessor.to_grayscale(sample_color_image)
        
        assert len(result.shape) == 2  # Should be 2D
        assert result.shape == (100, 100)

    def test_to_grayscale_already_gray(self, preprocessor, sample_grayscale_image):
        """Test grayscale conversion on already grayscale image."""
        result = preprocessor.to_grayscale(sample_grayscale_image)
        
        assert result.shape == sample_grayscale_image.shape
        np.testing.assert_array_equal(result, sample_grayscale_image)

    def test_denoise_grayscale(self, preprocessor):
        """Test denoising on grayscale image."""
        # Create noisy image
        noisy = np.random.randint(100, 200, (100, 100), dtype=np.uint8)
        
        result = preprocessor.denoise(noisy)
        
        assert result.shape == noisy.shape
        assert result.dtype == np.uint8

    def test_denoise_color(self, preprocessor, sample_color_image):
        """Test denoising on color image."""
        result = preprocessor.denoise(sample_color_image)
        
        assert result.shape == sample_color_image.shape

    def test_binarize(self, preprocessor, sample_grayscale_image):
        """Test image binarization."""
        result = preprocessor.binarize(sample_grayscale_image)
        
        assert result.shape == sample_grayscale_image.shape
        # Result should only contain 0 or 255
        unique_values = np.unique(result)
        assert all(v in [0, 255] for v in unique_values)

    def test_binarize_from_color(self, preprocessor, sample_color_image):
        """Test binarization handles color image."""
        result = preprocessor.binarize(sample_color_image)
        
        # Should be converted to grayscale first
        assert len(result.shape) == 2

    def test_deskew_straight_image(self, preprocessor):
        """Test deskew on already straight image."""
        # Create image with horizontal lines
        img = np.ones((100, 100), dtype=np.uint8) * 255
        img[30, :] = 0  # Horizontal line
        img[60, :] = 0  # Another horizontal line
        
        result = preprocessor.deskew(img)
        
        # Should return similar image (no significant rotation)
        assert result is not None

    def test_preprocess_full_pipeline(self, preprocessor, sample_color_image):
        """Test full preprocessing pipeline."""
        result = preprocessor.preprocess(
            sample_color_image,
            apply_grayscale=True,
            apply_denoise=True,
            apply_binarize=True,
            apply_deskew=False,  # Skip for simple test
        )
        
        assert result is not None
        assert len(result.shape) == 2  # Should be grayscale

    def test_preprocess_options(self, preprocessor, sample_color_image):
        """Test preprocessing with different options."""
        # Only grayscale
        result = preprocessor.preprocess(
            sample_color_image,
            apply_grayscale=True,
            apply_denoise=False,
            apply_binarize=False,
            apply_deskew=False,
        )
        assert len(result.shape) == 2

    def test_enhance_contrast(self, preprocessor, sample_grayscale_image):
        """Test contrast enhancement."""
        result = preprocessor.enhance_contrast(sample_grayscale_image)
        
        assert result.shape == sample_grayscale_image.shape

    def test_enhance_contrast_color(self, preprocessor, sample_color_image):
        """Test contrast enhancement on color image."""
        result = preprocessor.enhance_contrast(sample_color_image)
        
        assert result.shape == sample_color_image.shape

    def test_load_image_not_found(self, preprocessor):
        """Test loading non-existent image."""
        with pytest.raises(FileNotFoundError):
            preprocessor.load_image("/nonexistent/path/image.png")

    def test_save_and_load_image(self, preprocessor, sample_grayscale_image, temp_dir):
        """Test saving and loading image."""
        file_path = temp_dir / "test_image.png"
        
        # Save
        preprocessor.save_image(sample_grayscale_image, file_path)
        
        assert file_path.exists()
        
        # Load
        loaded = preprocessor.load_image(file_path)
        
        # Note: Some compression may occur
        assert loaded.shape[:2] == sample_grayscale_image.shape
