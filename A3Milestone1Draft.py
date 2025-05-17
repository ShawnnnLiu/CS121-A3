import json
import os
import glob
from bs4 import BeautifulSoup
import re
from collections import defaultdict
from tqdm import tqdm
import hashlib



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


    for filepath in tqdm(filepaths, desc="Processing files"): # I changed this to search for all subdirectories instead of 2 loops
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
            tokens = tokenize(text)
            # we have a list of words after tokenizing
            # how to stem the words?
            # TBI

            # For word in tokens
            #   if word not in invertedIndex
            #       add to dictionary and value is documentNumber
            # documentCounter += 1


            # Inside the file loop:
            for word in tokens:
                if filepath not in invertedIndex[word]:
                    invertedIndex[word][filepath] = 1
                else:
                    invertedIndex[word][filepath] += 1

            
                    
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
    

    #   if len(invertedIndex) > (some threshold to where its too big)
    #       # next 2 lines sorts keys alphabetically
    #       newList = sorted(myDict.items()) 
    #       alphabeticallySorted = dict(newList)
    #       TBI: offload inverted index into a file somehow (could make a seperate folder)
    #   go to next file
    
# at some point, merge all indexes together into a file

main()