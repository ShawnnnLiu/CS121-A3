import time
from nltk.stem import PorterStemmer
import re
import json
import math

def tokenize(text):
    return re.findall(r'\b\w+\b', text.lower())

def load_data():
    with open("inverted_index.json", "r") as f:
        inverted_index = json.load(f)
    with open("doc_id_table.json", "r") as f:
        doc_id_table = json.load(f)
    id_to_doc = {int(v): k for k, v in doc_id_table.items()}
    N = len(doc_id_table)
    return inverted_index, id_to_doc, N

def single_query(query, inverted_index, id_to_doc, N):
    stemmer = PorterStemmer()
    query_tokens = [stemmer.stem(tok) for tok in tokenize(query)]
    # collect doc‐ID sets for each token
    doc_sets = []
    for tok in query_tokens:
        if tok in inverted_index:
            doc_ids = set(map(int, inverted_index[tok].keys()))
            doc_sets.append(doc_ids)
        else:
            # if any token is missing, no results
            return []
    # intersection for AND
    matching_docs = set.intersection(*doc_sets) if doc_sets else set()
    if not matching_docs:
        return []
    # compute TF‐IDF scores
    doc_scores = {}
    for tok in query_tokens:
        postings = inverted_index[tok]
        df = len(postings)
        idf = math.log(N / df) if df > 0 else 0.0
        for did_str, tf in postings.items():
            did = int(did_str)
            if did in matching_docs:
                doc_scores[did] = doc_scores.get(did, 0.0) + tf * idf
    # sort by (score desc, did asc) and take top 5
    scored = [ (score, -did) for did, score in doc_scores.items() ]
    scored.sort(reverse=True)
    top5 = scored[:5]
    return [ (id_to_doc[-tup[1]], tup[0]) for tup in top5 ]

def run_batch():
    inverted_index, id_to_doc, N = load_data()
    results = {}
    timings  = {}
    with open("test_queries.txt") as f:
        for line in f:
            q = line.strip()
            t0 = time.time()
            top5 = single_query(q, inverted_index, id_to_doc, N)
            t1 = time.time()
            results[q] = top5
            timings[q] = (t1 - t0) * 1000  # milliseconds
    # dump both to disk for inspection
    with open("batch_results.json", "w") as f:
        json.dump(results, f, indent=2)
    with open("batch_timings.json", "w") as f:
        json.dump(timings, f, indent=2)
    print("Batch run complete; results → batch_results.json, timings → batch_timings.json")

if __name__ == "__main__":
    run_batch()
