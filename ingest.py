"""
Data ingestion and processing pipeline for climbing data.
Transforms raw climbing data into structured format for RAG.
"""

import json
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict, Counter
import statistics

from fetch import load_climbing_data, save_processed_data


class ClimbingDataProcessor:
    """Process and analyze climbing data for QA bot."""
    
    def __init__(self, data: List[Dict[str, Any]]):
        """
        Initialize processor with raw climbing data.
        
        Args:
            data: List of climb records from fetch module
        """
        self.raw_data = data
        self.processed_data = []
        self.stats = {}
    
    def process(self) -> Dict[str, Any]:
        """
        Process climbing data and generate statistics.
        
        Returns:
            Dictionary containing processed data and statistics
        """
        self._standardize_records()
        self._calculate_statistics()
        
        return {
            'climbs': self.processed_data,
            'statistics': self.stats,
            'raw_count': len(self.raw_data),
            'processed_count': len(self.processed_data)
        }
    
    def _standardize_records(self) -> None:
        """Convert raw records to standardized format."""
        for record in self.raw_data:
            # Handle both Mountain Project format and custom format
            standardized = {
                'route_name': record.get('route_name', 'Unknown Route'),
                'grade': record.get('grade', 'Unknown'),
                'area': record.get('area', 'Unknown Area'),
                'date': record.get('date', ''),
                'rating': self._parse_rating(record.get('rating', 0)),
                'type': record.get('type', 'Unknown'),
                'style': record.get('style', 'Unknown'),
                'notes': record.get('notes', ''),
            }
            
            # Skip invalid records (missing essential data)
            if standardized['route_name'] != 'Unknown Route' and standardized['grade'] != 'Unknown':
                self.processed_data.append(standardized)
    
    def _parse_rating(self, rating: Any) -> float:
        """Convert rating to float, handle various formats."""
        try:
            return float(rating) if rating else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def _calculate_statistics(self) -> None:
        """Calculate aggregated statistics from climbing data."""
        if not self.processed_data:
            return
        
        # Grade distribution
        grades = [climb['grade'] for climb in self.processed_data]
        grade_counts = Counter(grades)
        
        # Area statistics
        areas = [climb['area'] for climb in self.processed_data]
        area_counts = Counter(areas)
        
        # Rating statistics
        ratings = [climb['rating'] for climb in self.processed_data if climb['rating'] > 0]
        
        # Type distribution
        climb_types = [climb['type'] for climb in self.processed_data]
        type_counts = Counter(climb_types)
        
        # Top routes by rating
        top_routes = sorted(
            self.processed_data,
            key=lambda x: x['rating'],
            reverse=True
        )[:10]
        
        self.stats = {
            'total_climbs': len(self.processed_data),
            'unique_areas': len(area_counts),
            'unique_grades': len(grade_counts),
            'unique_routes': len(set(g['route_name'] for g in self.processed_data)),
            'grade_distribution': dict(grade_counts),
            'area_distribution': dict(area_counts),
            'climb_type_distribution': dict(type_counts),
            'top_areas': dict(area_counts.most_common(5)),
            'top_grades': dict(grade_counts.most_common(5)),
            'top_routes': [
                {
                    'name': r['route_name'],
                    'grade': r['grade'],
                    'area': r['area'],
                    'rating': r['rating']
                }
                for r in top_routes
            ],
            'average_rating': round(statistics.mean(ratings), 2) if ratings else 0.0,
        }
    
    def get_context_for_llm(self) -> str:
        """
        Generate context string to feed into LLM for RAG.
        
        Returns:
            Formatted string with climbing data for LLM context
        """
        context = "# Climbing History and Statistics\n\n"
        
        # Add statistics
        context += "## Summary Statistics\n"
        context += f"- Total climbs logged: {self.stats.get('total_climbs', 0)}\n"
        context += f"- Unique routes: {self.stats.get('unique_routes', 0)}\n"
        context += f"- Unique areas climbed: {self.stats.get('unique_areas', 0)}\n"
        context += f"- Average rating: {self.stats.get('average_rating', 0)}\n\n"
        
        # Top routes
        context += "## Top Rated Routes\n"
        for route in self.stats.get('top_routes', [])[:5]:
            context += f"- {route['name']} ({route['grade']}) in {route['area']} - Rating: {route['rating']}\n"
        context += "\n"
        
        # Grade distribution
        context += "## Climbs by Grade\n"
        for grade, count in sorted(self.stats.get('grade_distribution', {}).items()):
            context += f"- {grade}: {count} climbs\n"
        context += "\n"
        
        # Area distribution
        context += "## Climbs by Area\n"
        for area, count in sorted(self.stats.get('area_distribution', {}).items(), key=lambda x: x[1], reverse=True)[:10]:
            context += f"- {area}: {count} climbs\n"
        context += "\n"
        
        # Recent climbs (if dates available)
        dated_climbs = [c for c in self.processed_data if c.get('date')]
        if dated_climbs:
            context += "## Recent Climbs\n"
            recent = sorted(dated_climbs, key=lambda x: x['date'], reverse=True)[:5]
            for climb in recent:
                context += f"- {climb['route_name']} ({climb['grade']}) in {climb['area']} on {climb['date']}\n"
        
        return context


def process_climbing_data(input_path: str, output_path: str = None) -> Dict[str, Any]:
    """
    Main processing function.
    
    Args:
        input_path: Path to raw climbing data (CSV or JSON)
        output_path: Path to save processed data
        
    Returns:
        Processed data dictionary
    """
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
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else "cache/processed_data.json"
        
        result = process_climbing_data(input_file, output_file)
        print("\nProcessing complete!")
        print(f"Statistics: {json.dumps(result['statistics'], indent=2)}")
    else:
        print("Usage: python ingest.py <input_file> [output_file]")
        print("Example: python ingest.py data/climbing_data.csv cache/processed_data.json")
