"""Load lore data from JSON files for goal generation."""
import json
import os
from typing import List, Dict, Any

_PETITION_CACHE: List[Dict[str, Any]] | None = None
_DISASTER_CACHE: List[Dict[str, Any]] | None = None

def load_petitions() -> List[Dict[str, Any]]:
    """Load all petition goals from petitions2.json.
    
    Returns a flat list of petition dicts with keys: title, text, category, persona.
    Cached after first load.
    """
    global _PETITION_CACHE
    if _PETITION_CACHE is not None:
        return _PETITION_CACHE
    
    # Find the Lore directory relative to this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(current_dir))
    lore_path = os.path.join(repo_root, 'lore', 'petitions.json')
    
    try:
        with open(lore_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Flatten the nested structure into a single list of petitions
        petitions = []
        for category, personas in data.items():
            for persona, petition_list in personas.items():
                for petition in petition_list:
                    petitions.append({
                        'title': petition.get('title', ''),
                        'text': petition.get('text', ''),
                        'category': category,
                        'persona': persona
                    })
        
        _PETITION_CACHE = petitions
        return petitions
    except Exception as e:
        # Fallback to empty list if file not found or parse error
        print(f"Warning: Could not load petitions.json: {e}")
        _PETITION_CACHE = []
        return []

def get_petition_by_id(petition_id: int) -> Dict[str, Any] | None:
    """Get a specific petition by its ID (deprecated - new format doesn't have IDs)."""
    # This function is deprecated with petitions2.json
    return None

def get_petitions_by_category(category: str) -> List[Dict[str, Any]]:
    """Get all petitions from a specific category."""
    petitions = load_petitions()
    return [p for p in petitions if p.get('category') == category]

def get_petitions_by_persona(persona: str) -> List[Dict[str, Any]]:
    """Get all petitions from a specific persona type."""
    petitions = load_petitions()
    return [p for p in petitions if p.get('persona') == persona]

def load_disasters() -> List[Dict[str, Any]]:
    """Load all disaster goals from disaster.json.
    
    Returns a flat list of disaster dicts with keys: title, text, category.
    Cached after first load.
    """
    global _DISASTER_CACHE
    if _DISASTER_CACHE is not None:
        return _DISASTER_CACHE
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(current_dir))
    lore_path = os.path.join(repo_root, 'lore', 'disaster.json')
    
    try:
        with open(lore_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Flatten the nested structure into a single list of disasters
        disasters = []
        for category, disaster_list in data.items():
            for disaster in disaster_list:
                disasters.append({
                    'title': disaster.get('title', ''),
                    'text': disaster.get('text', ''),
                    'category': category
                })
        
        _DISASTER_CACHE = disasters
        return disasters
    except Exception as e:
        print(f"Warning: Could not load disaster.json: {e}")
        _DISASTER_CACHE = []
        return []

def get_disasters_by_category(category: str) -> List[Dict[str, Any]]:
    """Get all disasters from a specific category."""
    disasters = load_disasters()
    return [d for d in disasters if d.get('category') == category]
