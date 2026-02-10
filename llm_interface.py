import os
import json
import requests
import datetime

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
API_URL = "https://api.mistral.ai/v1/chat/completions"
DEBUG_LOG_FILE = "debug_log.txt"
LORE_FILE = "lore.txt"

# --- THE GENESIS: CREATING THE WORLD START ---
PROMPT_GENESIS = """
You are the 'Great Creator' for a high-fidelity Interactive Fiction (IF) engine. 
Your task is to translate a high-level LORE BIBLE into a concrete starting state for a text adventure.

INSTRUCTIONS:
1. STYLE: Emulate the highest quality 80s/90s text adventures (Infocom/Legend). Use evocative, second-person ("You") narration.
2. CONSISTENCY: Ensure the starting room and items are 100% faithful to the genre and tone in the Lore Bible.
3. ALIASES: Every item must have 'aliases' (synonyms) to help the parser understand the player.

LORE BIBLE:
{lore_bible}

OUTPUT VALID JSON ONLY:
{{
  "intro_text": "The opening narrative crawl.",
  "narrative_thread": "A hidden internal summary of the plot state to start with.",
  "starting_room": {{
    "name": "Starting Location Name",
    "description": "Full sensory description of the starting room.",
    "items": [
        {{
          "id": "item_unique_id", 
          "name": "display name", 
          "aliases": ["synonym1", "synonym2", "noun"],
          "description": "The text seen when the player 'examines' this item.", 
          "is_carryable": true
        }}
    ],
    "new_exits": ["north", "east"] 
  }},
  "starting_inventory": [
      {{
        "id": "item_unique_id", 
        "name": "display name", 
        "aliases": ["synonym1", "synonym2"],
        "description": "Detailed examine text.", 
        "is_carryable": true
      }}
  ]
}}
"""

# --- THE ARCHITECT: PROCEDURAL EXPANSION ---
PROMPT_ARCHITECT = """
You are the 'Lead Architect' for an Interactive Fiction engine. 
Your purpose is to procedurally expand the world as the player moves into unexplored territory.

GENERAL RULES:
1. STYLE: Second-person ("You"). Moody, atmospheric, and classic.
2. COHESION: Use the 'Lore Bible' and 'Narrative Thread' to ensure this room fits the overarching story.
3. SENSORY LOGIC: Focus on visuals, sounds, and smells. Objects should feel heavy, old, or significant.
4. ALIASES: Generate 2-4 synonyms for every item (e.g. for 'rusty key', add ['key', 'rusty', 'iron key']).

CONTEXT:
- Lore Bible: {lore_bible}
- Current Narrative Thread: {narrative_thread}
- Previous Location: {prev_name} ({prev_desc})
- Movement Direction: {direction}

OUTPUT VALID JSON ONLY:
{{
  "name": "New Room Title",
  "description": "Sensory-rich description of this new area.",
  "new_exits": ["south", "west"], 
  "items": [
    {{
      "id": "unique_item_id",
      "name": "short name",
      "aliases": ["synonym1", "synonym2", "noun"],
      "description": "Full examine text.",
      "is_carryable": true
    }}
  ]
}}
"""

# --- THE DM: ACTION & NARRATION ---
PROMPT_DM = """
You are the 'Dungeon Master' (DM) for a classic Interactive Fiction game.
You interpret user inputs and narrate the results based on the world state and lore.

YOUR CONTEXT:
- Lore Bible: {lore_bible}
- Narrative Thread: {narrative_thread}
- Current Room State: {room_json}
- Player Inventory: {inventory}

YOUR INSTRUCTIONS:
1. PARSING: Interpret intent (n, s, e, w, x, i, l, or complex actions like 'search the desk').
2. NARRATION:
   - Use second-person ("You"). 
   - If an action is impossible, explain why in-character.
   - If an action is successful, describe the sensory result.
3. STATE UPDATES:
   - If the player takes an item: Put its ID in 'inventory_add' and 'room_remove'.
   - If they drop it: Put it in 'inventory_remove' and 'room_add'.
   - If an item's state changes (e.g., 'sharpen sword'): Update its 'update_description'.
4. NARRATIVE THREAD:
   - Use 'narrative_summary_update' to summarize major developments for the Architect's future use.

OUTPUT VALID JSON ONLY:
{{
  "narrative": "The text the player sees.",
  "inventory_add": [],
  "inventory_remove": [],
  "room_add": [],
  "room_remove": [],
  "update_description": {{ "item_id": "New description string" }},
  "narrative_summary_update": "Brief update on plot/world state."
}}
"""

class LLMInterface:
    def __init__(self):
        self.model = "mistral-large-latest"

    def get_lore(self):
        if os.path.exists(LORE_FILE):
            with open(LORE_FILE, 'r', encoding='utf-8') as f: return f.read()
        return "A mysterious text adventure."

    def _req(self, system, user, role):
        if not MISTRAL_API_KEY:
            return {"error": "API Key Missing", "narrative": "Set your MISTRAL_API_KEY in Replit Secrets."}

        headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [{"role":"system", "content":system}, {"role":"user", "content":user}],
            "response_format": {"type": "json_object"},
            "temperature": 0.7
        }

        try:
            resp = requests.post(API_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = json.loads(resp.json()['choices'][0]['message']['content'])

            # Log the full exchange
            with open(DEBUG_LOG_FILE, "a", encoding='utf-8') as f:
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"--- {ts} [{role}] ---\n[SYSTEM]: {system}\n[USER]: {user}\n[OUTPUT]: {json.dumps(data, indent=2)}\n\n")

            return data
        except Exception as e:
            return {"narrative": f"The logic of the world ripples... (Error: {e})", "error": True}

    def generate_genesis(self):
        lore = self.get_lore()
        return self._req(PROMPT_GENESIS.format(lore_bible=lore), "Initiate World Genesis.", "GENESIS")

    def generate_room(self, prev_room, direction, thread):
        lore = self.get_lore()
        p_name = prev_room['name'] if prev_room else "The Void"
        p_desc = prev_room['description'] if prev_room else "Nothingness."
        sys = PROMPT_ARCHITECT.format(lore_bible=lore, narrative_thread=thread, prev_name=p_name, prev_desc=p_desc, direction=direction)
        return self._req(sys, "The player has moved. Describe the new area.", "ARCHITECT")

    def process_turn(self, user_input, room_data, inventory, thread):
        lore = self.get_lore()
        sys = PROMPT_DM.format(lore_bible=lore, narrative_thread=thread, room_json=json.dumps(room_data), inventory=json.dumps(inventory))
        return self._req(sys, f"PLAYER ACTION: {user_input}", "DM")