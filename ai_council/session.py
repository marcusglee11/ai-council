# ai_council/session.py
import os
import json
from .utils import logger

SESSION_FILE = "session_state.json"

def load_or_initialize_session() -> dict:
    """
    Checks for a session file. If found and user confirms, loads the state.
    Otherwise, returns a blank state template for a new session.
    """
    if os.path.exists(SESSION_FILE):
        resume = input("A previous session was found. Resume it? (y/n): ").lower()
        if resume == 'y':
            logger.info("Resuming previous session")
            try:
                with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                logger.error("Error reading session file. Starting a new session", exc_info=True)
                os.remove(SESSION_FILE)
        else:
            # User chose not to resume, so clean up and start fresh.
            os.remove(SESSION_FILE)
    
    # Return a blank template for a new session.
    # main.py will be responsible for filling this out.
    return {
        "running": True,
        "selected_models": {},
        "rapporteur_model_id": None,
        "council_histories": {},
        "session_log": [],
        "total_session_cost": 0.0,
        "turn_counter": 1,
        "last_rapporteur_report": "",
        "output_filename": "council_session.md",
        "last_user_input": ""
    }

def save_session_state(state: dict):
    """Saves the entire current session state to the JSON file."""
    with open(SESSION_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

def end_session(state: dict):
    """Writes the final Markdown report and cleans up the session file."""
    logger.info("Session ended")
    if state['session_log']:
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        filename = state.get('output_filename', 'council_report.md')
        full_path = os.path.join(output_dir, filename)
        
        # --- FIX IS HERE ---
        # The following lines are now correctly indented inside the 'with' block.
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write("# 🏛️ AI Council Session Report\n\n")
            f.write("This document contains the complete transcript of the AI Council session.\n\n")
            for turn in state['session_log']:
                f.write(f"***\n\n## 🔄 Turn {turn['turn']}\n\n")
                # Ensure user_prompt exists before replacing
                user_prompt = turn.get('user_prompt', '').replace('\n', '\n> ')
                f.write(f"> [!QUESTION] User Input for Turn {turn['turn']}\n> {user_prompt}\n\n")
                f.write("### 🧠 Rapporteur's Synthesis\n\n")
                f.write(f"{turn.get('rapporteur_report', 'No report generated.')}\n\n")
        # --- END FIX ---
        
        logger.info("Obsidian-friendly session report exported to %s", full_path)

    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
