# Frotz
Classic Interactive Fiction simulator

## Project structure notes
- `main.py`: Flask web server and gameplay API routes (`/`, `/get_state`, `/reset`, `/command`).
- `templates/index.html`: Main game UI template rendered by Flask.
- `static/style.css`: CRT-style terminal and HUD visual styling.
- `static/script.js`: Front-end logic for input handling, rendering responses, and HUD updates.
- `world_manager.py`: World state, room/item persistence, deterministic movement logic, and save/load helpers.
- `llm_interface.py`: LLM prompts and response handling for world genesis, room generation, and narrative turn processing.
- `savegame.json`: Persisted game state storage.
- `lore.txt`: Setting/world-building seed text used for content generation.
- `debug_log.txt`: Runtime debug output.
- `pyproject.toml` / `poetry.lock`: Python dependency and environment management.

## Feature notes
- Deterministic commands for inventory (`i/inv/inventory`), look (`l/look`), and examine (`x` / `examine`).
- Hybrid gameplay loop: deterministic movement/state transitions plus LLM-authored narrative interactions.
- Dynamic room generation when traveling to unexplored exits.
- Persistent mutable world (item movement/description updates + narrative thread memory).
- Responsive terminal-like web UI with side HUD for location, exits, and inventory.
