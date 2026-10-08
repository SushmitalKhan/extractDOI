import csv
import time
import urllib.parse
import requests

HEADERS = {"User-Agent": "ZoteroBatchImporter/1.0 (mailto:user@example.com)"}

# Read titles from your CSV file
titles = []
with open("/Users/sushmitakhan/Desktop/Research/genAI Privacy/unstructured.csv", "r", encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    for row in reader:
        if row and row[0].strip():
            # Clean up extraneous quotes
            cleaned = row[0].strip('“”" \t\r\n')
            titles.append(cleaned)

print(f"Found {len(titles)} titles. Querying Crossref...")

with open("papers_with_doi.bib", "w", encoding="utf-8") as out:
    for i, title in enumerate(titles, 1):
        print(f"[{i}/{len(titles)}] Matching: {title[:50]}...")
        q = urllib.parse.quote(title)
        url = f"https://api.crossref.org/works?query.bibliographic={q}&rows=1"

        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                items = r.json().get("message", {}).get("items", [])
                if items and "DOI" in items[0]:
                    doi = items[0]["DOI"]
                    # Fetch formatted BibTeX from DOI resolver
                    doi_url = f"https://doi.org/{doi}"
                    b_resp = requests.get(
                        doi_url,
                        headers={"Accept": "application/x-bibtex"},
                        timeout=10,
                    )
                    if b_resp.status_code == 200 and "@" in b_resp.text:
                        out.write(b_resp.text.strip() + "\n\n")
                        print(f"  -> Found DOI: {doi}")
                        time.sleep(0.3)
                        continue

            print(f"  -> No match found.")
        except Exception as e:
            print(f"  -> Error: {e}")

        time.sleep(0.3)

print("Done! Output saved to papers_with_doi.bib")