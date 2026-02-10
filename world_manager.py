import json
import os
import shutil
import uuid

SAVE_FILE = "savegame.json"
BACKUP_DIR = "backups"

DIRECTION_MAP = {
    "n": "north", "north": "north", "s": "south", "south": "south",
    "e": "east", "east": "east", "w": "west", "west": "west",
    "u": "up", "up": "up", "d": "down", "down": "down"
}


class WorldManager:
    def __init__(self):
        self.data = self.load_game()
        if self.data:
            self.ensure_schema()

    def load_game(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def save_game(self):
        with open(SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2)

    def is_initialized(self):
        return self.data is not None

    def ensure_schema(self):
        if not self.data:
            return

        player = self.data.setdefault('player', {})
        player.setdefault('inventory', [])
        player.setdefault('current_room', 'room_start')
        player.setdefault('description', 'You look like someone trying to survive this strange place.')
        player.setdefault('aliases', ['me', 'myself', 'self', 'player'])
        player.setdefault('worn', [])

        self.data.setdefault('characters', {})
        self.data.setdefault('narrative_thread', '')

        for room in self.data.get('rooms', {}).values():
            room.setdefault('items', [])
            room.setdefault('characters', [])
            room.setdefault('exits', {})
            room.setdefault('name', 'Unknown')
            room.setdefault('description', '...')
            room.setdefault('base_description', room.get('description', '...'))

        for item in self.data.get('items', {}).values():
            item.setdefault('id', f"item_{uuid.uuid4().hex[:6]}")
            item.setdefault('name', 'thing')
            item.setdefault('aliases', [])
            item['aliases'] = [a.lower() for a in item.get('aliases', [])]
            item.setdefault('description', '...')
            item.setdefault('carryable', True)
            item.setdefault('visible', True)

    def initialize_world(self, genesis_data):
        start_id = "room_start"
        items_db = {}

        def process_items(item_list):
            ids = []
            for i in item_list:
                iid = i.get('id', f"item_{uuid.uuid4().hex[:6]}")
                items_db[iid] = {
                    "id": iid,
                    "name": i.get('name', 'thing'),
                    "aliases": [a.lower() for a in i.get('aliases', [])],
                    "description": i.get('description', '...'),
                    "carryable": i.get('is_carryable', True),
                    "visible": i.get('visible', True)
                }
                ids.append(iid)
            return ids

        room_item_ids = process_items(genesis_data['starting_room'].get('items', []))
        inv_item_ids = process_items(genesis_data.get('starting_inventory', []))

        start_description = genesis_data['starting_room'].get('description', '...')
        rooms_db = {
            start_id: {
                "id": start_id,
                "name": genesis_data['starting_room'].get('name', 'Start'),
                "description": start_description,
                "base_description": start_description,
                "exits": {},
                "items": room_item_ids,
                "characters": [],
                "visited": True
            }
        }

        for d in genesis_data['starting_room'].get('new_exits', []):
            norm = DIRECTION_MAP.get(d.lower())
            if norm:
                stub_id = f"room_{uuid.uuid4().hex[:8]}"
                rooms_db[stub_id] = {
                    "id": stub_id,
                    "name": "Unknown",
                    "description": None,
                    "base_description": None,
                    "exits": {self.get_opposite_dir(norm): start_id},
                    "items": [],
                    "characters": [],
                    "visited": False
                }
                rooms_db[start_id]['exits'][norm] = stub_id

        self.data = {
            "narrative_thread": genesis_data.get('intro_text', '') + " " + genesis_data.get('narrative_thread', ''),
            "player": {
                "current_room": start_id,
                "inventory": inv_item_ids,
                "description": genesis_data.get('player_description', 'You look wary, alert, and very much alive.'),
                "aliases": ['me', 'myself', 'self', 'player'],
                "worn": []
            },
            "characters": {},
            "rooms": rooms_db,
            "items": items_db
        }
        self.ensure_schema()
        self.save_game()
        return genesis_data.get('intro_text', 'Welcome.')

    def hard_reset(self):
        if os.path.exists(SAVE_FILE):
            if not os.path.exists(BACKUP_DIR):
                os.makedirs(BACKUP_DIR)
            shutil.move(SAVE_FILE, os.path.join(BACKUP_DIR, f"save_{uuid.uuid4().hex[:8]}.json"))
        self.data = None

    def get_current_room(self):
        if not self.data:
            return None
        return self.data['rooms'].get(self.data['player']['current_room'])

    def get_room(self, rid):
        return self.data['rooms'].get(rid) if self.data else None

    def get_visible_room_items(self, room=None):
        room = room or self.get_current_room()
        if not room:
            return []
        out = []
        for iid in room.get('items', []):
            item = self.data['items'].get(iid)
            if item and item.get('visible', True):
                out.append(item)
        return out

    def describe_room(self, room=None):
        room = room or self.get_current_room()
        if not room:
            return "Unknown"

        base = room.get('base_description') or room.get('description') or '...'
        visible_items = self.get_visible_room_items(room)
        item_line = ''
        if visible_items:
            item_names = ", ".join(i['name'] for i in visible_items)
            item_line = f"\n\nYou can see here: {item_names}."

        chars = []
        for cid in room.get('characters', []):
            char = self.data.get('characters', {}).get(cid)
            if char and char.get('visible', True):
                chars.append(char.get('name', 'someone'))
        char_line = f"\nOthers present: {', '.join(chars)}." if chars else ''

        composed = f"{base}{item_line}{char_line}".strip()
        room['description'] = composed
        return composed

    def describe_player(self):
        player = self.data.get('player', {})
        base = player.get('description', 'You look ordinary.')
        worn_items = []
        for iid in player.get('worn', []):
            item = self.data['items'].get(iid)
            if item:
                worn_items.append(item['name'])

        worn_text = ''
        if worn_items:
            worn_text = f"\n\nYou are wearing: {', '.join(worn_items)}."

        inv_items = [self.data['items'][iid]['name'] for iid in player.get('inventory', []) if iid in self.data['items']]
        inv_text = ''
        if inv_items:
            inv_text = f"\nYou are carrying: {', '.join(inv_items)}."

        return f"{base}{worn_text}{inv_text}".strip()

    def get_item_by_name(self, query):
        query = query.lower().strip()
        room = self.get_current_room()
        candidates = self.data['player']['inventory'] + self.data['player'].get('worn', []) + room['items']

        for iid in candidates:
            item = self.data['items'].get(iid)
            if not item:
                continue
            if (not item.get('visible', True)) and (iid not in self.data['player']['inventory']) and (iid not in self.data['player'].get('worn', [])):
                continue
            if query in item.get('aliases', []):
                return item
            if query == item['name'].lower():
                return item

        for iid in candidates:
            item = self.data['items'].get(iid)
            if not item:
                continue
            if query in item['name'].lower():
                return item

        return None

    def is_self_reference(self, query):
        query = query.lower().strip()
        return query in {'me', 'myself', 'self', 'player', 'my character'}

    def move_player(self, d_input):
        direction = DIRECTION_MAP.get(d_input.lower())
        if not direction:
            return "error", "Invalid direction.", None

        curr = self.get_current_room()
        target_id = curr['exits'].get(direction)

        if not target_id:
            return "error", "You can't go that way.", curr['id']

        self.data['player']['current_room'] = target_id
        target = self.get_room(target_id)

        if target['description'] is None:
            return "generate", target_id, curr['id']

        target['visited'] = True
        self.describe_room(target)
        self.save_game()
        return "ok", target_id, curr['id']

    def create_room_from_stub(self, stub_id, ai_data):
        room = self.data['rooms'][stub_id]
        base_desc = ai_data.get('description', '...')
        room['name'] = ai_data.get('name', 'Unknown')
        room['base_description'] = base_desc
        room['description'] = base_desc

        for i in ai_data.get('items', []):
            iid = i.get('id', f"item_{uuid.uuid4().hex[:6]}")
            self.data['items'][iid] = {
                "id": iid,
                "name": i.get('name', 'thing'),
                "aliases": [a.lower() for a in i.get('aliases', [])],
                "description": i.get('description', '...'),
                "carryable": i.get('is_carryable', True),
                "visible": i.get('visible', True)
            }
            room['items'].append(iid)

        for d in ai_data.get('new_exits', []):
            norm = DIRECTION_MAP.get(d.lower())
            if norm and norm not in room['exits']:
                new_id = f"room_{uuid.uuid4().hex[:8]}"
                self.data['rooms'][new_id] = {
                    "id": new_id,
                    "name": "Unknown",
                    "description": None,
                    "base_description": None,
                    "exits": {self.get_opposite_dir(norm): stub_id},
                    "items": [],
                    "characters": [],
                    "visited": False
                }
                room['exits'][norm] = new_id
        self.describe_room(room)
        self.save_game()

    def update_item_description(self, iid, desc):
        if iid in self.data['items']:
            self.data['items'][iid]['description'] = desc

    def apply_outcome(self, outcome):
        room = self.get_current_room()
        player = self.data['player']

        if 'narrative_summary_update' in outcome:
            self.data['narrative_thread'] = outcome['narrative_summary_update']

        for iid in outcome.get('inventory_add', []):
            if iid in room['items']:
                room['items'].remove(iid)
            if iid not in player['inventory']:
                player['inventory'].append(iid)

        for iid in outcome.get('inventory_remove', []):
            if iid in player['inventory']:
                player['inventory'].remove(iid)
            if iid not in room['items']:
                room['items'].append(iid)

        for iid in outcome.get('room_add', []):
            if iid not in room['items']:
                room['items'].append(iid)

        for iid in outcome.get('room_remove', []):
            if iid in room['items']:
                room['items'].remove(iid)

        for iid in outcome.get('wear_add', []):
            if iid in player['inventory']:
                player['inventory'].remove(iid)
            if iid not in player['worn']:
                player['worn'].append(iid)

        for iid in outcome.get('wear_remove', []):
            if iid in player['worn']:
                player['worn'].remove(iid)
            if iid not in player['inventory']:
                player['inventory'].append(iid)

        for iid, desc in outcome.get('update_description', {}).items():
            self.update_item_description(iid, desc)

        for rid, base_desc in outcome.get('room_base_description_update', {}).items():
            target_room = self.get_room(rid)
            if target_room:
                target_room['base_description'] = base_desc

        if 'current_room_base_description' in outcome and room:
            room['base_description'] = outcome['current_room_base_description']

        if 'player_description_update' in outcome:
            player['description'] = outcome['player_description_update']

        for iid, vis in outcome.get('item_visibility_update', {}).items():
            if iid in self.data['items']:
                self.data['items'][iid]['visible'] = bool(vis)

        self.describe_room(room)
        self.save_game()

    def get_opposite_dir(self, d):
        return {
            "north": "south", "south": "north", "east": "west",
            "west": "east", "up": "down", "down": "up"
        }.get(d)
