"""Streamlit front end for the travel policy assistant."""
from pathlib import Path

from dotenv import load_dotenv
import streamlit as st

load_dotenv()

from config import GEMINI_API_KEY, GEMINI_MODEL, POLICY_DIR, TOP_K
from src.chatbot import TravelPolicyChatbot
from src.document_processor import load_policies
from src.gemini_client import GeminiClient
from src.policy_retriever import PolicyRetriever


MODE_LABELS = {
    "airways": "Airways",
    "railways": "Railways",
    "bus": "Bus",
}
QUICK_QUESTIONS = (
    ("Booking steps", "Explain travel booking steps"),
    ("Cancellation", "What is the cancellation process?"),
    ("Travel documents", "Explain travel documentation requirements"),
    ("Common policies", "What are common travel policies?"),
)


@st.cache_resource(show_spinner="Loading the policy library…")
def build_chatbot(policy_dir: str, api_key: str, model: str, top_k: int):
    chunks = load_policies(Path(policy_dir))
    client = GeminiClient(api_key, model) if api_key else None
    return TravelPolicyChatbot(PolicyRetriever(chunks), client, top_k), len(chunks)


def render_message(message: dict) -> None:
    role = message["role"]
    avatar = ":material/person:" if role == "user" else ":material/support_agent:"
    with st.chat_message(role, avatar=avatar):
        st.markdown(message["content"])
        if role == "assistant":
            mode = MODE_LABELS.get(message.get("mode"), "Travel policy")
            st.caption(mode)
            sources = message.get("sources", [])
            if sources:
                with st.expander(f"Sources · {len(sources)}"):
                    for source in sources:
                        st.markdown(f"- `{source}`")


st.set_page_config(
    page_title="Travel policy assistant",
    page_icon=":material/luggage:",
    layout="centered",
    initial_sidebar_state="expanded",
)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.markdown("### :material/luggage: Travel desk")
    st.caption("Policy guidance for work trips")
    mode_label = st.selectbox(
        "Choose a travel mode",
        options=list(MODE_LABELS.values()),
        key="travel_mode",
    )
    mode_key = mode_label.lower()

    if st.button("Start a new conversation", icon=":material/add_comment:"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.markdown("#### Your policy library")
    bot, chunk_count = build_chatbot(str(POLICY_DIR), GEMINI_API_KEY, GEMINI_MODEL, TOP_K)
    if chunk_count:
        st.success(f"{chunk_count} policy passages ready", icon=":material/library_books:")
    else:
        st.warning("No policy documents found. Add files to the Airways, Railways, or Bus folder.")

    if GEMINI_API_KEY:
        st.caption("Answer style · concise, policy-grounded points")
    else:
        st.caption("Offline mode · matching policy excerpts, summarized as points")

    with st.expander("What can I ask?"):
        st.markdown(
            "Ask about booking, cancellations, refunds, travel documents, baggage, "
            "or common rules for the selected mode."
        )
    with st.expander("Important"):
        st.markdown(
            "This assistant explains policy only. It cannot book or change travel, "
            "and it does not check live availability or booking status. Confirm "
            "specific rules with your company or the official provider."
        )

st.title("Travel, made clearer")
st.markdown(
    "A simple guide to the rules and steps behind your work trip. "
    "Choose a mode in the sidebar, then ask away."
)
st.caption(":material/shield_lock: Information only · No booking or live ticket access")

if not chunk_count:
    st.info(
        "The policy library is empty. Add approved `.txt`, `.md`, or text-based `.pdf` "
        "files under `data/sample_policies/airways`, `railways`, or `bus` to get started."
    )

if not GEMINI_API_KEY:
    st.caption("Answers use retrieved passages directly because Gemini is not configured.")

if not st.session_state.messages:
    with st.container(border=True):
        st.subheader(f"Ask about {mode_label.lower()}")
        st.write("Start with a common question, or type your own below.")
        left, right = st.columns(2)
        quick_prompt = None
        for index, (label, question) in enumerate(QUICK_QUESTIONS):
            column = left if index % 2 == 0 else right
            if column.button(label, key=f"quick_{index}", icon=":material/arrow_forward:"):
                quick_prompt = question

for message in st.session_state.messages:
    render_message(message)

typed_prompt = st.chat_input(
    f"Ask about {mode_label.lower()} travel policies…",
    max_chars=1200,
)
prompt = typed_prompt
if not st.session_state.messages:
    prompt = prompt or quick_prompt

if prompt:
    user_message = {"role": "user", "content": prompt, "mode": mode_key}
    st.session_state.messages.append(user_message)
    render_message(user_message)

    with st.chat_message("assistant", avatar=":material/support_agent:"):
        with st.status(f"Checking {mode_label.lower()} guidance", expanded=False) as status:
            result = bot.answer(prompt, mode=mode_key)
            status.update(label="Answer ready", state="complete")
        st.markdown(result["answer"])
        if result["sources"]:
            with st.expander(f"Sources · {len(result['sources'])}"):
                for source in result["sources"]:
                    st.markdown(f"- `{source}`")
        st.caption(mode_label)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "sources": result["sources"],
            "mode": mode_key,
        }
    )
