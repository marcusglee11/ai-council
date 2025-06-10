# ai_council/council.py
import asyncio
import json
from openai import AsyncOpenAI
# NEW: Import the Status spinner from rich
from rich.status import Status
from . import ui, utils
from .session import SessionState

async def ask_advisor(client: AsyncOpenAI, model_name: str, friendly_name: str, messages: list):
    # This function is correct and remains unchanged.
    try:
        response = await client.chat.completions.with_raw_response.create(model=model_name, messages=messages)
        chat_completion = response.parse()
        return {"advisor": friendly_name, "response": chat_completion.choices[0].message.content, "cost": float(response.headers.get("x-openrouter-cost", 0))}
    except Exception as e:
        return {"advisor": friendly_name, "response": e, "cost": 0, "error": True}

async def run_turn(client: AsyncOpenAI, state: SessionState, prompts: dict, council_prompt: str) -> SessionState:
    histories = state.council_histories
    models = state.selected_models
    rapporteur_model = state.rapporteur_model_id

    # 1. Dispatch to Council with Live Progress
    tasks = []
    for name, model_id in models.items():
        messages_for_model = histories.get(model_id, []) + [{"role": "user", "content": council_prompt}]
        task = asyncio.create_task(ask_advisor(client, model_id, name, messages_for_model))
        task.set_name(name)
        tasks.append(task)
    council_results = await ui.live_council_progress(tasks)

    # 2. Write audit log
    audit_data = {
        "turn": state.turn_counter,
        "prompt_sent_to_council": council_prompt,
        "raw_council_responses": [{k: (str(v) if isinstance(v, Exception) else v) for k, v in res.items()} for res in council_results],
    }
    utils.write_audit_log(state.turn_counter, audit_data)

    # 3. Process successful results
    current_responses = {}
    for result in council_results:
        if not result.get('error'):
            name, model_id, response_text = result['advisor'], models[result['advisor']], result['response']
            if model_id not in histories:
                histories[model_id] = []
            histories[model_id].extend([
                {"role": "user", "content": council_prompt},
                {"role": "assistant", "content": response_text},
            ])
            current_responses[name] = response_text
            state.total_session_cost += result.get('cost', 0)

    # 4. Call the Rapporteur for synthesis
    if not current_responses:
        print("\n[!] No successful responses from the council. Skipping Rapporteur.")
        state.last_rapporteur_report = "> [!ERROR]\n> No successful responses were received from the council for this turn."
    else:
        payload_json = json.dumps({"user_feedback": state.last_user_input, "council_responses": current_responses}, indent=2)
        rapporteur_user_prompt = (
            "Please analyze the following data from the AI Council session and generate your synthesis report...\n"
            "```json\n" f"{payload_json}\n" "```"
        )
        messages = [{"role": "system", "content": prompts['rapporteur_system_prompt']}, {"role": "user", "content": rapporteur_user_prompt}]
        
        # --- NEW: ADDED STATUS SPINNER ---
        with Status("[bold green]Rapporteur is compiling the report...", spinner="earth", console=ui.console):
            rapporteur_result = await ask_advisor(client, rapporteur_model, "Rapporteur", messages)
        # --- END NEW ---

        state.last_rapporteur_report = rapporteur_result.get('response', 'Rapporteur failed to generate a report.')
        state.total_session_cost += rapporteur_result.get('cost', 0)
    
    # 5. Display the final report for the turn
    ui.display_rapporteur_report(state.last_rapporteur_report)

    return state