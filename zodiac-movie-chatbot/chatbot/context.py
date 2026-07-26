"""
Dialogue context classes.

A "context" is a flag object that tracks where we are in the conversation:
- FirstGreeting: the very start of a fresh conversation
- IntentComplete: the bot just finished answering, and the next message
  should start a brand new conversation
"""


class Context:
    def __init__(self, name):
        self.lifespan = 2
        self.name = name
        self.active = False

    def activate_context(self):
        self.active = True

    def deactivate_context(self):
        self.active = False


class FirstGreeting(Context):
    def __init__(self):
        self.lifespan = 1
        self.name = "FirstGreeting"
        self.active = True


class IntentComplete(Context):
    def __init__(self):
        self.lifespan = 1
        self.name = "IntentComplete"
        self.active = True
