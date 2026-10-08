"""
Fills in missing 'Type' values in consolidated_dois.csv using the free CrossRef API.

Usage:
    pip install requests pandas
    python fill_publication_types.py

It only looks up DOIs currently marked "Not available" (the ones that came
from PubMed, Scopus, or the extracted list only, without a Web of Science
match). Existing Web of Science-derived types are left untouched.

Runtime: ~1-3 DOIs/sec depending on CrossRef load -> a few minutes for ~270 DOIs.
"""

import time
import requests
import pandas as pd

INPUT_FILE = "consolidated_dois.csv"
OUTPUT_FILE = "consolidated_dois_with_types.csv"

# CrossRef asks for a contact email in the User-Agent / mailto param so you get
# routed to their faster "polite pool". Put your real email here.
CONTACT_EMAIL = "your_email@example.com"

HEADERS = {
    "User-Agent": f"doi-type-lookup/1.0 (mailto:{CONTACT_EMAIL})"
}

# CrossRef 'type' values -> friendlier labels
TYPE_LABELS = {
    "journal-article": "Journal Article",
    "proceedings-article": "Proceedings Paper",
    "book-chapter": "Book Chapter",
    "book": "Book",
    "monograph": "Book",
    "reference-entry": "Reference Entry",
    "posted-content": "Preprint",
    "report": "Report",
    "dataset": "Dataset",
    "dissertation": "Dissertation",
    "peer-review": "Peer Review",
    "other": "Other",
}


def lookup_type(doi: str) -> str | None:
    url = f"https://api.crossref.org/works/{doi}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
    except requests.RequestException:
        return None

    if resp.status_code != 200:
        return None  # not found in CrossRef (e.g. some conference/DataCite DOIs)

    data = resp.json().get("message", {})
    crossref_type = data.get("type")
    if not crossref_type:
        return None
    return TYPE_LABELS.get(crossref_type, crossref_type)


def main():
    df = pd.read_csv(INPUT_FILE)
    to_lookup = df.index[df["Type"] == "Not available"].tolist()
    print(f"Looking up {len(to_lookup)} DOIs on CrossRef...")

    found, missed = 0, 0
    for i, idx in enumerate(to_lookup, 1):
        doi = df.at[idx, "DOI"]
        result = lookup_type(doi)
        if result:
            df.at[idx, "Type"] = result
            found += 1
        else:
            missed += 1

        if i % 20 == 0 or i == len(to_lookup):
            print(f"  {i}/{len(to_lookup)}  (found: {found}, missed: {missed})")

        time.sleep(0.1)  # be polite to the API

    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nDone. Found types for {found}/{len(to_lookup)} DOIs.")
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
