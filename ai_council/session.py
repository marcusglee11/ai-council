"""Utilities for persisting and finalising AI council sessions."""

import os
import json

SESSION_FILE = "session_state.json"

def load_or_initialize_session() -> dict:
    """Load a saved session or create a new blank state."""
    if os.path.exists(SESSION_FILE):
        resume = input("A previous session was found. Resume it? (y/n): ").lower()
        if resume == 'y':
            print("... Resuming previous session ...")
            try:
                with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                print("Error reading session file. Starting a new session.")
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

def save_session_state(state: dict) -> None:
    """Persist the current ``state`` to ``SESSION_FILE``."""
    with open(SESSION_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

def end_session(state: dict) -> None:
    """Write the markdown report and remove any session file."""
    print("\nSession ended.")
    if state['session_log']:
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        filename = state.get('output_filename', 'council_report.md')
        full_path = os.path.join(output_dir, filename)
        
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
        
        print(f"\n[+] Obsidian-friendly session report exported to {full_path}")

    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
