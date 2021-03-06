# This file is part of ArcJail.
#
# ArcJail is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ArcJail is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ArcJail.  If not, see <http://www.gnu.org/licenses/>.

from random import shuffle

from ...jail_map import get_games, teleport_player

from .. import stage

from .map_game import MapGame


class MapGameTeamBased(MapGame):
    stage_groups = {
        'mapgame-teleport-players2': ["mapgame-teleport-players2", ],
    }

    @stage('mapgame-teleport-players')
    def stage_mapgame_teleport_players(self):
        self.insert_stage_group("mapgame-teleport-players2")

    @stage('mapgame-teleport-players2')
    def stage_mapgame_teleport_players2(self):
        spawnpoints = list(self.map_data.get_spawnpoints('team1'))
        shuffle(spawnpoints)

        teleport_player(self.prisoner, spawnpoints.pop())

        spawnpoints = list(self.map_data.get_spawnpoints('team2'))
        shuffle(spawnpoints)

        teleport_player(self.guard, spawnpoints.pop())

    @classmethod
    def get_available_launchers(cls):
        result = []
        for map_data in get_games(cls.module):
            p_min = map_data['MIN_PLAYERS']
            p_max = map_data['MAX_PLAYERS']

            if p_min > 2:
                continue

            if p_max != -1 and p_max < 2:
                continue

            if not (len(map_data.get_spawnpoints('team1')) >= 1 and
                    len(map_data.get_spawnpoints('team2')) >= 1):

                continue

            result.append(cls.GameLauncher(cls, map_data))

        return result
