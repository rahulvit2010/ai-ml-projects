"""
Compatibility shim for loading intent_classifier_model.pkl.

The model was trained in a Colab notebook, where custom functions are
defined inside the `__main__` module. The pipeline's FunctionTransformer
step pickled a reference to `preprocess_text` as `__main__.preprocess_text`.
When we load the model from a normal Python file (not a notebook),
there is no `__main__.preprocess_text`, so joblib.load() fails with:

    AttributeError: Can't get attribute 'preprocess_text' on <module '__main__'>

The fix: define the exact same function here and register it onto the
`__main__` module before unpickling, so joblib finds what it expects.
This must be imported before `joblib.load(...)` is called anywhere in
the app (data_loader.py does this).
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


# Register onto __main__ so joblib/pickle can resolve it.
sys.modules["__main__"].preprocess_text = preprocess_text
