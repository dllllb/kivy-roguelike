from __future__ import annotations

import lzma
import pickle
import collections
from typing import TYPE_CHECKING

import numpy as np

import exceptions
from message_log import MessageLog

if TYPE_CHECKING:
    from entity import Entity
    from game_map import GameMap, GameWorld


class Engine:
    game_map: GameMap
    game_world: GameWorld

    def __init__(self, player: Entity):
        self.message_log = MessageLog()
        self.mouse_location = (0, 0)
        self.player = player

    def handle_enemy_turns(self) -> None:
        for entity in set(self.game_map.actors) - {self.player}:
            if entity.ai:
                try:
                    entity.ai.perform()
                except exceptions.Impossible:
                    pass  # Ignore impossible action exceptions from AI

    def update_fov(self) -> None:
        """Recompute the visible area based on the players point of view."""
        self.game_map.visible[:] = compute_fov(
            self.game_map.tiles["transparent"],
            (self.player.x, self.player.y),
            radius=8,
        )
        # If a tile is "visible" it should be added to "explored".
        self.game_map.explored |= self.game_map.visible

    def save_as(self, filename: str) -> None:
        """Save this Engine instance as a compressed file."""
        save_data = lzma.compress(pickle.dumps(self))
        with open(filename, "wb") as f:
            f.write(save_data)


def neighbours(grid, x, y):
    map_w, map_h = grid.shape
    candidates = [(x-1, y), (x+1, y), (x, y-1), (x, y+1), (x-1, y-1), (x+1, y+1), (x-1, y+1), (x+1, y-1)]
    for x, y in candidates:
        if x < map_w and x >=0 and y < map_h and y >=0:
            yield x, y


def compute_fov(wall_map, center, radius):
    visible = np.full(wall_map.shape, fill_value=False, order="F")
    visible[center[0], center[1]] = True

    queue = collections.deque([[center]])
    seen = set([center])
    while queue:
        path = queue.popleft()
        x, y = path[-1]
        for x2, y2 in neighbours(wall_map, x, y):
            if len(path) + 1 > radius:
                continue

            visible[x2, y2] = True
            # ignoring already processed tiles
            if  (x2, y2) not in seen:
                # ignoring neighbours of walls
                if wall_map[x2, y2] != 0:
                    queue.append(path + [(x2, y2)])
                    seen.add((x2, y2))

    return visible
