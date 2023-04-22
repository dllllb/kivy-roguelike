from __future__ import annotations

import random
from typing import Iterator, List, Tuple, TYPE_CHECKING

from game_map import GameMap
import entity_factories
import tiles

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity


max_items_by_floor = [
    (1, 4),
    (4, 8),
]

max_monsters_by_floor = [
    (1, 2),
    (4, 3),
    (6, 5),
]

item_chances: List[Tuple[int, Entity, int]] = [
    (0, entity_factories.health_potion, 8),
    (0, entity_factories.confusion_scroll, 4),
    (0, entity_factories.lightning_scroll, 4),
    (0, entity_factories.sword, 2),
    (0, entity_factories.fireball_scroll, 4),
    (0, entity_factories.chain_mail, 2),
]

enemy_chances: List[Tuple[int, Entity, int]] = (
    (0, entity_factories.orc, 80),
    (0, entity_factories.troll, 5),
    (3, entity_factories.troll, 15),
    (5, entity_factories.troll, 30),
    (7, entity_factories.troll, 60),
)

def get_max_value_for_floor(
    max_value_by_floor: List[Tuple[int, int]], floor: int
) -> int:
    current_value = 0

    for floor_minimum, value in max_value_by_floor:
        if floor_minimum > floor:
            break
        else:
            current_value = value

    return current_value

def get_entities_at_random(
    weighted_chances_by_floor: List[Tuple[int, Entity, int]],
    number_of_entities: int,
    current_floor: int,
) -> List[Entity]:
    entity_weighted_chances = {}

    for floor, entity, weight in weighted_chances_by_floor:
        if floor <= current_floor:
            entity_weighted_chances[entity] = weight

    entities = list(entity_weighted_chances.keys())
    entity_weighted_chance_values = list(entity_weighted_chances.values())

    chosen_entities = random.choices(
        entities, weights=entity_weighted_chance_values, k=number_of_entities
    )

    return chosen_entities


class RectangularRoom:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x1 = x
        self.y1 = y
        self.x2 = x + width
        self.y2 = y + height

    @property
    def center(self) -> Tuple[int, int]:
        center_x = int((self.x1 + self.x2) / 2)
        center_y = int((self.y1 + self.y2) / 2)

        return center_x, center_y

    @property
    def inner(self) -> Tuple[slice, slice]:
        """Return the inner area of this room as a 2D array index."""
        return slice(self.x1 + 1, self.x2), slice(self.y1 + 1, self.y2)

    def intersects(self, other: RectangularRoom) -> bool:
        """Return True if this room overlaps with another RectangularRoom."""
        return (
            self.x1 <= other.x2
            and self.x2 >= other.x1
            and self.y1 <= other.y2
            and self.y2 >= other.y1
        )


def tunnel_between(
   start: Tuple[int, int], end: Tuple[int, int]
) -> Iterator[Tuple[int, int]]:
    """Return an L-shaped tunnel between these two points."""
    x1, y1 = start
    x2, y2 = end
    
    if random.random() < 0.5:  # 50% chance.
        # Move horizontally, then vertically.

        dir = 1 if x1 < x2 else -1
        for dx in range(abs(x2-x1)+1):
            yield x1+dx*dir, y1

        dir = 1 if y1 < y2 else -1
        for dy in range(abs(y2-y1)+1):
            yield x2, y1+dy*dir
    else:
        # Move vertically, then horizontally.
        dir = 1 if y1 < y2 else -1
        for dy in range(abs(y2-y1)+1):
            yield x1, y1+dy*dir

        dir = 1 if x1 < x2 else -1
        for dx in range(abs(x2-x1)+1):
            yield x1+dx*dir, y2


def place_entities(
    room: RectangularRoom,
    dungeon: GameMap,
    floor_number: int,
) -> None:
    number_of_monsters = random.randint(
        0, get_max_value_for_floor(max_monsters_by_floor, floor_number)
    )

    number_of_items = random.randint(
        0, get_max_value_for_floor(max_items_by_floor, floor_number)
    )

    monsters: List[Entity] = get_entities_at_random(
        enemy_chances, number_of_monsters, floor_number
    )
    items: List[Entity] = get_entities_at_random(
        item_chances, number_of_items, floor_number
    )

    for entity in monsters + items:
        x = random.randint(room.x1 + 1, room.x2 - 1)
        y = random.randint(room.y1 + 1, room.y2 - 1)

        if not any(entity.x == x and entity.y == y for entity in dungeon.entities):
            entity.spawn(dungeon, x, y)


def generate_dungeon(
    max_rooms: int,
    room_min_size: int,
    room_max_size: int,
    map_width: int,
    map_height: int,
    engine: Engine,
) -> GameMap:
    """Generate a new dungeon map."""
    player = engine.player
    dungeon = GameMap(engine, map_width, map_height, [player])

    rooms: List[RectangularRoom] = []

    center_of_last_room = (0, 0)

    for r in range(max_rooms):
        room_width = random.randint(room_min_size, room_max_size)
        room_height = random.randint(room_min_size, room_max_size)

        x = random.randint(0, dungeon.width - room_width - 1)
        y = random.randint(0, dungeon.height - room_height - 1)

        # "RectangularRoom" class makes rectangles easier to work with
        new_room = RectangularRoom(x, y, room_width, room_height)

        # Run through the other rooms and see if they intersect with this one.
        if any(new_room.intersects(other_room) for other_room in rooms):
            continue  # This room intersects, so go to the next attempt.
        # If there are no intersections then the room is valid.

        # Dig out this rooms inner area.
        dungeon.tiles[new_room.inner] = tiles.floor

        if len(rooms) == 0:
            # The first room, where the player starts.
            player.place(*new_room.center, dungeon)
        else:  # All rooms after the first.
            # Dig out a tunnel between this room and the previous one.
            for x, y in tunnel_between(rooms[-1].center, new_room.center):
                dungeon.tiles[x, y] = tiles.floor

        center_of_last_room = new_room.center

        place_entities(new_room, dungeon, engine.game_world.current_floor)

        # Finally, append the new room to the list.
        rooms.append(new_room)

    dungeon.tiles[center_of_last_room] = tiles.down_stairs
    dungeon.downstairs_location = center_of_last_room

    return dungeon
