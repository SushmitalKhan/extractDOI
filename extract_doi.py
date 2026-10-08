import csv
import re
import sys

def extract_all_dois_to_csv(input_bib_path, output_csv_path="dois.csv"):
    # Matches:
    # 1. doi = {10.xxxx/...}
    # 2. url = {https://doi.org/10.xxxx/...}
    # 3. @entry_type{10.xxxx/...,
    doi_pattern = re.compile(
        r'(?:doi\s*=\s*[{"]\s*|url\s*=\s*[{"](?:https?://(?:dx\.)?doi\.org/)?|@\w+\{\s*)(10\.\d{4,9}/[^\s,}"\'>]+)',
        re.IGNORECASE
    )

    seen = set()
    dois = []

    with open(input_bib_path, "r", encoding="utf-8") as f:
        for line in f:
            matches = doi_pattern.findall(line)
            for doi in matches:
                # Clean up any trailing characters
                clean_doi = doi.strip().rstrip(',}{/')
                if clean_doi and clean_doi not in seen:
                    seen.add(clean_doi)
                    dois.append(clean_doi)

    # Write to CSV
    with open(output_csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["doi"])
        for doi in dois:
            writer.writerow([doi])

    print(f"Successfully extracted {len(dois)} DOIs to '{output_csv_path}'.")

if __name__ == "__main__":
    input_file = "/Users/sushmitakhan/Desktop/Research/globalSouth_LiteratureReview/chi.bib"     # Replace with your .bib file path
    output_file = "/Users/sushmitakhan/Desktop/Research/globalSouth_LiteratureReview/chi_dois.csv"   # Desired output .csv path

    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    try:
        extract_all_dois_to_csv(input_file, output_file)
    except FileNotFoundError:
        print(f"Error: Could not find file '{input_file}'")