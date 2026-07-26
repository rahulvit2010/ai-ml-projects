"""
The dialogue manager: given a user message and the current conversation
state, figures out the intent, collects any missing required parameters
by asking follow-up questions, and triggers the right action once
everything's collected.

This mirrors the original notebook's Session/reply logic, with two
changes: slot extraction now uses the fast n-gram index (slot_matcher.py)
instead of scanning millions of lines per message, and heavy resources
are loaded once via data_loader.py instead of being reloaded every call.
"""

import random
import re
import datetime

from .context import FirstGreeting, IntentComplete
from .intent import Intent
from . import data_loader as dl
from . import actions
from .slot_matcher import extract_slots

DATE_RE = re.compile(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})")

ACTION_MAP = {
    "zodiacSign_Action()": actions.zodiac_sign_action,
    "suggestMovie_Action()": actions.suggest_movie_action,
    "out_of_scope_Action()": actions.out_of_scope_action,
}


def load_intent(intent_name):
    if intent_name == "out_of_scope":
        return Intent("out_of_scope", [], "out_of_scope_Action()")

    cfg = dl.params_config
    if intent_name in cfg:
        data = cfg[intent_name]
        return Intent(data["intentname"], data["Parameters"], data["actions"])

    return Intent("out_of_scope", [], "out_of_scope_Action()")


def intent_predict(user_input):
    predicted = dl.intent_model.predict([user_input])[0]

    # Heuristic override: the classifier can over-fire on get_suggest_movie
    # for sentences that don't actually mention movies.
    if predicted == "get_suggest_movie":
        movie_keywords = ["movie", "film", "cinema", "suggest", "recommend", "watch"]
        if not any(k in user_input.lower() for k in movie_keywords):
            return "out_of_scope"

    return predicted


def get_attributes(user_input, context, attributes):
    """Extract slot values (date, actor, genre, language...) from user_input
    and merge them into the running attributes dict."""
    if context.name.startswith("IntentComplete"):
        return attributes, user_input

    working_input = user_input

    # Numeric date parsing, e.g. "21/03/2001" -> year/month/day
    match = DATE_RE.search(user_input)
    if match:
        val1, val2, year = match.groups()
        try:
            month, day = int(val1), int(val2)
            if month > 12 and day <= 12:
                month, day = day, month
            elif month > 12 and day > 12:
                raise ValueError("invalid month/day combination")
            datetime.datetime(int(year), month, day)  # validate

            attributes["year"] = str(year)
            attributes["month"] = str(month)
            attributes["day"] = str(day)
            working_input = working_input.replace(match.group(0), " ")
        except ValueError:
            pass  # fall through to slot-file matching

    matches = extract_slots(working_input, dl.slot_index)
    for slot_name, value in matches.items():
        if slot_name in ("year", "month", "day") and all(
            k in attributes for k in ("year", "month", "day")
        ):
            continue
        attributes[slot_name] = value

    return attributes, working_input


def intent_identifier(clean_input, current_intent, was_mid_collection):
    clean_input = clean_input.lower()
    if current_intent is None:
        return load_intent(intent_predict(clean_input))

    # If we were already mid-conversation collecting required parameters for
    # the current intent *before this message arrived*, keep that intent --
    # the user's reply (a date, a single word like "Comedy", an actor
    # name...) is answering our follow-up question, not a fresh request, and
    # would often confuse the ML classifier if re-run on its own. This check
    # must use the pre-extraction state: even if this message happens to
    # complete every remaining param (e.g. "21/03/2001" fills day+month+year
    # in one shot), it's still an answer, not a new query.
    if was_mid_collection:
        return current_intent

    return load_intent(intent_predict(clean_input))


def check_required_params(current_intent, attributes):
    """Returns (prompt, param_name) for the first missing required
    parameter, or (None, None) if everything's collected."""
    for param in current_intent.params:
        if param.required and param.name not in attributes:
            return random.choice(param.prompts), param.name
    return None, None


def check_actions(current_intent, attributes):
    fn = ACTION_MAP.get(current_intent.action)
    if fn is None:
        return current_intent.action
    return fn(attributes)


class Session:
    """One user's ongoing conversation with the bot."""

    def __init__(self):
        self.context = FirstGreeting()
        self.current_intent = None
        self.attributes = {}
        self.pending_param = None  # the specific param we most recently asked about

    def reply(self, user_input):
        if self.context.name == "IntentComplete":
            self.attributes = {}
            self.context = FirstGreeting()
            self.current_intent = None
            self.pending_param = None

        was_mid_collection = self.current_intent is not None and any(
            p.required and p.name not in self.attributes for p in self.current_intent.params
        )
        pending = self.pending_param if was_mid_collection else None

        self.attributes, clean_input = get_attributes(user_input, self.context, self.attributes)

        # Fallback for slots with no backing data file to validate against
        # (e.g. "year" has no slots/year.dat -- any 4-digit reply is valid).
        # If we asked specifically about `pending` and slot-matching didn't
        # find a value for it, trust the user's raw reply.
        if pending and pending not in self.attributes:
            cleaned = user_input.strip().strip(".,!?;:\"'")
            if cleaned:
                self.attributes[pending] = cleaned

        self.current_intent = intent_identifier(clean_input, self.current_intent, was_mid_collection)

        prompt, asked_param = check_required_params(self.current_intent, self.attributes)

        if prompt is None:
            prompt = check_actions(self.current_intent, self.attributes)
            self.context = IntentComplete()
            self.pending_param = None
        else:
            self.pending_param = asked_param

        if not prompt:
            prompt = "Sorry, could you rephrase that?"

        return prompt
