"""Document classification service."""

import logging
import re
from collections import Counter
from dataclasses import dataclass

from src.models.enums import DocumentType

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Result of document classification."""
    
    document_type: DocumentType
    confidence: float
    matched_keywords: list[str]
    all_scores: dict[str, float]


class DocumentClassifier:
    """
    Classify documents based on keywords and patterns.
    
    Supports both simple keyword matching and zero-shot classification
    using an LLM for more complex cases.
    """

    # Keyword patterns for each document type
    KEYWORD_PATTERNS: dict[DocumentType, list[str]] = {
        DocumentType.INVOICE: [
            "invoice", "inv", "bill to", "ship to", "total", "subtotal",
            "tax", "amount due", "payment terms", "due date", "invoice number",
            "invoice date", "purchase order", "po number", "qty", "quantity",
            "unit price", "line total", "balance due", "remit to",
        ],
        DocumentType.RECEIPT: [
            "receipt", "transaction", "paid", "cash", "credit card",
            "debit", "change", "subtotal", "total", "thank you",
            "store", "cashier", "transaction id", "authorization",
        ],
        DocumentType.MEDICAL: [
            "patient", "diagnosis", "prescription", "rx", "medication",
            "doctor", "physician", "hospital", "clinic", "treatment",
            "dosage", "mg", "tablet", "capsule", "medical record",
            "health", "symptom", "lab result", "blood", "vital signs",
            "insurance", "copay", "icd", "cpt",
        ],
        DocumentType.LEGAL: [
            "agreement", "contract", "hereby", "whereas", "party",
            "witness", "notary", "attorney", "law", "court", "legal",
            "plaintiff", "defendant", "jurisdiction", "liability",
            "indemnify", "terms and conditions", "effective date",
            "termination", "governing law", "arbitration",
        ],
        DocumentType.FINANCIAL: [
            "account", "balance", "statement", "transaction", "deposit",
            "withdrawal", "interest", "dividend", "stock", "bond",
            "portfolio", "investment", "bank", "credit", "debit",
            "fiscal", "revenue", "expense", "profit", "loss",
            "quarterly", "annual report", "income", "assets",
        ],
        DocumentType.IDENTITY: [
            "passport", "driver license", "id card", "social security",
            "ssn", "birth certificate", "nationality", "citizenship",
            "date of birth", "dob", "place of birth", "expiry date",
            "issue date", "id number", "identification",
            # Insurance card keywords
            "member id", "member name", "group number", "group:", "subscriber",
            "copay", "deductible", "coinsurance", "out of pocket",
            "in network", "out of network", "inn", "oon",
            "rxbin", "rxpcn", "rxgroup", "pharmacy",
            "pcp visit", "specialist", "urgent care", "emergency room",
            "ind/fam", "tier 1", "tier 2",
            "cigna", "aetna", "bcbs", "blue cross", "united healthcare",
            "humana", "anthem", "kaiser",
            # Driver license specific
            "driver", "license", "dl:", "class:", "restrictions",
            "endorsements", "hgt:", "sex:", "expires", "issued",
            "state of", "department of motor vehicles", "dmv",
            # Passport specific
            "surname", "given names", "passport no", "mrz",
            "p<usa", "nationality", "united states of america",
        ],
        DocumentType.CORRESPONDENCE: [
            "dear", "sincerely", "regards", "letter", "memo",
            "subject", "re:", "cc:", "bcc:", "attachment",
            "please find", "enclosed", "response", "inquiry",
            "follow up", "thank you for", "looking forward",
        ],
    }

    # Weighted patterns (higher weight = stronger signal)
    STRONG_INDICATORS: dict[DocumentType, list[str]] = {
        DocumentType.INVOICE: ["invoice number", "invoice date", "amount due"],
        DocumentType.RECEIPT: ["transaction id", "receipt"],
        DocumentType.MEDICAL: ["rx", "diagnosis", "prescription", "patient name"],
        DocumentType.LEGAL: ["hereby", "whereas", "witnesseth"],
        DocumentType.FINANCIAL: ["account statement", "portfolio summary"],
        DocumentType.IDENTITY: [
            "passport", "driver license", "ssn", "member id", 
            "rxbin", "rxpcn", "mrz", "p<usa", 
            "cigna", "aetna", "united healthcare", "blue cross", "humana", "anthem"
        ],
        DocumentType.CORRESPONDENCE: ["dear sir", "dear madam", "to whom it may concern"],
    }

    # Regex patterns for structural matching (Very high confidence)
    REGEX_PATTERNS: dict[DocumentType, list[str]] = {
        DocumentType.IDENTITY: [
            r"P<USA[\w<]+",  # Passport MRZ
            r"(?:DL|LIC|ID)\s*[:#]\s*[A-Z0-9-]{5,}",  # Driver License/ID
            r"(?:Member|Subscriber)\s*ID\s*[:#]?\s*[A-Z0-9]{5,}",  # Insurance Member ID
            r"Rx\s*(?:BIN|PCN|GRP|Group)",  # Pharmacy info
            r"Group\s*(?:No|#)\s*[:.]?\s*[A-Z0-9]{3,}",  # Group Number
            r"Class:\s*[A-Z]",  # License Class
            r"Enrollee\s*ID",
        ],
        DocumentType.INVOICE: [
            r"Invoice\s*(?:No|#)\s*[:.]?\s*[\w-]+",
            r"Due\s*Date\s*[:.]?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
        ],
    }

    def __init__(self, min_confidence: float = 0.3):
        """
        Initialize classifier.
        
        Args:
            min_confidence: Minimum confidence to assign a type (else UNKNOWN)
        """
        self.min_confidence = min_confidence

    def classify(self, text: str) -> ClassificationResult:
        """
        Classify a document based on its text content.
        
        Args:
            text: Raw text from OCR
            
        Returns:
            ClassificationResult with type and confidence
        """
        if not text or not text.strip():
            return ClassificationResult(
                document_type=DocumentType.UNKNOWN,
                confidence=0.0,
                matched_keywords=[],
                all_scores={},
            )

        # Normalize text
        normalized_text = text.lower()
        
        # Calculate TF-IDF weights for the document
        tf_weights = self._calculate_tf_weights(normalized_text)

        # Calculate scores for each document type
        scores: dict[DocumentType, float] = {}
        matched: dict[DocumentType, list[str]] = {}

        for doc_type, keywords in self.KEYWORD_PATTERNS.items():
            score, matches = self._calculate_score(
                normalized_text,
                keywords,
                self.STRONG_INDICATORS.get(doc_type, []),
            )
            
            # Add TF-IDF weighted bonus
            tfidf_bonus = self._tfidf_score(normalized_text, keywords, tf_weights)
            score += tfidf_bonus
            
            # Add bigram matching score
            bigram_bonus = self._bigram_score(normalized_text, keywords)
            score += bigram_bonus
            
            # Add position-aware scoring (keywords in first 20% weighted higher)
            position_bonus = self._position_score(text, keywords)
            score += position_bonus
            
            # Add context scoring (keywords near each other boost score)
            context_bonus = self._context_score(normalized_text, keywords)
            score += context_bonus
            
            # Add Regex structural matching (Massive Boost)
            regex_bonus = self._regex_score(text, self.REGEX_PATTERNS.get(doc_type, []))
            score += regex_bonus
            
            # Add context scoring (keywords near each other boost score)
            context_bonus = self._context_score(normalized_text, keywords)
            score += context_bonus
            
            scores[doc_type] = score
            matched[doc_type] = matches

        # Find best match
        if not scores or max(scores.values()) == 0:
            return ClassificationResult(
                document_type=DocumentType.UNKNOWN,
                confidence=0.0,
                matched_keywords=[],
                all_scores={str(k): v for k, v in scores.items()},
            )

        # Get document type with highest score
        best_type = max(scores, key=lambda k: scores[k])
        best_score = scores[best_type]

        # Normalize confidence with softmax-like scaling
        total_score = sum(scores.values())
        raw_confidence = best_score / total_score if total_score > 0 else 0.0
        
        # Apply confidence calibration
        confidence = self._calibrate_confidence(raw_confidence, best_score)

        # Check minimum confidence
        if confidence < self.min_confidence:
            best_type = DocumentType.UNKNOWN

        logger.info(f"Classified as {best_type} with confidence {confidence:.2%}")

        return ClassificationResult(
            document_type=best_type,
            confidence=confidence,
            matched_keywords=matched.get(best_type, []),
            all_scores={str(k): v for k, v in scores.items()},
        )

    def _calculate_score(
        self,
        text: str,
        keywords: list[str],
        strong_indicators: list[str],
    ) -> tuple[float, list[str]]:
        """
        Calculate classification score using fuzzy keyword matching.
        Handles OCR errors like merged words and typos.
        
        Args:
            text: Normalized text
            keywords: List of keywords to search for
            strong_indicators: Keywords with higher weight
            
        Returns:
            Tuple of (score, list of matched keywords)
        """
        matches = []
        score = 0.0

        for keyword in keywords:
            matched = False
            
            # 1. Exact word boundary match (highest confidence)
            pattern = r'\b' + re.escape(keyword) + r'\b'
            count = len(re.findall(pattern, text, re.IGNORECASE))
            if count > 0:
                matched = True
                score += min(count, 3) * (2.0 / len(keywords))  # Boosted weight
            
            # 2. Substring match (for merged words like "DRIVERLICENSE")
            elif keyword.lower().replace(" ", "") in text.lower().replace(" ", ""):
                matched = True
                score += 1.5 / len(keywords)
            
            # 3. Fuzzy match using Levenshtein distance for typos
            elif len(keyword) >= 4:
                words = re.findall(r'\b\w+\b', text.lower())
                for word in words:
                    if len(word) >= 3 and self._levenshtein_ratio(keyword.lower(), word) >= 0.70:
                        matched = True
                        score += 1.0 / len(keywords)
                        break
            
            # 4. N-gram match for partial matches
            if not matched and len(keyword) >= 5:
                ngram_score = self._ngram_match(text, keyword)
                if ngram_score >= 0.6:
                    matched = True
                    score += 0.7 * ngram_score / len(keywords)
            
            # 5. Soundex phonetic match for similar-sounding words
            if not matched and len(keyword) >= 4 and keyword.isalpha():
                keyword_soundex = self._soundex(keyword)
                words = re.findall(r'\b[a-zA-Z]+\b', text)
                for word in words:
                    if len(word) >= 3 and self._soundex(word) == keyword_soundex:
                        matched = True
                        score += 0.5 / len(keywords)
                        break
            
            if matched:
                matches.append(keyword)

        # Bonus for strong indicators (multi-method matching)
        for indicator in strong_indicators:
            indicator_lower = indicator.lower()
            text_lower = text.lower()
            
            # Exact match
            if indicator_lower in text_lower:
                score += 3.0  # Boosted
                if indicator not in matches:
                    matches.append(indicator)
            # Merged word match
            elif indicator_lower.replace(" ", "") in text_lower.replace(" ", ""):
                score += 2.5
                if indicator not in matches:
                    matches.append(indicator)
            # N-gram match for indicators
            elif self._ngram_match(text, indicator) >= 0.7:
                score += 1.5
                if indicator not in matches:
                    matches.append(indicator)

        return score, matches
    
    def _levenshtein_ratio(self, s1: str, s2: str) -> float:
        """Calculate similarity ratio between two strings using Levenshtein distance."""
        if len(s1) == 0 or len(s2) == 0:
            return 0.0
        
        # Create distance matrix
        rows = len(s1) + 1
        cols = len(s2) + 1
        dist = [[0] * cols for _ in range(rows)]
        
        for i in range(rows):
            dist[i][0] = i
        for j in range(cols):
            dist[0][j] = j
        
        for i in range(1, rows):
            for j in range(1, cols):
                cost = 0 if s1[i-1] == s2[j-1] else 1
                dist[i][j] = min(
                    dist[i-1][j] + 1,      # deletion
                    dist[i][j-1] + 1,      # insertion
                    dist[i-1][j-1] + cost  # substitution
                )
        
        distance = dist[rows-1][cols-1]
        max_len = max(len(s1), len(s2))
        return 1.0 - (distance / max_len)
    
    def _soundex(self, word: str) -> str:
        """Generate Soundex code for phonetic matching."""
        if not word:
            return ""
        
        word = word.upper()
        soundex = word[0]
        
        # Soundex encoding map
        codes = {
            'B': '1', 'F': '1', 'P': '1', 'V': '1',
            'C': '2', 'G': '2', 'J': '2', 'K': '2', 'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
            'D': '3', 'T': '3',
            'L': '4',
            'M': '5', 'N': '5',
            'R': '6'
        }
        
        prev_code = codes.get(word[0], '0')
        
        for char in word[1:]:
            code = codes.get(char, '0')
            if code != '0' and code != prev_code:
                soundex += code
            prev_code = code
            if len(soundex) >= 4:
                break
        
        return soundex.ljust(4, '0')[:4]
    
    def _ngram_match(self, text: str, keyword: str, n: int = 3) -> float:
        """Calculate n-gram similarity between keyword and any part of text."""
        if len(keyword) < n:
            return 1.0 if keyword.lower() in text.lower() else 0.0
        
        # Generate n-grams for keyword
        keyword_lower = keyword.lower().replace(" ", "")
        keyword_ngrams = set()
        for i in range(len(keyword_lower) - n + 1):
            keyword_ngrams.add(keyword_lower[i:i+n])
        
        if not keyword_ngrams:
            return 0.0
        
        # Search in text
        text_lower = text.lower().replace(" ", "")
        text_ngrams = set()
        for i in range(len(text_lower) - n + 1):
            text_ngrams.add(text_lower[i:i+n])
        
        # Calculate Jaccard similarity
        intersection = keyword_ngrams & text_ngrams
        union = keyword_ngrams | text_ngrams
        
        if not union:
            return 0.0
        
        return len(intersection) / len(keyword_ngrams)  # Recall-focused
    
    def _calculate_tf_weights(self, text: str) -> dict[str, float]:
        """Calculate term frequency weights for document."""
        words = re.findall(r'\b\w+\b', text.lower())
        word_counts = Counter(words)
        total_words = len(words) if words else 1
        
        return {word: count / total_words for word, count in word_counts.items()}
    
    def _tfidf_score(self, text: str, keywords: list[str], tf_weights: dict[str, float]) -> float:
        """Calculate TF-IDF weighted score for keywords."""
        score = 0.0
        
        # Inverse document frequency approximation (keywords appearing in many doc types get lower weight)
        keyword_doc_freq = {}
        for kw in keywords:
            count = sum(1 for kws in self.KEYWORD_PATTERNS.values() if kw in kws)
            keyword_doc_freq[kw] = count
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            words = keyword_lower.split()
            
            for word in words:
                if word in tf_weights:
                    # IDF weight: less common keywords across categories are more discriminative
                    idf = 1.0 / max(keyword_doc_freq.get(keyword, 1), 1)
                    score += tf_weights[word] * idf * 2.0
        
        return score
    
    def _bigram_score(self, text: str, keywords: list[str]) -> float:
        """Score based on bigram (two-word phrase) matches."""
        score = 0.0
        
        # Generate bigrams from text
        words = re.findall(r'\b\w+\b', text.lower())
        text_bigrams = set()
        for i in range(len(words) - 1):
            text_bigrams.add(f"{words[i]} {words[i+1]}")
        
        # Check multi-word keywords as bigrams
        for keyword in keywords:
            if " " in keyword:
                kw_words = keyword.lower().split()
                for i in range(len(kw_words) - 1):
                    bigram = f"{kw_words[i]} {kw_words[i+1]}"
                    if bigram in text_bigrams:
                        score += 1.5  # Bigram match bonus
        
        return score
    
    def _regex_score(self, text: str, patterns: list[str]) -> float:
        """Calculate score based on structural regex pattern matches."""
        score = 0.0
        if not patterns:
            return 0.0
            
        for pattern in patterns:
            # Check for matches (case insensitive)
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Significant boost for structural match
                score += 3.0 + (len(matches) * 0.5)
                
        return min(score, 10.0)  # Cap boost to avoid skewing too much
    
    def _position_score(self, text: str, keywords: list[str]) -> float:
        """Score keywords appearing in document header (first 20%) higher."""
        score = 0.0
        
        if not text:
            return 0.0
        
        text_lower = text.lower()
        header_cutoff = len(text_lower) // 5  # First 20%
        header = text_lower[:header_cutoff]
        
        for keyword in keywords:
            if keyword.lower() in header:
                score += 0.5  # Header position bonus
        
        return score
    
    def _context_score(self, text: str, keywords: list[str]) -> float:
        """Score based on keyword proximity - keywords near each other boost score."""
        score = 0.0
        
        # Find positions of all keyword matches
        keyword_positions = []
        for keyword in keywords:
            for match in re.finditer(re.escape(keyword.lower()), text.lower()):
                keyword_positions.append((match.start(), keyword))
        
        if len(keyword_positions) < 2:
            return 0.0
        
        # Sort by position
        keyword_positions.sort(key=lambda x: x[0])
        
        # Check proximity between consecutive keywords
        for i in range(len(keyword_positions) - 1):
            pos1, kw1 = keyword_positions[i]
            pos2, kw2 = keyword_positions[i + 1]
            
            distance = pos2 - pos1
            if distance < 100:  # Within ~100 characters
                score += 0.3
            elif distance < 300:
                score += 0.1
        
        return min(score, 2.0)  # Cap context bonus
    
    def _calibrate_confidence(self, raw_confidence: float, best_score: float) -> float:
        """Calibrate confidence for more accurate probability estimates."""
        import math
        
        # Apply sigmoid-like calibration
        if best_score <= 0:
            return 0.0
        
        # Scale based on absolute score (higher scores = more confident)
        # If score > 8.0 (likely regex match), allow full confidence
        if best_score > 8.0:
            return 1.0
            
        score_factor = min(best_score / 6.0, 1.0)  # Normalize to ~6.0 expected max
        
        # Combine relative and absolute confidence
        calibrated = (raw_confidence * 0.5 + score_factor * 0.5)
        
        # Apply smoothing but allow reaching 1.0
        # Sigmoid function centered at 0.5
        calibrated = 1 / (1 + math.exp(-10 * (calibrated - 0.5)))
        
        return min(max(calibrated, 0.0), 1.0)

    def classify_with_llm(
        self,
        text: str,
        llm_client,
    ) -> ClassificationResult:
        """
        Use LLM for zero-shot classification when keyword matching is uncertain.
        
        Args:
            text: Document text
            llm_client: LLM client for classification
            
        Returns:
            ClassificationResult
        """
        # First try keyword classification
        keyword_result = self.classify(text)
        
        # If confident enough, return keyword result
        if keyword_result.confidence >= 0.6:
            return keyword_result

        # Use LLM for uncertain cases
        logger.info("Using LLM for classification due to low keyword confidence")
        
        prompt = f"""Classify the following document text into one of these categories:
- INVOICE: Bills, invoices, payment requests
- RECEIPT: Purchase receipts, transaction records
- MEDICAL: Medical records, prescriptions, lab results
- LEGAL: Contracts, agreements, legal documents
- FINANCIAL: Bank statements, investment reports
- IDENTITY: ID cards, passports, licenses
- CORRESPONDENCE: Letters, emails, memos
- UNKNOWN: Cannot determine

Document text (first 2000 characters):
{text[:2000]}

Respond with ONLY the category name (e.g., INVOICE) and nothing else."""

        try:
            response = llm_client.generate(prompt, max_tokens=20)
            predicted_type = response.strip().upper()
            
            # Map response to DocumentType
            type_mapping = {
                "INVOICE": DocumentType.INVOICE,
                "RECEIPT": DocumentType.RECEIPT,
                "MEDICAL": DocumentType.MEDICAL,
                "LEGAL": DocumentType.LEGAL,
                "FINANCIAL": DocumentType.FINANCIAL,
                "IDENTITY": DocumentType.IDENTITY,
                "CORRESPONDENCE": DocumentType.CORRESPONDENCE,
            }
            
            doc_type = type_mapping.get(predicted_type, DocumentType.UNKNOWN)
            
            return ClassificationResult(
                document_type=doc_type,
                confidence=0.8 if doc_type != DocumentType.UNKNOWN else 0.0,
                matched_keywords=["llm_classification"],
                all_scores=keyword_result.all_scores,
            )
            
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return keyword_result


def classify_document(text: str) -> ClassificationResult:
    """
    Convenience function to classify a document.
    
    Args:
        text: Document text
        
    Returns:
        ClassificationResult
    """
    classifier = DocumentClassifier()
    return classifier.classify(text)
