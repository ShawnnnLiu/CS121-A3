import json
import os
import glob
from bs4 import BeautifulSoup
import re
from collections import defaultdict
from tqdm import tqdm
import hashlib
from nltk.stem import PorterStemmer
from collections import Counter

# Batch size for offloading partial indexes
BATCH_SIZE = 10000

def tokenize(text):
    return re.findall(r'\b\w+\b', text.lower())  # split into lowercase words

def main():
    # Change into the DEV directory where all JSON files reside
    os.chdir("DEV")

    # Gather all JSON file paths
    filepaths = sorted(glob.glob("**/*.json", recursive=True))

    # Prepare mappings:
    #   doc_id_table: filepath → int ID
    #   url_to_doc_id: normalized URL → int ID
    doc_id_table = {}
    url_to_doc_id = {}

    # First pass: assign doc IDs and record each document's URL
    for doc_id, filepath in enumerate(tqdm(filepaths, desc="Assigning doc IDs")):
        doc_id_table[filepath] = doc_id
        with open(filepath, 'r') as f:
            data = json.load(f)
            # Assume each JSON has a 'url' field
            url = data.get('url')
            if isinstance(url, str):
                url_to_doc_id[url] = doc_id

    # Initialize data structures for duplicate detection
    hashTable = {}                    # maps content-hash → first-seen filepath
    dupReport = defaultdict(list)     # maps original filepath → list of its duplicates

    stemmer = PorterStemmer()

    # Prepare directory for partial indexes
    os.makedirs("../partial_indexes", exist_ok=True)

    # This will hold the in-memory inverted index for the current batch:
    #    token → { doc_id: frequency, ... }
    invertedIndex = defaultdict(dict)

    batch_count = 0
    docs_in_batch = 0

    # Second pass: process each document, build/boost term frequencies, and offload in batches
    for doc_id, filepath in enumerate(tqdm(filepaths, desc="Processing files")):
        with open(filepath, 'r') as f:
            data = json.load(f)
            htmlContent = data.get('content', "")
            if not isinstance(htmlContent, str):
                print(f"Skipping non-str content in {filepath}: type={type(htmlContent)}")
                continue

            soup = BeautifulSoup(htmlContent, 'html.parser')  # parse HTML

            # Extract text for duplicate detection
            text = soup.get_text()
            standardizedText = " ".join(text.split())
            # Hash the standardized text
            hashedPage = hashlib.sha256(standardizedText.encode("utf-8")).hexdigest()
            if hashedPage in hashTable:
                dupReport[hashTable[hashedPage]].append(filepath)
            else:
                hashTable[hashedPage] = filepath

            # --- BOOSTS: Title and H1 ---
            # Title boost: +3 per token in <title>
            title_tag = soup.title
            if title_tag and title_tag.string:
                title_text = title_tag.string
                title_tokens = [stemmer.stem(token) for token in tokenize(title_text)]
                for token in title_tokens:
                    # Add boost to this doc's term frequency
                    invertedIndex[token][doc_id] = invertedIndex[token].get(doc_id, 0) + 3

            # H1 boost: +2 per token in each <h1>
            for h1_tag in soup.find_all('h1'):
                h1_text = h1_tag.get_text()
                h1_tokens = [stemmer.stem(token) for token in tokenize(h1_text)]
                for token in h1_tokens:
                    invertedIndex[token][doc_id] = invertedIndex[token].get(doc_id, 0) + 2

            # --- BODY TOKENS: base frequency +1 ---
            body_text = soup.get_text()  # we already have text; reusing for simplicity
            body_tokens = [stemmer.stem(token) for token in tokenize(body_text)]
            for token in body_tokens:
                # Add base count for each token occurrence
                invertedIndex[token][doc_id] = invertedIndex[token].get(doc_id, 0) + 1

            # --- ANCHOR BOOST: +5 per token in anchor text for linked doc ---
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                # If this href matches a known URL in our corpus, boost linked doc's TF
                target_id = url_to_doc_id.get(href)
                if target_id is not None:
                    link_text = a_tag.get_text()
                    link_tokens = [stemmer.stem(token) for token in tokenize(link_text)]
                    for token in link_tokens:
                        invertedIndex[token][target_id] = invertedIndex[token].get(target_id, 0) + 5

        docs_in_batch += 1

        # When batch size reached, offload current invertedIndex to disk
        if docs_in_batch == BATCH_SIZE:
            batch_filename = f"../partial_indexes/partial_index_{batch_count}.json"
            # Convert defaultdict to normal dict for JSON serialization
            serializable = {token: {str(did): freq for did, freq in postings.items()}
                            for token, postings in invertedIndex.items()}
            with open(batch_filename, "w") as batch_file:
                json.dump(serializable, batch_file, indent=2)
            # Clear in-memory index and reset batch counter
            invertedIndex.clear()
            docs_in_batch = 0
            batch_count += 1

    # Offload any remaining documents not filling a full batch
    if docs_in_batch > 0:
        batch_filename = f"../partial_indexes/partial_index_{batch_count}.json"
        serializable = {token: {str(did): freq for did, freq in postings.items()}
                        for token, postings in invertedIndex.items()}
        with open(batch_filename, "w") as batch_file:
            json.dump(serializable, batch_file, indent=2)
        invertedIndex.clear()
        batch_count += 1

    # Save duplicate report
    dupDict = {orig: dups for orig, dups in dupReport.items() if dups}
    with open("../exact_duplicates.json", "w") as f:
        json.dump(dupDict, f, indent=2)
    print(f"exact_duplicates.json has {len(dupDict)} entries")
    print("saved exact_duplicates.json to", os.path.abspath("../exact_duplicates.json"))

    # Save doc_id_table
    with open("../doc_id_table.json", "w") as f:
        json.dump(doc_id_table, f, indent=2)

    # --- MERGE PHASE: combine all partial indexes into one final index ---
    finalIndex = defaultdict(dict)
    partial_files = sorted(glob.glob("../partial_indexes/partial_index_*.json"))

    for pfile in tqdm(partial_files, desc="Merging partial indexes"):
        with open(pfile, "r") as f:
            part = json.load(f)
            for token, postings in part.items():
                for did_str, freq in postings.items():
                    did = int(did_str)
                    # Sum frequencies if the token-doc pair already exists
                    finalIndex[token][did] = finalIndex[token].get(did, 0) + freq

    # Write merged index to disk
    regular_dict = {token: {did: freq for did, freq in postings.items()}
                    for token, postings in finalIndex.items()}
    with open("../inverted_index.json", "w") as f:
        json.dump(regular_dict, f, indent=2)

    # --- ANALYTICS & REPORTING ---
    num_docs = len(filepaths)
    num_tokens = len(finalIndex)
    index_size_kb = os.path.getsize("../inverted_index.json") / 1024

    report_text = (
        "--- M1 Report Summary ---\n"
        f"Indexed documents: {num_docs}\n"
        f"Unique tokens: {num_tokens}\n"
        f"Index file size: {index_size_kb:.2f} KB\n"
    )

    with open("../m1_report.txt", "w") as f:
        f.write(report_text)

    print("Saved M1 stats")

    # Compute extra statistics
    total_tokens = 0
    for postings in finalIndex.values():
        total_tokens += sum(postings.values())
    avg_tokens_per_doc = total_tokens / num_docs if num_docs else 0

    token_freq = Counter()
    for token, postings in finalIndex.items():
        token_freq[token] = sum(postings.values())
    top_10_tokens = token_freq.most_common(10)

    duplicate_doc_count = sum(len(v) for v in dupDict.values())
    avg_tf_per_doc = total_tokens / num_docs if num_docs else 0

    extra_stats = (
        f"Average tokens per document: {avg_tokens_per_doc:.2f}\n"
        f"Average token frequency per document: {avg_tf_per_doc:.2f}\n"
        f"Duplicate document count: {duplicate_doc_count}\n"
        "\nTop 10 most frequent tokens:\n"
    )
    for token, freq in top_10_tokens:
        extra_stats += f"{token}: {freq}\n"

    with open("../m1_extra_analytics.txt", "w") as f:
        f.write(extra_stats)

if __name__ == "__main__":
    main()
