import json
import re
import math
from nltk.stem import PorterStemmer

def tokenize(text):
    return re.findall(r'\b\w+\b', text.lower())  # split into lowercase words




def main():
    # load the files first, moved to start of process for a cleaner look
    with open("inverted_index.json", "r") as f:
        inverted_index = json.load(f)

    with open("doc_id_table.json", "r") as f:
        doc_id_table = json.load(f)
        id_to_doc = {v: k for k, v in doc_id_table.items()}

    print("INF141 Group 42 Inverted Index Query Processing!")
    query = input("Enter a query: ")


    # should we also stem query? YES
    # query tokens are stemmed to match the porter-stemmed-index
    stemmer = PorterStemmer()
    query_tokens = [stemmer.stem(tok) for tok in tokenize(query)]

    # 1. give initial/sentinel value in set so it isn't empty? (struggling here) 
    # 2. problem: dont want to do and (intersection) with empty set
    # 3. another problem: if we have set {0} and set {1, 4, 6} at 
    # the start for example, and'ing them will be empty set, which will be a problem
    # in later iterations of for loop of finding word in index
   
    # setOfDocs = {0} # hold all doc IDs in setOfDocs
    # setToMerge = {} # to be figured out, will this be needed?

    """ 
    shawn: I decided to take a different approach that avoids the issues listed above. with doc_sets, no
    assumptions need to be made with the inital values (false positive results!)

    with the original approach, "setOfDocs = setOfDocs & setToMerge" was ran every loop which is a logical error
    that results in setOfDocs becoming empty immediately even if other query words appear in the same documents later.
    doc_sets results that as it cumulatively collects all doc ids that appears in the index before doing any AND operations
    """

    """ 
    doc_sets:
        contains sets of files that contain the queries
        for example:
            if query = "cristina lopes"
        doc_sets[0] contains a set of all doc ids with cristina in it
        doc_sets[1] contains a set of all doc ids with lopes in it
        solves issues 1-3
    """
    doc_sets = []


    for token in query_tokens:
        if token in inverted_index:
            doc_ids = set(map(int, inverted_index[token].keys()))
            doc_sets.append(doc_ids)
        else:
            print(f"No results found for token: '{token}'")
            return

    
    # with open("../inverted_index.json", 'r') as f:
    #     wordIndex = json.load(f)
        
    #     for word in setOfQueryTokens:
    #         if word in wordIndex:
    #             # wordIndex.values() gets dict for docIDs to word frequency
    #             # get the keys (docIDs) with .items()
    #             setToMerge = (wordIndex.values()).items()

    #             # this line should work? if 6 words for example are found in the same document
    #             # (ex, all 6 words appear in doc 4, 7, and 8), does this mean the set will never be empty?
    #             setOfDocs = setOfDocs & setToMerge

    #             # to be continued


     # perform AND across all doc sets
    if doc_sets:
        matching_docs = set.intersection(*doc_sets)
    else:
        matching_docs = set()

    if not matching_docs:
        print("No results found.")
    else:
        #holds total score for all the matching docs
        doc_scores = {}
        N = len(doc_id_table)

        #idf uses log formula from math library, if df is 0 it's set to 0 to avoid undefined result
        for tok in query_tokens:
            postings = inverted_index[tok]
            df = len(postings)
            idf = math.log(N / df) if df != 0 else 0

            #iterates over documents with the current token
            #checks if doc id is in matching docs to satisfy boolean AND condition
            #increments doc scores w/ sum over query tokens
            for did_str, tf in postings.items():
                did = int(did_str)
                if did in matching_docs:
                    score = tf * idf
                    doc_scores[did] = doc_scores.get(did, 0) + score

        #tuple contains a primary sort key, and a secondary key for tiebreakers (in cases of matching scores)
        #doc_id order is reversed since we prefer lower numbered documents when scores are the same
        score_tuples = []
        for doc_id, score in doc_scores.items():
            score_tuples.append((score, -doc_id))

        #sort in descending order w/ highest score first, then ascending doc id, giving only the top 5
        score_tuples.sort(reverse=True)
        top5 = score_tuples[:5]

        #modified printing to use tf-idf metric
        print(f"\nTop 5 results for '{query}':")
        for i, tup in enumerate(top5, 1):
            doc_id = -tup[1]
            score = tup[0]
            print(f"{i}. {id_to_doc[doc_id]} (tf-idf={score:.4f})")



main()