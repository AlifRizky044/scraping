import csv

input_file = "data/data.csv"
output_file = "data/faq_fixed.csv"

with open(input_file, newline="", encoding="utf-8") as f_in, \
     open(output_file, "w", newline="", encoding="utf-8") as f_out:

    reader = csv.reader(f_in)
    writer = csv.writer(f_out, quoting=csv.QUOTE_ALL)

    for row in reader:
        if len(row) >= 3:
            writer.writerow([row[0], row[1], ",".join(row[2:])])

print("✅ CSV aman, semua field di-quote")
