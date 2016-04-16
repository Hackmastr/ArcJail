from mathlib import Vector

from ...resource.strings import build_module_strings

from ..damage_hook import (
    get_hook, protected_player_manager, strings_module as strings_damage_hook)

from ..equipment_switcher import saved_player_manager

from ..players import main_player_manager

from ..rebels import register_rebel_filter

from ..show_damage import show_damage

from ..teams import GUARDS_TEAM

from .survival import SurvivalPlayerBasedFriendlyFire
from .survival import SurvivalTeamBasedFriendlyFire

from . import (
    add_available_game, stage)


strings_module = build_module_strings('games/survival_knockout')


def push_by_damage_amount(victim, attacker, damage, map_data):
    # TODO: When damage_hook module is refactored, use TakeDamageInfo instead
    d = victim.origin - attacker.origin

    dmg_base = map_data['ARENA_DAMAGE_BASE']
    base_force_h = map_data['ARENA_HORIZONTAL_FORCE_BASE']
    force_v = map_data['ARENA_VERTICAL_FORCE']

    vec_len = (d.x*d.x + d.y*d.y) ** 0.5

    if vec_len == 0.0:
        return

    f = {
        1: lambda x: x,
        2: lambda x: x ** 0.5,
        3: lambda x: x ** (1.0 / 3.0),
    }.get(map_data['ARENA_FORCE_FALLOFF'])

    if f is None:
        return

    k_h = (base_force_h / vec_len) * f(damage / dmg_base)
    k_v = f(damage / dmg_base)

    victim.base_velocity = Vector(d.x * k_h, d.y * k_h, force_v * k_v)


class SurvivalKnockoutPlayerBased(SurvivalPlayerBasedFriendlyFire):
    caption = strings_module['title playerbased_standard']
    module = 'survival_knockout_playerbased'

    @stage('survival-equip-damage-hooks')
    def stage_survival_equip_damage_hooks(self):
        def hook_on_death(counter, game_event):
            player = main_player_manager[game_event.get_int('userid')]
            if player in self._players:
                saved_player = saved_player_manager[player.userid]
                saved_player.strip()
                self.on_death(player)

            return True

        def hook_p(counter, game_event):
            victim_uid = game_event.get_int('userid')
            attacker_uid = game_event.get_int('attacker')

            if attacker_uid in (0, victim_uid):
                return False

            attacker = main_player_manager[attacker_uid]
            victim = main_player_manager[victim_uid]

            if attacker in self._players:
                damage = game_event.get_int('dmg_health')
                show_damage(attacker, damage)
                push_by_damage_amount(
                    victim, attacker, damage, self.map_data)

            return False

        def hook_w_min_damage(counter, game_event):
            if game_event.get_int('attacker') != 0:
                return False

            min_damage = self.map_data['ARENA_MIN_DAMAGE_TO_HURT']
            current_damage = game_event.get_int('dmg_health')
            return current_damage >= min_damage

        for player in main_player_manager.values():
            if player.dead:
                continue

            p_player = protected_player_manager[player.userid]
            self._counters[player.userid] = []
            if player in self._players:
                counter1 = p_player.new_counter(
                    display=strings_damage_hook['health against_guards'])

                counter1.hook_hurt = get_hook('G')
                counter1.hook_death = hook_on_death

                counter2 = p_player.new_counter()
                counter2.hook_hurt = hook_p

                counter3 = p_player.new_counter()
                counter3.hook_hurt = hook_w_min_damage
                counter3.hook_death = hook_on_death
                counter3.health = self.map_data['INITIAL_HEALTH']

                self._counters[player.userid].append(counter1)
                self._counters[player.userid].append(counter2)
                self._counters[player.userid].append(counter3)

            elif player.team == GUARDS_TEAM:
                counter = p_player.new_counter()
                if self.map_data['ALLOW_REBELLING']:
                    counter.hook_hurt = get_hook('SWP')
                    counter.display = strings_damage_hook[
                        'health against_prisoners']

                else:
                    counter.hook_hurt = get_hook('SW')
                    counter.display = strings_damage_hook['health general']

                self._counters[player.userid].append(counter)

            p_player.set_protected()

        if not self.map_data['ALLOW_REBELLING']:
            def rebel_filter(player):
                return player not in self._players_all

            self._rebel_filter = rebel_filter
            register_rebel_filter(rebel_filter)


add_available_game(SurvivalKnockoutPlayerBased)