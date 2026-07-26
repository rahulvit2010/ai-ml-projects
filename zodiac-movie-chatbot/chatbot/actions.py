"""
The actual "do something and reply" logic for each intent, once all
required parameters have been collected.
"""

import datetime
import re

from . import data_loader as dl


def _parse_month_day(text):
    """Parse a 'Month DD' string like 'March 21' into (month, day) ints."""
    parts = text.split()
    month = int(datetime.datetime.strptime(parts[0], "%B").strftime("%m"))
    day = int(parts[1])
    return (month, day)


def zodiac_sign_action(attributes):
    year = int(attributes["year"])
    month_str = attributes["month"]
    day = int(attributes["day"])

    try:
        month = int(month_str)
    except ValueError:
        try:
            month = int(datetime.datetime.strptime(month_str, "%b").strftime("%m"))
        except ValueError:
            month = int(datetime.datetime.strptime(month_str, "%B").strftime("%m"))

    try:
        datetime.datetime(year, month, day)
    except ValueError as e:
        return f"That doesn't look like a valid date ({e}). Could you double-check your date of birth?"

    usr_dob = (month, day)
    for _, row in dl.zodiac_df.iterrows():
        start = _parse_month_day(row["Start"])
        end = _parse_month_day(row["End"])
        if start <= usr_dob <= end:
            return f"Your zodiac sign is {row['Zodiac']}! \u2728"

    return "I couldn't determine your zodiac sign from that date -- mind trying again?"


def suggest_movie_action(attributes):
    language = attributes.get("language", "").lower().strip()
    genre_input = attributes.get("genre", "").lower().strip()
    actor_input = attributes.get("actor", "").lower().strip()

    filtered = dl.movie_df

    if language and "language" in filtered.columns:
        filtered = filtered[
            filtered["language"].str.contains(re.escape(language), case=False, na=False)
        ]

    if genre_input and "genre" in filtered.columns:
        terms = [re.escape(t.strip()) for t in genre_input.split(",") if t.strip()]
        if terms:
            pattern = "|".join(terms)
            filtered = filtered[
                filtered["genre"].str.contains(pattern, case=False, na=False, regex=True)
            ]

    if actor_input and "actor" in filtered.columns:
        terms = [re.escape(t.strip()) for t in actor_input.split(",") if t.strip()]
        if terms:
            pattern = "|".join(terms)
            filtered = filtered[
                filtered["actor"].str.contains(pattern, case=False, na=False, regex=True)
            ]

    if not filtered.empty and "title" in filtered.columns:
        titles = sorted(set(filtered["title"].tolist()))
        if len(titles) == 1:
            return f"How about watching '{titles[0].title()}'?"

        shown = titles[:5]
        if len(shown) > 1:
            movie_list = ", ".join(f"'{t.title()}'" for t in shown[:-1])
            movie_list += f", or '{shown[-1].title()}'"
        else:
            movie_list = f"'{shown[0].title()}'"

        extra = f" (plus {len(titles) - 5} more matches!)" if len(titles) > 5 else ""
        return f"I found some great matches: {movie_list}{extra}"

    criteria = []
    if language:
        criteria.append(f"Language: {language.title()}")
    if genre_input:
        criteria.append(f"Genre: {genre_input.title()}")
    if actor_input:
        criteria.append(f"Actor: {actor_input.title()}")
    suffix = f" ({', '.join(criteria)})" if criteria else ""

    return f"I couldn't find a movie matching your criteria{suffix}. Want to try different preferences?"


def out_of_scope_action(attributes=None):
    return (
        "I'm not sure I understood that. I can help you find your zodiac sign "
        "or suggest a movie -- try asking about either! \U0001F319\U0001F3AC"
    )
