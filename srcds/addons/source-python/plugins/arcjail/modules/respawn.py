from events import Event
from filters.players import PlayerIter
from menus import PagedMenu, PagedOption

from controlled_cvars.handlers import bool_handler

from ..arcjail import InternalEvent

from ..resource.strings import build_module_strings

from .game_status import GameStatus, get_status

from .jail_menu import new_available_option

from .leaders import is_leader

from .players import broadcast, tell

from . import build_module_config


strings_module = build_module_strings('respawn')
config_manager = build_module_config('respawn')


config_manager.controlled_cvar(
    bool_handler,
    "enabled",
    default=1,
    description="Enable/Disable respawning feature in jail menu",
)
config_manager.controlled_cvar(
    bool_handler,
    "allow_respawning_rebels",
    default=0,
    description="Allow/Disallow respawning rebels",
)


_round_end = False
_rebel_steamids = set()    # To prevent resetting rebel status by reconnecting
_popups = {}


def respawn(player):
    player.set_property_int('m_iPlayerState', 0)
    player.set_property_int('m_lifeState', 512)
    player.spawn()


def get_leader_respawn_denial_reason(player):
    if not config_manager['enabled']:
        return strings_module['fail_disabled']

    if _round_end:
        return strings_module['fail_round_end']

    if not is_leader(player):
        return strings_module['fail_leader_required']

    status = get_status()
    if status == GameStatus.BUSY:
        return strings_module['fail_game_busy']

    if status == GameStatus.NOT_STARTED:
        return strings_module['fail_game_not_started']

    for player_ in PlayerIter(['dead', 'jail_prisoner']):
        if (player_.steamid in _rebel_steamids and
                not config_manager['allow_respawning_rebels']):

            continue

        break

    else:
        return strings_module['fail_empty']

    return None


def send_leader_popup(player):
    reason = get_leader_respawn_denial_reason(player)
    if reason:
        tell(player, reason)
        return

    if player.userid in _popups:
        _popups[player.userid].close()

    def select_callback(popup, player_index, option):
        reason = get_leader_respawn_denial_reason(player)
        if reason:
            tell(player, reason)
            return

        player_ = option.value
        if not player_.dead:
            tell(player, strings_module['fail_alive'])
            return

        respawn(player_)

        broadcast(strings_module['resurrected_by_leader'].tokenize(
            player=player_.name))

    popup = _popups[player.userid] = PagedMenu(
        select_callback=select_callback,
        title=strings_module['popup_title_resurrect']
    )

    for player_ in PlayerIter(['dead', 'jail_prisoner']):
        if (player_.steamid in _rebel_steamids and
                not config_manager['allow_respawning_rebels']):

            continue

        popup.append(PagedOption(
            text=player_.name,
            value=player_,
            highlight=True,
            selectable=True
        ))

    popup.send(player.index)


@Event('round_start')
def on_round_start(game_event):
    for popup in _popups.values():
        popup.close()

    _popups.clear()

    _rebel_steamids.clear()


@InternalEvent('unload')
def on_unload(event_var):
    for popup in _popups.values():
        popup.close()

    _popups.clear()


# =============================================================================
# >> JAIL MENU ENTRIES
# =============================================================================
def jailmenu_respawn(player):
    send_leader_popup(player)


def jailmenu_respawn_handler_active(player):
    return get_leader_respawn_denial_reason(player) is None


new_available_option(
    'respawn',
    strings_module['jailmenu_entry_resurrect'],
    jailmenu_respawn,
    jailmenu_respawn_handler_active,
    jailmenu_respawn_handler_active,
)