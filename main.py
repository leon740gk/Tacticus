import requests
import json
import os
import re

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
POSTED_CODES_FILE = "posted_codes.json"


# =========================
# LOAD / SAVE POSTED CODES
# =========================
def load_posted_codes():
    if not os.path.exists(POSTED_CODES_FILE):
        return set()

    with open(POSTED_CODES_FILE, "r") as f:
        return set(json.load(f))


def save_posted_codes(codes):
    with open(POSTED_CODES_FILE, "w") as f:
        json.dump(list(codes), f, indent=2)


# =========================
# CLEAN TEXT (remove [[ ]])
# =========================
def clean_text(text):
    return re.sub(r"\[\[(.*?)\]\]", r"\1", text)


# =========================
# FORMAT REWARDS (CODEX)
# =========================
def format_reward(rewards):
    parts = []

    for r in rewards:
        name = r.get("name", "")
        r_type = r.get("type", "")
        qty = r.get("quantity", 0)

        if r_type == "energy":
            emoji = "⚡"
            label = "Energy"
        elif r_type == "gold":
            emoji = "💰"
            label = "Gold"
        elif r_type == "blackstone":
            emoji = "💎"
            label = "Blackstone"
        elif r_type == "shards":
            emoji = "🧬"
            label = f"{name.title()} Shards"
        elif r_type == "ammo":
            emoji = "🔫"
            label = "Ammo"
        elif r_type == "upgrade":
            emoji = "🛠️"
            label = name.title()
        else:
            emoji = "🎁"
            label = name.title()

        parts.append(f"{emoji} {qty} {label}")

    return ", ".join(parts)


# =========================
# FETCH FROM CODEX API (PRIMARY)
# =========================
def fetch_codes_codex():
    url = "https://api.tacticuscodex.com/api/gamecode"

    response = requests.get(url)
    data = response.json()

    codes = {}

    # sort newest first
    items = sorted(
        data.get("gameCodes", []),
        key=lambda x: x.get("postedDate", ""),
        reverse=True
    )

    for item in items:
        if not item.get("isActive", True):
            continue

        code = item.get("code", "").strip().upper()
        rewards = item.get("rewards", [])

        if code:
            reward_text = format_reward(rewards)
            codes[code] = reward_text

    return codes


# =========================
# FETCH FROM WIKI (FALLBACK)
# =========================
def fetch_codes_wiki():
    url = "https://tacticus.fandom.com/wiki/Redemption_Codes"

    html = requests.get(url).text

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    codes = {}

    for li in soup.select("li"):
        text = clean_text(li.get_text())

        if "-" in text:
            parts = text.split("-", 1)
            code = parts[0].strip().upper()
            reward = parts[1].strip()

            if code.isupper():
                codes[code] = reward

    return codes


# =========================
# SEND TO DISCORD
# =========================
def send_to_discord(message):
    if not DISCORD_WEBHOOK:
        print("❌ DISCORD_WEBHOOK is not set!")
        return

    chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]

    for chunk in chunks:
        response = requests.post(DISCORD_WEBHOOK, json={"content": chunk})
        print("Discord status:", response.status_code)

        if response.status_code != 204:
            print("Error:", response.text)


# =========================
# MAIN
# =========================
def main():
    posted_codes = load_posted_codes()

    codex_codes = fetch_codes_codex()
    wiki_codes = fetch_codes_wiki()

    # merge (codex primary, wiki fallback)
    all_codes = {**wiki_codes, **codex_codes}

    new_codes = {
        code: reward
        for code, reward in all_codes.items()
        if code not in posted_codes
    }

    if not new_codes:
        print("No new codes.")
        return

    # build ONE message
    lines = []

    for code, reward in new_codes.items():
        lines.append(f"🔹 **{code}**\n{reward}")

    message = "\n\n".join(lines)

    send_to_discord(message)

    # update storage
    posted_codes.update(new_codes.keys())
    save_posted_codes(posted_codes)

    print(f"Posted {len(new_codes)} new codes.")


if __name__ == "__main__":
    main()