# Tara — Zodiac & Movie Intent-Classification Chatbot

A conversational chatbot that classifies user intent (zodiac sign lookup vs.
movie suggestion) using a **TF-IDF + Logistic Regression** model, then walks
the user through follow-up questions to collect whatever's needed before
answering.

Originally prototyped in a Colab notebook (rule-based dialogue manager +
scikit-learn intent classifier + Gradio UI). This repo turns that prototype
into deployable apps — both a Flask app and a Streamlit app share the same
dialogue engine — and fixes a number of things that don't survive leaving a
notebook (see **Notable engineering decisions** below).

Live demo: **[add your Streamlit app URL here]**

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
- **`chatbot/model_compat.py`** — home of the `preprocess_text` function used
  by the trained model's pipeline.
- **`app.py`** — Flask API + serves the chat UI (`templates/index.html`).
- **`streamlit_app.py`** — Streamlit chat UI, reusing the same `chatbot/`
  engine. **This is the version currently deployed** (Streamlit Community
  Cloud, see **Deployment** below).

## Notable engineering decisions (vs. the original notebook/prototype)

1. **`slots/actor.dat` has 2.17 million entries.** The original approach
   substring-matched every one of these against every user message
   (~2.17M string comparisons per turn). `slot_matcher.py` instead builds a
   `value → slot` dictionary once, then walks the user's message and does
   longest-match dictionary lookups — cost scales with the *message* length,
   not the dataset size.
2. **The actor list has junk entries** that caused false-positive matches on
   ordinary words — e.g. bare initials/numbers matching things like the "a"
   in "suggest a movie", and common English words (`"Good"`, `"Nice"`,
   `"Zodiac"`) that are scraping artifacts, not real actor names. These are
   filtered out at load time via a minimum length, an alphabetic check, and
   a small blocklist (`COMMON_WORDS` in `slot_matcher.py`) — extend that set
   if you spot another false positive.
3. **Curated slot files must win collisions over the noisy actor list.**
   `actor.dat` also contains junk entries that literally match genre words
   (e.g. `"Drama"`, `"Romance"` appear in there too), and `language.dat`
   contains all 178 ISO 639-1 two-letter codes (e.g. `"my"` = Burmese),
   which collide with ordinary English words. Small, human-curated files
   (day/month/genre/language) are loaded before `actor.dat` so they always
   claim a colliding value first.
4. **`movie.csv` (126MB) and the model were being reloaded from disk on
   every action call** in the notebook. They're now loaded once at process
   startup (`data_loader.py`) and reused for every request.
5. **Multi-turn slot filling was fragile**: the original intent-reclassification
   logic re-ran the ML classifier on short follow-up answers ("Comedy", a
   raw date), which the classifier was never trained to handle, causing the
   conversation to fall out of the flow after the first follow-up question.
   The engine now sticks with the current intent while required parameters
   are still being collected.
6. **`year` has no backing slot file** (arbitrary numbers), so a plain
   fallback captures the raw reply for whichever specific question was just
   asked when no slot file can validate it.
7. **The model pickle originally referenced a `preprocess_text` function
   defined in Colab's `__main__`.** Patching `sys.modules["__main__"]` at
   runtime worked when running `python app.py` directly, but broke under
   Streamlit Cloud, which executes the app through its own internal runner
   where `sys.modules["__main__"]` isn't reliably the same object. Fixed by
   re-pickling the model so its `FunctionTransformer` step references
   `chatbot.model_compat.preprocess_text` directly — a real, always-
   importable location, regardless of launcher.

## Local setup

```bash
cd zodiac-movie-chatbot
python -m venv venv
source venv/Scripts/activate       # Windows Git Bash: source venv/Scripts/activate
                                    # Windows PowerShell/cmd: venv\Scripts\activate
                                    # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt

python app.py                      # Flask version -> http://localhost:5000
# or
streamlit run streamlit_app.py     # Streamlit version -> opens automatically
```

First load takes ~7-10 seconds while the model and 126MB movie database
load into memory.

## Deployment

This project uses **Git LFS** for the two large data files
(`data/movie.csv`, `data/slots/actor.dat`). Make sure Git LFS is installed
before cloning/pushing:

```bash
git lfs install
```

### Currently deployed on: Streamlit Community Cloud (free)

1. Push this repo to GitHub (LFS files included automatically on push).
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with
   GitHub, click **Create app**.
3. Repository: this repo. Branch: `main`. **Main file path:
   `zodiac-movie-chatbot/streamlit_app.py`** if deployed from a monorepo, or
   `streamlit_app.py` if this is the repo root.
4. Deploy. Streamlit Cloud clones the repo (Git LFS "just works" per their
   docs), installs `requirements.txt`, and starts the app.

Notes specific to this setup:
- **`runtime.txt`** pins Python to `3.11` for the deployment — newer
  Python versions (3.13+) may not yet have prebuilt wheels for `pandas`/
  `scikit-learn`, which can make the build hang trying to compile from
  source.
- **`.streamlit/config.toml`** locks the app to a light theme regardless of
  a visitor's system dark-mode setting.
- **Git LFS bandwidth**: GitHub's free tier includes 1GB/month of LFS
  bandwidth. Each full clone/redeploy pulls ~155MB (`movie.csv` +
  `actor.dat`), so avoid unnecessary reboots/redeploys — batch code changes
  into fewer pushes if you're iterating quickly.
- The app needs roughly 500-600MB of RAM once the movie database and actor
  index are loaded, comfortably under Streamlit Community Cloud's free 1GB
  limit.

### Alternative: the Flask app + Docker

`app.py` + `Dockerfile` are also included if you'd rather deploy the Flask
version somewhere that runs containers. Note that Hugging Face Spaces now
requires a paid PRO plan to create Docker/Gradio Spaces (only static
Spaces are free), and Render/Railway's free tiers cap RAM at ~512MB — too
tight for the full dataset unless you trim `data/movie.csv` down to a
smaller curated set first (happy to help generate one if you go this
route).

## Project structure

```
├── app.py                        # Flask app + API routes
├── streamlit_app.py                # Streamlit app (currently deployed version)
├── runtime.txt                       # pins Python 3.11 for Streamlit Cloud
├── .streamlit/config.toml              # locks light theme
├── chatbot/
│   ├── context.py                        # dialogue context classes
│   ├── intent.py                           # Intent/Parameter classes
│   ├── engine.py                             # Session dialogue manager
│   ├── slot_matcher.py                         # fast entity extraction
│   ├── actions.py                                # zodiac + movie action logic
│   ├── data_loader.py                              # loads model/data once at startup
│   └── model_compat.py                               # preprocess_text function
├── data/
│   ├── params/params.cfg          # intent → required params → prompts
│   ├── slots/*.dat                  # day/month/genre/language/actor values
│   ├── Zodiac_sign.csv                # zodiac date ranges
│   ├── movie.csv (Git LFS)              # movie database (691k rows)
│   └── training_set.csv                   # intent classifier training data
├── model/intent_classifier_model.pkl
├── templates/index.html            # Flask chat UI
├── static/{style.css,script.js}      # Flask chat UI styling + logic
├── requirements.txt
├── Dockerfile                        # for Docker-based hosts
├── Procfile                            # for Render/Railway
└── .gitattributes                        # Git LFS config
```
