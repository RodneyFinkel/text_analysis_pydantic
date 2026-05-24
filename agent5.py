import re
import urllib.parse
from ddgs import DDGS
import requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
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
        if "duckduckgo.com" in parsed.netloc:
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
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            url = r.get("href") or r.get("url")
            if not url:
                continue
            url =  unwrap_ddg(url) # Clean the DDG redirect link
            urls.append(url)
            
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
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        text = " ".join([p for p in paragraphs if p])
        
        if text.strip():
            # Clean up whitespace
            return re.sub(r"\s+", " ", text).strip()
            
        # --- Fallback logic if <p> tags fail ---
        meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if meta and meta.get("content"):
            return meta["content"].strip()
        if soup.title and soup.title.string:
            return soup.title.string.strip()
            
    except Exception:
        return "" # Fail silently
    return ""
        
        
# Chunk, embed and rank passages
def chunk_passages(text, max_words=120, overlap=20):
    """Split long text into smaller passages."""
    words = text.split()
    if not words:
        return []
    chunks = []
    i = 0
    while i < len(words):
        chunk = words[i: i + max_words]
        chunks.append(" ".join(chunk))
        i += max_words - overlap
        if i < 0:
            i = max_words - overlap // 2
    return chunks
    
def split_sentences(text):
    """A simple sentence splitter."""
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [p.strip() for p in parts if p.strip()]


class ShortResearchAgent():
    def __init__(self, embed_model=EMBEDDING_MODEL):
        print(f"Loading embedder: {embed_model}...")
        # This downloads the model on first run
        self.embedder = SentenceTransformer(embed_model)
        
        
    def run(self, query):
        start = time.time()
        # 1. Search
        urls = search_web(query)
        print(f"Found {len(urls)} urls.")
        # 2. Fetch and chunks
        docs = []
        for u in urls:
            txt = fetch_text(u)
            if not txt:
                continue
            chunks = chunk_passages(txt, max_words=120, overlap=20)
            for c in chunks[ : PASSAGES_PER_PAGE]:
                docs.append({"url": u, "passage": c})
                
        if not docs:
            print("No documents fetched.")
            return {"query": query, "passages": [], "summary": ""}
        
        # 3. Embed (Turn text into numbers)
        texts = [d["passage"] for d in docs]
        emb_txts = self.embedder.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        q_emb = self.embedder.encode(query, convert_to_numpy=True)
        
        # 4. Rank (Find similarity) USE CUSTOM COSINE FUNCTION OR SKLEARN
        # CUSTOM FUNCTION
        def cosine(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + + 1e-10) 
        
       
        # USING Scikit Learn
        def cosine_sklearn(a, b):
            a = np.asarray(a).reshape(1, -1)
            b = np.asarray(b).reshape(1, -1)
            similarity = cosine_similarity(a, b)[0][0] # original function from sklearn
            return similarity
        
        # sims = [cosine(e, q_emb) for e in emb_txts]
        sims = [cosine_sklearn(e, q_emb) for e in emb_txts]
        top_idx = np.argsort(sims)[::-1][:TOP_PASSAGES]
        top_passages = [{"url": docs[i]["url"], "passage": docs[i]["passage"], "score": float(sims[i])} for i in top_idx]
        
        # 5. Rerank passages to passages to create a mini summary
        sentences = []
        for tp in top_passages:
            for s in split_sentences(tp["passage"]):
                sentences.append({"sent": s, "url": tp["url"]})
                
        if not sentences:
            summary = "No summary could be generated"
        else:
            sent_texts = [s["sent"]for s in sentences]
            sent_embs = self.embedder.encode(sent_texts, convert_to_numpy=True, show_progress_bar=False)
            sent_sims = [cosine_sklearn(e, q_emb) for e in sent_embs]
            
            top_sent_idx = np.argsort(sent_sims)[::-1][:SUMMARY_SENTENCES]
            chosen = [sentences[idx] for idx in top_sent_idx]
            
            # deduplicate and format
            seen = set()
            lines = []
            for s in chosen:
                key = s["sent"].lower()[:80] # check first 80 chars
                if key in seen:
                    continue # continue to next item (key) in the loop
                seen.add(key)
                lines.append(f"{s['sent']} (Source: {s['url']})")
            summary = " ".join(lines)
            
        elapsed = time.time() - start
        return {"query": query, "passages": top_passages, "summary": summary, "time": elapsed}
    
                            
        
if __name__=="__main__":
    agent = ShortResearchAgent()
    q = "What causes urban heat islands and how can cities reduce them?"
    
    print(f"Running query: {q}\n")
    out = agent.run(q)
    
    print("\nTop passages:")
    for p in out["passages"]:
        print(f"- score {p['score']:.3f} src {p['url']}\n  {p['passage'][:200]}...\n")
        
    print("--- Extractive summary ---")
    print(out["summary"])
    print("--------------------------")
    print(f"\nDone in {out['time']:.1f}s")
    
             
             
            
            

    
        
        
        
    
        
    
