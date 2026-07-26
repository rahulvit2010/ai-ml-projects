"""
Streamlit UI for the zodiac/movie chatbot.

This reuses the chatbot/ package (engine.py, slot_matcher.py, actions.py,
data_loader.py) rather than reimplementing the dialogue logic inline --
that package already fixes the three bugs that were breaking multi-turn
follow-up questions in the original app.py:

  1. Intent got re-classified by the ML model on every message (including
     short follow-up answers like "Comedy" or a birth date), which the
     classifier was never trained to handle, so the conversation lost track
     of what it was doing after the first follow-up question.
  2. Slot matching looped over all ~2.17M actor.dat entries on every single
     message using plain Python string ops -- very slow.
  3. Slot values were used as raw (unescaped) regex patterns in re.sub(),
     which crashes on actor names containing regex metacharacters like
     parentheses.
"""

import streamlit as st

from chatbot.engine import Session

st.set_page_config(page_title="Tara - Zodiac & Movie Chatbot", page_icon="\U0001F319")

st.title("Tara \U0001F319\U0001F3AC")
st.caption("Ask me about your zodiac sign or for a movie suggestion.")


@st.cache_resource(show_spinner="Loading model and movie database (first run takes ~10s)...")
def get_engine_loaded():
    # Importing chatbot.engine triggers chatbot.data_loader, which loads the
    # model, dataframes, and slot index exactly once per process. Caching
    # this call means Streamlit reruns (every user interaction) don't repeat
    # that load.
    return True


get_engine_loaded()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "chatbot_session" not in st.session_state:
    st.session_state.chatbot_session = Session()
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": "Hi! I'm Tara. Ask me for your zodiac sign, or tell me what kind of movie you're in the mood for.",
        }
    )

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What can I help you with?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        bot_response = st.session_state.chatbot_session.reply(prompt)
    except Exception as e:
        bot_response = f"Sorry, something went wrong on my end ({e}). Let's start over -- what would you like to know?"
        st.session_state.chatbot_session = Session()

    with st.chat_message("assistant"):
        st.markdown(bot_response)
    st.session_state.messages.append({"role": "assistant", "content": bot_response})

with st.sidebar:
    st.markdown("### Reset conversation")
    if st.button("Start over"):
        st.session_state.chatbot_session = Session()
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Fresh start! Ask me about your zodiac sign or a movie recommendation.",
            }
        ]
        st.rerun()
