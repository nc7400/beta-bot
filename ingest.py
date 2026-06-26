"""
Data ingestion and processing pipeline for climbing data.

KEY CHANGE: get_context_for_llm() now accepts an optional `question` string.
When provided, it filters RAW CLIMB RECORDS to only rows relevant to that
question — keeping requests well under Groq's free-tier token limit.

Full records are still stored in self.processed_data for stats/UI display.

RATING CODE: The Mountain Project CSV includes a numeric "Rating Code" column
that encodes difficulty within a discipline — higher = harder, but ONLY when
comparing climbs of the same type:
  • Sport / Trad  → codes in the low thousands  (1800 = 5.7, 8600 = 5.13a)
  • Boulder       → codes in the 20000s          (20400 = V4, 20800 = V8)
Cross-discipline comparison is meaningless (a V1 at ~20100 is NOT harder than
a 5.13a at 8600).  All hardest/easiest lookups are therefore done per-discipline
and the model is explicitly told this constraint.
"""

import json
import re
from typing import List, Dict, Any, Optional
from collections import Counter
import statistics

from fetch import load_climbing_data, save_processed_data


# ── Grade helpers ──────────────────────────────────────────────────────────────

# Ordered Yosemite Decimal System grades for range queries
YDS_ORDER = [
    "5.6","5.7","5.8","5.9",
    "5.10a","5.10b","5.10c","5.10d","5.10-","5.10","5.10+",
    "5.11a","5.11b","5.11c","5.11d","5.11-","5.11","5.11+",
    "5.12a","5.12b","5.12c","5.12d","5.12-","5.12","5.12+",
    "5.13a","5.13b","5.13c","5.13d","5.13-","5.13","5.13+",
    "5.14a","5.14b","5.14c","5.14d","5.14-","5.14","5.14+",
    "5.15a","5.15b","5.15c","5.15d",
]
BOULDER_ORDER = ["V0","V1","V2","V3","V4","V5","V6","V7","V8","V9","V10","V11","V12","V13","V14","V15"]


def _extract_grades_from_question(question: str) -> list[str]:
    """Pull any grade tokens out of the question text."""
    q = question.upper()
    found = []
    # Sport/trad grades  e.g. 5.12d, 5.12a/b, 5.12-, 5.12+
    for m in re.finditer(r'5\.\d{2}[A-D/\-\+]?', q, re.IGNORECASE):
        found.append(m.group().lower())
    # Boulder grades  e.g. V7, v8
    for m in re.finditer(r'V\d{1,2}', q, re.IGNORECASE):
        found.append(m.group().upper())
    return found


def _extract_keywords(question: str) -> list[str]:
    """
    Return a list of lowercased tokens from the question that are useful
    for matching against route names, areas, styles, and dates.
    Strips common stopwords so we don't match everything.
    """
    stopwords = {
        "what","how","many","did","i","do","have","my","the","a","an",
        "is","are","was","were","at","in","on","of","to","for","with",
        "list","show","tell","me","give","all","any","some","most","best",
        "worst","top","hardest","easiest","routes","climbs","climb","route",
        "times","time","and","or","that","which","when","where","about",
        "been","can","could","would","should","you","your","been","been",
        "ive","i've","ive","ever","never","than","more","less","least",
    }
    tokens = re.findall(r"[a-z0-9'\.]+", question.lower())
    return [t for t in tokens if t not in stopwords and len(t) > 1]


class ClimbingDataProcessor:
    """Process and analyse climbing data for the Q&A bot."""

    def __init__(self, data: List[Dict[str, Any]]):
        self.raw_data = data
        self.processed_data: List[Dict[str, Any]] = []
        self.stats: Dict[str, Any] = {}

    def process(self) -> Dict[str, Any]:
        self._standardize_records()
        self._calculate_statistics()
        return {
            'climbs': self.processed_data,
            'statistics': self.stats,
            'raw_count': len(self.raw_data),
            'processed_count': len(self.processed_data),
        }

    def _standardize_records(self) -> None:
        for record in self.raw_data:
            try:
                rc = int(record.get('rating_code', 0) or 0)
            except (ValueError, TypeError):
                rc = 0
            s = {
                'route_name':    record.get('route_name', 'Unknown Route'),
                'grade':         record.get('grade', 'Unknown'),
                'area':          record.get('area', 'Unknown Area'),
                'full_location': record.get('full_location', ''),
                'date':          record.get('date', ''),
                'your_rating':   self._parse_rating(record.get('your_rating', 0)),
                'avg_stars':     self._parse_rating(record.get('avg_stars', 0)),
                'type':          record.get('type', 'Unknown'),
                'style':         record.get('style', 'Unknown'),
                'lead_style':    record.get('lead_style', ''),
                'notes':         record.get('notes', ''),
                'length':        record.get('length', ''),
                'pitches':       record.get('pitches', ''),
                'url':           record.get('url', ''),
                'your_grade':    record.get('your_grade', ''),
                'rating_code':   rc,
            }
            if s['route_name'] != 'Unknown Route':
                self.processed_data.append(s)

    def _parse_rating(self, rating: Any) -> float:
        try:
            return float(rating) if rating else 0.0
        except (ValueError, TypeError):
            return 0.0

    def _calculate_statistics(self) -> None:
        if not self.processed_data:
            return

        grades      = [c['grade']       for c in self.processed_data]
        areas       = [c['area']        for c in self.processed_data]
        ratings     = [c['your_rating'] for c in self.processed_data if c['your_rating'] > 0]
        climb_types = [c['type']        for c in self.processed_data]
        lead_styles = [c['lead_style']  for c in self.processed_data if c['lead_style']]

        # Split by discipline — rating_code is only comparable within a group
        rope_climbs    = [c for c in self.processed_data
                          if c['type'] in ('Sport', 'Trad', 'Sport, Alpine', 'Alpine')
                          and c['rating_code'] > 0]
        boulder_climbs = [c for c in self.processed_data
                          if c['type'] == 'Boulder' and c['rating_code'] > 0]

        def _hardest(group):
            if not group:
                return None
            h = max(group, key=lambda x: x['rating_code'])
            return {'name': h['route_name'], 'grade': h['grade'],
                    'rating_code': h['rating_code'], 'date': h['date']}

        def _easiest(group):
            if not group:
                return None
            e = min(group, key=lambda x: x['rating_code'])
            return {'name': e['route_name'], 'grade': e['grade'],
                    'rating_code': e['rating_code'], 'date': e['date']}

        top_routes = sorted(
            self.processed_data,
            key=lambda x: x['your_rating'],
            reverse=True,
        )[:10]

        self.stats = {
            'total_climbs':            len(self.processed_data),
            'unique_areas':            len(Counter(areas)),
            'unique_grades':           len(Counter(grades)),
            'unique_routes':           len(set(c['route_name'] for c in self.processed_data)),
            'grade_distribution':      dict(Counter(grades)),
            'area_distribution':       dict(Counter(areas)),
            'climb_type_distribution': dict(Counter(climb_types)),
            'lead_style_distribution': dict(Counter(lead_styles)),
            'top_areas':               dict(Counter(areas).most_common(5)),
            'top_grades':              dict(Counter(grades).most_common(10)),
            'top_routes': [
                {
                    'name':        r['route_name'],
                    'grade':       r['grade'],
                    'area':        r['area'],
                    'your_rating': r['your_rating'],
                    'date':        r['date'],
                    'lead_style':  r['lead_style'],
                    'rating_code': r['rating_code'],
                }
                for r in top_routes
            ],
            'average_rating':   round(statistics.mean(ratings), 2) if ratings else 0.0,
            'redpoints':        [c['route_name'] for c in self.processed_data if c['lead_style'] == 'Redpoint'],
            'onsights':         [c['route_name'] for c in self.processed_data if c['lead_style'] == 'Onsight'],
            'flashes':          [c['route_name'] for c in self.processed_data if c['lead_style'] == 'Flash'],
            # Per-discipline difficulty extremes using rating_code
            'hardest_rope':     _hardest(rope_climbs),
            'easiest_rope':     _easiest(rope_climbs),
            'hardest_boulder':  _hardest(boulder_climbs),
            'easiest_boulder':  _easiest(boulder_climbs),
        }

    # ── Context generation ─────────────────────────────────────────────────────

    def _row_matches_question(self, climb: Dict[str, Any], keywords: list[str], grades: list[str]) -> bool:
        """
        Return True if this climb record is relevant to the question.
        A record matches if:
          • any extracted grade token appears in the climb's grade field, OR
          • any keyword appears in route name, area, full location, lead style,
            type, date (year/month), or notes.
        """
        haystack = " ".join([
            climb['route_name'],
            climb['grade'],
            climb['area'],
            climb['full_location'],
            climb['lead_style'],
            climb['style'],
            climb['type'],
            climb['date'],
            climb['notes'],
            climb['your_grade'],
        ]).lower()

        if grades:
            for g in grades:
                if g in climb['grade'].lower():
                    return True

        if keywords:
            for kw in keywords:
                if kw in haystack:
                    return True

        return False

    def _is_global_question(self, question: str) -> bool:
        """
        Questions that require the full dataset (totals, bests, mosts, lists).
        These get the stats block + all records but we cap at MAX_RECORDS.
        """
        q = question.lower()
        global_triggers = [
            "total", "how many", "all", "every", "list all",
            "most", "hardest", "easiest", "best", "worst", "top",
            "average", "first", "last", "recent", "oldest", "highest rated",
            "how often", "count", "number of",
        ]
        return any(t in q for t in global_triggers)

    def get_context_for_llm(self, question: Optional[str] = None, max_records: int = 80) -> str:
        """
        Build a context string sized to stay under Groq's free-tier token limit.

        Strategy:
          • Always include the stats summary block (~400 tokens, fixed size).
          • For specific questions (grade/route/area/style lookups): filter raw
            records to matching rows only — usually 1–30 rows.
          • For global questions (totals, bests, lists): include up to
            `max_records` rows, sorted by date desc so recent climbs are
            prioritised when we have to truncate.
          • If no question supplied: return stats block only (safe default for
            initialisation; full records are fetched per-question at chat time).

        Token budget (rough, 1 token ≈ 4 chars):
          Stats block  ≈  400 tokens
          Per row      ≈   35 tokens
          80 rows      ≈ 2,800 tokens
          Total        ≈ 3,200 tokens  ← well under 12,000 limit
        """

        def safe(v: Any) -> str:
            return str(v).replace('\n', ' ').replace('|', '-').strip() or 'N/A'

        lines = []

        # ── Grounding rules ────────────────────────────────────────────────────
        lines += [
            "=== GROUNDING RULES (follow exactly) ===",
            "1. Answer ONLY from data in this context. Never invent route names, grades, dates, or styles.",
            "2. Copy route names and grades CHARACTER-FOR-CHARACTER from RAW CLIMB RECORDS.",
            "3. Count by scanning RAW CLIMB RECORDS — do not estimate.",
            "4. If the answer is absent, say exactly: 'I do not have that information in the data provided.'",
            "5. When listing routes include: Route Name | Grade | Date | Lead Style.",
            "6. RATING CODE encodes difficulty within a discipline only:",
            "     Sport/Trad → codes in the low thousands (higher = harder within rope climbing).",
            "     Boulder    → codes in the 20000s       (higher = harder within bouldering).",
            "   NEVER compare a Boulder rating code against a Sport/Trad rating code.",
            "   When asked for hardest/easiest, answer separately per discipline.",
            "",
        ]

        # ── Stats summary (always included) ───────────────────────────────────
        hr = self.stats.get('hardest_rope')
        er = self.stats.get('easiest_rope')
        hb = self.stats.get('hardest_boulder')
        eb = self.stats.get('easiest_boulder')

        lines += [
            "=== SUMMARY STATISTICS ===",
            f"Total climbs logged   : {self.stats.get('total_climbs', 0)}",
            f"Unique routes         : {self.stats.get('unique_routes', 0)}",
            f"Unique areas          : {self.stats.get('unique_areas', 0)}",
            f"Average your-rating   : {self.stats.get('average_rating', 0)}",
            f"Total redpoints       : {len(self.stats.get('redpoints', []))}",
            f"Total onsights        : {len(self.stats.get('onsights', []))}",
            f"Total flashes         : {len(self.stats.get('flashes', []))}",
            "",
            "Difficulty extremes (rating_code valid within discipline only):",
            f"  Hardest rope climb  : {hr['name']} {hr['grade']} (code {hr['rating_code']}, {hr['date']})" if hr else "  Hardest rope climb  : N/A",
            f"  Easiest rope climb  : {er['name']} {er['grade']} (code {er['rating_code']}, {er['date']})" if er else "  Easiest rope climb  : N/A",
            f"  Hardest boulder     : {hb['name']} {hb['grade']} (code {hb['rating_code']}, {hb['date']})" if hb else "  Hardest boulder     : N/A",
            f"  Easiest boulder     : {eb['name']} {eb['grade']} (code {eb['rating_code']}, {eb['date']})" if eb else "  Easiest boulder     : N/A",
            "",
            "Grade distribution (grade: count):",
        ]
        for grade, count in sorted(self.stats.get('grade_distribution', {}).items()):
            lines.append(f"  {grade}: {count}")

        lines += [
            "",
            "Top 10 areas by visit count:",
        ]
        for area, count in Counter(self.stats.get('area_distribution', {})).most_common(10):
            lines.append(f"  {area}: {count} climbs")

        lines += [
            "",
            "Lead style breakdown:",
        ]
        for style, count in self.stats.get('lead_style_distribution', {}).items():
            lines.append(f"  {style}: {count}")

        lines.append("")

        # ── Raw records (filtered or capped) ──────────────────────────────────
        if question is None:
            # No question yet — omit raw records, stats are enough for init
            lines += [
                "=== RAW CLIMB RECORDS ===",
                "(Records will be included when a question is asked.)",
            ]
        else:
            keywords = _extract_keywords(question)
            grades   = _extract_grades_from_question(question)
            global_q = self._is_global_question(question)

            if grades or (keywords and not global_q):
                # Specific grade or keyword — scan ALL records, no cap.
                # "How many 5.12d have I done?" must see every 5.12d row,
                # not just the most-recent 80. Targeted rows are small enough
                # (typically 1–40) that token limits are never an issue.
                selected  = [c for c in self.processed_data
                             if self._row_matches_question(c, keywords, grades)]
                truncated = False
                # Nothing matched — fall back to a small recent sample
                if not selected:
                    selected  = sorted(self.processed_data, key=lambda x: x['date'], reverse=True)[:30]
                    truncated = len(self.processed_data) > 30
            else:
                # True global question (totals, bests, area lists) with no
                # specific filter target — cap to max_records, newest first
                candidates = sorted(self.processed_data, key=lambda x: x['date'], reverse=True)
                selected   = candidates[:max_records]
                truncated  = len(self.processed_data) > max_records

            lines += [
                "=== RAW CLIMB RECORDS (authoritative — use for all specific answers) ===",
                "IMPORTANT: Each record is one climb. COUNT = number of records listed. LIST = copy records verbatim.",
                f"Showing {len(selected)} of {len(self.processed_data)} total records"
                + (" (most recent first, truncated to fit token limit)" if truncated else "") + ".",
                "",
            ]

            for c in selected:
                # Labeled format — no positional ambiguity for the model
                parts = [
                    f"date={safe(c['date'])}",
                    f"route={safe(c['route_name'])}",
                    f"grade={safe(c['grade'])}",
                    f"difficulty_code={c['rating_code'] if c['rating_code'] else 'N/A'}",
                    f"area={safe(c['area'])}",
                    f"lead_style={safe(c['lead_style'])}",
                    f"type={safe(c['type'])}",
                    f"your_rating={safe(c['your_rating'])}",
                ]
                if c.get('your_grade'):
                    parts.append(f"your_suggested_grade={safe(c['your_grade'])}")
                lines.append("  " + " | ".join(parts))

            if truncated:
                lines += [
                    "",
                    f"NOTE: {len(self.processed_data) - len(selected)} older records omitted to stay within token limits.",
                    "For questions about specific older climbs, please include the route name or date in your question.",
                ]

        lines.append("\n=== END OF DATA ===")
        return "\n".join(lines)


# ── CLI helper ────────────────────────────────────────────────────────────────

def process_climbing_data(input_path: str, output_path: str = None) -> Dict[str, Any]:
    print(f"Loading data from {input_path}...")
    raw_data = load_climbing_data(input_path)
    print(f"Loaded {len(raw_data)} records")
    processor = ClimbingDataProcessor(raw_data)
    result = processor.process()
    if output_path:
        save_processed_data(result, output_path)
        print(f"Saved processed data to {output_path}")
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = process_climbing_data(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
        print(f"\nDone. {result['processed_count']} climbs processed.")
    else:
        print("Usage: python ingest.py <input_file> [output_file]")