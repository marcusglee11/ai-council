# council_v2.py (Conversational Version)
import os
import asyncio
import json
import tomllib
import re  # NEW: Import regular expressions for sanitization
import datetime  # NEW: Import datetime for timestamping
from openai import AsyncOpenAI

# --- Configuration & Setup (Unchanged) ---

if not (api_key := os.getenv("OPENROUTER_API_KEY")):
    raise ValueError("FATAL: OPENROUTER_API_KEY environment variable not set.")

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)


RAPPORTEUR_SYSTEM_PROMPT = """
You are the Council Rapporteur, an expert AI analyst. Your task is to synthesize advice from a council of AI models.
Your output MUST be a clean, readable, **Obsidian-friendly** Markdown report.

Structure your report with the following FOUR sections, using Obsidian callouts for clarity:

---

### 1. Executive Synthesis
Use a `> [!SUMMARY]` callout for the 200-word narrative that blends the strongest ideas from THIS TURN into a single, actionable strategy.

### 2. Individual Advisor Summaries
For EACH advisor, use a `> [!NOTE]` callout to provide a concise, 2-3 sentence summary of their response for the current turn.

### 3. Comparison Table
Use a standard Markdown table under a `### Comparison Table` heading. Do not place this inside a callout.
| Advisor (Model) | Key Proposal / Core Idea | Potential Risks or Blind Spots |
|---|---|---|
| ... | ... | ... |

### 4. Divergent Viewpoints
Use a `> [!WARNING]` callout to explicitly highlight 1-2 interesting, conflicting, or unique perspectives from THIS TURN's responses.
"""

# --- NEW HELPER FUNCTION: AI-Powered Slug Generation ---

# In council_v2_final.py or your current script

async def generate_filename_slug(prompt: str, client: AsyncOpenAI, council_models: dict) -> str:
    """Uses a fast AI model from the selected council to create a filename slug."""
    print("... Generating filename slug from prompt ...")
    system_prompt = "You are a filename generator. Summarize the user's prompt into a 3-5 word, lowercase, snake_case string suitable for a filename. Example: for 'What are the top 10 rules for a happy life?', respond with 'rules_for_happy_life'."
    
    # Use the first available council model for this quick task. This is more robust.
    if not council_models:
        return "untitled_session"
    model_for_slug = list(council_models.values())[0]

    try:
        response = await client.chat.completions.create(
            model=model_for_slug,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1, max_tokens=20,
        )
        slug = response.choices[0].message.content.strip()
        slug = slug.lower()
        slug = re.sub(r'\s+', '_', slug)
        slug = re.sub(r'[^a-z0-9_]', '', slug)
        slug = slug.strip('_')
        return slug[:50] if slug else "untitled_session"
    except Exception as e:
        print(f"!! WARN: Could not generate AI slug: {e}. Falling back to default.")
        return "untitled_session"


# --- Core Functions (ask_advisor is now more general) ---

async def ask_advisor(model_name: str, friendly_name: str, messages: list):
    """
    Asks a single advisor a question based on a full message history.
    """
    print(f"… Querying {friendly_name} ({model_name})")
    try:
        response = await client.chat.completions.with_raw_response.create(
            model=model_name,
            messages=messages
        )
        chat_completion = response.parse()
        return {
            "advisor": friendly_name,
            "response": chat_completion.choices[0].message.content,
            "cost": float(response.headers.get("x-openrouter-cost", 0)),
        }
    except Exception as e:
        print(f"!! ERROR querying {friendly_name}: {e}")
        return {"advisor": friendly_name, "response": f"Error: {e}", "cost": 0}

# --- Helper Functions (Unchanged) ---
def load_config():
    # ... same as before
    try:
        with open("config.toml", "rb") as f: return tomllib.load(f)
    except FileNotFoundError: raise FileNotFoundError("FATAL: config.toml not found.")

def select_models(available_models):
    # ... same as before
    print("\n--- Select Your Advisors ---")
    model_items = list(available_models.items())
    for i, (name, model_id) in enumerate(model_items, 1):
        print(f"  [{i}] {name} ({model_id})")
    
    while True:
        selection = input("Select models by number (e.g., 1,3,4), or press Enter for all: ")
        if not selection: return available_models
        try:
            selected_indices = [int(x.strip()) - 1 for x in selection.split(",")]
            if all(0 <= i < len(model_items) for i in selected_indices):
                return {model_items[i][0]: model_items[i][1] for i in selected_indices}
            else: print("Invalid number detected.")
        except ValueError: print("Invalid input.")

# In council_v2_fixed.py

def export_to_markdown(session_history, filename="council_session.md"):
    """Exports the entire recursive session to a beautiful, Obsidian-friendly Markdown file."""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# 🏛️ AI Council Session Report\n\n")
        f.write("This document contains the complete transcript of the AI Council session.\n\n")

        for i, turn in enumerate(session_history):
            f.write(f"***\n\n")
            f.write(f"## 🔄 Turn {i+1}\n\n")

            # Format the user's input inside a 'QUESTION' callout
            f.write(f"> [!QUESTION] User Input for Turn {i+1}\n")
            # This ensures the entire prompt, including newlines, is inside the blockquote
            indented_prompt = "> " + turn['user_prompt'].replace('\n', '\n> ')
            f.write(f"{indented_prompt}\n\n")

            # The Rapporteur's report is now inserted directly, as it's already formatted
            f.write("### 🧠 Rapporteur's Synthesis\n\n")
            f.write(f"{turn['rapporteur_report']}\n\n")

    print(f"\n[+] Obsidian-friendly session report exported to {filename}")

# --- Main Application Logic (Completely Reworked for Conversation) ---

async def main():
    config = load_config()
    all_models = config.get("models", {})
    rapporteur_model_id = config.get("rapporteur", {}).get("model")

    print("="*50)
    print("Welcome to the AI Council (Conversational Session)")
    print("="*50)
    
    selected_models = select_models(all_models)
    
    council_histories = {model_id: [] for model_id in selected_models.values()}
    session_log = []
    total_session_cost = 0.0
    turn_counter = 1
    last_rapporteur_report = ""
    output_filename = "council_session.md" 

    while True:
        print("\n" + "="*20 + f" Turn {turn_counter} " + "="*20)
        
        if turn_counter == 1:
            user_input = input("Enter your initial prompt for the council:\n> ")
            
            # Call the improved slug generator, passing in the selected models
            slug = await generate_filename_slug(user_input, client, selected_models)
            date_str = datetime.datetime.now().strftime('%Y%m%d')
            
            # FIX: Ensure the file extension is correctly written as ".md"
            output_filename = f"{date_str}_{slug}.md"
            
            print(f"-> Session will be saved as: {output_filename}")
            prompt_for_council = user_input
        else:
            user_input = input("Enter your follow-up feedback (or type 'quit' to exit):\n> ")
            if user_input.lower() in ['quit', 'exit']:
                break
            
            prompt_for_council = (
                f"Here is the summary from the previous turn:\n---PREVIOUS SUMMARY---\n{last_rapporteur_report}\n\n"
                f"---END PREVIOUS SUMMARY---\n\n"
                f"Based on that summary, please address my new feedback: \"{user_input}\"\n"
                f"Refine or extend your previous answer according to this feedback."
            )
        
        # ... (The rest of the loop logic for dispatching, rapporteur, etc. is unchanged)
        # ... tasks = [] ...
        # ... council_results = await asyncio.gather(tasks) ...
        # ... rapporteur_result = await ask_advisor(...) ...
        
        # MODIFIED: When the loop ends, it passes the dynamically generated filename to the export function.
        # This happens in the 'if session_log:' block below.

    # End of session
    print("\nSession ended.")
    if session_log:
        # Pass the dynamic filename we generated on turn 1
        export_to_markdown(session_log, filename=output_filename)

if __name__ == "__main__":
    # Ensure you copy over the full code for ask_advisor, load_config etc.
    # The snippet above omits them for brevity.
    asyncio.run(main())