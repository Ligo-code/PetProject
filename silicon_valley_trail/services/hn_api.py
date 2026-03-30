"""
Hacker News trending service using the Algolia HN API.
No API key required.

Checks a list of startup-relevant keywords against recent HN stories.
Returns the first keyword that has active hits, or None.
"""

import os
from dataclasses import dataclass

import requests

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
TIMEOUT_SECONDS = 3
KEYWORDS = ["startup", "AI", "YC", "layoffs", "funding"]

USE_MOCK = os.getenv("MOCK_APIS", "false").lower() == "true"


@dataclass
class HNData:
    trending_keyword: str | None
    story_titles: list[str]


_MOCK_HN = HNData(trending_keyword=None, story_titles=[])


def get_trending_keyword() -> str | None:
    """
    Return the first keyword currently trending on HN, or None.
    Falls back to None on any error.
    """
    if USE_MOCK:
        return _MOCK_HN.trending_keyword

    for keyword in KEYWORDS:
        try:
            response = requests.get(
                HN_SEARCH_URL,
                params={
                    "query": keyword,
                    "tags": "story",
                    "hitsPerPage": 3,
                },
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("nbHits", 0) > 0:
                return keyword
        except Exception:
            continue

    return None
