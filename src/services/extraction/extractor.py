"""LLM-based field extraction service."""

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, ValidationError

from src.core.config import settings
from src.models.enums import DocumentType

logger = logging.getLogger(__name__)


# ============== Extraction Schema Definitions ==============

class InvoiceExtraction(BaseModel):
    """Schema for invoice field extraction."""
    invoice_number: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    vendor_name: str | None = None
    vendor_address: str | None = None
    customer_name: str | None = None
    customer_address: str | None = None
    subtotal: float | None = None
    tax_amount: float | None = None
    total_amount: float | None = None
    currency: str | None = None
    line_items: list[dict[str, Any]] | None = None


class ReceiptExtraction(BaseModel):
    """Schema for receipt field extraction."""
    store_name: str | None = None
    store_address: str | None = None
    transaction_date: str | None = None
    transaction_id: str | None = None
    payment_method: str | None = None
    items: list[dict[str, Any]] | None = None
    subtotal: float | None = None
    tax: float | None = None
    total: float | None = None


class MedicalExtraction(BaseModel):
    """Schema for medical document extraction."""
    patient_name: str | None = None
    patient_dob: str | None = None
    provider_name: str | None = None
    facility_name: str | None = None
    document_date: str | None = None
    diagnosis: list[str] | None = None
    medications: list[dict[str, Any]] | None = None
    procedures: list[str] | None = None
    notes: str | None = None


class LegalExtraction(BaseModel):
    """Schema for legal document extraction."""
    document_title: str | None = None
    parties: list[str] | None = None
    effective_date: str | None = None
    expiration_date: str | None = None
    key_terms: list[str] | None = None
    jurisdiction: str | None = None


class FinancialExtraction(BaseModel):
    """Schema for financial document extraction."""
    account_holder: str | None = None
    account_number: str | None = None
    statement_period: str | None = None
    opening_balance: float | None = None
    closing_balance: float | None = None
    total_deposits: float | None = None
    total_withdrawals: float | None = None
    transactions: list[dict[str, Any]] | None = None


class IdentityExtraction(BaseModel):
    """Schema for identity/insurance card extraction."""
    card_type: str | None = None  # e.g., "Insurance", "ID", "License"
    issuer_name: str | None = None  # e.g., "Cigna", "Aetna"
    member_name: str | None = None
    member_id: str | None = None
    group_number: str | None = None
    effective_date: str | None = None
    plan_type: str | None = None  # e.g., "Open Access Plus"
    # Copay structure
    copay_pcp: str | None = None  # e.g., "$20/$30" (in-network/out-of-network)
    copay_specialist: str | None = None
    copay_er: str | None = None
    copay_urgent_care: str | None = None
    copay_rx: str | None = None  # e.g., "$10/$30/$60" (tier 1/2/3)
    # Deductible structure
    deductible_individual: str | None = None  # e.g., "$500/$2500" (in/out)
    deductible_family: str | None = None
    out_of_pocket_individual: str | None = None
    out_of_pocket_family: str | None = None
    # Coinsurance
    coinsurance_in_network: str | None = None  # e.g., "85%/15%"
    coinsurance_out_of_network: str | None = None
    # Pharmacy identifiers
    rx_bin: str | None = None
    rx_pcn: str | None = None
    rx_group: str | None = None


class GenericExtraction(BaseModel):
    """Generic extraction for unknown document types."""
    title: str | None = None
    date: str | None = None
    key_entities: list[str] | None = None
    amounts: list[float] | None = None
    summary: str | None = None


# ============== Extraction Templates ==============

EXTRACTION_PROMPTS: dict[DocumentType, str] = {
    DocumentType.INVOICE: """You are a data extraction assistant. Extract the following fields from this invoice OCR text.
Return ONLY valid JSON with these fields:
- invoice_number: The invoice/bill number
- invoice_date: Date the invoice was issued (format: YYYY-MM-DD if possible)
- due_date: Payment due date
- vendor_name: Name of the company/vendor issuing the invoice
- vendor_address: Vendor's address
- customer_name: Name of the customer/bill recipient  
- customer_address: Customer's address
- subtotal: Amount before tax (number only)
- tax_amount: Tax amount (number only)
- total_amount: Total amount due (number only)
- currency: Currency code (USD, EUR, etc.)
- line_items: Array of items with description, quantity, unit_price, total

OCR Text:
{text}

Return ONLY JSON, no explanation:""",

    DocumentType.RECEIPT: """You are a data extraction assistant. Extract the following fields from this receipt OCR text.
Return ONLY valid JSON with these fields:
- store_name: Name of the store/business
- store_address: Store address
- transaction_date: Date of transaction (format: YYYY-MM-DD if possible)
- transaction_id: Receipt/transaction number
- payment_method: Cash, Credit Card, etc.
- items: Array of purchased items with name, quantity, price
- subtotal: Amount before tax
- tax: Tax amount
- total: Total amount paid

OCR Text:
{text}

Return ONLY JSON, no explanation:""",

    DocumentType.MEDICAL: """You are a medical data extraction assistant. Extract the following fields from this medical document OCR text.
Return ONLY valid JSON with these fields:
- patient_name: Full name of the patient
- patient_dob: Patient date of birth
- provider_name: Doctor/physician name
- facility_name: Hospital/clinic name
- document_date: Date of the document
- diagnosis: Array of diagnoses/conditions
- medications: Array of medications with name, dosage, frequency
- procedures: Array of procedures/treatments
- notes: Any additional clinical notes

OCR Text:
{text}

Return ONLY JSON, no explanation:""",

    DocumentType.LEGAL: """You are a legal document extraction assistant. Extract the following fields from this legal document OCR text.
Return ONLY valid JSON with these fields:
- document_title: Title/type of the legal document
- parties: Array of parties involved
- effective_date: When the agreement takes effect
- expiration_date: When the agreement expires
- key_terms: Array of key terms/provisions
- jurisdiction: Governing law/jurisdiction

OCR Text:
{text}

Return ONLY JSON, no explanation:""",

    DocumentType.FINANCIAL: """You are a financial document extraction assistant. Extract the following fields from this financial document OCR text.
Return ONLY valid JSON with these fields:
- account_holder: Name of account holder
- account_number: Account number (last 4 digits only for security)
- statement_period: Statement period dates
- opening_balance: Starting balance
- closing_balance: Ending balance
- total_deposits: Sum of deposits
- total_withdrawals: Sum of withdrawals
- transactions: Array of transactions with date, description, amount, type

OCR Text:
{text}

Return ONLY JSON, no explanation:""",

    DocumentType.UNKNOWN: """You are a data extraction assistant. Extract key information from this document OCR text.
Return ONLY valid JSON with these fields:
- title: Document title if identifiable
- date: Any date found in the document
- key_entities: Array of important names, organizations, or places
- amounts: Array of monetary amounts found
- summary: Brief 1-2 sentence summary of the document

OCR Text:
{text}

Return ONLY JSON, no explanation:""",

    DocumentType.IDENTITY: """You are a data extraction assistant specialized in insurance and ID cards. Extract the following fields from this insurance/ID card OCR text.
Return ONLY valid JSON with these fields:
- card_type: Type of card (Insurance, ID, License, etc.)
- issuer_name: Company/organization name (e.g., Cigna, Aetna, BCBS)
- member_name: Name of the card holder
- member_id: Member/ID number
- group_number: Group number if present
- effective_date: Coverage effective date
- plan_type: Plan name (e.g., Open Access Plus, PPO, HMO)
- copay_pcp: Primary care copay (format: "$XX/$YY" for in/out network, or just "$XX")
- copay_specialist: Specialist copay
- copay_er: Emergency room copay
- copay_urgent_care: Urgent care copay
- copay_rx: Prescription copay tiers (e.g., "$10/$30/$60" for tier 1/2/3)
- deductible_individual: Individual deductible (format: "$XXX/$YYYY" for in/out network)
- deductible_family: Family deductible
- out_of_pocket_individual: Individual out-of-pocket max
- out_of_pocket_family: Family out-of-pocket max
- coinsurance_in_network: In-network coinsurance (e.g., "85%/15%")
- coinsurance_out_of_network: Out-of-network coinsurance
- rx_bin: Pharmacy BIN number
- rx_pcn: Pharmacy PCN
- rx_group: Pharmacy group number

OCR Text:
{text}

Return ONLY JSON, no explanation:""",
}


# ============== LLM Client Classes ==============

class OpenAIClient:
    """Client for OpenAI API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.1,
    ):
        self.api_key = api_key or settings.openai_api_key
        self.model = model
        self.temperature = temperature
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def generate(self, prompt: str, max_tokens: int = 2000) -> str:
        """Generate completion from prompt."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=self.temperature,
        )
        return response.choices[0].message.content


class OllamaClient:
    """Client for local Ollama LLM."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str = "llama3",
    ):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model

    def generate(self, prompt: str, max_tokens: int = 2000) -> str:
        """Generate completion from prompt."""
        import httpx
        
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": max_tokens},
            },
            timeout=120.0,
        )
        response.raise_for_status()
        return response.json()["response"]


# ============== Extraction Service ==============

class ExtractionService:
    """
    LLM-based field extraction service.
    
    Extracts structured fields from OCR text using document-type-specific prompts.
    """

    SCHEMA_MAP: dict[DocumentType, type[BaseModel]] = {
        DocumentType.INVOICE: InvoiceExtraction,
        DocumentType.RECEIPT: ReceiptExtraction,
        DocumentType.MEDICAL: MedicalExtraction,
        DocumentType.LEGAL: LegalExtraction,
        DocumentType.FINANCIAL: FinancialExtraction,
        DocumentType.UNKNOWN: GenericExtraction,
        DocumentType.CORRESPONDENCE: GenericExtraction,
        DocumentType.IDENTITY: IdentityExtraction,
    }

    def __init__(
        self,
        use_local_llm: bool = False,
        openai_api_key: str | None = None,
    ):
        """
        Initialize extraction service.
        
        Args:
            use_local_llm: Use Ollama instead of OpenAI
            openai_api_key: OpenAI API key (uses settings if not provided)
        """
        self.use_local_llm = use_local_llm or settings.use_local_llm
        
        if self.use_local_llm:
            self.llm_client = OllamaClient(
                model=settings.local_llm_model,
            )
            self.model_name = settings.local_llm_model
        else:
            self.llm_client = OpenAIClient(
                api_key=openai_api_key,
                model=settings.llm_model,
                temperature=settings.llm_temperature,
            )
            self.model_name = settings.llm_model

    def extract(
        self,
        text: str,
        document_type: DocumentType,
    ) -> dict[str, Any]:
        """
        Extract structured fields from text.
        
        Args:
            text: OCR text content
            document_type: Type of document for field extraction
            
        Returns:
            Dictionary of extracted fields
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for extraction")
            return {}

        # Get appropriate prompt template
        prompt_template = EXTRACTION_PROMPTS.get(
            document_type,
            EXTRACTION_PROMPTS[DocumentType.UNKNOWN],
        )
        
        # Truncate text if too long (keep first 8000 chars)
        truncated_text = text[:8000] if len(text) > 8000 else text
        
        # Build prompt
        prompt = prompt_template.format(text=truncated_text)

        logger.info(f"Extracting fields for document type: {document_type}")

        try:
            # Call LLM
            response = self.llm_client.generate(prompt)
            
            # Parse JSON response
            extracted = self._parse_json_response(response)
            
            # Validate against schema
            schema_class = self.SCHEMA_MAP.get(document_type, GenericExtraction)
            validated = self._validate_extraction(extracted, schema_class)
            
            logger.info(f"Successfully extracted {len(validated)} fields")
            return validated
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            logger.info("Falling back to regex extraction")
            return self._regex_extract(text, document_type)

    def _regex_extract(self, text: str, document_type: DocumentType) -> dict[str, Any]:
        """
        Fallback extraction using regex patterns.
        """
        data = {}
        
        if document_type == DocumentType.INVOICE:
            # Invoice Number
            inv_match = re.search(r"(?:Invoice\s*(?:#|No\.?)|Inv\.?)\s*:?\s*([A-Za-z0-9-]+)", text, re.IGNORECASE)
            if inv_match:
                data["invoice_number"] = inv_match.group(1)
            
            # Date
            date_match = re.search(r"(?:Date|Invoice Date)\s*:?\s*(\w+\s+\d{1,2},?\s*\d{4}|\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
            if date_match:
                data["invoice_date"] = date_match.group(1)
                
            # Total Amount
            total_match = re.search(r"(?:Total|Amount Due|Balance Due)\s*:?\s*\$?\s*([\d,]+\.\d{2})", text, re.IGNORECASE)
            if total_match:
                try:
                    amount_str = total_match.group(1).replace(",", "")
                    data["total_amount"] = float(amount_str)
                except ValueError:
                    pass
                    
            # Set other fields to None to match schema
            for field in InvoiceExtraction.model_fields:
                if field not in data:
                    data[field] = None
        
        elif document_type == DocumentType.IDENTITY:
            # Issuer Name (insurance company)
            issuer_patterns = [
                r"(?:Administered\s*By|Issued\s*By)\s+([\w\s]+?)(?:\s*Co\.|Inc\.|LLC|\.|\n)",
                r"(Cigna|Aetna|UnitedHealthcare|Blue\s*Cross|BCBS|Humana|Kaiser|Anthem)",
            ]
            for pattern in issuer_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data["issuer_name"] = match.group(1).strip()
                    break
            
            # Card Type
            if re.search(r"insurance|health\s*plan|coverage", text, re.IGNORECASE):
                data["card_type"] = "Insurance"
            elif re.search(r"passport", text, re.IGNORECASE):
                data["card_type"] = "Passport"
            elif re.search(r"driver|license", text, re.IGNORECASE):
                data["card_type"] = "Driver License"
            
            # Plan Type
            plan_match = re.search(r"(Open\s*Access\s*Plus|PPO|HMO|EPO|POS|Medicare|Medicaid)", text, re.IGNORECASE)
            if plan_match:
                data["plan_type"] = plan_match.group(1)
            
            # Effective Date
            eff_date = re.search(r"(?:Effective|Coverage\s*Effective)\s*(?:Date)?:?\s*(\d{1,2}/\d{1,2}/\d{2,4})", text, re.IGNORECASE)
            if eff_date:
                data["effective_date"] = eff_date.group(1)
            
            # Member ID - improved pattern
            id_patterns = [
                r"ID\s*:?\s*([A-Z0-9]{6,}(?:\s+\d+)?)",  # ID: U89084829 03
                r"Member\s*ID\s*:?\s*([A-Z0-9]+)",
                r"Subscriber\s*ID\s*:?\s*([A-Z0-9]+)",
            ]
            for pattern in id_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data["member_id"] = match.group(1).strip()
                    break
            
            # Group Number
            group_match = re.search(r"Group:?\s*(\d{5,})", text, re.IGNORECASE)
            if group_match:
                data["group_number"] = group_match.group(1)
            
            # Name - improved pattern
            name_patterns = [
                r"Name:?\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",  # Name: Varni Jain
                r"Member\s*Name:?\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
            ]
            for pattern in name_patterns:
                match = re.search(pattern, text)
                if match:
                    data["member_name"] = match.group(1).strip()
                    break
            
            # Copays - improved patterns with more flexible matching
            copay_patterns = [
                (r"PCP\s*(?:Visit)?\s*(?:Tier\s*\d+/\w+)?\s*\$(\d+)/\$?(\d+)", "copay_pcp"),
                (r"Specialist\s*(?:Tier\s*\d+/\w+)?\s*\$(\d+)/\$?(\d+)", "copay_specialist"),
                (r"Hospital\s*ER\s*\$?(\d+)", "copay_er"),
                (r"Urgent\s*Care\s*\$?(\d+)", "copay_urgent_care"),
                (r"Rx\s*\$?(\d+)/(\d+)/(\d+)", "copay_rx"),
            ]
            for pattern, field in copay_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    if len(groups) == 1:
                        data[field] = f"${groups[0]}"
                    elif len(groups) == 2:
                        data[field] = f"${groups[0]}/${groups[1]}"
                    elif len(groups) == 3:
                        data[field] = f"${groups[0]}/${groups[1]}/${groups[2]}"
            
            # Deductibles - improved patterns
            inn_ded = re.search(r"INN\s*DED\s*Ind/Fam\s*\$?(\d+)/\$?(\d+)", text, re.IGNORECASE)
            if inn_ded:
                data["deductible_individual"] = f"${inn_ded.group(1)}"
                data["deductible_family"] = f"${inn_ded.group(2)}"
            
            # Out of Pocket
            inn_oop = re.search(r"INN\s*OOP\s*Ind/Fam\s*\$?(\d+)/\$?(\d+)", text, re.IGNORECASE)
            if inn_oop:
                data["out_of_pocket_individual"] = f"${inn_oop.group(1)}"
                data["out_of_pocket_family"] = f"${inn_oop.group(2)}"
            
            # Coinsurance
            coins_in = re.search(r"In\s*(\d+)%?/(\d+)%", text, re.IGNORECASE)
            if coins_in:
                data["coinsurance_in_network"] = f"{coins_in.group(1)}%/{coins_in.group(2)}%"
            
            coins_out = re.search(r"Out\s*[-—]?\s*(\d+)%?/(\d+)%", text, re.IGNORECASE)
            if coins_out:
                data["coinsurance_out_of_network"] = f"{coins_out.group(1)}%/{coins_out.group(2)}%"
            
            # Rx identifiers
            rxbin = re.search(r"RxBIN\s*:?\s*(\d+)", text, re.IGNORECASE)
            if rxbin:
                data["rx_bin"] = rxbin.group(1)
            
            rxpcn = re.search(r"RxPCN\s*:?\s*([A-Z0-9]+)", text, re.IGNORECASE)
            if rxpcn:
                data["rx_pcn"] = rxpcn.group(1)
            
            rxgroup = re.search(r"RxGroup\s*:?\s*(\d+)", text, re.IGNORECASE)
            if rxgroup:
                data["rx_group"] = rxgroup.group(1)
                     
        return data  # Return partial data instead of error

    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """
        Parse JSON from LLM response, handling common issues.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Parsed dictionary
        """
        # Clean response
        cleaned = response.strip()
        
        # Remove markdown code blocks if present
        if cleaned.startswith("```"):
            # Find the end of the code block
            lines = cleaned.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```"):
                    in_block = not in_block
                    continue
                if in_block or not line.startswith("```"):
                    json_lines.append(line)
            cleaned = "\n".join(json_lines)
        
        # Try to find JSON in response
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if json_match:
            cleaned = json_match.group()
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            # Try to fix common issues
            cleaned = cleaned.replace("'", '"')  # Single to double quotes
            cleaned = re.sub(r',\s*}', '}', cleaned)  # Remove trailing commas
            cleaned = re.sub(r',\s*]', ']', cleaned)
            return json.loads(cleaned)

    def _validate_extraction(
        self,
        data: dict[str, Any],
        schema_class: type[BaseModel],
    ) -> dict[str, Any]:
        """
        Validate extracted data against Pydantic schema.
        
        Args:
            data: Extracted data dictionary
            schema_class: Pydantic model to validate against
            
        Returns:
            Validated dictionary (with None for invalid fields)
        """
        try:
            validated = schema_class.model_validate(data)
            return validated.model_dump(exclude_none=False)
        except ValidationError as e:
            logger.warning(f"Validation errors: {e}")
            # Return data with invalid fields set to None
            result = {}
            for field in schema_class.model_fields:
                if field in data:
                    try:
                        # Try to validate individual field
                        result[field] = data[field]
                    except Exception:
                        result[field] = None
                else:
                    result[field] = None
            return result

    def extract_with_confidence(
        self,
        text: str,
        document_type: DocumentType,
    ) -> tuple[dict[str, Any], float]:
        """
        Extract fields and estimate confidence.
        
        Args:
            text: OCR text
            document_type: Document type
            
        Returns:
            Tuple of (extracted_data, confidence_score)
        """
        extracted = self.extract(text, document_type)
        
        # Calculate confidence based on non-null fields
        schema_class = self.SCHEMA_MAP.get(document_type, GenericExtraction)
        total_fields = len(schema_class.model_fields)
        filled_fields = sum(1 for v in extracted.values() if v is not None)
        
        confidence = filled_fields / total_fields if total_fields > 0 else 0.0
        
        return extracted, confidence


def extract_document_fields(
    text: str,
    document_type: DocumentType,
    use_local_llm: bool = False,
) -> dict[str, Any]:
    """
    Convenience function to extract fields from document text.
    
    Args:
        text: Document OCR text
        document_type: Type of document
        use_local_llm: Use local Ollama instead of OpenAI
        
    Returns:
        Dictionary of extracted fields
    """
    service = ExtractionService(use_local_llm=use_local_llm)
    return service.extract(text, document_type)
