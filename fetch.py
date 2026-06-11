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
    
    Mountain Project columns:
    - Date, Route, Rating (Avg Stars), Your Stars, Location, Style, Lead Style,
      Route Type, Your Rating, Length, Pitches, Notes, URL, Rating Code
    
    Args:
        row: CSV row as dictionary
        
    Returns:
        Standardized climb record
    """
    # Extract area from Location (e.g., "Kentucky > Red River Gorge > Muir Valley > Crag")
    location = row.get('Location', '')
    area_parts = location.split('>')
    
    # Try to use area, fall back to location
    if len(area_parts) >= 3:
        area = area_parts[-2].strip()  # Use second-to-last part (usually crag name)
    elif len(area_parts) >= 2:
        area = area_parts[-1].strip()
    else:
        area = location.strip() if location else 'Unknown Area'
    
    return {
        'route_name': row.get('Route', 'Unknown Route').strip('"'),
        'grade': row.get('Rating', 'Unknown').strip(),
        'area': area,
        'date': row.get('Date', ''),
        'rating': row.get('Your Stars', 0),
        'type': row.get('Route Type', 'Unknown'),
        'style': row.get('Lead Style', row.get('Style', 'Unknown')),
        'notes': row.get('Notes', ''),
        'avg_stars': row.get('Avg Stars', 0),
        'length': row.get('Length', ''),
        'pitches': row.get('Pitches', ''),
    }


def load_csv_data(filepath: str) -> List[Dict[str, Any]]:
    """
    Load climbing data from CSV file.
    Supports Mountain Project export format.
    
    Args:
        filepath: Path to CSV file
        
    Returns:
        List of dictionaries containing climb records
    """
    climbs = []
    path = Path(filepath)
    
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Check if this is a Mountain Project export (has 'Route' column)
            if 'Route' in row:
                normalized = normalize_mountain_project_csv(row)
                climbs.append(normalized)
            else:
                # Fall back to raw row for custom formats
                climbs.append(row)
    
    return climbs


def load_json_data(filepath: str) -> List[Dict[str, Any]]:
    """
    Load climbing data from JSON file.
    
    Expected JSON format:
    [
        {
            "route_name": "Route Name",
            "grade": "5.10a",
            "area": "Area Name",
            "date": "2023-06-15",
            "rating": 4.5,
            "type": "Sport",
            "notes": "Great route!"
        },
        ...
    ]
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        List of dictionaries containing climb records
    """
    path = Path(filepath)
    
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    
    with open(path, 'r', encoding='utf-8') as f:
        climbs = json.load(f)
    
    return climbs if isinstance(climbs, list) else [climbs]


def save_processed_data(data: List[Dict[str, Any]], output_path: str) -> None:
    """
    Save processed climbing data to JSON for caching.
    
    Args:
        data: List of processed climb records
        output_path: Path to output JSON file
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_processed_data(filepath: str) -> List[Dict[str, Any]]:
    """Load cached processed data."""
    return load_json_data(filepath)


def detect_data_format(filepath: str) -> str:
    """Detect data file format by extension."""
    ext = Path(filepath).suffix.lower()
    if ext == '.csv':
        return 'csv'
    elif ext == '.json':
        return 'json'
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def load_climbing_data(filepath: str) -> List[Dict[str, Any]]:
    """
    Auto-detect and load climbing data from file.
    
    Args:
        filepath: Path to data file (CSV or JSON)
        
    Returns:
        List of climb records
    """
    fmt = detect_data_format(filepath)
    
    if fmt == 'csv':
        return load_csv_data(filepath)
    elif fmt == 'json':
        return load_json_data(filepath)
