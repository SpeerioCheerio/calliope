# generate_word_data.py
# -----------------------------------------------------------------------------
# Description:
#   Enrich a list of words with detailed lexical data using the OpenAI Python
#   client v1.x interface. Reads OPENAI_API_KEY from .env (override=True) and
#   writes the output to words_enriched.json.
#   Auto‑detects an available chat model: tries env var OPENAI_MODEL, then
#   'gpt-4o-mini', then falls back to 'gpt-3.5-turbo'.
# -----------------------------------------------------------------------------

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict

from dotenv import load_dotenv
from openai import OpenAI, NotFoundError
from datetime import timezone
# -----------------------------------------------------------------------------
# Load environment variables from .env file with override
# This will override any existing environment variables with values from .env
# -----------------------------------------------------------------------------
load_dotenv(override=True)

# Initialize OpenAI API with better error handling
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("[ERROR] FATAL: No OpenAI API key found in environment variables!")
    print("[ERROR] Please ensure OPENAI_API_KEY is set in your environment or .env file.")
    raise EnvironmentError("[FATAL] No OpenAI API key found in environment variables!")
else:
    print(f"[INFO] OpenAI API key loaded successfully. Length: {len(api_key)} characters")
    print(f"[INFO] API key preview: {api_key[:20]}...{api_key[-4:]}")
    
    # Additional validation for placeholder keys
    if api_key.startswith("sk-<") or len(api_key) < 40:
        print("[ERROR] FATAL: Invalid OpenAI API key detected (appears to be placeholder)")
        print("[ERROR] Please ensure you have set a real OpenAI API key in your .env file.")
        raise EnvironmentError("[FATAL] Invalid or placeholder OpenAI API key")

client = OpenAI(api_key=api_key)

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
WORDS: list[str] = [
    "Tractable", "Officious", "Occasioned", "Avowal", "Desirous", "Remonstrance",
    "Repining", "Conjugal", "Querulous", "Coppice", "Pecuniary", "Untinctured",
    "Hauteur", "Acrimony", "Palliation", "Licentiousness", "Connubial", "Gally",
    "Panegyric", "Tacit", "Gaiety", "Obsequious", "Arrear", "Blaspheme", "Bestial",
    "Libidinous", "Licentious", "Conflagration", "Gentility", "Exculpate", "Abject",
    "Myopic", "Encomium", "Sepulchers", "Dolorous", "Sepulchral", "Paroxysm",
    "Internecine", "Annulling", "Triune", "Abutment", "Inveighing", "Simony",
    "Pliant", "Pejorative", "Didactic", "Frenetic", "Oppilation", "Metes",
    "Castigate", "Bereavement", "Mantras", "Paradigmatic", "Perfunctory", "Endemic",
    "Presage", "Envenom", "Purgation", "Enfiladed", "Stolidly", "Beneficence",
    "Ineffable", "Detritus", "Largesse", "Simulacrum", "Brevity", "Abase",
    "Philanderer", "Votive", "Ensconced", "Merriment", "Vacillated", "Spurious",
    "Perfidious", "Katabasis", "Sinuous", "Pomposity", "Denuded", "Reticent",
    "Dither", "Palavering", "Compunction", "Germane", "Invective", "Farcical",
    "Tedium", "Baleful", "Apoplectic", "Acolytes", "Probity", "Infantile",
    "Somnolent", "Surreptitiously", "Abscond", "Bilious", "Fomenting", "Untoward",
    "Pariah", "Erudite", "Fatuous", "Mutability", "Epicene", "Garrulous", "Ablative",
    "Dative", "Aorist", "Lineament", "Exegesis", "Palimpsest", "Alacrity", "Salient",
    "Perforce", "Protuberant", "Saturnine", "Preternatural", "Fumigate", "Amorphous",
    "Encumbrance", "Saccharine", "Traipsing", "Maundering", "Syllogism", "Swive",
    "Carnality", "Roistering", "Fecundity", "Anathema", "Vicegerent", "Tonsure",
    "Catamite", "Absconded", "Piquant", "Fulsomely", "Harridan", "Bawdier",
    "Palling", "Intransigence", "Impetuosity", "Trundled", "Apotropaic",
    "Effrontery", "Episcopal", "Ophidian", "Mendacity", "Recalcitrant", "Iniquity",
    "Inculcate", "Inchoate", "Appellation", "Scabrous", "Sangfroid", "Equanimity",
    "Impenturbility", "Paucity", "Referent", "Bromides", "Lassitude", "Japer",
    "Racy", "Perambulate", "Cognomen", "Jocularity", "Debonair", "Opalescent",
    "Acrid", "Sibilant", "Coevals", "Fey", "Palliative", "Perineum", "Tartan",
    "Chameleonic", "Voluptas", "Tritest", "Inveigled", "Coruscating", "Fructuate",
    "Pugilist", "Crenulated", "Memory", "Phocine", "Favonian", "Meretricious",
    "Nacreous", "Nicating", "Incipient", "Indefatigable", "Rigmarole", "Alembic",
    "Plumulaceous", "Umbrace", "Purblind", "Saturate", "Archly", "Carbuncles",
    "Jalopy", "Hoary", "Rubious", "Lentor", "Spoonerette", "Maudlin", "Parlance",
    "Addendum", "Antimeridian", "Callipygian", "Emeritus", "Gonadal", "Coranting"
]

OUTPUT_PATH = Path("starting_words.json")

# Prefer env‑defined model or fallback chain
PRIMARY_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
FALLBACK_MODEL = "gpt-3.5-turbo"
TEMPERATURE = 0.2
MAX_TOKENS = 250

# -----------------------------------------------------------------------------
# Prompt templates
# -----------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are a precise dictionary augmentation tool.\n"
    "Return STRICT minified JSON with keys: pos, definition, example_sentence, rarity, sentiment.\n\n"
    "Rarity labels (exact spelling):\n"
    "  notty → common advanced (~80%).\n"
    "  luke  → less common, high‑level (~15%).\n    "
    "  alex  → rare, exotic, archaic (~5%).\n\n"
    "Sentiment labels (exact spelling): positive, negative, neutral, formal.\n"
    "No extra keys. No extra text."
)


USER_TEMPLATE = "Provide the data for the word '{word}'."

# -----------------------------------------------------------------------------
# Helper to perform a single chat completion with fallback
# -----------------------------------------------------------------------------

def call_openai(messages, model):
    return client.chat.completions.create(
        model=model,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        messages=messages,
    )


def fetch_word_data(word: str) -> Dict[str, str]:
    """Query OpenAI with fallback model strategy."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TEMPLATE.format(word=word)},
    ]

    try:
        chat = call_openai(messages, PRIMARY_MODEL)
    except NotFoundError:
        print(f"[WARN] Model '{PRIMARY_MODEL}' not available. Falling back to '{FALLBACK_MODEL}'.")
        chat = call_openai(messages, FALLBACK_MODEL)

    raw = chat.choices[0].message.content.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"[WARN] JSON parse failed for '{word}'. Using placeholder.")
        data = {
            "pos": "unknown",
            "definition": "Definition unavailable.",
            "example_sentence": "Example unavailable.",
            "rarity": "notty",
            "sentiment": "neutral",
            "_raw": raw,
        }

    for key, default in {
        "pos": "unknown",
        "definition": "Definition unavailable.",
        "example_sentence": "Example unavailable.",
        "rarity": "notty",
        "sentiment": "neutral",
    }.items():
        data.setdefault(key, default)

    return {
        "word": word,
        **data,
        "date_added": datetime.now(timezone.utc).isoformat(),
    }

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> None:
    enriched: List[Dict[str, str]] = []
    for w in WORDS:
        print(f"→ Processing {w} …")
        enriched.append(fetch_word_data(w))

    OUTPUT_PATH.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✔ Data written to {OUTPUT_PATH} (total {len(enriched)} words).")


if __name__ == "__main__":
    main()
