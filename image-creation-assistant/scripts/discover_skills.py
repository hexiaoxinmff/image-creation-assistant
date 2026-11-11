#!/usr/bin/env python3
"""Search a small set of generic capability topics on skills.sh; never install."""
from __future__ import annotations
import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

TOPICS = {
    "image-editing": "image editing",
    "image-generation": "image generation",
    "image-compositing": "image compositing",
    "image-text": "image text editing",
    "presentation-creation": "presentation creation",
    "presentation-editing": "pptx editing",
    "presentation-design": "presentation design",
    "presentation-templates": "presentation templates",
    "image-to-presentation": "image to editable pptx",
}
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
MAX_RESPONSE = 2_000_000

def discover(topic: str) -> dict:
    query = TOPICS[topic]
    url = "https://skills.sh/api/search?" + urllib.parse.urlencode({"q": query})
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "generic-skill-discovery/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = response.read(MAX_RESPONSE + 1)
        if len(payload) > MAX_RESPONSE:
            raise ValueError("response too large")
        data = json.loads(payload)
        if not isinstance(data, dict) or not isinstance(data.get("skills"), list):
            raise ValueError("unexpected search response")
        results = []
        for item in data["skills"]:
            if not isinstance(item, dict):
                continue
            repo, name = item.get("source"), item.get("skillId")
            if not isinstance(repo, str) or not REPO.fullmatch(repo) or not isinstance(name, str) or not NAME.fullmatch(name):
                continue
            results.append({"source": repo, "skill": name, "repository": "https://github.com/" + repo})
            if len(results) >= 5:
                break
        return {"status": "ok" if results else "no_results", "topic": topic, "query": query, "results": results,
                "note": "Search results are unverified candidates. Inspect the source, license, dependencies and data flow before use; no installation performed."}
    except (OSError, ValueError, TypeError, json.JSONDecodeError, urllib.error.URLError):
        return {"status": "unavailable", "topic": topic, "query": query, "results": [],
                "note": "Search failed or returned an unexpected response; continue using the current platform where possible."}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True, choices=sorted(TOPICS))
    args = parser.parse_args()
    result = discover(args.topic)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["status"] == "unavailable" else 0

if __name__ == "__main__":
    raise SystemExit(main())
