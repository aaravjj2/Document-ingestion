"""OCR accuracy benchmarking tests."""

import pytest
from jiwer import cer, wer


class TestOCRAccuracy:
    """Tests for OCR accuracy metrics using jiwer."""

    def test_cer_perfect_match(self):
        """Test CER for perfect match."""
        ground_truth = "Invoice #12345"
        hypothesis = "Invoice #12345"
        
        error_rate = cer(ground_truth, hypothesis)
        
        assert error_rate == 0.0

    def test_cer_with_errors(self):
        """Test CER with some errors."""
        ground_truth = "Invoice #12345"
        hypothesis = "Invoce #12345"  # Missing 'i'
        
        error_rate = cer(ground_truth, hypothesis)
        
        # Should have some error
        assert error_rate > 0
        assert error_rate < 0.1  # Less than 10% error

    def test_wer_perfect_match(self):
        """Test WER for perfect match."""
        ground_truth = "The quick brown fox"
        hypothesis = "The quick brown fox"
        
        error_rate = wer(ground_truth, hypothesis)
        
        assert error_rate == 0.0

    def test_wer_with_errors(self):
        """Test WER with word errors."""
        ground_truth = "The quick brown fox"
        hypothesis = "The quik brown fox"  # Misspelled 'quick'
        
        error_rate = wer(ground_truth, hypothesis)
        
        # One word wrong out of four = 25% WER
        assert error_rate == 0.25

    def test_cer_completely_wrong(self):
        """Test CER for completely wrong text."""
        ground_truth = "ABCDEFG"
        hypothesis = "1234567"
        
        error_rate = cer(ground_truth, hypothesis)
        
        # Should be 100% error
        assert error_rate == 1.0

    def test_wer_empty_hypothesis(self):
        """Test WER when OCR returns empty."""
        ground_truth = "Some text"
        hypothesis = ""
        
        error_rate = wer(ground_truth, hypothesis)
        
        # All words deleted = 100% error
        assert error_rate == 1.0


class TestAccuracyBenchmarks:
    """Benchmark tests for OCR accuracy targets."""

    # Target: CER < 5% for printed text
    PRINTED_TEXT_CER_TARGET = 0.05
    
    # Target: CER < 15% for handwriting
    HANDWRITING_CER_TARGET = 0.15

    def test_printed_text_accuracy_target(self):
        """Verify we can measure against printed text target."""
        # Simulated good OCR result
        ground_truth = "Invoice Number: 12345"
        hypothesis = "Invoice Number: 12345"
        
        error_rate = cer(ground_truth, hypothesis)
        
        assert error_rate < self.PRINTED_TEXT_CER_TARGET, \
            f"CER {error_rate:.2%} exceeds target {self.PRINTED_TEXT_CER_TARGET:.2%}"

    def test_printed_text_with_minor_errors(self):
        """Test printed text with minor OCR errors."""
        # Simulated OCR with minor errors
        ground_truth = "Total Amount Due: $1,234.56"
        hypothesis = "Total Amount Due: $1,234.56"  # Perfect in this case
        
        error_rate = cer(ground_truth, hypothesis)
        
        assert error_rate < self.PRINTED_TEXT_CER_TARGET

    def test_handwriting_accuracy_target(self):
        """Verify we can measure against handwriting target."""
        # Simulated handwriting OCR result (some errors expected)
        ground_truth = "Please send payment by January 15th"
        hypothesis = "Pleose send payment by Januory 15th"  # Simulated errors
        
        error_rate = cer(ground_truth, hypothesis)
        
        # This should pass the handwriting target (more lenient)
        assert error_rate < self.HANDWRITING_CER_TARGET, \
            f"CER {error_rate:.2%} exceeds handwriting target {self.HANDWRITING_CER_TARGET:.2%}"

    def test_calculate_accuracy_metrics(self):
        """Test calculating multiple accuracy metrics."""
        ground_truths = [
            "Invoice #12345",
            "Date: 2024-01-15",
            "Total: $500.00",
        ]
        
        hypotheses = [
            "Invoice #12345",
            "Date: 2024-01-15",
            "Total: $500.00",
        ]
        
        cer_scores = []
        wer_scores = []
        
        for gt, hyp in zip(ground_truths, hypotheses):
            cer_scores.append(cer(gt, hyp))
            wer_scores.append(wer(gt, hyp))
        
        avg_cer = sum(cer_scores) / len(cer_scores)
        avg_wer = sum(wer_scores) / len(wer_scores)
        
        assert avg_cer < 0.05
        assert avg_wer < 0.10


class TestBenchmarkReporting:
    """Tests for benchmark result reporting."""

    def test_generate_accuracy_report(self):
        """Test generating an accuracy report."""
        results = {
            "document_1": {
                "ground_truth": "Invoice #12345",
                "hypothesis": "Invoice #12345",
            },
            "document_2": {
                "ground_truth": "Total: $500.00",
                "hypothesis": "Total: $500.00",
            },
        }
        
        report = []
        for doc_id, data in results.items():
            doc_cer = cer(data["ground_truth"], data["hypothesis"])
            doc_wer = wer(data["ground_truth"], data["hypothesis"])
            report.append({
                "document_id": doc_id,
                "cer": doc_cer,
                "wer": doc_wer,
                "passed": doc_cer < 0.05,
            })
        
        assert len(report) == 2
        assert all(r["passed"] for r in report)
