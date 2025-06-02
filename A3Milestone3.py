import time
import json
import math
import re
from nltk.stem import PorterStemmer
from tkinter import Tk, Label, Entry, Button, Text, END, Scrollbar, RIGHT, Y

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
    scored = [(score, -did) for did, score in doc_scores.items()]
    scored.sort(reverse=True)
    top5 = scored[:5]
    return [(id_to_doc[-tup[1]], tup[0]) for tup in top5]

class SearchGUI:
    def __init__(self, master):
        self.master = master
        master.title("ICS Search Engine")

        # Load index once
        self.inverted_index, self.id_to_doc, self.N = load_data()

        # Label and entry for the query
        self.label = Label(master, text="Enter search query:")
        self.label.pack(pady=(10, 0))

        self.entry = Entry(master, width=60)
        self.entry.pack(pady=(0, 10))
        self.entry.bind('<Return>', self.perform_search)

        # Search button
        self.search_button = Button(master, text="Search", command=self.perform_search)
        self.search_button.pack()

        # Label to display search time
        self.time_label = Label(master, text="Search time: N/A")
        self.time_label.pack(pady=(10, 0))

        # Text area (with scrollbar) to display top 5 results
        self.scrollbar = Scrollbar(master)
        self.scrollbar.pack(side=RIGHT, fill=Y)

        self.result_box = Text(master, height=10, width=80, wrap='word', yscrollcommand=self.scrollbar.set)
        self.result_box.pack(pady=(5, 10))
        self.scrollbar.config(command=self.result_box.yview)

    def perform_search(self, event=None):
        query = self.entry.get().strip()
        if not query:
            return

        # Time the search
        t0 = time.time()
        top5 = single_query(query, self.inverted_index, self.id_to_doc, self.N)
        t1 = time.time()
        elapsed_ms = (t1 - t0) * 1000

        # Print to terminal
        print(f"Query: '{query}'  —  time: {elapsed_ms:.2f} ms")

        # Update GUI time label
        self.time_label.config(text=f"Search time: {elapsed_ms:.2f} ms")

        # Display results in the text box
        self.result_box.delete(1.0, END)
        if not top5:
            self.result_box.insert(END, "No results found.\n")
        else:
            for i, (url, score) in enumerate(top5, start=1):
                self.result_box.insert(END, f"{i}. {url}  (score={score:.4f})\n")

if __name__ == "__main__":
    root = Tk()
    gui = SearchGUI(root)
    root.mainloop()
