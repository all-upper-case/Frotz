import json
import os
import uuid
import shutil

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

    def load_game(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, 'r') as f: return json.load(f)
            except: pass
        return None

    def save_game(self):
        with open(SAVE_FILE, 'w') as f:
            json.dump(self.data, f, indent=2)

    def is_initialized(self):
        return self.data is not None

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
                    "aliases": [a.lower() for a in i.get('aliases', [])], # Store lowercase aliases
                    "description": i.get('description', '...'),
                    "carryable": i.get('is_carryable', True)
                }
                ids.append(iid)
            return ids

        room_item_ids = process_items(genesis_data['starting_room'].get('items', []))
        inv_item_ids = process_items(genesis_data.get('starting_inventory', []))

        rooms_db = {
            start_id: {
                "id": start_id,
                "name": genesis_data['starting_room'].get('name', 'Start'),
                "description": genesis_data['starting_room'].get('description', '...'),
                "exits": {},
                "items": room_item_ids,
                "visited": True
            }
        }

        # Stubs
        for d in genesis_data['starting_room'].get('new_exits', []):
            norm = DIRECTION_MAP.get(d.lower())
            if norm:
                stub_id = f"room_{uuid.uuid4().hex[:8]}"
                rooms_db[stub_id] = {
                    "id": stub_id, "name": "Unknown", "description": None,
                    "exits": {self.get_opposite_dir(norm): start_id},
                    "items": [], "visited": False
                }
                rooms_db[start_id]['exits'][norm] = stub_id

        self.data = {
            "narrative_thread": genesis_data.get('intro_text', '') + " " + genesis_data.get('narrative_thread', ''),
            "player": {"current_room": start_id, "inventory": inv_item_ids},
            "rooms": rooms_db,
            "items": items_db
        }
        self.save_game()
        return genesis_data.get('intro_text', 'Welcome.')

    def hard_reset(self):
        if os.path.exists(SAVE_FILE):
            if not os.path.exists(BACKUP_DIR): os.makedirs(BACKUP_DIR)
            shutil.move(SAVE_FILE, os.path.join(BACKUP_DIR, f"save_{uuid.uuid4().hex[:8]}.json"))
        self.data = None

    def get_current_room(self):
        if not self.data: return None
        return self.data['rooms'].get(self.data['player']['current_room'])

    def get_room(self, rid):
        return self.data['rooms'].get(rid) if self.data else None

    def get_item_by_name(self, query):
        """Robust search: check aliases first, then substring match."""
        query = query.lower().strip()

        # 1. Gather all candidates (Inventory + Room)
        room = self.get_current_room()
        candidates = self.data['player']['inventory'] + room['items']

        for iid in candidates:
            item = self.data['items'].get(iid)
            if not item: continue

            # Check Aliases (Exact Match)
            if query in item.get('aliases', []):
                return item

            # Check Name (Exact Match)
            if query == item['name'].lower():
                return item

        # 2. Fallback: Check Name (Substring Match)
        for iid in candidates:
            item = self.data['items'].get(iid)
            if not item: continue
            if query in item['name'].lower():
                return item

        return None

    def move_player(self, d_input):
        direction = DIRECTION_MAP.get(d_input.lower())
        if not direction: return "error", "Invalid direction.", None

        curr = self.get_current_room()
        target_id = curr['exits'].get(direction)

        if not target_id: return "error", "You can't go that way.", curr['id']

        self.data['player']['current_room'] = target_id
        target = self.get_room(target_id)

        if target['description'] is None:
            return "generate", target_id, curr['id']
        else:
            target['visited'] = True
            self.save_game()
            return "ok", target_id, curr['id']

    def create_room_from_stub(self, stub_id, ai_data):
        room = self.data['rooms'][stub_id]
        room['name'] = ai_data.get('name', 'Unknown')
        room['description'] = ai_data.get('description', '...')

        for i in ai_data.get('items', []):
            iid = i.get('id', f"item_{uuid.uuid4().hex[:6]}")
            self.data['items'][iid] = {
                "id": iid, 
                "name": i.get('name'), 
                "aliases": [a.lower() for a in i.get('aliases', [])],
                "description": i.get('description'), 
                "carryable": i.get('is_carryable', True)
            }
            room['items'].append(iid)

        for d in ai_data.get('new_exits', []):
            norm = DIRECTION_MAP.get(d.lower())
            if norm and norm not in room['exits']:
                new_id = f"room_{uuid.uuid4().hex[:8]}"
                self.data['rooms'][new_id] = {
                    "id": new_id, "name": "Unknown", "description": None,
                    "exits": {self.get_opposite_dir(norm): stub_id},
                    "items": [], "visited": False
                }
                room['exits'][norm] = new_id
        self.save_game()

    def update_item_description(self, iid, desc):
        if iid in self.data['items']:
            self.data['items'][iid]['description'] = desc
            self.save_game()

    def get_opposite_dir(self, d):
        return {"north":"south", "south":"north", "east":"west", "west":"east", "up":"down", "down":"up"}.get(d)