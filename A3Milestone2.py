import json
import re

def tokenize(text):
    return re.findall(r'\b\w+\b', text.lower())  # split into lowercase words

def main():
    print("INF141 Group 42 Inverted Index Query Processing!")
    query = input("Enter a query: ")

    # should we also stem query?
    queryTokens = tokenize(query) # tokenize query and put into list
    setOfQueryTokens = set(queryTokens) # eliminate duplicate words in query

    # give initial/sentinel value in set so it isn't empty? (struggling here) 
    # problem: dont want to do and (intersection) with empty set
    # another problem: if we have set {0} and set {1, 4, 6} at 
    # the start for example, and'ing them will be empty set, which will be a problem
    # in later iterations of for loop of finding word in index
   
    setOfDocs = {0} # hold all doc IDs in setOfDocs
    setToMerge = {} # to be figured out, will this be needed?

    with open("../inverted_index.json", 'r') as f:
        wordIndex = json.load(f)
        
        for word in setOfQueryTokens:
            if word in wordIndex:
                # wordIndex.values() gets dict for docIDs to word frequency
                # get the keys (docIDs) with .items()
                setToMerge = (wordIndex.values()).items()

                # this line should work? if 6 words for example are found in the same document
                # (ex, all 6 words appear in doc 4, 7, and 8), does this mean the set will never be empty?
                setOfDocs = setOfDocs & setToMerge

                # to be continued


    if len(setOfDocs) == 0:
        print("No results found.")
    else:
        print("Top 5 results for ", query)
        # show URLs somehow, hash docID to URL?
