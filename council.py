# council_v3.py (Resumable & File-Based)
# ---
# Features:
# - Durable sessions saved to `session_state.json` after each turn.
# - Ability to resume interrupted sessions on startup.
# - All previous features: Conversational loop, AI filenames, Obsidian formatting.

import os
import asyncio
import json
import tomllib
import re
import datetime
from openai import AsyncOpenAI

# --- Configuration & Setup ---
if not (api_key := os.getenv("OPENROUTER_API_KEY")):
    raise ValueError("FATAL: OPENROUTER_API_KEY environment variable not set.")

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

RAPPORTEUR_SYSTEM_PROMPT = """
You are the Council Rapporteur, an expert AI analyst...
[The long, Obsidian-friendly system prompt remains the same as before]
"""

# --- Helper Functions (Unchanged from v2) ---
# The following functions are copied directly from the previous version.
async def generate_filename_slug(prompt: str, client: AsyncOpenAI, council_models: dict) -> str:
    print("... Generating filename slug from prompt ...")
    system_prompt = "You are a filename generator. Summarize the user's prompt into a 3-5 word, lowercase, snake_case string suitable for a filename. Example: for 'What are the top 10 rules for a happy life?', respond with 'rules_for_happy_life'."
    if not council_models: return "untitled_session"
    model_for_slug = list(council_models.values())[0]
    try:
        response = await client.chat.completions.create(
            model=model_for_slug, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=20,
        )
        slug = response.choices[0].message.content.strip().lower()
        slug = re.sub(r'\s+', '_', slug)
        slug = re.sub(r'[^a-z0-9_]', '', slug)
        return slug.strip('_')[:50] or "untitled_session"
    except Exception as e:
        print(f"!! WARN: Could not generate AI slug: {e}. Falling back to default.")
        return "untitled_session"

async def ask_advisor(model_name: str, friendly_name: str, messages: list):
    print(f"… Querying {friendly_name} ({model_name})")
    try:
        response = await client.chat.completions.with_raw_response.create(model=model_name, messages=messages)
        chat_completion = response.parse()
        return {"advisor": friendly_name, "response": chat_completion.choices[0].message.content, "cost": float(response.headers.get("x-openrouter-cost", 0))}
    except Exception as e:
        print(f"!! ERROR querying {friendly_name}: {e}")
        return {"advisor": friendly_name, "response": f"Error: {e}", "cost": 0}

def load_config():
    try:
        with open("config.toml", "rb") as f: return tomllib.load(f)
    except FileNotFoundError: raise FileNotFoundError("FATAL: config.toml not found. Please create it.")

def select_models(available_models):
    print("\n--- Select Your Advisors ---")
    model_items = list(available_models.items())
    for i, (name, _) in enumerate(model_items, 1):
        print(f"  [{i}] {name}")
    while True:
        selection = input("Select models by number (e.g., 1,3,4), or press Enter for all: ")
        if not selection: return available_models
        try:
            selected_indices = [int(x.strip()) - 1 for x in selection.split(",")]
            if all(0 <= i < len(model_items) for i in selected_indices):
                return {model_items[i][0]: model_items[i][1] for i in selected_indices}
            else: print("Invalid number detected.")
        except ValueError: print("Invalid input.")

def export_to_markdown(session_history, filename="council_session.md"):
    # This function remains the same
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# 🏛️ AI Council Session Report\n\n[...]\n") # Abbreviated for brevity
    print(f"\n[+] Obsidian-friendly session report exported to {filename}")

# --- Main Application Logic (Reworked for Resumability) ---
async def main():
    session_file = "session_state.json"
    
    # --- 1. Startup: Check for a session to resume ---
    if os.path.exists(session_file):
        resume = input("A previous session was found. Resume it? (y/n): ").lower()
        if resume == 'y':
            print("... Resuming previous session ...")
            with open(session_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            council_histories = state['council_histories']
            session_log = state['session_log']
            total_session_cost = state['total_session_cost']
            turn_counter = state['turn_counter']
            last_rapporteur_report = state['last_rapporteur_report']
            output_filename = state['output_filename']
            selected_models = state['selected_models']
        else:
            os.remove(session_file)
            state = None
    else:
        state = None

    if state is None:
        # Initialize a fresh session
        config = load_config()
        all_models = config.get("models", {})
        print("="*50 + "\nWelcome to the AI Council (Conversational Session)\n" + "="*50)
        selected_models = select_models(all_models)
        council_histories = {model_id: [] for model_id in selected_models.values()}
        session_log, total_session_cost, turn_counter, last_rapporteur_report = [], 0.0, 1, ""
        output_filename = "council_session.md"

    rapporteur_model_id = load_config().get("rapporteur", {}).get("model")

    while True:
        print("\n" + "="*20 + f" Turn {turn_counter} " + "="*20)
        
        if turn_counter == 1 and not session_log: # Only run on the very first turn of a new session
            user_input = input("Enter your initial prompt for the council:\n> ")
            slug = await generate_filename_slug(user_input, client, selected_models)
            date_str = datetime.datetime.now().strftime('%Y%m%d')
            output_filename = f"{date_str}_{slug}.md"
            print(f"-> Session will be saved as: {output_filename}")
            prompt_for_council = user_input
        else:
            user_input = input("Enter your follow-up feedback (or type 'quit' to exit):\n> ")
            if user_input.lower() in ['quit', 'exit']: break
            prompt_for_council = (f"Previous summary:\n{last_rapporteur_report}\n\nMy new feedback: \"{user_input}\"\nRefine your answer.")

        # --- The core dispatch/synthesis loop ---
        tasks = [ask_advisor(model_id, name, council_histories[model_id] + [{"role": "user", "content": prompt_for_council}]) for name, model_id in selected_models.items()]
        council_results = await asyncio.gather(*tasks)
        
        current_turn_responses = {}
        for result in council_results:
            model_id = selected_models.get(result['advisor'])
            if model_id:
                # Add both user and assistant messages to the history for next turn
                council_histories[model_id].append({"role": "user", "content": prompt_for_council})
                council_histories[model_id].append({"role": "assistant", "content": result['response']})
                current_turn_responses[result['advisor']] = result['response']
                total_session_cost += result.get('cost', 0)
        
        rapporteur_payload = json.dumps({"user_feedback": user_input, "council_responses": current_turn_responses}, indent=2)
        rapporteur_result = await ask_advisor(rapporteur_model_id, "Rapporteur", [{"role": "system", "content": RAPPORTEUR_SYSTEM_PROMPT}, {"role": "user", "content": rapporteur_payload}])
        last_rapporteur_report = rapporteur_result.get("response", "Rapporteur failed.")
        total_session_cost += rapporteur_result.get('cost', 0)

        print("\n" + "="*50 + "\n           COUNCIL RAPPORTEUR'S REPORT\n" + "="*50)
        print(last_rapporteur_report)

        current_turn_cost = total_session_cost - sum(t.get('total_cost', 0) for t in session_log)
        print(f"\n--- Turn {turn_counter} Cost: ${current_turn_cost:.6f} | Total Session Cost: ${total_session_cost:.6f} ---")

        session_log.append({"turn": turn_counter, "user_prompt": user_input, "rapporteur_report": last_rapporteur_report, "total_cost": total_session_cost})
        turn_counter += 1

        # --- 2. After each successful turn, save the complete state ---
        state_to_save = {
            'council_histories': council_histories, 'session_log': session_log, 'total_session_cost': total_session_cost,
            'turn_counter': turn_counter, 'last_rapporteur_report': last_rapporteur_report,
            'output_filename': output_filename, 'selected_models': selected_models,
        }
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(state_to_save, f, indent=2)

    # --- 3. On Graceful Exit ---
    print("\nSession ended.")
    if session_log:
        export_to_markdown(session_log, filename=output_filename)
        if os.path.exists(session_file):
            os.remove(session_file) # Clean up the state file

if __name__ == "__main__":
    asyncio.run(main())