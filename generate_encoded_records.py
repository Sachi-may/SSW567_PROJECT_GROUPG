import json
from MRTD import encode_mrz

INPUT_FILE = "records_decoded.json"
OUTPUT_FILE = "records_encoded.json"


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


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as infile:
        data = json.load(infile)

    decoded_records = data["records_decoded"]
    encoded_records = []

    for record in decoded_records:
        fields = convert_record_to_fields(record)
        line1, line2 = encode_mrz(fields, include_composite_check_digit=True)
        encoded_records.append(f"{line1};{line2}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:
        json.dump({"records_encoded": encoded_records}, outfile, indent=2)

    print(f"Created {OUTPUT_FILE} with {len(encoded_records)} encoded records.")


if __name__ == "__main__":
    main()