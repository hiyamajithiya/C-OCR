"""
Validation service for extracted field values.
Includes regex patterns for Indian documents (PAN, GSTIN, etc.).
"""

import re
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import structlog

logger = structlog.get_logger()


class ValidationService:
    """Service for validating extracted field values."""

    # Indian document patterns
    PATTERNS = {
        "pan": r"^[A-Z]{5}[0-9]{4}[A-Z]$",
        "gstin": r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{3}$",
        "aadhaar": r"^\d{12}$",
        "cin": r"^[UL][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$",
        "ifsc": r"^[A-Z]{4}0[A-Z0-9]{6}$",
        "phone_in": r"^[6-9]\d{9}$",
        "pincode": r"^\d{6}$",
        "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        "amount": r"^\d+(\.\d{1,2})?$",
        "invoice_no": r"^[A-Z0-9\-/]+$",
    }

    # Date formats
    DATE_FORMATS = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d, %Y",
    ]

    def __init__(self):
        """Initialize validation service."""
        pass

    def validate_field(
        self, field_value: str, field_type: str, custom_pattern: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a field value against expected format.

        Args:
            field_value: Value to validate
            field_type: Type of field (pan, gstin, date, amount, etc.)
            custom_pattern: Optional custom regex pattern

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not field_value:
            return False, "Empty value"

        # Clean value
        cleaned_value = field_value.strip()

        try:
            # Use custom pattern if provided
            if custom_pattern:
                return self._validate_pattern(cleaned_value, custom_pattern)

            # Validate based on field type
            if field_type == "pan":
                return self.validate_pan(cleaned_value)
            elif field_type == "gstin":
                return self.validate_gstin(cleaned_value)
            elif field_type == "aadhaar":
                return self.validate_aadhaar(cleaned_value)
            elif field_type == "cin":
                return self.validate_cin(cleaned_value)
            elif field_type == "ifsc":
                return self.validate_ifsc(cleaned_value)
            elif field_type == "date":
                return self.validate_date(cleaned_value)
            elif field_type == "amount":
                return self.validate_amount(cleaned_value)
            elif field_type == "email":
                return self.validate_email(cleaned_value)
            elif field_type == "phone":
                return self.validate_phone(cleaned_value)
            elif field_type == "pincode":
                return self.validate_pincode(cleaned_value)
            else:
                # No specific validation
                return True, None

        except Exception as e:
            logger.error("validation_failed", field_type=field_type, error=str(e))
            return False, f"Validation error: {str(e)}"

    def validate_pan(self, pan: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Indian PAN (Permanent Account Number).
        Format: AAAAA9999A

        Args:
            pan: PAN number

        Returns:
            Tuple of (is_valid, error_message)
        """
        pan = pan.upper().replace(" ", "")

        if not re.match(self.PATTERNS["pan"], pan):
            return False, "Invalid PAN format. Expected: AAAAA9999A"

        # Additional check: 4th character should be P for person, C for company, etc.
        valid_4th_chars = ["P", "C", "H", "F", "A", "T", "B", "L", "J", "G"]
        if pan[3] not in valid_4th_chars:
            return False, f"Invalid PAN entity type: {pan[3]}"

        return True, None

    def validate_gstin(self, gstin: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Indian GSTIN (Goods and Services Tax Identification Number).
        Format: 99AAAAA9999A9Z9

        Args:
            gstin: GSTIN number

        Returns:
            Tuple of (is_valid, error_message)
        """
        gstin = gstin.upper().replace(" ", "")

        if not re.match(self.PATTERNS["gstin"], gstin):
            return False, "Invalid GSTIN format. Expected: 99AAAAA9999A9Z9"

        # Validate state code (first 2 digits)
        state_code = int(gstin[:2])
        if state_code < 1 or state_code > 37:
            return False, f"Invalid state code: {state_code}"

        # Check if PAN portion is valid
        pan_portion = gstin[2:12]
        is_valid_pan, _ = self.validate_pan(pan_portion)
        if not is_valid_pan:
            return False, "Invalid PAN portion in GSTIN"

        return True, None

    def validate_aadhaar(self, aadhaar: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Indian Aadhaar number.
        Format: 999999999999 (12 digits)

        Args:
            aadhaar: Aadhaar number

        Returns:
            Tuple of (is_valid, error_message)
        """
        aadhaar = aadhaar.replace(" ", "").replace("-", "")

        if not re.match(self.PATTERNS["aadhaar"], aadhaar):
            return False, "Invalid Aadhaar format. Expected: 12 digits"

        return True, None

    def validate_cin(self, cin: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Corporate Identity Number (CIN).
        Format: U/L99999XX9999XXX999999

        Args:
            cin: CIN number

        Returns:
            Tuple of (is_valid, error_message)
        """
        cin = cin.upper().replace(" ", "")

        if not re.match(self.PATTERNS["cin"], cin):
            return False, "Invalid CIN format"

        return True, None

    def validate_ifsc(self, ifsc: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Indian Financial System Code (IFSC).
        Format: AAAA0AAAAAA

        Args:
            ifsc: IFSC code

        Returns:
            Tuple of (is_valid, error_message)
        """
        ifsc = ifsc.upper().replace(" ", "")

        if not re.match(self.PATTERNS["ifsc"], ifsc):
            return False, "Invalid IFSC format. Expected: AAAA0AAAAAA"

        return True, None

    def validate_date(self, date_str: str) -> Tuple[bool, Optional[str]]:
        """
        Validate date string in various formats.

        Args:
            date_str: Date string

        Returns:
            Tuple of (is_valid, error_message)
        """
        for date_format in self.DATE_FORMATS:
            try:
                datetime.strptime(date_str, date_format)
                return True, None
            except ValueError:
                continue

        return (
            False,
            f"Invalid date format. Supported: {', '.join(self.DATE_FORMATS[:3])}",
        )

    def validate_amount(self, amount_str: str) -> Tuple[bool, Optional[str]]:
        """
        Validate amount/currency value.

        Args:
            amount_str: Amount string

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Remove common currency symbols and separators
        cleaned = amount_str.replace("\u20b9", "").replace("$", "").replace(",", "").strip()

        if not re.match(self.PATTERNS["amount"], cleaned):
            return False, "Invalid amount format"

        try:
            float(cleaned)
            return True, None
        except ValueError:
            return False, "Amount must be a valid number"

    def validate_email(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Validate email address.

        Args:
            email: Email address

        Returns:
            Tuple of (is_valid, error_message)
        """
        email = email.lower().strip()

        if not re.match(self.PATTERNS["email"], email):
            return False, "Invalid email format"

        return True, None

    def validate_phone(self, phone: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Indian phone number.

        Args:
            phone: Phone number

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Remove common separators
        cleaned = (
            phone.replace(" ", "")
            .replace("-", "")
            .replace("+91", "")
            .replace("(", "")
            .replace(")", "")
        )

        if not re.match(self.PATTERNS["phone_in"], cleaned):
            return False, "Invalid phone format. Expected: 10 digits starting with 6-9"

        return True, None

    def validate_pincode(self, pincode: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Indian PIN code.

        Args:
            pincode: PIN code

        Returns:
            Tuple of (is_valid, error_message)
        """
        pincode = pincode.replace(" ", "")

        if not re.match(self.PATTERNS["pincode"], pincode):
            return False, "Invalid PIN code. Expected: 6 digits"

        return True, None

    def _validate_pattern(self, value: str, pattern: str) -> Tuple[bool, Optional[str]]:
        """
        Validate value against custom regex pattern.

        Args:
            value: Value to validate
            pattern: Regex pattern

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if re.match(pattern, value):
                return True, None
            else:
                return False, f"Value does not match pattern: {pattern}"
        except re.error as e:
            return False, f"Invalid regex pattern: {str(e)}"

    def normalize_value(self, value: str, field_type: str) -> str:
        """
        Normalize field value to standard format.

        Args:
            value: Value to normalize
            field_type: Field type

        Returns:
            Normalized value
        """
        value = value.strip()

        if field_type in ["pan", "gstin", "cin", "ifsc"]:
            return value.upper().replace(" ", "")

        elif field_type == "phone":
            return value.replace(" ", "").replace("-", "").replace("+91", "")

        elif field_type == "amount":
            return value.replace("\u20b9", "").replace("$", "").replace(",", "").strip()

        elif field_type == "email":
            return value.lower()

        return value

    def cross_validate(
        self, extracted_fields: Dict[str, Any], rules: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """
        Perform cross-validation between fields.
        Example: sum of table column = total amount

        Args:
            extracted_fields: Extracted fields dictionary
            rules: Validation rules

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors = []

        for rule in rules:
            rule_type = rule.get("type")

            if rule_type == "sum_equals":
                # Validate sum of fields equals target field
                source_fields = rule.get("source_fields", [])
                target_field = rule.get("target_field")

                try:
                    total = sum(
                        float(extracted_fields.get(f, {}).get("value", 0))
                        for f in source_fields
                    )
                    expected = float(
                        extracted_fields.get(target_field, {}).get("value", 0)
                    )

                    if (
                        abs(total - expected) > 0.01
                    ):  # Allow small floating point differences
                        errors.append(
                            f"Sum validation failed: {source_fields} sum ({total}) != {target_field} ({expected})"
                        )
                except (ValueError, TypeError) as e:
                    errors.append(f"Sum validation error: {str(e)}")

        is_valid = len(errors) == 0

        return is_valid, errors


# Global validation service instance
validation_service = ValidationService()
