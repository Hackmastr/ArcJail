import os
from traceback import format_exc
from warnings import warn

from commands.say import SayCommand
from events import Event
from filters.players import PlayerIter
from listeners.tick import Delay
from menus import PagedMenu, PagedOption

from controlled_cvars import InvalidValue
from controlled_cvars.handlers import (
    bool_handler, float_handler, int_handler, sound_nullable_handler)

from ...arcjail import InternalEvent, load_downloadables

from ...resource.strings import build_module_strings

from ..game_status import (
    GameStatus, get_status, set_status, strings_module as strings_game_status)

from ..games import (
    game_event_handler, game_internal_event_handler, GameMeta, push, stage)

from ..players import broadcast, main_player_manager, tell

from ..rebels import is_rebel, register_rebel_filter

from ..teams import PRISONERS_TEAM

from .. import build_module_config, parse_modules


strings_module = build_module_strings('lrs/common')
config_manager = build_module_config('lrs/common')

config_manager.controlled_cvar(
    bool_handler,
    "enabled",
    default=1,
    description="Enable/Disable !lr feature",
)
config_manager.controlled_cvar(
    int_handler,
    "prisoners_limit",
    default=1,
    description="Number of alive prisoners left for Last Request to become "
                "available",
)


def allow_rebels_handler(cvar):
    val = int_handler(cvar)
    if not 0 <= val <= 2:
        raise InvalidValue
    return val

config_manager.controlled_cvar(
    allow_rebels_handler,
    "allow_rebels",
    default=2,
    description="Allow rebels to play Last Request (0 - disallow, 1 - allow, "
                "2 - ask the guard)",
)


def ask_guard_timeout_handler(cvar):
    val = float_handler(cvar)
    if not 3 <= val <= 60:
        raise InvalidValue
    return val

config_manager.controlled_cvar(
    ask_guard_timeout_handler,
    "ask_guard_timeout",
    default=15,
    description="Number of seconds for the guard to decide whether a rebel "
                "can play or not (before auto action occurs); min: 3, max: 60",
)
config_manager.controlled_cvar(
    bool_handler,
    "ask_guard_auto_action",
    default=1,
    description="What to do if the guard didn't decide whether a rebel can "
                "play or not: 0 - automatically disallow, "
                "1 - automatically allow",
)
config_manager.controlled_cvar(
    int_handler,
    "max_at_once",
    default=1,
    description="How many Last Request games can be played at the same "
                "time as most",
)
config_manager.controlled_cvar(
    bool_handler,
    "win_reward_enabled",
    default=1,
    description="Enable/Disable Win Reward feature",
)


def win_reward_timeout_handler(cvar):
    val = float_handler(cvar)
    if not 3 <= val <= 60:
        raise InvalidValue
    return val

config_manager.controlled_cvar(
    win_reward_timeout_handler,
    "win_reward_timeout",
    default=7,
    description="Number of seconds Win Reward lasts for; min: 3, max: 60",
)
config_manager.controlled_cvar(
    bool_handler,
    "win_reward_countdown_enabled",
    default=1,
    description="Enable/Disable countdown for Win Reward remaining time",
)
config_manager.controlled_cvar(
    sound_nullable_handler,
    "win_reward_countdown_sound",
    default="arcjail/beep2.mp3",
    description="Sound used for Win Reward countdown, leave empty to disable",
)
config_manager.controlled_cvar(
    sound_nullable_handler,
    "win_reward_start_sound",
    default="arcjail/finishhim.mp3",
    description="Sound used to announce Win Reward, leave empty to disable",
)
config_manager.controlled_cvar(
    sound_nullable_handler,
    "victory_sound",
    default="arcjail/lrwin3.mp3",
    description="Sound to play to Last Request winner, leave empty to disable",
)
config_manager.controlled_cvar(
    sound_nullable_handler,
    "flawless_sound",
    default="arcjail/flawless.mp3",
    description="Additional sound to play if the victory was flawless, "
                "leave empty to disable",
)
config_manager.controlled_cvar(
    sound_nullable_handler,
    "availability_sound",
    default="arcjail/lr3.mp3",
    description="Sound to play when Last Request becomes available to play, "
                "leave empty to disable",
)
config_manager.controlled_cvar(
    sound_nullable_handler,
    "combat_lr_start_sound",
    default="arcjail/fight.mp3",
    description="Sound to play when Last Request of a combat type starts, "
                "leave empty to disable",
)


class DestructionFailure(Warning):
    pass


class LastRequestGameStatus:
    NOT_STARTED = 0
    IN_PROGRESS = 1
    FINISHED = 2


class GameLauncher:
    def __init__(self, game_class):
        self.caption = game_class.caption
        self.game_class = game_class.caption

    def __eq__(self, other):
        return self.game_class == other.game_class

    def launch(self, players, **kwargs):
        raise NotImplementedError

    def get_launch_denial_reason(self, **kwargs):
        if self not in self.game_class.get_available_launchers():
            return strings_module['fail game_unavailable']

        return None


_rebel_delays = {}
_popups = {}
_game_instances = []
_available_game_classes = []
_downloadables_sounds = load_downloadables('lrs-base-sounds.res')
_announced = False
_saved_game_status = None


def _launch_game(launcher, players, **kwargs):
    game = launcher.launch(players=players, **kwargs)
    add_instance(game)
    game.set_stage_group('init')


def _rebel_filter(player):
    for game_instance in _game_instances:
        if game_instance.status != LastRequestGameStatus.IN_PROGRESS:
            continue

        if player in game_instance.players:
            return False

    return True

register_rebel_filter(_rebel_filter)


def check_if_announced():
    global _announced
    if _announced:
        return

    if not is_available():
        return

    broadcast(strings_module['announce_available'])

    if config_manager['availability_sound'] is not None:
        config_manager['availability_sound'].play()

    _announced = True


def is_available():
    for player in PlayerIter(['jail_prisoner', 'alive']):
        if get_lr_denial_reason(player) is None:
            return True

    return False


def get_lr_denial_reason(player):
    if not config_manager['enabled']:
        return strings_module['fail disabled']

    if get_status() == GameStatus.BUSY and _saved_game_status is None:
        return strings_game_status['busy']

    if get_status() == GameStatus.NOT_STARTED:
        return strings_game_status['not_started']

    if player.dead:
        return strings_module['fail dead']

    if player.team != PRISONERS_TEAM:
        return strings_module['fail wrong_team']

    if config_manager['allow_rebels'] == 0 and is_rebel(player):
        return strings_module['fail rebel']

    if get_player_game_instance(player):
        return strings_module['fail already_playing']

    for player_ in PlayerIter(['jail_guard', 'alive']):
        if get_player_game_instance(player_) is None:
            break
    else:
        return strings_module['fail no_partners']

    if (len(PlayerIter(['jail_prisoner', 'alive'])) >
            config_manager['prisoners_limit']):

        return strings_module['fail too_many_prisoners']

    if len(get_started_games()) >= config_manager['max_at_once']:
        return strings_module['fail too_many_lrs']

    return None


def get_player_game_instance(player):
    for game_instance in _game_instances:
        if game_instance.status != LastRequestGameStatus.IN_PROGRESS:
            continue

        if player in game_instance.players:
            return game_instance

    return None


def get_started_games():
    rs = []
    for game_instance in _game_instances:
        if game_instance.status == LastRequestGameStatus.IN_PROGRESS:
            rs.append(game_instance)

    return tuple(rs)


def add_instance(game_instance):
    global _saved_game_status
    if _saved_game_status is None:
        _saved_game_status = get_status()

    set_status(GameStatus.BUSY)
    _game_instances.append(game_instance)


def remove_instance(game_instance):
    _game_instances.remove(game_instance)

    if not _game_instances:
        global _saved_game_status
        set_status(_saved_game_status)
        _saved_game_status = None


def add_available_game(game_class):
    _available_game_classes.append(game_class)


def remove_available_game(game_class):
    _available_game_classes.remove(game_class)


def get_available_launchers():
    rs = []
    for game_class in _available_game_classes:
        rs.extend(game_class.get_available_launchers())
    return tuple (rs)


def send_popup(player):
    reason = get_lr_denial_reason(player)
    if reason:
        tell(player, reason)
        return

    if player.userid in _rebel_delays:
        tell(player, strings_module['fail already_asking_guard'])
        return

    if player.userid in _popups:
        _popups[player.userid].close()

    def select_callback_game(popup, player_index, option):
        reason = get_lr_denial_reason(player)
        if reason is not None:
            tell(player, reason)
            return

        launcher = option.value
        reason = launcher.get_launch_denial_reason()
        if reason is not None:
            tell(player, reason)
            return

        if player.userid in _popups:
            _popups[player.userid].close()

        def select_callback_player(popup, player_index, option):
            reason = get_lr_denial_reason(player)
            if reason is not None:
                tell(player, reason)
                return

            reason = launcher.get_launch_denial_reason()
            if reason is not None:
                tell(player, reason)
                return

            guard = option.value
            if get_player_game_instance(guard) is not None:
                tell(player, strings_module['fail busy_partner'])
                return

            if is_rebel(player):
                if guard.userid in _popups:
                    _popups[guard.userid].close()

                def auto_action():
                    del _rebel_delays[player.userid]

                    if config_manager['ask_guard_auto_action']:
                        reason = get_lr_denial_reason(player)
                        if reason is not None:
                            tell(player, reason)
                            return

                        reason = launcher.get_launch_denial_reason()
                        if reason is not None:
                            tell(player, reason)
                            return

                        if get_player_game_instance(guard) is not None:
                            tell(player, strings_module['fail busy_partner'])
                            return

                        _launch_game(launcher, (player, guard))

                    else:
                        tell(player, strings_module['fail decline'])

                _rebel_delays[player.userid] = Delay(
                    config_manager['ask_guard_timeout'], auto_action)

                def select_callback_rebel(popup, player_index, option):
                    if player.userid in _rebel_delays:
                        if _rebel_delays[player.userid].running:
                            _rebel_delays[player.userid].cancel()

                        del _rebel_delays[player.userid]

                    if option.value:
                        reason = get_lr_denial_reason(player)
                        if reason is not None:
                            tell(player, reason)
                            return

                        reason = launcher.get_launch_denial_reason()
                        if reason is not None:
                            tell(player, reason)
                            return

                        if get_player_game_instance(guard) is not None:
                            tell(player, strings_module['fail busy_partner'])
                            return

                        _launch_game(launcher, (player, guard))

                    else:
                        tell(player, strings_module['fail decline'])

                popup = _popups[guard.userid] = PagedMenu(
                    select_callback=select_callback_rebel,
                    title=strings_module['let_him_play']
                )

                popup.append(PagedOption(
                    text=strings_module['let_him_play yes'],
                    value=True,
                    highlight=True,
                    selectable=True
                ))
                popup.append(PagedOption(
                    text=strings_module['let_him_play no'],
                    value=False,
                    highlight=True,
                    selectable=True
                ))

                popup.send(guard.index)

                tell(player, strings_module['rebel_asking_guard'])

            else:
                _launch_game(launcher, (player, guard))

        popup = _popups[player.userid] = PagedMenu(
            select_callback=select_callback_player,
            title=strings_module['popup title choose_player'],
        )

        spare_players = set(PlayerIter(['#jail_guard', '#alive']))

        for game_instance in _game_instances:
            spare_players.difference_update(game_instance.players)

        for player_ in spare_players:
            popup.append(PagedOption(
                text=player_.name,
                value=player_,
                highlight=True,
                selectable=True
            ))

        popup.send(player.index)

    popup = _popups[player.userid] = PagedMenu(
        select_callback=select_callback_game,
        title=strings_module['popup title choose_game']
    )

    for launcher in get_available_launchers():
        popup.append(PagedOption(
            text=launcher.caption,
            value=launcher,
            highlight=True,
            selectable=True
        ))

    popup.send(player.index)


def reset():
    global _saved_game_status
    _saved_game_status = None

    global _announced
    _announced = False

    for game_instance in _game_instances:
        if game_instance.status != LastRequestGameStatus.FINISHED:
            try:
                game_instance.set_stage_group('destroy')
            except Exception as e:
                warn(DestructionFailure(
                    "Couldn't properly destroy the game. "
                    "Exception: {}. Traceback:\n{}".format(e, format_exc())
                ))

    _game_instances.clear()

    for popup in _popups.values():
        popup.close()

    _popups.clear()


@Event('player_hurt')
def on_player_hurt(game_event):
    victim = main_player_manager[game_event.get_int('userid')]
    if victim.dead:     # Will be handled by player_death
        return

    attacker_uid = game_event.get_int('attacker')
    if attacker_uid in (victim.userid, 0):
        return

    attacker = main_player_manager[attacker_uid]
    game_instance_victim = get_player_game_instance(victim)
    game_instance_attacker = get_player_game_instance(attacker)
    damage = game_event.get_int('dmg_health')

    # Case 1. Attacker and victim are in the same LR
    # Will be handled inside LR if needed
    if game_instance_victim == game_instance_attacker:
        return

    # Case 2. Non-LR player attacks LR player
    if game_instance_victim is not None and game_instance_attacker is None:
        victim.health += damage
        attacker.take_damage(attacker.health + 1)

        broadcast(strings_module['crime external slay'].tokenize(
            player=attacker.name))

        return

    # Cases 3 and 4. LR player attacks non-LR player
    # or LR player attacks player from different LR
    if game_instance_attacker is not None:
        victim.health += damage

        return


@Event('player_death_real')
def on_player_death_real(game_event):
    check_if_announced()

    victim = main_player_manager[game_event.get_int('userid')]
    attacker_uid = game_event.get_int('attacker')
    if attacker_uid in (victim.userid, 0):
        return

    attacker = main_player_manager[attacker_uid]
    game_instance_victim = get_player_game_instance(victim)
    game_instance_attacker = get_player_game_instance(attacker)

    # Case 1 (see comments to on_player_hurt)
    if game_instance_victim == game_instance_attacker:
        return

    # Cases 2, 3 and 4
    if (game_instance_victim is not None and game_instance_attacker is None or
            game_instance_attacker is not None):

        attacker.take_damage(attacker.health + 1)

        broadcast(strings_module['crime external slay'].tokenize(
            player=attacker.name))

        return


@Event('round_start')
def on_round_start(game_event):
    reset()
    check_if_announced()


@InternalEvent('unload')
def on_unload(event_var):
    reset()


@SayCommand('!lr')
def say_games(command, index, team_only):
    player = main_player_manager.get_by_index(index)
    send_popup(player)


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