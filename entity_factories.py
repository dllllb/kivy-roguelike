from components.ai import HostileEnemy
from components import consumable, equippable
from components.fighter import Fighter
from components.inventory import Inventory
from components.level import Level
from components.equipment import Equipment
from entity import Actor, Item

player = Actor(
    tile=ord('@'),
    name="Player",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(hp=30, base_defense=1, base_power=4),
    inventory=Inventory(capacity=26),
    level=Level(level_up_base=200),
)

orc = Actor(
    tile=ord('o'),
    name="Orc",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(hp=10, base_defense=0, base_power=3),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=35),
)

troll = Actor(
    tile=ord('T'),
    name="Troll",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(hp=16, base_defense=1, base_power=4),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=100),
)

health_potion = Item(
    tile=ord(':'),
    name="Health Potion",
    consumable=consumable.HealingConsumable(amount=4),
)

lightning_scroll = Item(
    tile=ord('%'),
    name="Lightning Scroll",
    consumable=consumable.LightningDamageConsumable(damage=20, maximum_range=5),
)

confusion_scroll = Item(
    tile=ord('?'),
    name="Confusion Scroll",
    consumable=consumable.ConfusionConsumable(number_of_turns=10),
)

fireball_scroll = Item(
    tile=ord('*'),
    name="Fireball Scroll",
    consumable=consumable.FireballDamageConsumable(damage=12, radius=3),
)

dagger = Item(
    tile=ord("/"),
    name="Dagger",
    equippable=equippable.Dagger()
)

sword = Item(
    tile=ord("/"),
    name="Sword",
    equippable=equippable.Sword())

leather_armor = Item(
    tile=ord("["),
    name="Leather Armor",
    equippable=equippable.LeatherArmor(),
)

chain_mail = Item(
    tile=ord("["),
    name="Chain Mail",
    equippable=equippable.ChainMail()
)
