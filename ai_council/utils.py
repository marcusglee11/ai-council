# ai_council/utils.py
import os, tomllib, re, json, logging
from openai import AsyncOpenAI

logger = logging.getLogger("ai_council")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

def load_config(file_path: str):
    try:
        with open(file_path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        logger.error("Configuration file not found at %s", file_path, exc_info=True)
        raise FileNotFoundError(f"FATAL: Configuration file not found at {file_path}.")

async def generate_filename_slug(prompt: str, client: AsyncOpenAI, council_models: dict, system_prompt: str) -> str:
    logger.info("Generating filename slug from prompt")
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
        logger.warning("Could not generate AI slug: %s. Falling back to default", e, exc_info=True)
        return "untitled_session"

def write_audit_log(turn_number: int, data: dict):
    """Writes a detailed JSON log for a single turn."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    filename = os.path.join(log_dir, f"turn_{turn_number:03d}_log.json")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    logger.info("Audit log saved to %s", filename)
