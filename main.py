# main.py
import os
import asyncio
import datetime
import re  # NEW: Import regular expressions
from openai import AsyncOpenAI
from ai_council import council, session, utils, ui

def extract_suggested_question(report: str) -> str | None:
    """Uses regex to find the question within the 'QUESTION' callout block."""
    # This pattern looks for the text between the callout title and the end of the line
    match = re.search(r'>\s*\[!QUESTION\]\s*.*\n>\s*(.*)', report, re.MULTILINE)
    if match:
        # Clean up the extracted question
        question = match.group(1).strip()
        # Remove markdown bolding if present
        question = question.replace('**', '')
        return question
    return None

async def main():
    if not (api_key := os.getenv("OPENROUTER_API_KEY")):
        raise ValueError("FATAL: OPENROUTER_API_KEY environment variable not set.")
    
    client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    prompts_config = utils.load_config("config/prompts.toml")
    models_config = utils.load_config("config/models.toml")
    templates_config = utils.load_config("config/templates.toml")
    
    state = session.load_or_initialize_session()

    if state.turn_counter == 1 and not state.selected_models:
        ui.display_welcome()
        state.selected_models = ui.select_models(models_config.get("models", {}))
        state.rapporteur_model_id = models_config.get("rapporteur", {}).get("model")

    while state.running:
        
        # --- Get User Input ---
        if state.turn_counter == 1:
            council_prompt = ui.get_initial_prompt(templates_config)
            state.last_user_input = council_prompt.split("--- END DOCUMENT CONTEXT ---")[-1].strip()

            slug = await utils.generate_filename_slug(state.last_user_input, client, state.selected_models, prompts_config['filename_slug_prompt'])
            date_str = datetime.datetime.now().strftime('%Y%m%d')
            state.output_filename = f"{date_str}_{slug}.md"
            print(f"-> Session will be saved to: output/{state.output_filename}")
        else:
            user_input = ui.get_follow_up_input(state.turn_counter)
            
            # --- NEW: "go" command logic ---
            if user_input.lower() == 'go':
                suggested_question = extract_suggested_question(state.last_rapporteur_report)
                if suggested_question:
                    ui.console.print(f"\n[bold green]Using suggested question:[/bold green] '{suggested_question}'")
                    user_input = suggested_question
                else:
                    ui.console.print("[bold red]Could not find a suggested question. Please enter your feedback manually.[/bold red]")
                    user_input = ui.get_follow_up_input(state.turn_counter)  # Re-prompt
            # --- END NEW ---

            if user_input.lower() in ['quit', 'exit']:
                state.running = False
                break

            state.last_user_input = user_input
            doc_context = ui.get_document_context()
            council_prompt = doc_context + f"Previous summary:\n{state.last_rapporteur_report}\n\nMy new feedback: \"{user_input}\"\nRefine your answer."

        # C. Run the turn
        state = await council.run_turn(client, state, prompts_config, council_prompt)

        # D. Update and save state
        turn_cost = state.total_session_cost - sum(t.get('total_cost', 0) for t in state.session_log)
        ui.display_turn_telemetry(turn_cost, state.total_session_cost, state.turn_counter)
        state.session_log.append({"turn": state.turn_counter, "user_prompt": state.last_user_input, "rapporteur_report": state.last_rapporteur_report, "total_cost": state.total_session_cost})
        state.turn_counter += 1
        session.save_session_state(state)

    # 4. Clean up
    session.end_session(state)

if __name__ == "__main__":
    asyncio.run(main())