# Mistral Z-Machine - Interactive Fiction Engine

## Overview
A web-based text adventure game engine powered by Mistral AI. Players interact through a retro-style terminal interface. The game world is procedurally generated using AI, with rooms, items, and narratives created dynamically based on a lore bible.

## Project Architecture
- **Language**: Python 3.11
- **Framework**: Flask (web server)
- **Package Manager**: Poetry
- **AI Backend**: Mistral AI API (mistral-large-latest model)
- **Frontend**: Static HTML/CSS/JS with retro CRT terminal styling

## Project Structure
- `main.py` - Flask app with routes (/, /get_state, /reset, /command)
- `llm_interface.py` - Mistral AI API integration (Genesis, Architect, DM prompts)
- `world_manager.py` - Game state management (rooms, items, inventory, movement)
- `templates/index.html` - Main game UI template
- `static/style.css` - Retro terminal styling
- `static/script.js` - Frontend game logic
- `lore.txt` - World lore bible for AI context
- `savegame.json` - Persistent game state (auto-generated)
- `debug_log.txt` - AI interaction logs

## Configuration
- Frontend runs on port 5000 (0.0.0.0)
- Requires `MISTRAL_API_KEY` secret for AI functionality
- Uses Poetry for dependency management

## Recent Changes
- 2026-02-10: Initial import and Replit setup, changed port from 8080 to 5000
