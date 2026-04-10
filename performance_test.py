import csv
import json
import time
from MRTD import encode_mrz, decode_mrz

DECODED_FILE = "records_decoded.json"
ENCODED_FILE = "records_encoded.json"
CSV_FILE = "timing_results.csv"

SIZES = [100, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]


def convert_record_to_fields(record):
    return {
        "document_type": "P",
        "issuing_country": record["line1"]["issuing_country"],
        "surname": record["line1"]["last_name"],
        "given_names": record["line1"]["given_name"],
        "passport_number": record["line2"]["passport_number"],
        "nationality": record["line2"]["country_code"],
        "birth_date": record["line2"]["birth_date"],
        "sex": record["line2"]["sex"],
        "expiration_date": record["line2"]["expiration_date"],
        "personal_number": record["line2"]["personal_number"],
    }


def load_decoded_records():
    with open(DECODED_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["records_decoded"]


def load_encoded_records():
    with open(ENCODED_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["records_encoded"]


def encode_without_test(records):
    for record in records:
        fields = convert_record_to_fields(record)
        encode_mrz(fields, include_composite_check_digit=True)


def encode_with_test(records):
    for record in records:
        fields = convert_record_to_fields(record)
        line1, line2 = encode_mrz(fields, include_composite_check_digit=True)

        assert isinstance(line1, str)
        assert isinstance(line2, str)
        assert len(line1) == 44
        assert len(line2) == 44
        assert ";" not in line1
        assert ";" not in line2


def decode_without_test(records):
    for entry in records:
        line1, line2 = entry.split(";")
        decode_mrz(line1, line2)


def decode_with_test(records):
    for entry in records:
        line1, line2 = entry.split(";")
        decoded = decode_mrz(line1, line2)

        assert "passport_number" in decoded
        assert "birth_date" in decoded
        assert "expiration_date" in decoded
        assert "surname" in decoded
        assert "given_names" in decoded
        assert len(line1) == 44
        assert len(line2) == 44


def measure_time(function, records):
    start = time.perf_counter()
    function(records)
    end = time.perf_counter()
    return end - start


def main():
    decoded_records = load_decoded_records()
    encoded_records = load_encoded_records()

    results = []

    for size in SIZES:
        print(f"Measuring size {size}...")

        decoded_subset = decoded_records[:size]
        encoded_subset = encoded_records[:size]

        enc_no_test = measure_time(encode_without_test, decoded_subset)
        enc_with_test = measure_time(encode_with_test, decoded_subset)
        dec_no_test = measure_time(decode_without_test, encoded_subset)
        dec_with_test = measure_time(decode_with_test, encoded_subset)

        results.append([
            size,
            enc_with_test,
            enc_no_test,
            dec_with_test,
            dec_no_test,
        ])

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "num_records",
            "enc_with_test_s",
            "enc_without_test_s",
            "dec_with_test_s",
            "dec_without_test_s",
        ])
        writer.writerows(results)

    print(f"Created {CSV_FILE}")


if __name__ == "__main__":
    main()