import requests
import json
import os
import re
from datetime import datetime

API_URL = "https://tacticus.wiki.gg/api.php"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")


# -------------------------
# CLEAN TEXT (wiki cleanup)
# -------------------------
def clean_text(text):
    text = re.sub(r"'{2,}", "", text)  # bold/italic
    text = re.sub(r"\[\[[^|\]]+\|([^\]]+)\]\]", r"\1", text)  # [[Page|Name]]
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)  # [[Page]]
    text = re.sub(r"\s+", " ", text)  # normalize spaces
    return text.strip()


# -------------------------
# FETCH CODES FROM API
# -------------------------
def fetch_codes():
    params = {
        "action": "parse",
        "page": "Active_Codes",
        "format": "json",
        "prop": "wikitext"
    }

    response = requests.get(API_URL, params=params)
    data = response.json()

    text = data["parse"]["wikitext"]["*"]

    codes = {}

    for line in text.split("\n"):
        line = line.strip()

        if " - " in line:
            parts = line.split(" - ", 1)

            code = clean_text(parts[0].replace("*", "").strip())
            reward = clean_text(parts[1])

            if code.isupper():
                codes[code] = reward

    return codes


# -------------------------
# LOAD / SAVE
# -------------------------
def load_saved_codes():
    if not os.path.exists("codes.json"):
        return {}

    with open("codes.json", "r") as f:
        return json.load(f)


def save_codes(codes):
    with open("codes.json", "w") as f:
        json.dump(codes, f, indent=2)


# -------------------------
# SPLIT LONG MESSAGE
# -------------------------
def split_message(text, limit=2000):
    parts = []
    while len(text) > limit:
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        parts.append(text[:split_at])
        text = text[split_at:]
    parts.append(text)
    return parts


# -------------------------
# SEND TO DISCORD
# -------------------------
def send_grouped_to_discord(new_codes):
    if not new_codes:
        return

    # sort codes alphabetically (stable)
    sorted_codes = dict(sorted(new_codes.items()))

    description = ""
    for code, reward in sorted_codes.items():
        description += f"🔹 **{code}**\n{reward}\n\n"

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    embed = {
        "title": "New Tacticus Codes",
        "description": description,
        "color": 5814783,
        "footer": {"text": f"Updated: {timestamp}"}
    }

    data = {
        "embeds": [embed]
    }

    # handle Discord message length limit
    messages = split_message(description)

    for msg in messages:
        embed["description"] = msg
        requests.post(WEBHOOK_URL, json=data)


# -------------------------
# MAIN LOGIC
# -------------------------
def main():
    current_codes = fetch_codes()
    saved_codes = load_saved_codes()

    new_codes = {
        code: reward
        for code, reward in current_codes.items()
        if code not in saved_codes
    }

    if new_codes:
        send_grouped_to_discord(new_codes)

    save_codes(current_codes)


if __name__ == "__main__":
    main()