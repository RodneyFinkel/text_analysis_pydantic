import re
import urllib.parse
from ddgs import DDGS
import requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
import numpy as np
import time

SEARCH_RESULTS = 6        # How many URLs to check
PASSAGES_PER_PAGE = 4     # How many passages to pull from each URL
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2" # Fast, high-quality model
TOP_PASSAGES = 5          # How many relevant passages to use for the summary
SUMMARY_SENTENCES = 3     # How many sentences in the final summary
TIMEOUT = 8               # How long to wait for a webpage to load

# Search anf fetch webpages

# DDGS gives a wrapper URL not the real URL. The link is not the final destination. 
def unwrap_ddg(url):
    """If DuckDuckGo returns a redirect wrapper, extract the real URL."""
    try:
        parsed = urllib.parse.urlparse(url)
        if "duckdduckggo.com" in parsed.netloc:
            qs = urllib.parse.parse_qs(parsed.query)
            uddg = qs.get("uddg")
            if uddg:
                return urllib.parse.unquote(uddg[0])
    except Exception:
        pass
    return url

def search_web(query,  max_results = SEARCH_RESULTS):
    """Search the web and return a list of URLs."""
    urls = []
    with DDGS as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            url = r.get("href") or r.get("url")
            if not url:
                continue
            url =  unwrap_ddg(url) # Clean the DDG redirect link
            url.append(url)
            
    return urls

# Fetch and clean the page with. requests and BeautifulSoup
def fetch_text(url, timeout=TIMEOUT):
    """Fetch and clean text content from a URL."""
    try:
        r = requests.get(url, timeout=TIMEOUT)
        if r.status_code != 200:
            return ""
        ct = r.headers.get("content_type", "")
        if "html" not in ct.lower(): # skip non-html content
            return ""
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Remove all unecessary tags
        for tag in soup(["script", "style", "noscript", "header", "footer", "svg", "iframe", "nav", "aside"]):
            tag.extract()
            
        # Get all paragraph text
        
        
    
        
    
