"""PDF to image conversion utilities."""

import logging
from pathlib import Path
from typing import Generator

import numpy as np
from numpy.typing import NDArray
from pdf2image import convert_from_path
from PIL import Image

logger = logging.getLogger(__name__)


class PDFConverter:
    """Convert PDF documents to images for OCR processing."""

    def __init__(
        self,
        dpi: int = 300,
        output_format: str = "PNG",
        thread_count: int = 4,
    ):
        """
        Initialize PDF converter.
        
        Args:
            dpi: Resolution for PDF rendering (higher = better quality but slower)
            output_format: Output image format (PNG recommended for OCR)
            thread_count: Number of threads for parallel conversion
        """
        self.dpi = dpi
        self.output_format = output_format
        self.thread_count = thread_count

    def convert_to_images(
        self,
        pdf_path: str | Path,
        output_dir: str | Path | None = None,
    ) -> list[NDArray[np.uint8]]:
        """
        Convert all pages of a PDF to images.
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Optional directory to save images
            
        Returns:
            List of images as numpy arrays
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        logger.info(f"Converting PDF: {pdf_path}")

        # Convert PDF to PIL images
        pil_images = convert_from_path(
            pdf_path,
            dpi=self.dpi,
            thread_count=self.thread_count,
            fmt=self.output_format.lower(),
        )

        logger.info(f"Converted {len(pil_images)} pages")

        # Convert to numpy arrays
        images = []
        for i, pil_image in enumerate(pil_images):
            # Convert PIL to numpy array (RGB)
            np_image = np.array(pil_image)
            
            # Convert RGB to BGR for OpenCV compatibility
            if len(np_image.shape) == 3 and np_image.shape[2] == 3:
                np_image = np_image[:, :, ::-1].copy()

            images.append(np_image)

            # Optionally save to disk
            if output_dir:
                output_path = Path(output_dir) / f"page_{i + 1:04d}.{self.output_format.lower()}"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                pil_image.save(str(output_path))
                logger.debug(f"Saved page {i + 1} to {output_path}")

        return images

    def convert_to_images_generator(
        self,
        pdf_path: str | Path,
    ) -> Generator[tuple[int, NDArray[np.uint8]], None, None]:
        """
        Convert PDF to images using a generator (memory efficient for large PDFs).
        
        Args:
            pdf_path: Path to PDF file
            
        Yields:
            Tuple of (page_number, image)
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Use first_page and last_page to process one page at a time
        page_count = self.get_page_count(pdf_path)

        for page_num in range(1, page_count + 1):
            pil_images = convert_from_path(
                pdf_path,
                dpi=self.dpi,
                first_page=page_num,
                last_page=page_num,
                thread_count=self.thread_count,
            )

            if pil_images:
                np_image = np.array(pil_images[0])
                if len(np_image.shape) == 3 and np_image.shape[2] == 3:
                    np_image = np_image[:, :, ::-1].copy()
                yield page_num, np_image

    def get_page_count(self, pdf_path: str | Path) -> int:
        """
        Get the number of pages in a PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Number of pages
        """
        from pypdf import PdfReader
        
        reader = PdfReader(str(pdf_path))
        return len(reader.pages)

    def extract_text_layer(self, pdf_path: str | Path) -> str | None:
        """
        Extract existing text layer from PDF (if any).
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text or None if no text layer
        """
        from pypdf import PdfReader
        
        reader = PdfReader(str(pdf_path))
        text_parts = []

        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)

        if text_parts:
            return "\n\n".join(text_parts)
        return None


def convert_pdf_to_images(
    pdf_path: str | Path,
    output_dir: str | Path | None = None,
    dpi: int = 300,
) -> list[NDArray[np.uint8]]:
    """
    Convenience function to convert PDF to images.
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Optional directory to save images
        dpi: Resolution for rendering
        
    Returns:
        List of images as numpy arrays
    """
    converter = PDFConverter(dpi=dpi)
    return converter.convert_to_images(pdf_path, output_dir)
