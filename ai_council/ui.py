"""Interactive console utilities for the AI council application."""

import os
import re
import time
import asyncio
import fitz
from rich.live import Live
from rich.table import Table
from rich.spinner import Spinner
from rich.console import Console
from rich.markdown import Markdown

console = Console()

def display_welcome() -> None:
    """Print the opening banner."""
    console.print("=" * 50, style="bold blue")
    console.print("Welcome to the AI Council (v5.2 - Context-Aware UI)", style="bold blue")
    console.print("=" * 50, style="bold blue")

def select_models(available_models: dict) -> dict:
    """Prompt the user to choose which advisor models to use."""
    console.print("\n--- Select Your Advisors ---", style="bold yellow")
    model_items = list(available_models.items())
    for i, (name, _) in enumerate(model_items, 1):
        print(f"  [{i}] {name}")
    while True:
        selection = input("Select models by number (e.g., 1,3), or press Enter for all: ")
        if not selection: return available_models
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(",")]
            if all(0 <= i < len(model_items) for i in indices):
                return {model_items[i][0]: model_items[i][1] for i in indices}
            else: console.print("Invalid number detected.", style="red")
        except ValueError: console.print("Invalid input.", style="red")

def get_document_context() -> str:
    """Load optional context from a user provided document."""
    while True:
        add_doc = input("Add a file for context (txt, md, pdf)? (y/n): ").lower()
        if add_doc == 'n': return ""
        if add_doc == 'y':
            raw_path = input("Please provide the full path to the file: ")
            file_path = raw_path.strip().strip('"').strip("'")
            if not os.path.exists(file_path):
                console.print(f"❌ ERROR: File not found at '{file_path}'. Please try again.", style="red")
                continue
            try:
                content = ""
                if file_path.lower().endswith('.pdf'):
                    with fitz.open(file_path) as doc: content = "".join(page.get_text() for page in doc)
                elif file_path.lower().endswith(('.txt', '.md')):
                    with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
                else:
                    console.print("❌ ERROR: Unsupported file type.", style="red"); continue
                
                console.print(f"✅ Loaded {len(content):,} characters from {os.path.basename(file_path)}.", style="green")
                return f"--- DOCUMENT CONTEXT ---\n{content}\n--- END DOCUMENT CONTEXT ---\n\n"
            except Exception as e: console.print(f"❌ ERROR: Could not read file: {e}", style="red")
        else: console.print("Invalid input.", style="red")

def get_initial_prompt(templates: dict) -> str:
    """Handle prompt gathering for the first turn using templates."""
    console.print("\n--- Select a Prompt Template ---", style="bold yellow")
    categories = list(templates.keys())
    for i, category in enumerate(categories): print(f"  [{i+1}] {category.replace('_', ' ').title()}")
    print("  [0] Enter a custom prompt")

    while True:
        try:
            choice = int(input("Select a category by number, or 0 for custom: "))
            if choice == 0:
                return input("Enter your custom prompt for the council:\n> ")

            if 0 < choice <= len(categories):
                category_key = categories[choice-1]
                selected_category = templates[category_key]
                
                template_items = list(selected_category.items())
                console.print(f"\n--- Templates in '{category_key.title()}' ---", style="bold yellow")
                for j, (name, _) in enumerate(template_items): print(f"  [{j+1}] {name.replace('_', ' ').title()}")
                
                template_choice = int(input("Select a template: "))
                if 0 < template_choice <= len(template_items):
                    _, template_string = template_items[template_choice-1]
                    
                    placeholders = re.findall(r'\{(.*?)\}', template_string)
                    filled_values = {}

                    console.print("\n--- Fill in the template placeholders ---", style="bold yellow")
                    for placeholder in placeholders:
                        # Create a version of the template with the current placeholder highlighted
                        highlighted_template = template_string.replace(
                            f"{{{placeholder}}}",
                            f"**`{{{placeholder}}}`**"  # Use Markdown bold/code for highlight
                        )

                        console.print(f"\nTemplate Context for '[bold magenta]{placeholder}[/bold magenta]':")
                        # Display the full template with the highlight inside a quote block
                        console.print(Markdown(f"> {highlighted_template}"))

                        # Ask for the input for this specific placeholder
                        value = input(f"  Enter value for [bold magenta]{placeholder}[/bold magenta]: ")
                        filled_values[placeholder] = value

                    return template_string.format(**filled_values)
                else:
                    console.print("Invalid template selection.", style="red")
            else:
                console.print("Invalid category selection.", style="red")
        except (ValueError, IndexError):
            console.print("Invalid input. Please try again.", style="red")

def get_follow_up_input(turn_counter: int) -> str:
    """Collect follow-up feedback from the user."""
    console.print(f"\n" + "="*20 + f" Turn {turn_counter} " + "="*20, style="bold blue")
    
    console.print(
        "Enter your follow-up feedback, or type [bold green]'go'[/bold green] to use the Facilitator's suggested question.",
        justify="left",
    )
    user_input = input("Type 'quit' to exit > ")
    return user_input

def generate_status_table(statuses: dict) -> Table:
    """Create the rich ``Table`` for the live progress dashboard."""
    table = Table(title="AI Council Status", expand=True, border_style="blue")
    table.add_column("Advisor", style="cyan", no_wrap=True)
    table.add_column("Status")
    table.add_column("Time (s)", style="green", justify="right")
    for name, data in statuses.items():
        if "Querying" in data['status']:
            status_display = Spinner("dots", text=f"[yellow]{data['status']}[/yellow]")
        elif "Done" in data['status']:
            status_display = f"[green]{data['status']}[/green]"
        else: # Error
            error_msg = data.get('error_msg', 'Unknown Error')
            status_display = f"[red]❌ Error: {error_msg}[/red]"
        time_str = f"{data['time']:.2f}" if data['time'] > 0 else ""
        table.add_row(name, status_display, time_str)
    return table

async def live_council_progress(tasks: list[asyncio.Task]) -> list:
    """Display progress for advisor tasks and return their results."""
    model_statuses = {task.get_name(): {"status": "Querying...", "time": 0} for task in tasks}
    start_time = time.time()
    results = []
    with Live(generate_status_table(model_statuses), console=console, refresh_per_second=10, vertical_overflow="visible") as live:
        for task in asyncio.as_completed(tasks):
            result = await task
            advisor_name = result['advisor']
            elapsed = time.time() - start_time
            if result.get("error"):
                model_statuses[advisor_name]['status'] = "❌ Error"
                model_statuses[advisor_name]['error_msg'] = str(result.get('response', 'N/A'))
            else:
                model_statuses[advisor_name]['status'] = "✅ Done"
            model_statuses[advisor_name]['time'] = elapsed
            results.append(result)
            live.update(generate_status_table(model_statuses))
    console.print("\n...Council deliberation complete...", style="bold green")
    return results

def display_rapporteur_report(report: str) -> None:
    """Render the Rapporteur's Markdown report to the terminal."""
    console.print("\n" + "="*50, style="bold blue")
    console.print("           COUNCIL FACILITATOR'S REPORT", style="bold blue")
    console.print("="*50, style="bold blue")
    console.print(Markdown(report))

def display_turn_telemetry(turn_cost: float, total_cost: float, turn: int) -> None:
    """Print cost information for the completed turn."""
    console.print(f"\n--- Turn {turn} Cost: ${turn_cost:.6f} | Total Session Cost: ${total_cost:.6f} ---", style="yellow")
