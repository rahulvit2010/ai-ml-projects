# Stella — Zodiac & Movie Intent-Classification Chatbot

A conversational chatbot that classifies user intent (zodiac sign lookup vs.
movie suggestion) using a **TF-IDF + Logistic Regression** model, then walks
the user through follow-up questions to collect whatever's needed before
answering.

Originally prototyped in a Colab notebook (rule-based dialogue manager +
scikit-learn intent classifier + Gradio UI). This repo turns that prototype
into a deployable Flask app with a custom web UI, and fixes a couple of
things that don't survive leaving a notebook (see **Notable engineering
decisions** below).

## How it works

```
user message
     │
     ▼
┌─────────────────────┐     ┌──────────────────────────┐
│ slot extraction      │────▶│ intent classifier (ML)   │
│ (dates, actor, genre,│     │ TF-IDF + LogisticReg     │
│  language...)        │     │ falls back to keyword    │
└─────────────────────┘     │ heuristic if unsure       │
     │                       └──────────────────────────┘
     ▼
┌─────────────────────┐
│ have all required    │  no → ask a follow-up question
│ params for this      │
│ intent?               │  yes → run the action (zodiac
└─────────────────────┘        lookup / movie filter)
```

- **`chatbot/context.py`, `chatbot/intent.py`** — the original dialogue
  framework classes (contexts, intents, parameters), unchanged.
- **`chatbot/engine.py`** — the `Session` dialogue manager: tracks
  conversation state, decides when to ask a follow-up question vs. act.
- **`chatbot/slot_matcher.py`** — extracts entities (actor names, genres,
  languages, dates) from free text.
- **`chatbot/actions.py`** — the zodiac-sign lookup and movie-filtering logic.
- **`chatbot/data_loader.py`** — loads the model + datasets once at startup.
- **`app.py`** — Flask API + serves the chat UI (`templates/index.html`).

## Notable engineering decisions (vs. the original notebook)

The original notebook's helper code was written to run once per cell in
Colab, with unlimited memory and no strict latency requirement. Turning it
into a live web service surfaced a few things worth calling out:

1. **`slots/actor.dat` has 2.17 million entries.** The original approach
   substring-matched every one of these against every user message
   (~2.17M string comparisons per turn). `slot_matcher.py` instead builds a
   `value → slot` dictionary once, then walks the user's message and does
   longest-match dictionary lookups — cost scales with the *message* length,
   not the dataset size.
2. **The actor list has ~7k junk entries** (bare initials, numbers, stray
   punctuation from source-data scraping) that caused false-positive matches
   on ordinary words (e.g. the "a" in "suggest a movie" matching an entry
   literally named "A"). These are filtered out at load time.
3. **`movie.csv` (126MB) and the model were being reloaded from disk on
   every action call** in the notebook. They're now loaded once at process
   startup (`data_loader.py`) and reused for every request.
4. **Multi-turn slot filling was fragile**: the original intent-reclassification
   logic re-ran the ML classifier on short follow-up answers ("Comedy", a
   raw date), which the classifier was never trained to handle, causing the
   conversation to fall out of the flow after the first follow-up question.
   The engine now sticks with the current intent while required parameters
   are still being collected.
5. **`year` has no backing slot file** (arbitrary numbers), so a plain
   fallback captures the raw reply for whichever specific question was just
   asked when no slot file can validate it.
6. **The model pickle references a `preprocess_text` function defined in
   Colab's `__main__`.** `chatbot/model_compat.py` re-registers an identical
   function so `joblib.load()` can resolve it outside a notebook.

## Local setup

```bash
cd zodiac-movie-chatbot
python -m venv venv
source venv/Scripts/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Visit `http://localhost:5000`. First load takes ~7-10 seconds while the
model and 126MB movie database load into memory.

## Deployment

This project uses **Git LFS** for the two large data files
(`data/movie.csv`, `data/slots/actor.dat`). Make sure Git LFS is installed
before cloning/pushing:

```bash
git lfs install
```

### Recommended: Hugging Face Spaces (free, generous memory)

The app needs roughly 500-600MB of RAM once the movie database and actor
index are loaded. Most free hosts (Render, Railway) cap free web services
at 512MB RAM, which is too tight. **Hugging Face Spaces' free CPU Basic
tier gives 16GB RAM / 2 CPU cores**, comfortably fitting the full dataset.

1. Create a free account at [huggingface.co](https://huggingface.co) if you
   don't have one.
2. Create a new Space → choose **Docker** as the SDK, CPU Basic hardware
   (free), any name (e.g. `zodiac-movie-chatbot`).
3. Push this repo's code to the Space's git remote:
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/zodiac-movie-chatbot
   git push space main
   ```
   (Hugging Face will prompt for a username + access token — generate one
   under Settings → Access Tokens on huggingface.co.)
4. The Space builds the `Dockerfile` and starts automatically. First build
   takes a few minutes (installing dependencies + uploading the LFS files).
5. Your live demo URL will be:
   `https://huggingface.co/spaces/<your-username>/zodiac-movie-chatbot`

### Alternative: Render / Railway (if you trim the dataset)

If you'd rather use Render or Railway, both read the included `Procfile`
directly. Their free tiers cap RAM at ~512MB, so you'd want to first reduce
`data/movie.csv` to a smaller curated set (a few thousand rows) and prune
`data/slots/actor.dat` to just the actors present in it — happy to help
generate a trimmed version if you go this route.

## Project structure

```
├── app.py                     # Flask app + API routes
├── chatbot/
│   ├── context.py              # dialogue context classes
│   ├── intent.py                # Intent/Parameter classes
│   ├── engine.py                 # Session dialogue manager
│   ├── slot_matcher.py            # fast entity extraction
│   ├── actions.py                  # zodiac + movie action logic
│   ├── data_loader.py               # loads model/data once at startup
│   └── model_compat.py               # pickle compatibility shim
├── data/
│   ├── params/params.cfg        # intent → required params → prompts
│   ├── slots/*.dat               # day/month/genre/language/actor values
│   ├── Zodiac_sign.csv            # zodiac date ranges
│   ├── movie.csv (Git LFS)         # movie database (691k rows)
│   └── training_set.csv            # intent classifier training data
├── model/intent_classifier_model.pkl
├── templates/index.html          # chat UI
├── static/{style.css,script.js}    # chat UI styling + logic
├── requirements.txt
├── Dockerfile                     # for Hugging Face Spaces
├── Procfile                        # for Render/Railway
└── .gitattributes                    # Git LFS config
```

## Showcasing on LinkedIn

A few things that tend to land well for a project like this:

- **Screen-record a short clip** (15-30s) of an actual conversation: ask
  for a zodiac sign, then ask for a movie and watch it ask follow-ups.
  A live back-and-forth reads much better than static screenshots.
- **Lead with the problem, not the stack**: "Built a chatbot that figures
  out what you're asking for and asks smart follow-up questions" lands
  better than "Built a Flask + scikit-learn app."
- **Mention the interesting engineering bit**: going from a 2.17-million-row
  substring scan per message to a dictionary-lookup approach is a concrete,
  relatable "I optimized this" story — much more memorable than "I deployed
  a model."
- Link the live Space URL directly in the post (not just the GitHub repo)
  so people can try it in one click.
