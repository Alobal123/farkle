"""Load lore data from JSON files for goal generation."""
import json
import os
from typing import List, Dict, Any

_PETITION_CACHE: List[Dict[str, Any]] | None = None
_DISASTER_CACHE: List[Dict[str, Any]] | None = None

def load_petitions() -> List[Dict[str, Any]]:
    """Load all petition goals from petitions.json.
    
    Returns a flat list of petition dicts with keys: id, title, flavor, category.
    Cached after first load.
    """
    global _PETITION_CACHE
    if _PETITION_CACHE is not None:
        return _PETITION_CACHE
    
    # Find the Lore directory relative to this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(current_dir))
    lore_path = os.path.join(repo_root, 'Lore', 'petitions.json')
    
    try:
        with open(lore_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Flatten categories into a single list of petitions
        petitions = []
        for category in data.get('categories', []):
            category_id = category.get('id', '')
            category_name = category.get('name', '')
            for goal in category.get('goals', []):
                petitions.append({
                    'id': goal.get('id'),
                    'title': goal.get('title', ''),
                    'flavor': goal.get('flavor', ''),
                    'category': category_id,
                    'category_name': category_name
                })
        
        _PETITION_CACHE = petitions
        return petitions
    except Exception as e:
        # Fallback to empty list if file not found or parse error
        print(f"Warning: Could not load petitions.json: {e}")
        _PETITION_CACHE = []
        return []

def get_petition_by_id(petition_id: int) -> Dict[str, Any] | None:
    """Get a specific petition by its ID."""
    petitions = load_petitions()
    for p in petitions:
        if p.get('id') == petition_id:
            return p
    return None

def get_petitions_by_category(category: str) -> List[Dict[str, Any]]:
    """Get all petitions from a specific category."""
    petitions = load_petitions()
    return [p for p in petitions if p.get('category') == category]

def load_disasters() -> List[Dict[str, Any]]:
    """Load all disaster goals from disaster.json.
    
    Returns a flat list of disaster dicts with keys: id, title, flavor, category.
    Cached after first load.
    """
    global _DISASTER_CACHE
    if _DISASTER_CACHE is not None:
        return _DISASTER_CACHE
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(current_dir))
    lore_path = os.path.join(repo_root, 'Lore', 'disaster.json')
    
    try:
        with open(lore_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        disasters = []
        for category in data.get('categories', []):
            category_id = category.get('id', '')
            category_name = category.get('name', '')
            for goal in category.get('goals', []):
                disasters.append({
                    'id': goal.get('id'),
                    'title': goal.get('title', ''),
                    'flavor': goal.get('flavor', ''),
                    'category': category_id,
                    'category_name': category_name
                })
        
        _DISASTER_CACHE = disasters
        return disasters
    except Exception as e:
        print(f"Warning: Could not load disaster.json: {e}")
        _DISASTER_CACHE = []
        return []
