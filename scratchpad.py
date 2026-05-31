import asyncio
import aiohttp

async def fetch_text_async(session: aiohttp.ClientSession, url: str, timeout: int TIMEOUT):
    """ Asynchronously fetch and clean text content from a URL."""
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "DNT": 1,
        "Connection": "keep-alive"
    }
    
    print(f"Fetching: {url} (asynchronously)")
    try:
        async with session.get(url, timeout=timeout, headers=headers, allow_redirects=True) as r:
            