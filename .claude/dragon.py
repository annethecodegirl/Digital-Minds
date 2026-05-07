#!/usr/bin/env python3
import random
import sys

DRAGON = r"""
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

MOODS = [
    "roar! got ur back.",
    "fire ready. let's go.",
    "watching ur code...",
    "that looked spicy 🔥",
    "*wing flap*",
    "impressive. more.",
    "i believe in u.",
    "onward, coder.",
    "scales tingling...",
    "breathing fire at bugs.",
]

def main():
    mood = random.choice(MOODS)
    width = max(len(line) for line in DRAGON.splitlines())
    bubble = f"  < {mood} >"
    print(bubble)
    print(DRAGON)

if __name__ == "__main__":
    main()
