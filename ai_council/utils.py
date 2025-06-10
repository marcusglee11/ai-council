"""Helper functions for configuration loading and logging."""

import os
import tomllib
import re
import datetime
import json
from openai import AsyncOpenAI

def load_config(file_path: str) -> dict:
    """Load a TOML configuration file."""
    try:
        with open(file_path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"FATAL: Configuration file not found at {file_path}."
        )

async def generate_filename_slug(prompt: str, client: AsyncOpenAI, council_models: dict, system_prompt: str) -> str:
    """Generate a filesystem friendly slug based on the initial prompt."""
    print("... Generating filename slug from prompt ...")
    if not council_models: return "untitled_session"
    model_for_slug = list(council_models.values())[0]

    try:
        response = await client.chat.completions.create(
            model=model_for_slug,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=20,
        )
        slug = response.choices[0].message.content.strip().lower()
        slug = re.sub(r'\s+', '_', slug)
        slug = re.sub(r'[^a-z0-9_]', '', slug)
        return slug.strip('_')[:50] or "untitled_session"
    except Exception as e:
        print(f"!! WARN: Could not generate AI slug: {e}. Falling back to default.")
        return "untitled_session"

def write_audit_log(turn_number: int, data: dict) -> None:
    """Write a JSON audit log for a single turn."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    filename = os.path.join(log_dir, f"turn_{turn_number:03d}_log.json")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"-> Audit log saved to {filename}")    
