"""
pagerank.py

Compute PageRank scores over the corpus without performing any search.
Reads `doc_id_table.json` and the JSON files in DEV/ to build the link graph,
runs the PageRank algorithm, and writes the resulting scores to `pagerank.json`.

"""

import json
import os
import glob
import math
import re
from collections import defaultdict
from bs4 import BeautifulSoup
from tqdm import tqdm

# PageRank parameters
DAMPING_FACTOR = 0.85
PAGERANK_ITERATIONS = 20
PAGERANK_TOLERANCE = 1e-6

def load_doc_id_table(path="doc_id_table.json"):
    """Load mapping: filepath (relative to DEV) → doc_id (int)."""
    with open(path, "r") as f:
        return json.load(f)

def build_link_graph(doc_id_table, dev_dir="DEV"):
    """
    Parse every document in DEV/, extract <a href="..."> links, map to doc IDs,
    and build an adjacency list: doc_id → set(outgoing doc_ids).
    """
    # Build URL → doc_id from doc_id_table
    url_to_doc = {}
    for rel_path, doc_id in doc_id_table.items():
        full_path = os.path.join(dev_dir, rel_path)
        if not os.path.isfile(full_path):
            continue
        with open(full_path, "r") as f:
            data = json.load(f)
            url = data.get("url")
            if isinstance(url, str):
                url_to_doc[url] = doc_id

    adjacency = defaultdict(set)
    all_rel_paths = list(doc_id_table.keys())

    # Now scan each file in DEV/ to collect outgoing links
    for rel_path in tqdm(all_rel_paths, desc="Building link graph"):
        src_id = doc_id_table[rel_path]
        full_path = os.path.join(dev_dir, rel_path)
        if not os.path.isfile(full_path):
            continue

        with open(full_path, "r") as f:
            data = json.load(f)
            html = data.get("content", "")
            if not isinstance(html, str):
                continue
            soup = BeautifulSoup(html, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                tgt_id = url_to_doc.get(href)
                if tgt_id is not None and tgt_id != src_id:
                    adjacency[src_id].add(tgt_id)

    return adjacency

def compute_pagerank(adjacency, num_docs):
    """
    Compute PageRank over num_docs pages using adjacency list.
    adjacency: dict(doc_id → set(outgoing doc_ids))
    Returns: dict(doc_id → pagerank score)
    """
    # Precompute out-degree for each page
    outdeg = {i: len(adjacency.get(i, set())) for i in range(num_docs)}

    # Build in-links map: for each page i, inlinks[i] = set of pages that link to i
    inlinks = {i: set() for i in range(num_docs)}
    for src, neighbors in adjacency.items():
        for tgt in neighbors:
            inlinks[tgt].add(src)

    # Initialize PR vector: PR[i] = 1/N
    N = num_docs
    d = DAMPING_FACTOR
    pr = {i: 1.0 / N for i in range(N)}

    # Identify dangling nodes (pages with no outgoing links)
    dangling_nodes = {i for i, deg in outdeg.items() if deg == 0}

    for _ in tqdm(range(PAGERANK_ITERATIONS), desc="PageRank iterations"):
        new_pr = {}
        # Sum of PR of all dangling nodes
        dangling_sum = sum(pr[p] for p in dangling_nodes)

        for i in range(N):
            # Base term: (1 - d) / N
            rank_i = (1 - d) / N

            # Dangling contribution: d * (sum of PR of dangling pages) / N
            rank_i += d * (dangling_sum / N)

            # In-link contribution: d * Σ_{j ∈ inlinks[i]} [ PR[j] / outdeg[j] ]
            inlink_sum = 0.0
            for j in inlinks[i]:
                inlink_sum += pr[j] / outdeg[j]
            rank_i += d * inlink_sum

            new_pr[i] = rank_i

        # Check convergence (L1 norm)
        diff = sum(abs(new_pr[i] - pr[i]) for i in range(N))
        pr = new_pr
        if diff < PAGERANK_TOLERANCE:
            break

    return pr

def main():
    # 1. Load document ID mapping
    print("Loading doc_id_table.json...")
    if not os.path.isfile("doc_id_table.json"):
        print("ERROR: doc_id_table.json not found in current directory.")
        return

    doc_id_table = load_doc_id_table()
    num_docs = len(doc_id_table)
    print(f"Found {num_docs} documents in doc_id_table.json.")

    # 2. Build adjacency list (link graph)
    print("Building link graph (scanning DEV/) ...")
    adjacency = build_link_graph(doc_id_table)

    # 3. Compute PageRank scores
    print("Computing PageRank scores...")
    pr_scores = compute_pagerank(adjacency, num_docs)

    # 4. Serialize to pagerank.json
    pr_serializable = {str(doc_id): score for doc_id, score in pr_scores.items()}
    output_path = "pagerank.json"
    with open(output_path, "w") as out_f:
        json.dump(pr_serializable, out_f, indent=2)

    print(f"PageRank computation complete. Scores saved to {os.path.abspath(output_path)}")

if __name__ == "__main__":
    main()
