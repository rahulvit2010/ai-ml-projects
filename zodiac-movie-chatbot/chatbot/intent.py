"""
Intent and Parameter definitions, loaded from data/params/params.cfg.

Each Intent (e.g. "get_Zodiac_Sign") has a list of required Parameters
(e.g. day/month/year), each with follow-up prompts to ask the user
if that parameter hasn't been collected yet.
"""


class Intent:
    def __init__(self, name, params, action):
        self.name = name
        self.action = action
        self.params = [Parameter(p) for p in params]


class Parameter:
    def __init__(self, info):
        self.name = info["name"]
        self.placeholder = info["placeholder"]
        self.prompts = info["prompts"]
        self.required = info["required"]
        self.context = info["context"]
