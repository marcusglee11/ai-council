# council_v4.1.py (Output Bug Fix & Final Polish)

import os, asyncio, json, tomllib, re, datetime, time
from openai import AsyncOpenAI
from rich.live import Live
from rich.table import Table
from rich.spinner import Spinner

# --- Configuration & Setup ---
# ... (This section is unchanged)

# --- Helper Functions ---
# ... (All helper functions are unchanged)

# --- Main Application Logic ---
async def main():
    # ... (Resume logic is unchanged)

    # Initialize a fresh session if no state is loaded
    config = load_config()
    all_models = config.get("models", {})
    print("="*50 + "\nWelcome to the AI Council (Live Progress)\n" + "="*50)
    selected_models = select_models(all_models)
    council_histories = {model_id: [] for model_id in selected_models.values()}
    session_log, total_session_cost, turn_counter, last_rapporteur_report = [], 0.0, 1, ""
    output_filename = "council_session.md"
    rapporteur_model_id = config.get("rapporteur", {}).get("model")

    while True:
        print("\n" + "="*20 + f" Turn {turn_counter} " + "="*20)
        
        # --- Get User Input ---
        if turn_counter == 1 and not session_log:
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

        # --- Live Progress Dispatch Loop ---
        model_statuses = {name: {"status": "Querying...", "time": 0} for name in selected_models.keys()}
        start_time = time.time()
        with Live(generate_status_table(model_statuses), refresh_per_second=10, vertical_overflow="visible") as live:
            task_list = [asyncio.create_task(ask_advisor(model_id, name, council_histories[model_id] + [{"role": "user", "content": prompt_for_council}])) for name, model_id in selected_models.items()]
            for task in asyncio.as_completed(task_list):
                result = await task
                advisor_name = result['advisor']
                elapsed_time = time.time() - start_time
                model_statuses[advisor_name]['status'] = "❌ Error" if result.get("error") else "✅ Done"
                model_statuses[advisor_name]['time'] = elapsed_time
                model_statuses[advisor_name]['result_data'] = result
                live.update(generate_status_table(model_statuses))
        
        print("\n...Council deliberation complete...")
        
        # --- Process results after the live loop ---
        current_turn_responses_text = {}
        for name, data in model_statuses.items():
            result = data.get('result_data')
            if result and not result.get('error'):
                model_id = selected_models[name]
                response_text = result.get('response', '')
                council_histories[model_id].extend([{"role": "user", "content": prompt_for_council}, {"role": "assistant", "content": response_text}])
                current_turn_responses_text[name] = response_text
                total_session_cost += result.get('cost', 0)
        
        if not any(current_turn_responses_text):
            print("\n[!] No successful responses from the council. Skipping Rapporteur.")
            continue

        # --- FIX FOR EMPTY OUTPUT IS HERE ---
        rapporteur_payload_json = json.dumps({"user_feedback": user_input, "council_responses": current_turn_responses_text}, indent=2)
        rapporteur_user_prompt = (
            "Please analyze the following data from the AI Council session and generate your synthesis report according to your instructions. "
            "The data is provided in JSON format below:\n\n"
            "```json\n"
            f"{rapporteur_payload_json}\n"
            "```"
        )
        rapporteur_result = await ask_advisor(rapporteur_model_id, "Rapporteur", [{"role": "system", "content": RAPPORTEUR_SYSTEM_PROMPT}, {"role": "user", "content": rapporteur_user_prompt}])
        # --- END FIX ---

        last_rapporteur_report = rapporteur_result.get("response", "Rapporteur failed to generate a report.")
        total_session_cost += rapporteur_result.get('cost', 0)

        print("\n" + "="*50 + "\n           COUNCIL RAPPORTEUR'S REPORT\n" + "="*50)
        print(last_rapporteur_report) # This should now print the full report

        # ... (rest of the loop for cost calculation, saving state, etc. is unchanged)

    # --- On Graceful Exit ---
    # ... (this section is unchanged)