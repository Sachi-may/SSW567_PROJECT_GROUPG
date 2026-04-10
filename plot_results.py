import csv
import matplotlib.pyplot as plt

CSV_FILE = "timing_results.csv"
PLOT_FILE = "timing_plot.png"

num_records = []
enc_with_test = []
enc_without_test = []
dec_with_test = []
dec_without_test = []

with open(CSV_FILE, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        num_records.append(int(row["num_records"]))
        enc_with_test.append(float(row["enc_with_test_s"]))
        enc_without_test.append(float(row["enc_without_test_s"]))
        dec_with_test.append(float(row["dec_with_test_s"]))
        dec_without_test.append(float(row["dec_without_test_s"]))

plt.figure(figsize=(10, 6))
plt.plot(num_records, enc_with_test, marker="o", label="Encode with Testing")
plt.plot(num_records, enc_without_test, marker="o", label="Encode without Testing")
plt.plot(num_records, dec_with_test, marker="o", label="Decode with Testing")
plt.plot(num_records, dec_without_test, marker="o", label="Decode without Testing")

plt.xlabel("Number of Records Processed")
plt.ylabel("Execution Time (seconds)")
plt.title("Performance of MRTD Encode and Decode Functions")
plt.legend()
plt.grid(True)

plt.savefig(PLOT_FILE, dpi=300, bbox_inches="tight")
plt.show()

print(f"Created {PLOT_FILE}")