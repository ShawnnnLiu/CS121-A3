import json
import os
import glob
from bs4 import BeautifulSoup

def main():
    invertedIndex = {}
    documentCounter = 1 # first file we process will be doc #1, etc
    os.chdir("DEV")
    for file in glob.glob("*.json"): # not sure if this goes through every folder, need 2 loops?
        with open(file, 'r') as f:
            data = json.load(f)
            htmlContent = data['content'] # does this look for content tag in json file to find html? or is it htmlContent = data['html']
            soup = BeautifulSoup(html_content, 'html.parser')

            # get text?
            # use one of our tokenizers (or make some function for tokenizing)
            # we have a list of words after tokenizing
            # how to stem the words?
            # For word in list
            #   if word not in invertedIndex
            #       add to dictionary and value is documentNumber
            # documentCounter += 1
            


    #   if len(invertedIndex) > (some threshold to where its too big)
    #       sort keys alphabetically
    #       offload inverted index into a file somehow (could make a seperate folder)
    #   go to next file

# at some point, merge all indexes together

# extra credit? somehow eliminate exact duplicate pages? do we bother?