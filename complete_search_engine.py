import time
import json
import math
import re
from nltk.stem import PorterStemmer
from flask import Flask, request, render_template_string

def tokenize(text):
    return re.findall(r'\b\w+\b', text.lower())

def load_data():
    with open("inverted_index.json", "r") as f:
        inverted_index = json.load(f)
    with open("doc_id_table.json", "r") as f:
        doc_id_table = json.load(f)
    with open("pagerank.json", "r") as f:
        pagerank_raw = json.load(f)
    with open("doc_url_table.json", "r") as f:
        doc_url_table_raw = json.load(f)

    # Convert doc_id_table keys to int → filepath mapping
    id_to_doc = {int(v): k for k, v in doc_id_table.items()}
    # Convert pagerank keys from strings to ints
    pagerank = {int(k): v for k, v in pagerank_raw.items()}
    # Convert doc_url_table keys from strings to ints
    doc_url_table = {int(k): v for k, v in doc_url_table_raw.items()}

    N = len(doc_id_table)
    return inverted_index, id_to_doc, pagerank, doc_url_table, N

def single_query(query, inverted_index, id_to_doc, pagerank, doc_url_table, N):
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
    tfidf_scores = {}
    for tok in query_tokens:
        postings = inverted_index[tok]
        df = len(postings)
        idf = math.log(N / df) if df > 0 else 0.0
        for did_str, tf in postings.items():
            did = int(did_str)
            if did in matching_docs:
                tfidf_scores[did] = tfidf_scores.get(did, 0.0) + tf * idf
    # combine TF‐IDF and PageRank for each matching doc
    combined_scores = {}
    for did, tfidf_score in tfidf_scores.items():
        pr_score = pagerank.get(did, 0.0)
        combined_scores[did] = 0.7 * tfidf_score + 0.3 * pr_score
    # sort by (combined score desc, doc_id asc) and take top 5
    scored = [(score, -did) for did, score in combined_scores.items()]
    scored.sort(reverse=True)
    top5 = scored[:5]
    # Return (filepath, url, score)
    results = []
    for score, neg_did in top5:
        did = -neg_did
        filepath = id_to_doc.get(did, "")
        url = doc_url_table.get(did, "")
        results.append((filepath, url, score))
    return results

# Initialize Flask app
app = Flask(__name__)

# Load index, PageRank, and URL table once at startup
inverted_index, id_to_doc, pagerank, doc_url_table, N = load_data()

# HTML template for search page and results
def get_template():
    return """
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>ICS Search Engine</title>
        <style>
          body {
            background-color: #f5f7fa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
          }
          h1 {
            margin-top: 40px;
            color: #333;
          }
          form {
            display: flex;
            justify-content: center;
            margin: 20px 0;
          }
          input[type="text"] {
            width: 400px;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 4px 0 0 4px;
            font-size: 16px;
            outline: none;
          }
          button {
            padding: 10px 20px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 0 4px 4px 0;
            font-size: 16px;
            cursor: pointer;
            transition: background-color 0.2s ease-in-out;
          }
          button:hover {
            background-color: #0056b3;
          }
          .time-label {
            color: #555;
            margin-bottom: 20px;
          }
          .results-container {
            width: 80%;
            max-width: 800px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 40px;
          }
          .results-container h2 {
            margin-top: 0;
            color: #333;
          }
          ol {
            padding-left: 20px;
          }
          li {
            margin-bottom: 15px;
            line-height: 1.5;
          }
          .filepath {
            font-weight: bold;
            color: #555;
          }
          .url-link {
            color: #007bff;
            text-decoration: none;
          }
          .url-link:hover {
            text-decoration: underline;
          }
          .score {
            color: #333;
            font-size: 14px;
          }
        </style>
      </head>
      <body>
        <h1>ICS Search Engine</h1>
        <form action="/search" method="get">
          <input type="text" id="query" name="query" placeholder="Enter search query..." value="{{ query or '' }}">
          <button type="submit">Search</button>
        </form>
        {% if time is not none %}
          <div class="time-label">Search time: {{ "%.2f"|format(time) }} ms</div>
        {% endif %}
        {% if results is not none %}
          <div class="results-container">
            <h2>Results:</h2>
            {% if results %}
              <ol>
              {% for filepath, url, score in results %}
                <li>
                  <div class="filepath">Path: {{ filepath }}</div>
                  <div><a href="{{ url }}" class="url-link" target="_blank">{{ url }}</a></div>
                  <div class="score">Score: {{ "%.4f"|format(score) }}</div>
                </li>
              {% endfor %}
              </ol>
            {% else %}
              <p>No results found.</p>
            {% endif %}
          </div>
        {% endif %}
      </body>
    </html>
    """

@app.route('/', methods=['GET'])
def index():
    # Show empty form on landing
    return render_template_string(get_template(), results=None, time=None, query=None)

@app.route('/search', methods=['GET'])
def perform_search():
    query = request.args.get('query', '').strip()
    if not query:
        return render_template_string(get_template(), results=None, time=None, query=None)

    # Time the search
    t0 = time.time()
    top5 = single_query(query, inverted_index, id_to_doc, pagerank, doc_url_table, N)
    t1 = time.time()
    elapsed_ms = (t1 - t0) * 1000

    return render_template_string(
        get_template(),
        results=top5,
        time=elapsed_ms,
        query=query
    )

if __name__ == "__main__":
    app.run(debug=True)
