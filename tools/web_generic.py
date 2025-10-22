# C:\bots\ecosys\tools\web_generic.py
from __future__ import annotations
import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

class WebTools:
    desc = "Generic web tools: search/open/read"

    async def search(self, q: str, max_results: int = 5, safe: str = "off"):
        ddgs = DDGS()
        # returns list of dicts: {'title','href','body'}
        return list(ddgs.text(q, max_results=max_results, safesearch=safe))

    async def open(self, url: str):
        return {"handle": url}

    async def read(self, handle: str, timeout: float = 15.0):
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as cli:
            r = await cli.get(handle, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            for tag in soup(["script", "style", "noscript"]):
                tag.extract()
            text = " ".join(soup.get_text(separator=" ").split())
            return {"url": handle, "text": text[:20000]}

def register(tools):
    wt = WebTools()
    tools.add("web.search", wt.search, desc="Search the web (DuckDuckGo)")
    tools.add("web.open",   wt.open,   desc="Open a URL (returns handle)")
    tools.add("web.read",   wt.read,   desc="Read URL text content")
