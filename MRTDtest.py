"""Unit tests for the MRTD module."""

import unittest
from unittest.mock import Mock

import MRTD


class MRTDUnitTests(unittest.TestCase):
    def setUp(self):
        self.sample_fields = {
            "document_type": "P",
            "issuing_country": "UTO",
            "surname": "ANDRES",
            "given_names": ["LEO", "MESSI"],
            "passport_number": "L898902C3",
            "nationality": "UTO",
            "birth_date": "740812",
            "sex": "F",
            "expiration_date": "120415",
            "personal_number": "ZE184226B",
        }
        self.expected_line1 = "P<UTOANDRES<<LEO<MESSI<<<<<<<<<<<<<<<<<<<<<<"
        self.expected_line2 = "L898902C31UTO7408123F1204155ZE184226B<<<<<0"
        self.expected_line2_with_composite = self.expected_line2 + "5"

    # This test checks requirement 1 by reading two valid MRZ lines from a mocked scanner.
    def test_scan_mrz_reads_two_lines_from_mock_scanner(self):
        scanner = Mock(return_value=(self.expected_line1.lower(), self.expected_line2.lower()))

        line1, line2 = MRTD.scan_mrz(scanner=scanner)

        self.assertEqual(self.expected_line1, line1)
        self.assertEqual(self.expected_line2, line2)
        scanner.assert_called_once_with()

    # This test checks requirement 1 validation when the mocked scanner does not return two lines.
    def test_scan_mrz_rejects_invalid_scanner_payload(self):
        scanner = Mock(return_value="NOT_A_PAIR")

        with self.assertRaises(ValueError):
            MRTD.scan_mrz(scanner=scanner)

    # This additional mutation-focused test checks that a three line scanner payload fails with the requirement-specific error.
    def test_scan_mrz_rejects_three_line_payload_with_clear_message(self):
        scanner = Mock(return_value=[self.expected_line1, self.expected_line2, self.expected_line2])

        with self.assertRaisesRegex(ValueError, "Scanner must return exactly two MRZ lines."):
            MRTD.scan_mrz(scanner=scanner)



    # This test checks requirement 2 by decoding a valid MRZ sample into its major document fields.
    def test_decode_mrz_parses_expected_fields(self):
        decoded = MRTD.decode_mrz(self.expected_line1, self.expected_line2)

        self.assertEqual("P", decoded["document_type"])
        self.assertEqual("UTO", decoded["issuing_country"])
        self.assertEqual("ANDRES", decoded["surname"])
        self.assertEqual(["LEO", "MESSI"], decoded["given_names"])
        self.assertEqual("L898902C3", decoded["passport_number"])
        self.assertEqual("1", decoded["passport_number_check_digit"])
        self.assertEqual("UTO", decoded["nationality"])
        self.assertEqual("740812", decoded["birth_date"])
        self.assertEqual("3", decoded["birth_date_check_digit"])
        self.assertEqual("F", decoded["sex"])
        self.assertEqual("120415", decoded["expiration_date"])
        self.assertEqual("5", decoded["expiration_date_check_digit"])
        self.assertEqual("ZE184226B", decoded["personal_number"])
        self.assertEqual("0", decoded["personal_number_check_digit"])
        self.assertIsNone(decoded["composite_check_digit"])

    # This test checks requirement 2 when an optional composite check digit is present on line 2.
    def test_decode_mrz_accepts_line2_with_composite_digit(self):
        decoded = MRTD.decode_mrz(
            self.expected_line1, self.expected_line2_with_composite
        )

        self.assertEqual("5", decoded["composite_check_digit"])

    # This test checks requirement 2 rejects MRZ input when the line lengths are incorrect.
    def test_decode_mrz_rejects_invalid_line_lengths(self):
        with self.assertRaises(ValueError):
            MRTD.decode_mrz("P<UTO", self.expected_line2)

    # This test checks requirement 2 rejects line 2 values that are not 43 or 44 characters long.
    def test_decode_mrz_rejects_invalid_line2_length(self):
        with self.assertRaises(ValueError):
            MRTD.decode_mrz(self.expected_line1, "SHORTLINE2")

    # This test checks requirement 2 rejects characters that are not part of the MRZ alphabet.
    def test_decode_mrz_rejects_invalid_characters(self):
        bad_line1 = "P<UTOANDRES<<LEO?MESSI<<<<<<<<<<<<<<<<<<<<<<"

        with self.assertRaises(ValueError):
            MRTD.decode_mrz(bad_line1, self.expected_line2)

    # This test checks requirement 2 rejects non-string MRZ values before any parsing starts.
    def test_decode_mrz_rejects_non_string_input(self):
        with self.assertRaises(TypeError):
            MRTD.decode_mrz(self.expected_line1, 12345)

    # This test checks the Group G Luhn logic for an alphanumeric field with trailing filler characters.
    def test_calculate_check_digit_supports_letters_digits_and_fillers(self):
        self.assertEqual("0", MRTD.calculate_check_digit("ZE184226B<<<<<"))

    # This test checks requirement 3 by encoding a complete field dictionary into the expected MRZ lines.
    def test_encode_mrz_builds_expected_lines_from_fields(self):
        line1, line2 = MRTD.encode_mrz(self.sample_fields)

        self.assertEqual(self.expected_line1, line1)
        self.assertEqual(self.expected_line2, line2)

    # This test checks requirement 3 by loading the document fields through a mocked database accessor.
    def test_encode_mrz_reads_fields_from_mock_database(self):
        accessor = Mock(return_value=self.sample_fields)

        line1, line2 = MRTD.encode_mrz(fields=None, document_id="DOC123", db_accessor=accessor)

        self.assertEqual(self.expected_line1, line1)
        self.assertEqual(self.expected_line2, line2)
        accessor.assert_called_once_with("DOC123")

    # This test checks requirement 3 can also encode when given names are supplied as one string.
    def test_encode_mrz_accepts_given_names_as_single_string(self):
        line1, line2 = MRTD.encode_mrz(
            dict(self.sample_fields, given_names="LEO MESSI")
        )

        self.assertEqual(self.expected_line1, line1)
        self.assertEqual(self.expected_line2, line2)

    # This test checks requirement 3 normalizes accents, punctuation, and whitespace before encoding names.
    def test_encode_mrz_normalizes_name_characters(self):
        varied_fields = {
            "document_type": "P",
            "issuing_country": "GBR",
            "surname": "O'Neil-Smith",
            "given_names": ["Ana María", "Jo"],
            "passport_number": "A12B34C56",
            "nationality": "GBR",
            "birth_date": "900101",
            "sex": "F",
            "expiration_date": "300101",
            "personal_number": "ID9001",
        }

        line1, line2 = MRTD.encode_mrz(varied_fields)

        self.assertTrue(line1.startswith("P<GBRO<NEIL<SMITH<<ANA<MARIA<JO"))
        self.assertEqual(MRTD.MRZ_LINE_1_LENGTH, len(line1))
        self.assertEqual(MRTD.MRZ_LINE_2_LENGTH, len(line2))

    # This test checks requirement 3 and requirement 2 three-letter codes such as RKS and GBP.
    def test_encode_and_decode_support_section5_country_and_nationality_codes(self):
        section5_fields = {
            "document_type": "P",
            "issuing_country": "RKS",
            "surname": "SMITH",
            "given_names": ["ELLA"],
            "passport_number": "A12345678",
            "nationality": "GBP",
            "birth_date": "850101",
            "sex": "F",
            "expiration_date": "300101",
            "personal_number": "EU2024X",
        }

        line1, line2 = MRTD.encode_mrz(section5_fields)
        decoded = MRTD.decode_mrz(line1, line2)

        self.assertEqual("RKS", decoded["issuing_country"])
        self.assertEqual("GBP", decoded["nationality"])
        self.assertEqual("SMITH", decoded["surname"])
        self.assertEqual(["ELLA"], decoded["given_names"])

    # This test checks requirement 3 collapses repeated filler markers created during name normalization.
    def test_encode_mrz_collapses_repeated_fillers_in_names(self):
        varied_fields = dict(self.sample_fields, given_names=["LEO  MESSI"])

        line1, _ = MRTD.encode_mrz(varied_fields)

        self.assertIn("<<LEO<MESSI", line1)
        self.assertNotIn("<<LEO<<MESSI", line1)

    # This test checks requirement 3 converts unsupported punctuation in names into MRZ filler characters.
    def test_encode_mrz_replaces_unsupported_name_punctuation(self):
        varied_fields = dict(self.sample_fields, given_names=["LEO.", "MESSI"])

        line1, _ = MRTD.encode_mrz(varied_fields)

        self.assertIn("<<LEO<MESSI", line1)

    # This test checks requirement 3 can optionally append the composite check digit to line 2.
    def test_encode_mrz_can_include_composite_check_digit(self):
        _, line2 = MRTD.encode_mrz(
            self.sample_fields, include_composite_check_digit=True
        )

        self.assertEqual(self.expected_line2_with_composite, line2)

    # This test checks requirement 3 rejects an incomplete field dictionary before encoding starts.
    def test_encode_mrz_rejects_missing_required_fields(self):
        incomplete_fields = dict(self.sample_fields)
        incomplete_fields.pop("sex")

        with self.assertRaises(ValueError):
            MRTD.encode_mrz(incomplete_fields)

    # This test checks requirement 3 validates the YYMMDD date format before line 2 is assembled.
    def test_encode_mrz_rejects_invalid_date_format(self):
        bad_fields = dict(self.sample_fields)
        bad_fields["birth_date"] = "19740812"

        with self.assertRaises(ValueError):
            MRTD.encode_mrz(bad_fields)

    # This test checks requirement 3 rejects invalid sex values before encoding line 2.
    def test_encode_mrz_rejects_invalid_sex_value(self):
        bad_fields = dict(self.sample_fields)
        bad_fields["sex"] = "X"

        with self.assertRaises(ValueError):
            MRTD.encode_mrz(bad_fields)

    # This test checks requirement 3 rejects invalid code-field characters such as punctuation.
    def test_encode_mrz_rejects_invalid_code_characters(self):
        bad_fields = dict(self.sample_fields)
        bad_fields["passport_number"] = "ABC#123"

        with self.assertRaises(ValueError):
            MRTD.encode_mrz(bad_fields)

    # This test checks requirement 3 rejects code fields that become empty after normalization.
    def test_encode_mrz_rejects_empty_code_after_normalization(self):
        bad_fields = dict(self.sample_fields)
        bad_fields["passport_number"] = "---"

        with self.assertRaises(ValueError):
            MRTD.encode_mrz(bad_fields)

    # This test checks requirement 3 rejects empty name content after normalization.
    def test_encode_mrz_rejects_empty_name_after_normalization(self):
        bad_fields = dict(self.sample_fields)
        bad_fields["surname"] = "---"

        with self.assertRaises(ValueError):
            MRTD.encode_mrz(bad_fields)


    # This test checks requirement 4 returns a valid result and no mismatches for a correct MRZ pair.
    def test_report_mrz_check_digit_mismatches_returns_valid_result(self):
        result = MRTD.report_mrz_check_digit_mismatches(
            self.expected_line1, self.expected_line2
        )

        self.assertTrue(result["is_valid"])
        self.assertEqual([], result["mismatches"])

    # This test checks requirement 4 reports the passport number field when only that check digit is wrong.
    def test_report_mrz_check_digit_mismatches_flags_single_passport_error(self):
        altered_line2 = "L898902C39UTO7408123F1204155ZE184226B<<<<<0"

        result = MRTD.report_mrz_check_digit_mismatches(self.expected_line1, altered_line2)

        self.assertFalse(result["is_valid"])
        self.assertEqual(
            [
                {
                    "field": "passport_number",
                    "expected_check_digit": "1",
                    "actual_check_digit": "9",
                }
            ],
            result["mismatches"],
        )

    # This test checks requirement 4 can report multiple field mismatches in the same MRZ line.
    def test_report_mrz_check_digit_mismatches_flags_multiple_errors(self):
        altered_line2 = "L898902C39UTO7408128F1204154ZE184226B<<<<<0"

        result = MRTD.report_mrz_check_digit_mismatches(self.expected_line1, altered_line2)

        self.assertFalse(result["is_valid"])
        self.assertEqual(
            ["passport_number", "birth_date", "expiration_date"],
            [item["field"] for item in result["mismatches"]],
        )

    # This test checks requirement 4 validates the optional composite digit when a 44-character line 2 is used.
    def test_report_mrz_check_digit_mismatches_flags_bad_composite_digit(self):
        altered_line2 = self.expected_line2 + "8"

        result = MRTD.report_mrz_check_digit_mismatches(self.expected_line1, altered_line2)

        self.assertFalse(result["is_valid"])
        self.assertEqual("composite", result["mismatches"][0]["field"])
        self.assertEqual("5", result["mismatches"][0]["expected_check_digit"])
        self.assertEqual("8", result["mismatches"][0]["actual_check_digit"])

    # This test checks requirement 2 can decode a name section that contains only a surname.
    def test_decode_mrz_handles_surname_without_given_names(self):
        surname_only_fields = dict(self.sample_fields, given_names=[])
        line1, line2 = MRTD.encode_mrz(surname_only_fields)

        decoded = MRTD.decode_mrz(line1, line2)

        self.assertEqual("ANDRES", decoded["surname"])
        self.assertEqual([], decoded["given_names"])

    # This test checks requirement 2 can still parse a line 1 name section even if no << delimiter exists.
    def test_decode_mrz_handles_name_section_without_delimiter(self):
        line1 = "P<UTO" + ("A" * 39)

        decoded = MRTD.decode_mrz(line1, self.expected_line2)

        self.assertEqual("A" * 39, decoded["surname"])
        self.assertEqual([], decoded["given_names"])


if __name__ == "__main__":
    unittest.main()
