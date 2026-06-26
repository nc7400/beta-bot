"""
Data loading utilities for Mountain Project climbing data.
Handles loading from local files (CSV, JSON, etc.)
Supports Mountain Project export format and custom formats.
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any


def normalize_mountain_project_csv(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Mountain Project CSV format to standardized format.
    Preserves ALL fields to prevent lossy context generation.
    """

    def _get_first_existing(keys, default=''):
        for key in keys:
            if key in row and row[key] not in (None, ''):
                return row[key]
        return default

    location = _get_first_existing(['Location', 'Area', 'Area Name'], '')
    area_parts = location.split('>')

    if len(area_parts) >= 3:
        area = area_parts[-2].strip()
    elif len(area_parts) >= 2:
        area = area_parts[-1].strip()
    else:
        area = location.strip() if location else 'Unknown Area'

    # Rating Code is a numeric difficulty index — valid ONLY within the same
    # discipline (Sport/Trad share one scale; Boulder uses a separate scale).
    # Store as int so we can sort/compare reliably; 0 means absent/unknown.
    raw_code = _get_first_existing(['Rating Code'], '')
    try:
        rating_code = int(raw_code) if raw_code else 0
    except (ValueError, TypeError):
        rating_code = 0

    return {
        'route_name':       str(_get_first_existing(['Route', 'Route Name'], 'Unknown Route')).strip('"'),
        'grade':            str(_get_first_existing(['Rating', 'Grade'], 'Unknown')).strip(),
        'area':             area,
        'full_location':    location,
        'date':             str(_get_first_existing(['Date', 'Climb Date'], '')),
        'your_rating':      _get_first_existing(['Your Stars', 'Your Rating'], ''),
        'avg_stars':        _get_first_existing(['Avg Stars', 'Average Rating'], ''),
        'type':             str(_get_first_existing(['Route Type', 'Type'], 'Unknown')),
        'style':            str(_get_first_existing(['Style'], 'Unknown')),
        'lead_style':       str(_get_first_existing(['Lead Style'], '')),
        'notes':            str(_get_first_existing(['Notes', 'Comment', 'Comments'], '')),
        'length':           str(_get_first_existing(['Length', 'Length In Feet'], '')),
        'pitches':          str(_get_first_existing(['Pitches', 'Pitch Count'], '')),
        'url':              str(_get_first_existing(['URL'], '')),
        'your_grade':       str(_get_first_existing(['Your Suggested Grade'], '')),  # never fall back to Your Rating
        'rating_code':      rating_code,
    }


def load_csv_data(filepath: str) -> List[Dict[str, Any]]:
    climbs = []
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")

    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'Route' in row:
                normalized = normalize_mountain_project_csv(row)
                climbs.append(normalized)
            else:
                climbs.append(row)

    return climbs


def load_json_data(filepath: str) -> List[Dict[str, Any]]:
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")

    with open(path, 'r', encoding='utf-8') as f:
        climbs = json.load(f)

    return climbs if isinstance(climbs, list) else [climbs]


def save_processed_data(data: List[Dict[str, Any]], output_path: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_processed_data(filepath: str) -> List[Dict[str, Any]]:
    return load_json_data(filepath)


def detect_data_format(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    if ext == '.csv':
        return 'csv'
    elif ext == '.json':
        return 'json'
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def load_climbing_data(filepath: str) -> List[Dict[str, Any]]:
    fmt = detect_data_format(filepath)
    if fmt == 'csv':
        return load_csv_data(filepath)
    elif fmt == 'json':
        return load_json_data(filepath)