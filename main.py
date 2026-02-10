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
    return jsonify({"response": f"### {room['name']}\n{world.describe_room(room)}", "state": get_ui_state()})


@app.route('/reset', methods=['POST'])
def reset_game():
    world.hard_reset()
    try:
        genesis_data = ai.generate_genesis()
        intro = world.initialize_world(genesis_data)
        room = world.get_current_room()
        full_text = f"{intro}\n\n### {room['name']}\n{world.describe_room(room)}"
        return jsonify({"response": full_text, "state": get_ui_state()})
    except Exception as e:
        return jsonify({"response": f"Genesis Failed: {str(e)}", "state": None})


@app.route('/command', methods=['POST'])
def handle_command():
    if not world.is_initialized():
        return jsonify({"response": "World not initialized. Please Reset."})

    user_input = request.json.get('input', '').strip()
    clean_input = user_input.lower().strip()
    if not user_input:
        return jsonify({"response": ""})

    if clean_input in ['i', 'inv', 'inventory']:
        items = [world.data['items'][i]['name'] for i in world.data['player']['inventory'] if i in world.data['items']]
        worn = [world.data['items'][i]['name'] for i in world.data['player'].get('worn', []) if i in world.data['items']]
        if not items and not worn:
            return jsonify({"response": "You are not carrying anything.", "state": get_ui_state()})

        output = []
        if items:
            output.append("**You are carrying:**\n" + "\n".join([f"- {name}" for name in items]))
        if worn:
            output.append("**You are wearing:**\n" + "\n".join([f"- {name}" for name in worn]))
        return jsonify({"response": "\n\n".join(output), "state": get_ui_state()})

    if clean_input in ['l', 'look']:
        room = world.get_current_room()
        return jsonify({"response": f"### {room['name']}\n{world.describe_room(room)}", "state": get_ui_state()})

    if clean_input.startswith('x ') or clean_input.startswith('examine '):
        parts = clean_input.split(' ', 1)
        if len(parts) > 1:
            target = parts[1].strip()
            if world.is_self_reference(target):
                return jsonify({"response": world.describe_player(), "state": get_ui_state()})

            item = world.get_item_by_name(target)
            if item:
                return jsonify({"response": item['description'], "state": get_ui_state()})

    status, target, prev_id = world.move_player(user_input)

    if status == "ok":
        room = world.get_room(target)
        return jsonify({"response": f"### {room['name']}\n{world.describe_room(room)}", "state": get_ui_state()})

    if status == "generate":
        prev = world.get_room(prev_id)
        thread = world.data.get('narrative_thread', '')
        new_data = ai.generate_room(prev, user_input, thread)
        world.create_room_from_stub(target, new_data)
        room = world.get_room(target)
        return jsonify({"response": f"### {room['name']}\n{world.describe_room(room)}", "state": get_ui_state()})

    if status == "error":
        if "Invalid direction" in target:
            return process_ai_turn(user_input)
        return jsonify({"response": target, "state": get_ui_state()})

    return jsonify({"response": "Error."})


def process_ai_turn(inp):
    room = world.get_current_room()
    inv = [world.data['items'][i] for i in world.data['player']['inventory'] if i in world.data['items']]
    worn = [world.data['items'][i] for i in world.data['player'].get('worn', []) if i in world.data['items']]
    thread = world.data.get('narrative_thread', '')

    outcome = ai.process_turn(inp, room, inv, worn, world.data.get('player', {}), thread)
    world.apply_outcome(outcome)

    return jsonify({"response": outcome.get("narrative", "..."), "state": get_ui_state()})


def get_ui_state():
    if not world.is_initialized():
        return None

    room = world.get_current_room()
    inv = [world.data['items'][i]['name'] for i in world.data['player']['inventory'] if i in world.data['items']]
    return {
        "location": room.get('name', 'Unknown'),
        "inventory": inv,
        "exits": list(room.get('exits', {}).keys())
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)