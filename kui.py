from typing import Callable

from kivy.config import Config
Config.set('graphics', 'resizable', False)

from kivy.app import App
from kivy.core.image import Image as CoreImage
from kivy.uix.image import Image as UxImage
from kivy.graphics import Rectangle, Color
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.modalview import ModalView as ModalView
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.logger import Logger

from engine import Engine
import entity
import actions
import exceptions
from setup_game import new_game, load_game
import color

MAPPER_1BIT = {
    '@': (28, 0), # character
    '+': (11, 2), # wall
    ' ': (2, 0), # floor
    '>': (7, 12), # ladder
    'T': (30, 6), # troll
    'o': (29, 2), # orc
    '*': (15, 10), # fireball scroll
    '%': (12, 5), # lightning scroll
    '?': (37, 13), # confusion scroll
    ':': (34, 13), # health potion
    '/': (34, 6), # weapon
    '[': (34, 1), # armor
    'x': (0, 15), # corpse
    'X': (25, 14), # selection mark
}

class Tileset:
    def __init__(self, tile_image_path, mapper, tile_width=16, tile_height=16, row_border=0, col_border=0):
        self.mapper = mapper
        img = CoreImage(tile_image_path)
        texture = CoreImage(tile_image_path).texture
        self.tile_width = tile_width
        self.tile_height = tile_height
        self.row_border = row_border
        self.col_border = col_border

        self.n_rows = (img.height+row_border) // (tile_height+row_border)
        self.n_cols = (img.width+col_border) // (tile_width+col_border)

        self.images = [[0 for y in range(self.n_rows)] for x in range(self.n_cols)]

        for x in range(self.n_cols):
            for y in range(self.n_rows):
                # invert y for OpenGL coordinates
                tx = x*self.tile_width + x*self.col_border
                ty = img.height - y*self.tile_height - y*self.row_border - self.tile_height
                tile = texture.get_region(tx, ty, tile_width, tile_height)
                self.images[x][y] = tile

    def get_image(self, iid: str):
        x, y = self.mapper[iid]
        return self.images[x][y]


class GameWidget(Widget):
    def __init__(self, engine: Engine, tileset: Tileset, scale=1, **kwargs):
        super().__init__(**kwargs)

        self.engine = engine
        self.tileset = tileset
        self.scale = scale

    def on_size(self, *args):
        self.draw()

    def draw(self):
        self.canvas.clear()
        self.canvas.after.clear()

        tiles = self.engine.game_map.get_tiles_to_draw()
        wx, wy = self.pos
        tile_width = self.tileset.tile_width * self.scale
        tile_height = self.tileset.tile_height * self.scale

        with self.canvas:
            for x, y, iid, _ in tiles:
                texture = self.tileset.get_image(iid)

                pos_x = wx + x * tile_width
                pos_y = wy + y * tile_height
                size = (tile_width, tile_height)

                Rectangle(texture=texture, pos=(pos_x, pos_y), size=size)

        with self.canvas.after:
            for x, y, _, visible in tiles:
                if visible:
                    continue

                pos_x = wx + x * tile_width
                pos_y = wy + y * tile_height
                size = (tile_width, tile_height)

                Color(0, 0, 0, .4)
                Rectangle(pos=(pos_x, pos_y), size=size)


class GlobalEventHandler(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_screen = None

    def new_game(self):
        config = App.get_running_app().config
        level_width = config.getint('metrics', 'level_width')
        level_height =config.getint('metrics', 'level_height')

        engine = new_game(
            max_rooms=5,
            room_min_size=6,
            room_max_size=10,
            map_height=level_height,
            map_width=level_width
        )
        self._set_current_screen(MainGameScreen(engine))

    def main_menu(self):
        self._set_current_screen(MenuScreen())

    def load_game(self):
        engine = load_game('savegame.sav')
        self._set_current_screen(MainGameScreen(engine))

    def _set_current_screen(self, screen):
        if self.current_screen is not None:
            Window.unbind(on_keyboard=self.current_screen.on_keyboard)
            self.remove_widget(self.current_screen)
        self.current_screen = screen
        Window.bind(on_keyboard=screen.on_keyboard)
        self.add_widget(screen)


class DefaultGlobalEventHandler(GlobalEventHandler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.main_menu()


class DebugGlobalEventHandler(GlobalEventHandler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.new_game()


class MenuScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.orientation = 'vertical'

        self.add_widget(Label(text='[N] Play a new game'))
        self.add_widget(Label(text='[C] Continue last game'))
        self.add_widget(Label(text='[Q] Quit'))

        Window.bind(on_keyboard=self.on_keyboard)

    def on_keyboard(self, instance, keyboard, keycode, text, modifiers):
        if text == 'n':
            self.parent.new_game()
        elif text == 'c':
            self.parent.load_game()
        elif text == 'q':
            App.get_running_app().stop()


class MainGameScreen(BoxLayout):
    def __init__(self, engine: Engine, **kwargs):
        super().__init__(**kwargs)

        self.orientation = 'vertical'

        self.tileset = Tileset('1bit-pack-kenney.png', MAPPER_1BIT, col_border=1, row_border=1)
        self.engine = engine

        config = App.get_running_app().config
        level_height = config.getint('metrics', 'level_height')
        bar_height = config.getint('metrics', 'bar_height')
        gw_height = level_height/(level_height+bar_height)
        db_height = bar_height/(level_height+bar_height)

        self.game = GameWidget(self.engine, self.tileset, scale=2, size_hint=(1, gw_height))
        self.add_widget(self.game)

        down_bar = BoxLayout(orientation='horizontal', size_hint=(1, db_height))
        self.add_widget(down_bar)

        left_panel = BoxLayout(size_hint=(.4, 1), orientation='vertical')
        down_bar.add_widget(left_panel)

        self.level_number = LevelNumber(engine)
        left_panel.add_widget(self.level_number)
        self.health_bar = HealthBar(engine)
        left_panel.add_widget(self.health_bar)

        self.msg_log = MsgLog(engine, size_hint=(.6, 1))
        down_bar.add_widget(self.msg_log)

        Window.bind(on_close=self.on_close)

    def on_keyboard(self, instance, keyboard, keycode, text, modifiers):
        if keycode == 81:
            self.move_player(0, -1)
        elif keycode == 82:
            self.move_player(0, 1)
        elif keycode == 80:
            self.move_player(-1, 0)
        elif keycode == 79:
            self.move_player(1, 0)
        elif text == 'q':
            self.save_game()
            self.parent.main_menu()
        elif text == '.' and 'shift' in modifiers: # descend
            self.handle_action(actions.TakeStairsAction(self.engine.player))
        elif text == '.': # wait
            self.handle_action(actions.WaitAction(self.engine.player))
        elif text == 'g': # pickup item
            self.handle_action(actions.PickupAction(self.engine.player))
        elif text == 'v': # show message log
            MsgLogPopup(self.engine).open()
        elif text == 'c': # show character
            CharScreenPopup(self.engine).open()
        elif text == 'i': # use item
            self.open_popup(popup = InventoryActivatePopup(self.engine, self.game))
        elif text == 'd': # drop item
            self.open_popup(InventoryDropPopup(self.engine, self.tileset))
        elif text == '/': # look
            p = self.engine.player
            popup = SelectPopup(self.tileset, self.game, (p.x, p.y))
            self.open_popup(popup)

    def open_popup(self, popup: Popup):
        popup.bind(on_dismiss=self.handle_popup)
        Window.unbind(on_keyboard=self.on_keyboard)
        Window.bind(on_keyboard=popup.on_keyboard)
        popup.open()

    def handle_popup(self, popup):
        Window.unbind(on_keyboard=popup.on_keyboard)
        Window.bind(on_keyboard=self.on_keyboard)
        if hasattr(popup, 'action'):
            self.handle_action(popup.action)
        elif hasattr(popup, 'popup'):
            self.open_popup(popup.popup)
        elif not self.engine.player.is_alive: # after end game popup
            self.parent.main_menu()

    def handle_action(self, action: actions.Action) -> bool:
        try:
            action.perform()
        except exceptions.Impossible as exc:
            self.engine.message_log.add_message(exc.args[0], color.impossible)
            self.msg_log.draw()
            return False  # Skip enemy turn on exceptions.
        
        self.engine.handle_enemy_turns()
        self.engine.update_fov()

        if not self.engine.player.is_alive:
            self.open_popup(popup = EndGamePopup())
        elif self.engine.player.level.requires_level_up:
            self.open_popup(popup = LevelUpPopup(self.engine))

        self.game.draw()
        self.health_bar.draw()
        self.msg_log.draw()
        self.level_number.draw()

        return True

    def move_player(self, dx, dy):
        action = actions.BumpAction(self.engine.player, dx, dy)
        self.handle_action(action)

    def save_game(self):
        file_name = 'savegame.sav'
        self.engine.save_as(file_name)
        Logger.info(f'Game saved to {file_name}')

    def on_close(self, *args):
        self.save_game()
        return True


class HealthBar(Widget):
    def __init__(self, engine, **kwargs):
        super().__init__(**kwargs)
        self.engine = engine

    def on_size(self, *args):
        self.draw()

    def draw(self):
        self.canvas.clear()
        with self.canvas:
            wx, wy = self.pos
            wsx, wsy = self.size

            current_hp = self.engine.player.fighter.hp
            max_hp = self.engine.player.fighter.max_hp
            max_size_x = wsx-20
            curr_size_x = current_hp/max_hp*max_size_x

            Color(40/256, 40/256, 40/256, 1)
            Rectangle(pos=self.pos, size=self.size)

            Color(86/255, 105/255, 104/255)
            Rectangle(pos=(wx+10, wy+10), size=(max_size_x, wsy-20))

            Color(26/255, 107/255, 53/255)
            Rectangle(pos=(wx+10, wy+10), size=(curr_size_x, wsy-20))


class MsgLog(BoxLayout):
    def __init__(self, engine, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.engine = engine

    def on_size(self, *args):
        self.draw()

    def draw(self):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(40/256, 40/256, 40/256, 1)
            Rectangle(pos=self.pos, size=self.size)

        self.clear_widgets()

        for msg in self.engine.message_log.messages[-3:]:
            self.add_widget(Label(text=msg.full_text, color=msg.color))


class LevelNumber(BoxLayout):
    def __init__(self, engine, **kwargs):
        super().__init__(**kwargs)

        self.engine = engine

        self.label = Label(text='level')
        self.add_widget(self.label)

    def on_size(self, *args):
        self.draw()

    def draw(self):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(40/256, 40/256, 40/256, 1)
            Rectangle(pos=self.pos, size=self.size)

        floor = self.engine.game_world.current_floor
        self.label.text = f'Level {self.engine.game_world.current_floor}'


class EndGamePopup(ModalView):
    def on_size(self, *args):
        self.canvas.clear()

    def on_keyboard(self, instance, keyboard, keycode, text, modifiers):
        pass


class SelectPopup(ModalView):
    def __init__(
            self,
            game: GameWidget,
            start_xy: tuple[int, int],
            **kwargs):
        super().__init__(**kwargs)

        self.game = game

        sx, sy = start_xy
        self.sel_x = sx
        self.sel_y = sy

    def on_size(self, *args):
        self.draw()
    
    def draw(self):
        self.canvas.clear()

        with self.canvas:
            x = self.sel_x
            y = self.sel_y

            texture = self.game.tileset.get_image('X')

            wx, wy = self.game.pos
            tile_width = self.game.tileset.tile_width * self.game.scale
            tile_height = self.game.tileset.tile_height * self.game.scale
            pos_x = wx + x * tile_width
            pos_y = wy + y * tile_height
            size = (tile_width, tile_height)

            Rectangle(texture=texture, pos=(pos_x, pos_y), size=size)

    def on_keyboard(self, instance, keyboard, keycode, text, modifiers):
        if keycode == 81:
            self.sel_y -= 1
            self.draw()
        elif keycode == 82:
            self.sel_y += 1
            self.draw()
        elif keycode == 80:
            self.sel_x -= 1
            self.draw()
        elif keycode == 79:
            self.sel_x += 1
            self.draw()
        elif keycode == 40 or keycode == 44: # enter (40) or space (44)
            self.target_selected = True
            self.on_target_selected()
            self.dismiss()

    def on_target_selected(self):
        pass


class SelectCellPopup(SelectPopup):
    def __init__(
            self,
            game: GameWidget,
            start_xy: tuple[int, int],
            action_factory: Callable[[tuple[int, int]], actions.Action],
            **kwargs):
        super().__init__(game, start_xy, **kwargs)

        self.action_factory = action_factory

    def on_target_selected(self):
        self.action = self.action_factory((self.sel_x, self.sel_y))


class SelectAreaPopup(SelectCellPopup):
    def __init__(
            self,
            game: GameWidget,
            start_xy: int,
            action_factory: Callable[[tuple[int, int]], actions.Action],
            radius: int,
            **kwargs):
        super().__init__(game, start_xy, action_factory, **kwargs)

        self.radius = radius

    def draw(self):
        self.canvas.clear()

        with self.canvas:
            x = self.sel_x
            y = self.sel_y
            r = self.radius

            wx, wy = self.game.pos
            tile_width = self.game.tileset.tile_width * self.game.scale
            tile_height = self.game.tileset.tile_height * self.game.scale

            pos_x = wx + (x-(r-1)) * tile_width
            pos_y = wy + (y-(r-1)) * tile_height
            size = (tile_width * ((r-1) * 2 + 1), tile_height * ((r-1) * 2 + 1))

            Color(1, 0, 0, .25)
            Rectangle(pos=(pos_x, pos_y), size=size)

            for dx, dy in [[-r, 0], [r, 0], [0, -r], [0, r]]:
                pos_x = wx + (x+dx) * tile_width
                pos_y = wy + (y+dy) * tile_height
                size = (tile_width, tile_height)
                Rectangle(pos=(pos_x, pos_y), size=size)


class MsgLogPopup(Popup):
    def __init__(self, engine, **kwargs):
        super().__init__(**kwargs)
        self.title='Messages'

        messages = BoxLayout(orientation='vertical')
        for msg in engine.message_log.messages[-20:]:
            messages.add_widget(Label(text=msg.full_text, color=msg.color))
        self.add_widget(messages)


class CharScreenPopup(Popup):
    def __init__(self, engine, **kwargs):
        super().__init__(**kwargs)
        self.title='Character'

        main = BoxLayout(orientation='vertical')
        main.add_widget(Label(text=f'Level: {engine.player.level.current_level}'))
        main.add_widget(Label(text=f'XP: {engine.player.level.current_xp}'))
        main.add_widget(Label(text=f'XP for next Level: {engine.player.level.experience_to_next_level}'))
        main.add_widget(Label(text=f'Attack: {engine.player.fighter.power}'))
        main.add_widget(Label(text=f'Defense: {engine.player.fighter.defense}'))
        self.add_widget(main)


class InventoryPopup(Popup):    
    def __init__(self, engine: Engine, tileset: Tileset, **kwargs):
        super().__init__(**kwargs)
        self.engine = engine
        self.tileset = tileset

        self.title = 'Inventory'

        items = BoxLayout(orientation='vertical')
        for i, item in enumerate(engine.player.inventory.items):
            texture = self.tileset.get_image(chr(item.tile))

            row = BoxLayout(orientation='horizontal')
            row.add_widget(UxImage(texture=texture, size_hint=(.1, 1)))

            item_key = chr(ord('a') + i)
            item_string = f"({item_key}) {item.name}"

            if engine.player.equipment.item_is_equipped(item):
                item_string = f"{item_string} (E)"

            row.add_widget(Label(text=item_string))
            items.add_widget(row)
        self.add_widget(items)


    def on_keyboard(self, instance, keyboard, keycode, text, modifiers):
        self.select_item(text)
        self.dismiss()

    def select_item(self, key: str):
        index = ord(key) - ord('a')

        try:
            selected_item = self.engine.player.inventory.items[index]
            self.on_item_selected(selected_item)
        except IndexError:
            self.engine.message_log.add_message("Invalid entry.", color.invalid)

    def on_item_selected(self, item: entity.Item):
        """Called when the user selects a valid item."""
        raise NotImplementedError()


class InventoryActivatePopup(InventoryPopup):
    def __init__(self, engine: Engine, game: GameWidget, **kwargs):
        super().__init__(engine, game.tileset, **kwargs)
        self.game = game

        self.title = 'Select an item to use'
        
    def on_item_selected(self, item: entity.Item):
        if item.consumable:
            if item.consumable.selector == 'single_cell':
                self.engine.message_log.add_message(
                    "Select a target location.", color.needs_target
                )
                p = self.engine.player
                action_factory = lambda xy: actions.ItemAction(self.engine.player, item, xy)
                self.popup = SelectCellPopup(self.game, (p.x, p.y), action_factory)
            elif item.consumable.selector == 'area':
                p = self.engine.player
                action_factory = lambda xy: actions.ItemAction(self.engine.player, item, xy)
                self.popup = SelectAreaPopup(self.game, (p.x, p.y), action_factory, item.consumable.radius)
            else:
                self.action = item.consumable.get_action(self.engine.player)
        elif item.equippable:
            self.action = actions.EquipAction(self.engine.player, item)


class InventoryDropPopup(InventoryPopup):
    def __init__(self, engine: Engine, tileset: Tileset, **kwargs):
        super().__init__(engine, tileset, **kwargs)

        self.title = 'Select an item to drop'

    def on_item_selected(self, item: entity.Item):
        self.action = actions.DropItem(self.engine.player, item)


class LevelUpPopup(Popup):
    def __init__(self, engine, **kwargs):
        super().__init__(**kwargs)
        self.engine = engine

        self.title='Level Up!'

        main = BoxLayout(orientation='vertical')
        main.add_widget(Label(text='Congratulations! You level up!'))
        main.add_widget(Label(text='Select an attribute to increase.'))
        main.add_widget(Label(text=f'a) Constitution (+20 HP, from {engine.player.fighter.max_hp})'))
        main.add_widget(Label(text=f'b) Strength (+1 attack, from {engine.player.fighter.power})'))
        main.add_widget(Label(text=f'c) Agility (+1 defense, from {engine.player.fighter.defense})'))
        self.add_widget(main)

    def on_keyboard(self, instance, keyboard, keycode, text, modifiers):
        if text == 'a':
            self.engine.player.level.increase_max_hp()
            self.dismiss()
        elif text == 'b':
            self.engine.player.level.increase_power()
            self.dismiss()
        elif text == 'c':
            self.engine.player.level.increase_defense()
            self.dismiss()
        else:
            self.engine.message_log.add_message("Invalid entry.", color.invalid)


class DHApp(App):
    def build_config(self, config):
        config.adddefaultsection('metrics')
    
    def build(self):
        self.title = 'DigHack'
        config = self.config
        level_width = self.config.getint('metrics', 'level_width')
        level_height = self.config.getint('metrics', 'level_height')
        bar_height = self.config.getint('metrics', 'bar_height')
        Window.size = (level_width*16, (level_height+bar_height)*16)
        return self.make_handler()
    
    def make_handler(self):
        return DefaultGlobalEventHandler()


class DebugDHApp(DHApp):
    def make_handler(self):
        return DebugGlobalEventHandler()


if __name__ == '__main__':
    DebugDHApp().run()
