"""
build_doc_url_table.py

Reads `doc_id_table.json` to get each document’s relative path (under DEV/),
opens each JSON in DEV/, extracts its "url" field, and writes a new
`doc_url_table.json` mapping doc_id -> URL.


Assumes:
 - `doc_id_table.json` is in the same directory as this script.
 - A subdirectory named DEV/ holds all the crawled JSON files.
 - Each JSON inside DEV/ contains a "url" field.
"""

import json
import os

def load_doc_id_table(path="doc_id_table.json"):
    """Load mapping: filepath (relative to DEV/) -> doc_id (int)."""
    with open(path, "r") as f:
        return json.load(f)

def main():
    # 1. Load the existing doc_id_table.json
    if not os.path.isfile("doc_id_table.json"):
        print("ERROR: doc_id_table.json not found in current directory.")
        return

    doc_id_table = load_doc_id_table()

    # 2. For each filepath under DEV/, open and extract "url"
    doc_url_table = {}
    missing_count = 0

    for rel_path, doc_id in doc_id_table.items():
        full_path = os.path.join("DEV", rel_path)
        if not os.path.isfile(full_path):
            print(f"WARNING: {full_path} not found; skipping.")
            missing_count += 1
            continue

        with open(full_path, "r") as f:
            data = json.load(f)
            url = data.get("url")
            if isinstance(url, str):
                doc_url_table[str(doc_id)] = url
            else:
                # If "url" field missing or not a string, leave blank or skip
                doc_url_table[str(doc_id)] = ""
                missing_count += 1

    # 3. Write out doc_url_table.json
    with open("doc_url_table.json", "w") as out_f:
        json.dump(doc_url_table, out_f, indent=2)

    total = len(doc_id_table)
    print(f"Processed {total} documents; {missing_count} had missing URLs.")
    print("doc_url_table.json written to", os.path.abspath("doc_url_table.json"))

if __name__ == "__main__":
    main()
