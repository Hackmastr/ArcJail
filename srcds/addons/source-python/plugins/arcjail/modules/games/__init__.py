import os

from commands.say import SayCommand
from events import Event
from filters.players import PlayerIter
from menus import PagedMenu, PagedOption

from controlled_cvars.handlers import (
    bool_handler, color_handler, float_handler, int_handler,
    sound_nullable_handler, string_handler
)

from ...arcjail import InternalEvent, load_downloadables

from ...resource.strings import build_module_strings

from ..effects import set_player_sprite

from ..game_status import get_status, GameStatus, set_status
from ..game_status import strings_module as strings_game_status

from ..jail_menu import new_available_option

from ..leaders import is_leader

from ..players import main_player_manager, tell

from .. import build_module_config, parse_modules


strings_module = build_module_strings('games/common')
config_manager = build_module_config('games/common')

config_manager.controlled_cvar(
    bool_handler,
    "enabled",
    default=1,
    description="Enable/Disable !games feature",
)
config_manager.controlled_cvar(
    int_handler,
    "min_players_number",
    default=2,
    description="Minimum number of prisoners to be able to "
                "launch the game with",
)
config_manager.controlled_cvar(
    bool_handler,
    "launch_from_cage",
    default=1,
    description="Allow area-specific games to be launched from the cage",
)
config_manager.controlled_cvar(
    bool_handler,
    "launch_from_anywhere",
    default=0,
    description="Allow area-specific games to be launched from "
                "any place on the map",
)
config_manager.controlled_cvar(
    string_handler,
    "winner_sprite",
    default="arcjail/winner.vmt",
    description="Winner sprite (don't forget to include VMT/SPR extension)",
)
config_manager.controlled_cvar(
    string_handler,
    "loser_sprite",
    default="arcjail/loser.vmt",
    description="Loser sprite (don't forget to include VMT/SPR extension)",
)
config_manager.controlled_cvar(
    float_handler,
    "sprite_duration",
    default=5.0,
    description="How long sprites above players heads should "
                "last, 0 - disable",
)
config_manager.controlled_cvar(
    color_handler,
    "team1_color",
    default="0,146,226",
    description="Color for players in team Alpha",
)
config_manager.controlled_cvar(
    string_handler,
    "team1_model",
    default="models/player/arcjail/team_alpha/team_alpha.mdl",
    description="Model for team Alpha players",
)
config_manager.controlled_cvar(
    color_handler,
    "team2_color",
    default="235,200,0",
    description="Color for players in team Bravo",
)
config_manager.controlled_cvar(
    string_handler,
    "team2_model",
    default="models/player/arcjail/team_bravo/team_bravo.mdl",
    description="Model for team Bravo players",
)
config_manager.controlled_cvar(
    color_handler,
    "team3_color",
    default="255,0,170",
    description="Color for players in team Charlie",
)
config_manager.controlled_cvar(
    string_handler,
    "team3_model",
    default="models/player/arcjail/team_charlie/team_charlie.mdl",
    description="Model for team Charlie players",
)
config_manager.controlled_cvar(
    color_handler,
    "team4_color",
    default="255,102,0",
    description="Color for players in team Delta",
)
config_manager.controlled_cvar(
    string_handler,
    "team4_model",
    default="models/player/arcjail/team_delta/team_delta.mdl",
    description="Model for team Delta players",
)
config_manager.controlled_cvar(
    bool_handler,
    "prefer_model_over_color",
    default=1,
    description="Enable/Disable marking prisoners with a model (TEAMX_MODEL) "
                "instead of color (TEAMX_COLOR)",
)
config_manager.controlled_cvar(
    sound_nullable_handler,
    "winner_sound",
    default="arcjail/gamewin.mp3",
    description="Winner sound",
)
config_manager.controlled_cvar(
    sound_nullable_handler,
    "loser_sound",
    default="",
    description="Loser sound",
)
config_manager.controlled_cvar(
    sound_nullable_handler,
    "score_sound",
    default="arcjail/goalsound.mp3",
    description="Score sound",
)
config_manager.controlled_cvar(
    sound_nullable_handler,
    "prepare_sound",
    default="arcjail/gameprepare.mp3",
    description="Prepare sound",
)
config_manager.controlled_cvar(
    sound_nullable_handler,
    "countdown_sound",
    default="arcjail/beep2.mp3",
    description="Countdown sound",
)
config_manager.controlled_cvar(
    float_handler,
    "prepare_timeout",
    default=3.0,
    description="Preparation timeout for games that require it",
)


class GameLauncher:
    def __init__(self, game_class):
        self.caption = game_class.caption
        self.game_class = game_class

    def __eq__(self, value):
        return self.game_class == value.game_class

    def launch(self, leader_player, players, **kwargs):
        raise NotImplementedError

    def get_launch_denial_reason(self, leader_player, players, **kwargs):
        if self not in self.game_class.get_available_launchers(
                leader_player, players):

            return strings_module['fail_game_unavailable']

        return None


_popups = {}
_game_instances = []
_available_game_classes = []
_sounds = {}
_downloadables_sounds = load_downloadables('games-base-sounds.res')
_downloadables_sprites = load_downloadables('games-base-sprites.res')


def _launch_game(launcher, leader_player, players, **kwargs):
    game = launcher.launch(leader_player, players=players, **kwargs)
    set_instance(game)
    game.set_stage_group('init')


def get_players_to_play():
    rs = []
    for player in PlayerIter(('jail_prisoner', 'alive')):
        if player.userid in main_player_manager:
            rs.append(main_player_manager[player.userid])

    return tuple(rs)


def get_available_launchers(leader_player, players):
    result = []
    for game_class in _available_game_classes:
        result.extend(
            game_class.get_available_launchers(leader_player, players))

    return tuple(result)


def get_game_denial_reason(player):
    if not config_manager['enabled']:
        return strings_module['fail_disabled']

    if _game_instances:
        return strings_module['fail_game_already_started']

    status = get_status()
    if status == GameStatus.BUSY:
        return strings_game_status['busy']

    if status == GameStatus.NOT_STARTED:
        return strings_game_status['not_started']

    if not is_leader(player):
        return strings_module['fail_leaders_only']

    if not get_available_launchers(player, get_players_to_play()):
        return strings_module['fail_none_available']

    return None


def add_available_game(game_class):
    _available_game_classes.append(game_class)


def remove_available_game(game_class):
    _available_game_classes.remove(game_class)


def set_instance(game):
    if game is None:
        set_status(GameStatus.FREE)
        _game_instances.clear()

    else:
        set_status(GameStatus.BUSY)
        _game_instances.append(game)


def get_instance():
    return _game_instances[0] if _game_instances else None


def helper_set_winner(player, effects=True):
    InternalEvent.fire('jail_game_winner', player=player)

    if player.dead or not effects:
        return

    if (config_manager['winner_sprite'] != "" and
            config_manager['sprite_duration'] > 0):

        set_player_sprite(player,
                          config_manager['winner_sprite'],
                          config_manager['sprite_duration'])

    if config_manager['winner_sound'] is not None:
        config_manager['winner_sound'].play(player.index)


def helper_set_loser(player, effects=True):
    InternalEvent.fire('jail_game_loser', player=player)

    if player.dead or not effects:
        return

    if (config_manager['loser_sprite'] != "" and
            config_manager['sprite_duration'] > 0):

        set_player_sprite(player,
                          config_manager['loser_sprite'],
                          config_manager['sprite_duration'])

    if config_manager['loser_sound'] is not None:
        config_manager['loser_sound'].play(player.index)


def helper_set_neutral(player):
    InternalEvent.fire('jail_game_neutral', player=player)


def send_popup(player):
    reason = get_game_denial_reason(player)
    if reason:
        tell(player, reason)
        return

    if player.userid in _popups:
        _popups[player.userid].close()

    players = get_players_to_play()

    def select_callback(popup, player_index, option):
        reason = get_game_denial_reason(player)
        if reason is not None:
            tell(player, reason)
            return

        launcher = option.value
        reason = launcher.get_launch_denial_reason(player, players)
        if reason is not None:
            tell(player, reason)
            return

        _launch_game(launcher, player, players)

    popup = _popups[player.userid] = PagedMenu(
        select_callback=select_callback,
        title=strings_module['popup title_choose']
    )

    for launcher in get_available_launchers(player, players):
        popup.append(PagedOption(
            text=launcher.caption,
            value=launcher,
            highlight=True,
            selectable=True
        ))

    popup.send(player.index)


def reset():
    game = get_instance()
    if game is not None:
        try:
            game.set_stage_group('destroy')
        finally:
            set_instance(None)

    for popup in _popups.values():
        popup.close()

    _popups.clear()


@Event('round_start')
def on_round_start(game_event):
    reset()


@InternalEvent('unload')
def on_unload(event_var):
    reset()


@SayCommand('!games')
def say_games(command, index, team_only):
    player = main_player_manager.get_by_index(index)
    send_popup(player)


# =============================================================================
# >> JAIL MENU ENTRIES
# =============================================================================
def jailmenu_games(player):
    send_popup(player)


def jailmenu_games_handler_active(player):
    return get_game_denial_reason(player) is None


new_available_option(
    'launch-game',
    strings_module['jailmenu_entry_option'],
    jailmenu_games,
    handler_active=jailmenu_games_handler_active,
)


# =============================================================================
# >> DECORATORS
# =============================================================================
def stage(stage_id):
    def stage_gen(func):
        stage_ = Stage(stage_id)
        stage_.callback = func
        return stage_
    return stage_gen


class Stage:
    def __init__(self, stage_id):
        self.stage_id = stage_id
        self.callback = None
        self.game_instance = None

    def __call__(self, *args, **kwargs):
        if self.callback is not None:
            self.callback(self.game_instance, *args, **kwargs)


def game_event_handler(alias, event):
    def decorator(func):
        game_event_handler_ = GameEventHandler(alias, event)
        game_event_handler_.callback = func
        return game_event_handler_
    return decorator


class GameEventHandler:
    def __init__(self, alias, event):
        self.alias = alias
        self.event = event
        self.callback = None
        self.game_instance = None

    def __call__(self, event_data):
        if self.callback is not None:
            self.callback(self.game_instance, event_data)


def game_internal_event_handler(alias, event):
    def decorator(func):
        game_internal_event_handler_ = GameInternalEventHandler(alias, event)
        game_internal_event_handler_.callback = func
        return game_internal_event_handler_
    return decorator


class GameInternalEventHandler:
    def __init__(self, alias, event):
        self.alias = alias
        self.event = event
        self.callback = None
        self.game_instance = None

    def __call__(self, event_data):
        if self.callback is not None:
            self.callback(self.game_instance, event_data)


class Push:
    def __init__(self, slot_id, push_id):
        self.slot_id = slot_id
        self.push_id = push_id
        self.callback = None
        self.game_instance = None

    def __call__(self, args):
        if self.callback is not None:
            self.callback(self.game_instance, args)


def push(slot_id, push_id):
    def decorator(func):
        push_ = Push(slot_id, push_id)
        push_.callback = func
        return push_
    return decorator


# =============================================================================
# >> METACLASS
# =============================================================================
class GameMeta(type):
    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)

        cls._stages_map = {}
        cls._internal_events = {}
        cls._events = {}
        cls._stage_groups = {}
        for base in bases[::-1]:
            cls._events.update(base._events)
            cls._stages_map.update(base._stages_map)
            cls._stage_groups.update(base._stage_groups)

        for key, value in namespace.items():
            if isinstance(value, Stage):
                cls._stages_map[value.stage_id] = value

            elif isinstance(value, GameInternalEventHandler):
                cls._internal_events[value.alias] = value

            elif isinstance(value, GameEventHandler):
                cls._events[value.alias] = value

            elif key == 'stage_groups':
                cls._stage_groups.update(value)

        return cls


# =============================================================================
# >> BASE CLASSES IMPORT
# =============================================================================
from . import base_classes


# =============================================================================
# >> GAMES IMPORT
# =============================================================================
current_dir = os.path.dirname(__file__)
__all__ = parse_modules(current_dir)


from . import *
