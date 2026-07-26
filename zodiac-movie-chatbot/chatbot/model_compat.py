"""
Home of `preprocess_text`, used by the intent classifier's FunctionTransformer
step.

Originally, the model was trained in a Colab notebook, where custom
functions are defined inside the `__main__` module. The pipeline's
FunctionTransformer step pickled a reference to `preprocess_text` as
`__main__.preprocess_text`. Patching `sys.modules["__main__"]` at runtime
worked when running `python app.py` directly, but turned out to be
unreliable under Streamlit -- Streamlit executes the app script through
its own internal runner, where `sys.modules["__main__"]` isn't
consistently the same object the patch touches, so `joblib.load()` still
failed there with:

    AttributeError: Can't get attribute 'preprocess_text' on <module '__main__'>

The real fix: the model file has been re-pickled (see the one-off script
used during development) so its FunctionTransformer now references
`chatbot.model_compat.preprocess_text` directly -- a real, always-
importable location, regardless of what happens to be `__main__` in
whatever process loads it. `joblib.load()` in data_loader.py now works
with no patching required.

The `sys.modules["__main__"]` registration below is kept only as a
harmless defensive fallback in case the model is ever retrained and
re-pickled from a notebook again, reintroducing a `__main__`-based
reference.
"""

import re
import sys


def preprocess_text(text):
    """Must exactly match the preprocessing function used during training."""
    if isinstance(text, str):
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
    return text


# Defensive fallback only -- see docstring above. The model no longer
# depends on this for normal operation.
sys.modules["__main__"].preprocess_text = preprocess_text
