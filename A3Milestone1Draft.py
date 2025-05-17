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



def tokenize(text):
    return re.findall(r'\b\w+\b', text.lower())  # split into lowercase words

def main():
    documentCounter = 1 # first file we process will be doc #1, etc
    os.chdir("DEV")

    # initialize the inverted index, this initialization automatically creates a new empty dict if you access a key that does not exist
    invertedIndex = defaultdict(dict)  
    filepaths = glob.glob("**/*.json", recursive=True)

    #hashtable stores 1st file path that generates a particular hash
    hashTable = {}
    dupReport = defaultdict(list)

    stemmer = PorterStemmer()



    doc_id_table = {}  # maps file path → int ID

    for doc_id, filepath in enumerate(tqdm(filepaths, desc="Processing files")): # I changed this to search for all subdirectories instead of 2 loops
        doc_id_table[filepath] = doc_id
        with open(filepath, 'r') as f:
            data = json.load(f)
            htmlContent = data['content'] # does this look for content tag in json file to find html? or is it htmlContent = data['html']
            if not isinstance(htmlContent, str):
                print(f"Skipping non-str content in {filepath}: type={type(htmlContent)}")
                continue

            soup = BeautifulSoup(htmlContent, 'html.parser')  # typo fix

            text = soup.get_text() # get text from html content

            #standardizes all whitespace (newlines, page breaks, multiple spaces) into single spaces
            standardizedText = " ".join(text.split())
            #hashes the file, if it already exists in the table, add file path to the dupe report
            #otherwise record it as an original file
            hashedPage = hashlib.sha256(standardizedText.encode("utf-8")).hexdigest()
            if hashedPage in hashTable:
                dupReport[hashTable[hashedPage]].append(filepath)
            else:
                hashTable[hashedPage] = filepath


            # use one of our tokenizers (or make some function for tokenizing)
            # we have a list of words after tokenizing
            # how to stem the words?

            tokens = [stemmer.stem(token) for token in tokenize(text)]
            

            # For word in tokens
            #   if word not in invertedIndex
            #       add to dictionary and value is documentNumber
            # documentCounter += 1


            # Inside the file loop:
            for word in tokens:
                if doc_id not in invertedIndex[word]:
                    invertedIndex[word][doc_id] = 1
                else:
                    invertedIndex[word][doc_id] += 1

            
                    
    regular_dict = {}
    for key in invertedIndex:
        regular_dict[key] = dict(invertedIndex[key])

    with open("../inverted_index.json", "w") as f:
        json.dump(regular_dict, f, indent=2)


    
    #only include files that have a value (duplicate) for key (original file)
    dupDict = {}
    for k, v in dupReport.items():
        if v:
            dupDict[k] = v

    #outputs new file listing all dups
    with open("../exact_duplicates.json", "w") as f:
        json.dump(dupDict, f, indent=2)
    print(f"exact_duplicates.json has {len(dupDict)} entries")
    print("saved exact_duplicates.json to", os.path.abspath("../exact_duplicates.json"))

    with open("../doc_id_table.json", "w") as f:
        json.dump(doc_id_table, f, indent=2)


    num_docs = len(filepaths)
    num_tokens = len(invertedIndex)
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

    total_tokens = 0
    for postings in invertedIndex.values():
        total_tokens += sum(postings.values())
    avg_tokens_per_doc = total_tokens / len(filepaths)

    # top 10 most frequent tokens (total across all docs)
    token_freq = Counter()
    for token, postings in invertedIndex.items():
        token_freq[token] = sum(postings.values())
    top_10_tokens = token_freq.most_common(10)

    # dupe count
    duplicate_doc_count = sum(len(v) for v in dupDict.values())

    # avg token frequency
    avg_tf_per_doc = total_tokens / len(filepaths)

    # --- Output or save analytics ---
    extra_stats = (
        f"Average tokens per document: {avg_tokens_per_doc:.2f}\n"
        f"Average token frequency per document: {avg_tf_per_doc:.2f}\n"
        f"Duplicate document count: {duplicate_doc_count}\n"
        "\nTop 10 most frequent tokens:\n"
    )
    for token, freq in top_10_tokens:
        extra_stats += f"{token}: {freq}\n"

    # Save to file
    with open("../m1_extra_analytics.txt", "w") as f:
        f.write(extra_stats)


        

    #   if len(invertedIndex) > (some threshold to where its too big)
    #       # next 2 lines sorts keys alphabetically
    #       newList = sorted(myDict.items()) 
    #       alphabeticallySorted = dict(newList)
    #       TBI: offload inverted index into a file somehow (could make a seperate folder)
    #   go to next file
    
# at some point, merge all indexes together into a file

main()