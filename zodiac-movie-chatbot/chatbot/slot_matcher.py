"""
Optimized slot value extraction.

The original notebook code identified slot values (actor names, genres,
languages, etc.) by looping over every line of every slot file and
checking whether it appeared as a substring in the user's message. With
slots/actor.dat containing 2.17 million actor names, that's ~2.17M
substring checks on *every single chat message* -- far too slow for a
live demo.

This module flips the direction of the search: instead of checking every
known value against the (short) user message, it builds a single
value -> slot_name dictionary once at startup, then walks the user's
message word-by-word, trying the longest plausible n-gram first
(greedy longest-match) and doing an O(1) dictionary lookup at each
position. Cost is proportional to the length of the user's message, not
the size of the slot dataset -- so it stays fast no matter how large
actor.dat is.
"""

import os
import re

MAX_NGRAM = 5  # covers 99.97%+ of actor names in the provided dataset
_STRIP_PUNCT = re.compile(r'^[\s.,!?;:"\'()]+|[\s.,!?;:"\'()]+$')

# actor.dat is scraped from a movie database and contains ~7k junk entries
# (bare initials, numbers, stray punctuation like "A", "1", "AB", "...").
# Left in, these cause false-positive slot matches on ordinary short words
# in the user's message (e.g. the "a" in "suggest a movie" matching the
# actor entry "A"). Real actor full names are effectively always at least
# this many characters, so a length floor removes the junk without losing
# genuine (if short) names.
MIN_ACTOR_LEN = 4
COMMON_WORDS = {
    "good", "nice", "great", "best", "new", "old", "some", "any", "all",
    "movie", "film", "show", "watch", "suggest", "recommend", "please",
    "one", "top", "cool", "fun", "nothing", "something", "anything",
    "zodiac", "sign",   # <-- add these
}


def load_slot_index(slots_dir):
    """Build a {lowercased_value: (original_value, slot_name)} index
    from every .dat file in slots_dir.

    Load order matters: actor.dat is scraped and noisy (contains junk
    entries that happen to collide with real words, e.g. literal entries
    "Drama"/"Romance" that aren't actually actor names). The small,
    human-curated slot files (day/month/genre/language) are loaded first
    so they claim any colliding value; actor.dat is loaded last and can
    only fill in values nothing else already claimed.
    """
    index = {}
    all_files = [f for f in os.listdir(slots_dir) if f.endswith(".dat")]
    curated = sorted(f for f in all_files if f != "actor.dat")
    ordered_files = curated + (["actor.dat"] if "actor.dat" in all_files else [])

    for fname in ordered_files:
        slot_name = fname[:-4]
        path = os.path.join(slots_dir, fname)
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                val = line.strip()
                if not val:
                    continue
                if slot_name == "actor" and (
                    len(val) < MIN_ACTOR_LEN
                    or not any(c.isalpha() for c in val)
                    or val.lower() in COMMON_WORDS
                ):
                    continue
                key = val.lower()
                # First file to claim a value wins -- curated files are
                # processed before actor.dat, so they always win collisions.
                index.setdefault(key, (val, slot_name))
    return index


def extract_slots(user_input, slot_index, max_ngram=MAX_NGRAM):
    """Greedy longest-match slot extraction.

    Returns a dict of {slot_name: matched_value} found in user_input.
    """
    words = user_input.split()
    n = len(words)
    matches = {}
    i = 0
    while i < n:
        matched = False
        upper = min(max_ngram, n - i)
        for length in range(upper, 0, -1):
            candidate = " ".join(words[i:i + length])
            candidate = _STRIP_PUNCT.sub("", candidate).lower()
            if candidate and candidate in slot_index:
                original_val, slot_name = slot_index[candidate]
                # Don't overwrite a slot we already matched with a longer span
                if slot_name not in matches:
                    matches[slot_name] = original_val
                i += length
                matched = True
                break
        if not matched:
            i += 1
    return matches
