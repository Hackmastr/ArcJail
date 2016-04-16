from ....arcjail import InternalEvent

from ...games.base_classes.base_game import BaseGame

from ...players import broadcast

from .. import GameLauncher, stage, strings_module


class BaseGame(BaseGame):
    class GameLauncher(GameLauncher):
        def launch(self, players, **kwargs):
            return self.game_class(players, **kwargs)

    def __init__(self, players, **kwargs):
        self._prisoner, self._guard = players
        self._players = list(players)
        self._players_all = list(players)
        self._lock_stage_queue = False
        self._cur_stage_id = None
        self._stage_queue = []
        self._executed_stages = []
        self._settings = kwargs
        self._status = None
        self._results = {}

        for stage_ in self._stages_map.values():
            stage_.game_instance = self

        for game_event_handler_ in self._events.values():
            game_event_handler_.game_instance = self

        for game_internal_event_handler_ in self._internal_events.values():
            game_internal_event_handler_.game_instance = self

    @property
    def guard(self):
        return self._guard

    @property
    def prisoner(self):
        return self._prisoner

    @property
    def status(self):
        return self._status

    @classmethod
    def get_available_launchers(cls):
        return (cls.GameLauncher(cls),)

    @stage('start-notify')
    def stage_start_notify(self):
        InternalEvent.fire('jail_lrs_game_started', instance=self)
        broadcast(strings_module['game_started'].tokenize(
            player1=self.prisoner.name,
            player2=self.guard.name,
            game=self.caption
        ))