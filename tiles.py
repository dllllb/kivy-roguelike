from typing import Tuple

import numpy as np  # type: ignore


tile_dt = np.dtype([
    ('walkable', bool),  # True if this tile can be walked over.
    ('transparent', bool),  # True if this tile doesn't block FOV.
    ('tile', int),  # Tile ID
])

def new_tile(
    *,  # Enforce the use of keywords, so that parameter order doesn't matter.
    walkable: int,
    transparent: int,
    tile: int,
) -> np.ndarray:
    """Helper function for defining individual tile types """
    return np.array((walkable, transparent, tile), dtype=tile_dt)

floor = new_tile(
    walkable=True,
    transparent=True,
    tile=ord(' '),
)

wall = new_tile(
    walkable=False,
    transparent=False,
    tile=ord('+'),
)

down_stairs = new_tile(
    walkable=True,
    transparent=True,
    tile=ord(">"),
)
