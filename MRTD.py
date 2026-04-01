

import re
import unicodedata
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

MRZ_LINE_1_LENGTH = 44
MRZ_LINE_2_LENGTH = 43
MRZ_LINE_2_WITH_COMPOSITE_LENGTH = 44
MRZ_ALLOWED_CHARACTERS = re.compile(r"^[A-Z0-9<]+$")


def hardware_scan() -> Tuple[str, str]:
    # Placeholder for the real hardware integration.

    raise NotImplementedError("Hardware scanner integration is not implemented yet.")


def fetch_document_from_database(document_id: str) -> Dict[str, object]:
    # Placeholder for the real database integration.

    raise NotImplementedError("Database integration is not implemented yet.")


def scan_mrz(
    scanner: Optional[Callable[[], Sequence[str]]] = None,
) -> Tuple[str, str]:
    # Requirement 1: read and validate the two MRZ lines from a scanner.
    # The hardware device is injected so tests can supply a mock object/function.

    scanner_function = scanner or hardware_scan
    result = scanner_function()

    if not isinstance(result, (tuple, list)) or len(result) != 2:
        raise ValueError("Scanner must return exactly two MRZ lines.")

    line1, line2 = result
    return _normalize_and_validate_lines(line1, line2)


def decode_mrz(line1: str, line2: str) -> Dict[str, object]:
    # Requirement 2: decode two MRZ lines into their document fields.

    normalized_line1, normalized_line2 = _normalize_and_validate_lines(line1, line2)
    parsed_line1 = _parse_line1(normalized_line1)
    parsed_line2 = _parse_line2(normalized_line2)

    decoded = {}
    decoded.update(parsed_line1)
    decoded.update(parsed_line2)
    return decoded


def encode_mrz(
    fields: Optional[Dict[str, object]] = None,
    document_id: Optional[str] = None,
    db_accessor: Optional[Callable[[str], Dict[str, object]]] = None,
    include_composite_check_digit: bool = False,
) -> Tuple[str, str]:
    # Requirement 3: encode travel-document fields into two MRZ lines.

    if fields is None:
        if not document_id:
            raise ValueError("document_id is required when fields are not provided.")
        accessor = db_accessor or fetch_document_from_database
        fields = accessor(document_id)

    prepared = _prepare_fields(fields)

    name_section = _encode_name_section(prepared["surname"], prepared["given_names"])
    line1 = (
        prepared["document_type"]
        + "<"
        + _pad_field(prepared["issuing_country"], 3)
        + _pad_field(name_section, MRZ_LINE_1_LENGTH - 5)
    )

    passport_field = _pad_field(prepared["passport_number"], 9)
    birth_field = _validate_date_field(prepared["birth_date"], "birth_date")
    expiration_field = _validate_date_field(
        prepared["expiration_date"], "expiration_date"
    )
    personal_field = _pad_field(prepared["personal_number"], 14)

    passport_digit = calculate_check_digit(passport_field)
    birth_digit = calculate_check_digit(birth_field)
    expiration_digit = calculate_check_digit(expiration_field)
    personal_digit = calculate_check_digit(personal_field)

    line2 = (
        passport_field
        + passport_digit
        + _pad_field(prepared["nationality"], 3)
        + birth_field
        + birth_digit
        + prepared["sex"]
        + expiration_field
        + expiration_digit
        + personal_field
        + personal_digit
    )

    if include_composite_check_digit:
        composite_source = (
            passport_field
            + passport_digit
            + birth_field
            + birth_digit
            + expiration_field
            + expiration_digit
            + personal_field
            + personal_digit
        )
        line2 += calculate_check_digit(composite_source)

    return line1, line2


def report_mrz_check_digit_mismatches(line1: str, line2: str) -> Dict[str, object]:
    # Requirement 4: report where MRZ check-digit mismatches occur.

    decoded = decode_mrz(line1, line2)
    mismatches = []

    fields_to_check = [
        ("passport_number", "passport_number_check_digit", _pad_field(decoded["passport_number"], 9)),
        ("birth_date", "birth_date_check_digit", decoded["birth_date"]),
        ("expiration_date", "expiration_date_check_digit", decoded["expiration_date"]),
        ("personal_number", "personal_number_check_digit", _pad_field(decoded["personal_number"], 14)),
    ]

    for field_name, digit_name, value in fields_to_check:
        expected_digit = calculate_check_digit(value)
        actual_digit = decoded[digit_name]
        if actual_digit != expected_digit:
            mismatches.append(
                {
                    "field": field_name,
                    "expected_check_digit": expected_digit,
                    "actual_check_digit": actual_digit,
                }
            )

    composite_digit = decoded.get("composite_check_digit")
    if composite_digit is not None:
        composite_source = (
            _pad_field(decoded["passport_number"], 9)
            + decoded["passport_number_check_digit"]
            + decoded["birth_date"]
            + decoded["birth_date_check_digit"]
            + decoded["expiration_date"]
            + decoded["expiration_date_check_digit"]
            + _pad_field(decoded["personal_number"], 14)
            + decoded["personal_number_check_digit"]
        )
        expected_composite_digit = calculate_check_digit(composite_source)
        if composite_digit != expected_composite_digit:
            mismatches.append(
                {
                    "field": "composite",
                    "expected_check_digit": expected_composite_digit,
                    "actual_check_digit": composite_digit,
                }
            )

    return {"is_valid": not mismatches, "mismatches": mismatches, "decoded_fields": decoded}











# HELPER_FUNCTIONS
def calculate_check_digit(value: str) -> str:
    # Calculate a single decimal check digit using Luhn algorithm.

    numeric_text = _mrz_text_to_luhn_digits(value)
    checksum = _luhn_checksum(numeric_text + "0")
    return str((10 - checksum) % 10)


def _normalize_and_validate_lines(line1: str, line2: str) -> Tuple[str, str]:
    normalized_line1 = _normalize_mrz_text(line1)
    normalized_line2 = _normalize_mrz_text(line2)

    if len(normalized_line1) != MRZ_LINE_1_LENGTH:
        raise ValueError("MRZ line 1 must contain exactly 44 characters.")

    if len(normalized_line2) not in (
        MRZ_LINE_2_LENGTH,
        MRZ_LINE_2_WITH_COMPOSITE_LENGTH,
    ):
        raise ValueError("MRZ line 2 must contain 43 or 44 characters.")

    return normalized_line1, normalized_line2


def _normalize_mrz_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("MRZ values must be strings.")

    normalized = text.strip().upper()
    if not MRZ_ALLOWED_CHARACTERS.fullmatch(normalized):
        raise ValueError("MRZ values may contain only A-Z, 0-9, and '<'.")

    return normalized


def _parse_line1(line1: str) -> Dict[str, object]:
    name_section = line1[5:]
    surname_raw, given_names_raw = _split_name_section(name_section)

    return {
        "document_type": line1[0],
        "issuing_country": line1[2:5].replace("<", ""),
        "surname": _decode_name_component(surname_raw),
        "given_names": _decode_given_names(given_names_raw),
    }


def _parse_line2(line2: str) -> Dict[str, object]:
    decoded = {
        "passport_number": line2[0:9].rstrip("<"),
        "passport_number_check_digit": line2[9],
        "nationality": line2[10:13].replace("<", ""),
        "birth_date": line2[13:19],
        "birth_date_check_digit": line2[19],
        "sex": line2[20],
        "expiration_date": line2[21:27],
        "expiration_date_check_digit": line2[27],
        "personal_number": line2[28:42].rstrip("<"),
        "personal_number_check_digit": line2[42],
    }

    if len(line2) == MRZ_LINE_2_WITH_COMPOSITE_LENGTH:
        decoded["composite_check_digit"] = line2[43]
    else:
        decoded["composite_check_digit"] = None

    return decoded


def _prepare_fields(fields: Dict[str, object]) -> Dict[str, str]:
    required_keys = [
        "document_type",
        "issuing_country",
        "surname",
        "given_names",
        "passport_number",
        "nationality",
        "birth_date",
        "sex",
        "expiration_date",
        "personal_number",
    ]

    missing_keys = [key for key in required_keys if key not in fields]
    if missing_keys:
        raise ValueError("Missing required MRTD fields: {0}".format(", ".join(missing_keys)))

    given_names_value = fields["given_names"]
    if isinstance(given_names_value, str):
        given_names = [
            _sanitize_name_component(name)
            for name in given_names_value.split()
            if name.strip()
        ]
    else:
        given_names = [
            _sanitize_name_component(str(name))
            for name in given_names_value
            if str(name).strip()
        ]

    prepared = {
        "document_type": _sanitize_code(str(fields["document_type"]), 1),
        "issuing_country": _sanitize_code(str(fields["issuing_country"]), 3),
        "surname": _sanitize_name_component(str(fields["surname"])),
        "given_names": given_names,
        "passport_number": _sanitize_code(str(fields["passport_number"]), 9),
        "nationality": _sanitize_code(str(fields["nationality"]), 3),
        "birth_date": str(fields["birth_date"]).strip(),
        "sex": _sanitize_sex(str(fields["sex"])),
        "expiration_date": str(fields["expiration_date"]).strip(),
        "personal_number": _sanitize_code(str(fields["personal_number"]), 14),
    }

    return prepared


def _sanitize_code(value: str, max_length: int) -> str:
    normalized = _ascii_upper(value)
    cleaned = normalized.replace(" ", "").replace("-", "").replace("_", "")
    if not cleaned:
        raise ValueError("Code fields may not be empty.")

    if not re.fullmatch(r"[A-Z0-9]+", cleaned):
        raise ValueError("Code fields may contain only letters and digits.")

    return cleaned[:max_length]


def _sanitize_name_component(value: str) -> str:
    normalized = _ascii_upper(value)
    translated = []
    for char in normalized:
        if char.isalnum():
            translated.append(char)
        elif char in {" ", "-", "'"}:
            translated.append("<")
        else:
            translated.append("<")

    cleaned = "".join(translated).strip("<")
    if not cleaned:
        raise ValueError("Name fields may not be empty.")

    while "<<" in cleaned:
        cleaned = cleaned.replace("<<", "<")

    return cleaned


def _sanitize_sex(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in {"M", "F", "<"}:
        raise ValueError("sex must be 'M', 'F', or '<'.")
    return normalized


def _encode_name_section(surname: str, given_names: Iterable[str]) -> str:
    parts = [surname]
    normalized_given_names = [name for name in given_names if name]
    if normalized_given_names:
        parts.append("<".join(normalized_given_names))

    return "<<".join(parts)


def _split_name_section(name_section: str) -> Tuple[str, str]:
    if "<<" in name_section:
        surname_raw, given_names_raw = name_section.split("<<", 1)
    else:
        surname_raw, given_names_raw = name_section, ""
    return surname_raw.rstrip("<"), given_names_raw.rstrip("<")


def _decode_name_component(value: str) -> str:
    return value.replace("<", " ").strip()


def _decode_given_names(value: str) -> List[str]:
    if not value:
        return []
    return [part for part in (_decode_name_component(piece) for piece in value.split("<")) if part]


def _pad_field(value: str, length: int) -> str:
    sanitized = value[:length]
    return sanitized.ljust(length, "<")


def _validate_date_field(value: str, field_name: str) -> str:
    if not re.fullmatch(r"\d{6}", value):
        raise ValueError("{0} must contain exactly 6 digits in YYMMDD format.".format(field_name))
    return value


def _mrz_text_to_luhn_digits(value: str) -> str:
    normalized = _normalize_mrz_text(value)
    digits = []
    for char in normalized:
        if char.isdigit():
            digits.append(char)
        elif char == "<":
            digits.append("0")
        else:
            digits.append(str(ord(char) - ord("A") + 10))
    return "".join(digits)


def _luhn_checksum(number: str) -> int:
    digits = [int(character) for character in number]
    parity = len(digits) % 2
    total = 0

    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit

    return total % 10


def _ascii_upper(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_only.upper()
