"""
Fills remaining gaps in consolidated_dois.csv (Type, Venue, Abstract, Keywords)
using the free CrossRef API (https://api.crossref.org/works/{doi}).

Usage:
    pip install requests pandas
    python enrich_dois.py

--------------------------------------------------------------------------
IMPORTANT LIMITATION -- read before relying on the Type column for ACM
--------------------------------------------------------------------------
CrossRef only stores a COARSE top-level type per DOI:
    journal-article, proceedings-article, book-chapter, book,
    posted-content, dataset, report, dissertation, peer-review, other...

It does NOT store ACM's internal content-type breakdown (Research Paper,
Short Paper, Poster, Demonstration, Extended Abstract, Late-Breaking Work,
Doctoral Consortium, Tutorial, Workshop Summary, Keynote, Invited Talk,
etc.). That classification lives only in ACM's own e-Rights/Digital Library
metadata system and is not exposed through CrossRef's public API -- no
script calling CrossRef can recover it, because the data simply isn't
there. If you need that level of granularity for the ACM-sourced DOIs,
you would have to pull it from the ACM Digital Library page for each
paper directly (manually, or via an ACM DL API/export if your institution
has access to one).

Everything below fetches what CrossRef *does* have: coarse type,
container-title (venue), abstract (when the publisher submitted one), and
subject tags. Note "subject" is NOT the same thing as author keywords --
CrossRef doesn't store author keywords at all -- so Keywords coverage from
this API will be thin. It's included as a best-effort fallback only for
DOIs where the local files (Scopus/WoS) didn't already supply keywords.
--------------------------------------------------------------------------

Only rows still marked "Not available" in a given column are looked up,
and each DOI is queried once regardless of how many fields it's missing.
"""

import re
import time
import requests
import pandas as pd

INPUT_FILE = "consolidated_dois.csv"
OUTPUT_FILE = "consolidated_dois_enriched.csv"

# CrossRef routes you to a faster "polite pool" if you identify yourself.
CONTACT_EMAIL = "your_email@example.com"
HEADERS = {"User-Agent": f"doi-enrichment-lookup/1.0 (mailto:{CONTACT_EMAIL})"}

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

TAG_RE = re.compile(r"<[^>]+>")


def clean_abstract(raw: str) -> str:
    """CrossRef abstracts are JATS XML, e.g. '<jats:p>Some text</jats:p>'."""
    text = TAG_RE.sub(" ", raw)
    return re.sub(r"\s+", " ", text).strip()


def lookup_crossref(doi: str) -> dict:
    url = f"https://api.crossref.org/works/{doi}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
    except requests.RequestException:
        return {}

    if resp.status_code != 200:
        return {}  # DOI not registered with CrossRef (e.g. some DataCite DOIs)

    m = resp.json().get("message", {})

    result = {}

    crossref_type = m.get("type")
    if crossref_type:
        result["type"] = TYPE_LABELS.get(crossref_type, crossref_type)

    container = m.get("container-title")  # journal name or proceedings/conference name
    if container:
        result["venue"] = container[0] if isinstance(container, list) else container

    raw_abstract = m.get("abstract")
    if raw_abstract:
        result["abstract"] = clean_abstract(raw_abstract)

    subjects = m.get("subject")  # best-effort only -- not author keywords
    if subjects:
        result["keywords"] = "; ".join(subjects)

    return result


def main():
    df = pd.read_csv(INPUT_FILE)

    needs_lookup = df.index[
        (df["Type"] == "Not available")
        | (df["Venue"] == "Not available")
        | (df["Abstract"] == "Not available")
        | (df["Keywords"] == "Not available")
    ].tolist()
    print(f"Looking up {len(needs_lookup)} DOIs on CrossRef...")

    counts = {"type": 0, "venue": 0, "abstract": 0, "keywords": 0}
    no_data = 0

    for i, idx in enumerate(needs_lookup, 1):
        doi = df.at[idx, "DOI"]
        result = lookup_crossref(doi)

        if not result:
            no_data += 1
        else:
            for field, col in [("type", "Type"), ("venue", "Venue"),
                                ("abstract", "Abstract"), ("keywords", "Keywords")]:
                if df.at[idx, col] == "Not available" and result.get(field):
                    df.at[idx, col] = result[field]
                    counts[field] += 1

        if i % 20 == 0 or i == len(needs_lookup):
            print(f"  {i}/{len(needs_lookup)}  "
                  f"type:{counts['type']} venue:{counts['venue']} "
                  f"abstract:{counts['abstract']} keywords:{counts['keywords']} "
                  f"no-match:{no_data}")

        time.sleep(0.1)  # be polite to the API

    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nDone. Filled -- type: {counts['type']}, venue: {counts['venue']}, "
          f"abstract: {counts['abstract']}, keywords: {counts['keywords']}")
    print(f"Saved to {OUTPUT_FILE}")
    print("\nReminder: 'Keywords' from CrossRef are publisher subject tags, not "
          "author keywords, and ACM's granular paper-type breakdown is not in "
          "CrossRef at all -- see the notice at the top of this script.")


if __name__ == "__main__":
    main()
