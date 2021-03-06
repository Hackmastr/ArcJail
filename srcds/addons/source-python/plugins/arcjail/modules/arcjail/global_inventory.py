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

from listeners.tick import GameThread

from ...resource.logger import logger

from .item import Item


class GlobalInventory(dict):
    def __init__(self):
        super().__init__()

        self._temp_items = []

    def __missing__(self, key):
        item = Item(key)

        GameThread(target=item.load_from_database).start()

        self[key] = item

        return item

    def create(self, class_id, instance_id, player=None, amount=1, async=True):
        from .arcjail_user import ArcjailUser

        logger.log_debug(
            "GlobalInventory.create: creating item of (class_id={}, "
            "instance_id={}) (amount={}) (async={})".format(
                class_id, instance_id, amount, async))

        item = Item(None)
        item.class_id = class_id
        item.instance_id = instance_id
        item.player = player
        item.amount = amount
        item._loaded = True

        if async:
            def save_to_database():
                logger.log_debug(
                    "GlobalInventory.create: Saving created item {} "
                    "to database (async=True)".format(item))

                item.save_to_database()

                try:
                    item.get_player()
                except ValueError:
                    logger.log_debug(
                        "GlobalInventory.create: Player (SteamID={}) has "
                        "already disconnected', saving temp item {}".format(
                            item._current_owner, item))

                    ArcjailUser.save_temp_item(item._current_owner, item)

                self._temp_items.remove(item)
                self[item.id] = item

            self._temp_items.append(item)

            GameThread(target=save_to_database).start()

        else:
            logger.log_debug("GlobalInventory.create: Saving created item {} "
                             "to database (async=False)".format(item))

            item.save_to_database()
            self[item.id] = item

        return item

    def delete(self, item, async=True):
        logger.log_debug("GlobalInventory.delete: deleting {} "
                         "(async={})".format(item, async))

        del self[item.id]

        if async:
            GameThread(target=item.delete_from_database).start()
        else:
            item.delete_from_database()

    @staticmethod
    def save(item, async=True):
        logger.log_debug("GlobalInventory.save: saving {} "
                         "(async={})".format(item, async))

        if async:
            GameThread(target=item.save_to_database).start()
        else:
            item.save_to_database()

global_inventory = GlobalInventory()
