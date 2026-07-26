"""
Loads every heavy resource (ML model, movie database, zodiac table, intent
config, slot index) exactly once at process startup, and exposes them as
module-level singletons that the rest of the app imports.

IMPORTANT: run with a single worker process (see Procfile) -- each worker
loads its own full copy of this data (~500-600MB), so multiple workers
multiply memory use.
"""

import json
import os
import time

from . import model_compat  # noqa: F401  (must run before joblib.load)
import joblib
import pandas as pd

from .slot_matcher import load_slot_index

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "model")

_t0 = time.time()

print("[startup] Loading intent classification model...", flush=True)
intent_model = joblib.load(os.path.join(MODEL_DIR, "intent_classifier_model.pkl"))

print("[startup] Loading zodiac sign date ranges...", flush=True)
zodiac_df = pd.read_csv(os.path.join(DATA_DIR, "Zodiac_sign.csv"))

print("[startup] Loading movie database (this can take several seconds)...", flush=True)
movie_df = pd.read_csv(os.path.join(DATA_DIR, "movie.csv"))
movie_df.columns = movie_df.columns.str.lower()

print("[startup] Loading intent parameter config...", flush=True)
with open(os.path.join(DATA_DIR, "params", "params.cfg")) as f:
    params_config = json.load(f)

print("[startup] Building slot lookup index (actor/genre/language/day/month)...", flush=True)
slot_index = load_slot_index(os.path.join(DATA_DIR, "slots"))

print(
    f"[startup] Ready in {time.time() - _t0:.1f}s -- "
    f"{len(movie_df)} movies, {len(slot_index)} slot values indexed.",
    flush=True,
)
