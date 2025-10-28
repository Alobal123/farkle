"""God icon loading and management."""

import pygame
from pathlib import Path
from typing import Dict

# God icon positions in the sprite sheet (2x2 grid)
# Top-left, Top-right, Bottom-left, Bottom-right
GOD_ICON_POSITIONS = {
    "Ares": (0, 0),      # Top-left (red background, warrior with helmet)
    "Hermes": (1, 0),    # Top-right (orange background, winged helmet)
    "Hades": (0, 1),     # Bottom-left (purple/dark background, hooded figure)
    "Demeter": (1, 1),   # Bottom-right (green background, figure with wheat)
}

_god_icons: Dict[str, pygame.Surface] = {}
_icons_loaded = False


def load_god_icons() -> Dict[str, pygame.Surface]:
    """Load god icons from the sprite sheet.
    
    Returns:
        Dictionary mapping god names to their icon surfaces
    """
    global _god_icons, _icons_loaded
    
    if _icons_loaded:
        return _god_icons
    
    # Load the sprite sheet
    graphics_path = Path(__file__).parent.parent.parent / "graphics" / "gods.png"
    
    if not graphics_path.exists():
        # Return empty dict if file doesn't exist
        _icons_loaded = True
        return _god_icons
    
    try:
        sprite_sheet = pygame.image.load(str(graphics_path))
        
        # The image is 2x2 grid of god portraits
        sheet_width = sprite_sheet.get_width()
        sheet_height = sprite_sheet.get_height()
        
        icon_width = sheet_width // 2
        icon_height = sheet_height // 2
        
        # Extract each god's icon
        for god_name, (col, row) in GOD_ICON_POSITIONS.items():
            x = col * icon_width
            y = row * icon_height
            
            # Create a subsurface for this god's icon
            icon_rect = pygame.Rect(x, y, icon_width, icon_height)
            icon = sprite_sheet.subsurface(icon_rect).copy()
            
            _god_icons[god_name] = icon
        
        _icons_loaded = True
        
    except Exception as e:
        print(f"Failed to load god icons: {e}")
        _icons_loaded = True
    
    return _god_icons


def get_god_icon(god_name: str) -> pygame.Surface | None:
    """Get the icon surface for a specific god.
    
    Args:
        god_name: Name of the god
        
    Returns:
        Icon surface, or None if not found
    """
    icons = load_god_icons()
    return icons.get(god_name)
