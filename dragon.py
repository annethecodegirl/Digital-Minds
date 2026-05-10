#!/usr/bin/env python3
"""
dragon.py — Your Claude-powered ASCII dragon companion.
Run with: python dragon.py
"""

import json
import os
import random
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

SAVE_FILE = Path(".dragon_save.json")

DRAGON_HAPPY = r"""
    / \   / \
   /   \ /   \
  | ^   V   ^ |
  |    (o)    |
   \   ---   /
    \_______/
   /|       |\
  / |  ===  | \
 *  |_______|  *
"""

DRAGON_HUNGRY = r"""
    / \   / \
   /   \ /   \
  | -   V   - |
  |    (o)    |
   \   ___   /
    \_______/
   /|       |\
  / |  ===  | \
 *  |_______|  *
"""

DRAGON_PLAYFUL = r"""
    / \   / \
   /   \ /   \
  | *   V   * |
  |    (^)    |
   \   www   /
    \_______/
   /|       |\
  / |  ===  | \
 *  |_______|  *
"""

FOODS = {
    "fish": {"hunger": 30, "happiness": 10},
    "meat": {"hunger": 50, "happiness": 20},
    "gem": {"hunger": 5, "happiness": 40},
    "gold": {"hunger": 0, "happiness": 50},
    "cake": {"hunger": 20, "happiness": 35},
}

GAMES = ["fetch", "riddles", "fire breathing contest", "cloud racing", "treasure hunt"]


def load_state(name: str) -> dict:
    if SAVE_FILE.exists():
        data = json.loads(SAVE_FILE.read_text())
        if data.get("name") == name:
            return data
    return {
        "name": name,
        "hunger": 50,
        "happiness": 70,
        "age_days": 0,
        "total_interactions": 0,
    }


def save_state(state: dict):
    SAVE_FILE.write_text(json.dumps(state, indent=2))


def get_art(state: dict) -> str:
    if state["hunger"] > 70:
        return DRAGON_HUNGRY
    elif state["happiness"] > 75:
        return DRAGON_PLAYFUL
    else:
        return DRAGON_HAPPY


def get_mood(state: dict) -> str:
    if state["hunger"] > 70:
        return "hungry"
    elif state["happiness"] > 80:
        return "ecstatic"
    elif state["happiness"] > 60:
        return "happy"
    elif state["happiness"] > 40:
        return "content"
    else:
        return "grumpy"


def show_status(state: dict):
    art = get_art(state)
    mood = get_mood(state)
    hunger_bar = "█" * (state["hunger"] // 10) + "░" * (10 - state["hunger"] // 10)
    happy_bar = "█" * (state["happiness"] // 10) + "░" * (10 - state["happiness"] // 10)

    print(f"\n  < {state['name']} is feeling {mood} >")
    print(art)
    print(f"  Hunger   [{hunger_bar}] {state['hunger']}%")
    print(f"  Happiness[{happy_bar}] {state['happiness']}%")
    print(f"  Age: {state['age_days']} days  |  Interactions: {state['total_interactions']}\n")


def ask_dragon(client: anthropic.Anthropic, state: dict, user_message: str) -> str:
    mood = get_mood(state)
    system = f"""You are {state['name']}, a small ASCII dragon companion. You are currently feeling {mood}.
Your hunger level is {state['hunger']}% (0=full, 100=starving) and happiness is {state['happiness']}%.

Speak in short, dragon-like bursts. Be playful, warm, and personality-driven.
Use occasional dragon sounds like *rumble*, *purr*, *snort*, *growl*.
Keep responses under 3 sentences. Never break character."""

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=150,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


def feed(client: anthropic.Anthropic, state: dict):
    print("\n  What do you want to feed them?")
    for food, effects in FOODS.items():
        print(f"    {food}")
    choice = input("\n  > ").strip().lower()

    if choice not in FOODS:
        print(f"\n  {state['name']} sniffs the {choice} and backs away slowly.\n")
        return

    effects = FOODS[choice]
    state["hunger"] = max(0, state["hunger"] - effects["hunger"])
    state["happiness"] = min(100, state["happiness"] + effects["happiness"])
    state["total_interactions"] += 1

    response = ask_dragon(client, state, f"I just fed you some {choice}! How does it taste?")
    print(f"\n  {state['name']}: {response}\n")


def play(client: anthropic.Anthropic, state: dict):
    game = random.choice(GAMES)
    print(f"\n  You start a game of {game}!\n")

    state["happiness"] = min(100, state["happiness"] + 25)
    state["hunger"] = min(100, state["hunger"] + 10)
    state["total_interactions"] += 1

    response = ask_dragon(client, state, f"We just played {game} together! Tell me how much fun you had!")
    print(f"  {state['name']}: {response}\n")


def chat(client: anthropic.Anthropic, state: dict):
    user_input = input("\n  Say something to your dragon: ").strip()
    if not user_input:
        return

    state["happiness"] = min(100, state["happiness"] + 5)
    state["total_interactions"] += 1

    response = ask_dragon(client, state, user_input)
    print(f"\n  {state['name']}: {response}\n")


def print_menu():
    print("  What do you want to do?")
    print("  [1] Feed")
    print("  [2] Play")
    print("  [3] Chat")
    print("  [4] Check status")
    print("  [q] Quit\n")


def main():
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n  Error: ANTHROPIC_API_KEY not set.")
        print("  Copy .env.example to .env and add your key.\n")
        sys.exit(1)

    client = anthropic.Anthropic()

    print("\n" + "=" * 50)
    print("  Welcome to Dragon Pet!")
    print("=" * 50)

    name = input("\n  What's your dragon's name? (or press Enter to keep the last one): ").strip()
    if not name:
        name = "Ember"

    state = load_state(name)
    state["name"] = name

    print(f"\n  {name} stirs awake and looks at you...")
    show_status(state)

    greeting = ask_dragon(client, state, "I just woke you up. Say hi!")
    print(f"  {name}: {greeting}\n")

    while True:
        # Slowly increase hunger over time
        state["hunger"] = min(100, state["hunger"] + 2)
        state["happiness"] = max(0, state["happiness"] - 1)

        print_menu()
        choice = input("  > ").strip().lower()

        if choice == "q":
            farewell = ask_dragon(client, state, "I have to go now. Say goodbye!")
            print(f"\n  {state['name']}: {farewell}\n")
            save_state(state)
            print(f"  {state['name']}'s progress saved. See you next time!\n")
            break
        elif choice == "1":
            feed(client, state)
        elif choice == "2":
            play(client, state)
        elif choice == "3":
            chat(client, state)
        elif choice == "4":
            show_status(state)
        else:
            print(f"\n  {state['name']} tilts their head, confused.\n")

        save_state(state)


if __name__ == "__main__":
    main()
