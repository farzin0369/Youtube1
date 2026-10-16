from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
BANK = ROOT / "ideas.jsonl"
API = "https://api.openalex.org/works"
FIELDS = "id,doi,title,publication_year,type,cited_by_count,authorships,primary_location,open_access,topics"


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.casefold()).strip()


def load_records(path: Path = BANK) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            if isinstance(item, dict) and item.get("title"):
                records.append(item)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return records


def save_records(records: list[dict[str, Any]], path: Path = BANK) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records), encoding="utf-8")
    temp.replace(path)


def dedupe_key(record: dict[str, Any]) -> str:
    doi = (record.get("doi") or "").strip().lower()
    if not doi:
        for source in record.get("sources", []):
            if isinstance(source, dict) and source.get("doi"):
                doi = str(source["doi"]).strip().lower()
                break
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    return "doi:" + doi if doi else "title:" + normalize_title(str(record.get("title", "")))


def merge_records(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen = {dedupe_key(r) for r in existing}
    added = 0
    for record in incoming:
        key = dedupe_key(record)
        if key == "title:" or key in seen:
            continue
        existing.append(record)
        seen.add(key)
        added += 1
    return existing, added


def search_bank(query: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    terms = [t for t in normalize_title(query).split() if t]
    if not terms:
        return records
    def score(record: dict[str, Any]) -> int:
        haystack = normalize_title(" ".join([
            str(record.get("title", "")),
            str(record.get("hook", "")),
            str(record.get("plain_explanation", "")),
            " ".join(record.get("tags", [])) if isinstance(record.get("tags"), list) else str(record.get("tags", "")),
        ]))
        return sum(1 for term in terms if term in haystack)
    return sorted((r for r in records if score(r)), key=lambda r: (-score(r), r.get("title", "")))


def fetch_openalex(query: str, limit: int) -> list[dict[str, Any]]:
    if not query.strip():
        raise ValueError("Query must not be empty.")
    limit = max(1, min(int(limit), 100))
    params = {
        "search": query,
        "per-page": str(limit),
        "select": FIELDS,
    }
    mailto = os.environ.get("OPENALEX_MAILTO")
    if mailto:
        params["mailto"] = mailto
    api_key = os.environ.get("OPENALEX_API_KEY")
    if api_key:
        params["api_key"] = api_key
    request = urllib.request.Request(
        API + "?" + urllib.parse.urlencode(params),
        headers={"User-Agent": "Youtube1-ScienceIdeaEngine/0.1 (metadata research; contact via repository)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"OpenAlex request failed: {exc}") from exc

    records = []
    for work in payload.get("results", []):
        title = (work.get("title") or "").strip()
        if not title:
            continue
        topics = work.get("topics") or []
        authors = []
        for auth in (work.get("authorships") or [])[:4]:
            name = (auth.get("author") or {}).get("display_name")
            if name:
                authors.append(name)
        primary = work.get("primary_location") or {}
        source = primary.get("source") or {}
        oa = work.get("open_access") or {}
        doi = work.get("doi")
        records.append({
            "id": "oa-" + str(work.get("id", "").rstrip("/").split("/")[-1]),
            "title": title,
            "tags": [t.get("display_name") for t in topics[:8] if t.get("display_name")],
            "hook": "What does the research tell us about: " + title.rstrip("?. ") + "?",
            "plain_explanation": "Write and fact-check a plain-language explanation after reviewing the cited source; do not infer findings from the title alone.",
            "deeper_angle": "Review methods, limitations, competing interpretations, and specialist context.",
            "visual_plan": ["Open with a visual question", "Show a verified model or diagram", "End with the key limitation or unanswered question"],
            "sources": [{
                "provider": "OpenAlex",
                "work_id": work.get("id"),
                "doi": doi,
                "url": (doi or work.get("id") or ""),
                "publication_year": work.get("publication_year"),
                "source_name": source.get("display_name"),
                "is_oa": oa.get("is_oa"),
                "authors": authors,
                "cited_by_count": work.get("cited_by_count", 0),
                "work_type": work.get("type"),
            }],
            "evidence_status": "needs_review",
            "workflow_status": "research_candidate",
            "language": "en",
        })
    return records



def parse_arxiv_feed(xml_data: bytes, limit: int = 10) -> list[dict[str, Any]]:
    """Convert an arXiv Atom response to review-required research candidates."""
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid arXiv XML: {exc}") from exc
    records: list[dict[str, Any]] = []
    for entry in root.findall("atom:entry", ns)[:max(1, min(int(limit), 100))]:
        title = " ".join(entry.findtext("atom:title", default="", namespaces=ns).split())
        if not title:
            continue
        summary = " ".join(entry.findtext("atom:summary", default="", namespaces=ns).split())
        entry_id = entry.findtext("atom:id", default="", namespaces=ns).strip()
        published = entry.findtext("atom:published", default="", namespaces=ns).strip()
        authors = [a.findtext("atom:name", default="", namespaces=ns).strip() for a in entry.findall("atom:author", ns)]
        categories = [x.attrib.get("term", "") for x in entry.findall("atom:category", ns) if x.attrib.get("term")]
        doi = entry.findtext("arxiv:doi", default="", namespaces=ns).strip()
        records.append({
            "id": "arxiv-" + entry_id.rstrip("/").split("/")[-1],
            "title": title,
            "tags": categories,
            "hook": "What can this research teach us about: " + title.rstrip("?. ") + "?",
            "plain_explanation": "Review the paper, then write and fact-check a plain-language explanation; the abstract alone is not enough.",
            "deeper_angle": summary,
            "visual_plan": ["Frame the research question", "Illustrate verified concepts", "Show limitations and open questions"],
            "sources": [{"provider": "arXiv", "url": entry_id, "doi": doi or None, "published": published, "authors": authors[:8], "source_type": "preprint_or_paper_record"}],
            "evidence_status": "needs_review",
            "workflow_status": "research_candidate",
            "language": "en",
        })
    return records


def fetch_arxiv(query: str, limit: int) -> list[dict[str, Any]]:
    if not query.strip():
        raise ValueError("Query must not be empty.")
    params = {"search_query": "all:" + query, "start": "0", "max_results": str(max(1, min(int(limit), 100))), "sortBy": "relevance", "sortOrder": "descending"}
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": "Youtube1-ScienceIdeaEngine/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"arXiv request failed: {exc}") from exc
    return parse_arxiv_feed(payload, limit)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Search and grow the isolated science idea bank.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("stats", help="Show idea-bank counts.")
    search = sub.add_parser("search", help="Search existing ideas.")
    search.add_argument("query")
    imp = sub.add_parser("import-openalex", help="Import research metadata candidates from OpenAlex.")
    imp.add_argument("--query", required=True)
    imp.add_argument("--limit", type=int, default=10)
    arxiv = sub.add_parser("import-arxiv", help="Import research candidates from the arXiv API.")
    arxiv.add_argument("--query", required=True)
    arxiv.add_argument("--limit", type=int, default=10)
    rank = sub.add_parser("rank", help="Rank idea candidates with an explainable editorial rubric.")
    rank.add_argument("--limit", type=int, default=30)
    args = parser.parse_args(argv)

    try:
        records = load_records()
        if args.command == "stats":
            subjects: dict[str, int] = {}
            for item in records:
                for tag in item.get("tags", []):
                    subjects[tag] = subjects.get(tag, 0) + 1
            print(json.dumps({"total_ideas": len(records), "source_records": sum(bool(r.get("sources")) for r in records), "subjects": dict(sorted(subjects.items(), key=lambda x: (-x[1], x[0]))[:20])}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "search":
            hits = search_bank(args.query, records)
            print(json.dumps(hits[:30], ensure_ascii=False, indent=2))
            print(f"\nMatches: {len(hits)}", file=sys.stderr)
            return 0
        if args.command == "rank":
            from science_engine.ranking import rank_ideas
            print(json.dumps(rank_ideas(records)[:max(1, min(args.limit, 500))], ensure_ascii=False, indent=2))
            return 0
        if args.command == "import-arxiv":
            incoming = fetch_arxiv(args.query, args.limit)
            merged, added = merge_records(records, incoming)
            save_records(merged)
            print(json.dumps({"query": args.query, "source": "arXiv", "fetched": len(incoming), "added": added, "duplicates_skipped": len(incoming) - added, "total_ideas": len(merged)}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "import-openalex":
            incoming = fetch_openalex(args.query, args.limit)
            merged, added = merge_records(records, incoming)
            save_records(merged)
            print(json.dumps({"query": args.query, "fetched": len(incoming), "added": added, "duplicates_skipped": len(incoming) - added, "total_ideas": len(merged), "bank": str(BANK.relative_to(Path.cwd())) if BANK.is_relative_to(Path.cwd()) else str(BANK)}, ensure_ascii=False, indent=2))
            return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
