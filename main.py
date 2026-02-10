import os
from flask import Flask, render_template, request, jsonify
from world_manager import WorldManager
from llm_interface import LLMInterface

app = Flask(__name__)
world = WorldManager()
ai = LLMInterface()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_state', methods=['GET'])
def get_state():
    if not world.is_initialized():
        return jsonify({"response": "INITIALIZING_GENESIS", "state": None})

    room = world.get_current_room()
    return jsonify({"response": f"### {room['name']}\n{room['description']}", "state": get_ui_state()})

@app.route('/reset', methods=['POST'])
def reset_game():
    world.hard_reset()
    try:
        genesis_data = ai.generate_genesis()
        intro = world.initialize_world(genesis_data)
        room = world.get_current_room()
        full_text = f"{intro}\n\n### {room['name']}\n{room['description']}"
        return jsonify({"response": full_text, "state": get_ui_state()})
    except Exception as e:
        return jsonify({"response": f"Genesis Failed: {str(e)}", "state": None})

@app.route('/command', methods=['POST'])
def handle_command():
    if not world.is_initialized():
        return jsonify({"response": "World not initialized. Please Reset."})

    user_input = request.json.get('input', '').strip()
    clean_input = user_input.lower().strip()
    if not user_input: return jsonify({"response": ""})

    # 1. Deterministic Inventory
    if clean_input in ['i', 'inv', 'inventory']:
        items = [world.data['items'][i]['name'] for i in world.data['player']['inventory']]
        if not items:
            return jsonify({"response": "You are not carrying anything.", "state": get_ui_state()})
        list_str = "\n".join([f"- {name}" for name in items])
        return jsonify({"response": f"**You are carrying:**\n{list_str}", "state": get_ui_state()})

    # 2. Deterministic Look
    if clean_input in ['l', 'look']:
        room = world.get_current_room()
        return jsonify({"response": f"### {room['name']}\n{room['description']}", "state": get_ui_state()})

    # 3. Deterministic Examine
    if clean_input.startswith('x ') or clean_input.startswith('examine '):
        # Extract target name (e.g., "x mail" -> "mail")
        parts = clean_input.split(' ', 1)
        if len(parts) > 1:
            target = parts[1]
            item = world.get_item_by_name(target)
            if item:
                return jsonify({"response": item['description'], "state": get_ui_state()})
            # If item is None, we fall through to AI (for scenery like "paperback")

    # 4. Movement
    status, target, prev_id = world.move_player(user_input)

    if status == "ok":
        room = world.get_room(target)
        return jsonify({"response": f"### {room['name']}\n{room['description']}", "state": get_ui_state()})

    elif status == "generate":
        prev = world.get_room(prev_id)
        thread = world.data.get('narrative_thread', '')
        new_data = ai.generate_room(prev, user_input, thread)
        world.create_room_from_stub(target, new_data)
        room = world.get_room(target)
        return jsonify({"response": f"### {room['name']}\n{room['description']}", "state": get_ui_state()})

    elif status == "error":
        if "Invalid direction" in target:
            return process_ai_turn(user_input)
        return jsonify({"response": target, "state": get_ui_state()})

    return jsonify({"response": "Error."})

def process_ai_turn(inp):
    room = world.get_current_room()
    inv = [world.data['items'][i] for i in world.data['player']['inventory'] if i in world.data['items']]
    thread = world.data.get('narrative_thread', '')

    outcome = ai.process_turn(inp, room, inv, thread)

    if "narrative_summary_update" in outcome:
        world.data['narrative_thread'] = outcome['narrative_summary_update']

    if "inventory_add" in outcome:
        for i in outcome["inventory_add"]:
            if i in room['items']:
                room['items'].remove(i)
                world.data['player']['inventory'].append(i)

    if "inventory_remove" in outcome:
        for i in outcome["inventory_remove"]:
            if i in world.data['player']['inventory']:
                world.data['player']['inventory'].remove(i)
                room['items'].append(i)

    if "update_description" in outcome:
        for i, d in outcome["update_description"].items():
            world.update_item_description(i, d)

    world.save_game()
    return jsonify({"response": outcome.get("narrative", "..."), "state": get_ui_state()})

def get_ui_state():
    if not world.is_initialized(): return None
    room = world.get_current_room()
    inv = [world.data['items'][i]['name'] for i in world.data['player']['inventory'] if i in world.data['items']]
    return {
        "location": room.get('name', 'Unknown'),
        "inventory": inv,
        "exits": list(room.get('exits', {}).keys())
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)