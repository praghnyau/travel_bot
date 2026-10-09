"""Streamlit front end for the TripWise AI travel policy assistant."""
from pathlib import Path
import hashlib
import importlib
from urllib.parse import urlparse

from dotenv import load_dotenv
import streamlit as st

load_dotenv()

from config import GEMINI_API_KEY, GEMINI_MODEL, POLICY_DIR, TOP_K
import src.chatbot as chatbot_module
import src.document_processor as document_processor_module
from src.gemini_client import GeminiClient
import src.policy_retriever as policy_retriever_module


MODE_LABELS = {"airways": "Airways", "railways": "Train", "bus": "Bus"}
MODE_KEYS = {label: key for key, label in MODE_LABELS.items()}
TRAVEL_MODES = ("Airways", "Bus", "Train")
AIRLINE_LABELS = {"SpiceJet": "spicejet", "IndiGo": "indigo", "Air India": "air_india"}
BUS_PROVIDER_LABELS = {
    "redBus": "redbus",
    "AbhiBus": "abhibus",
    "MakeMyTrip": "makemytrip",
    "APSRTC Official Portal": "apsrtc",
}
TOPIC_ITEMS = (
    "Ask anything",
    "Booking Process",
    "Cancellations",
    "Refunds",
    "FAQs",
)
QUICK_QUESTIONS = {
    "Ask anything": (
        ("Booking steps", "Explain travel booking steps"),
        ("Cancellation", "What is the cancellation process?"),
        ("Travel documents", "Explain travel documentation requirements"),
        ("Common policies", "What are common travel policies?"),
    ),
    "Booking Process": (
        ("Booking steps", "Explain travel booking steps"),
        ("Travel documents", "Explain travel documentation requirements"),
        ("Before departure", "What should I check before departure?"),
        ("Common policies", "What are common travel policies?"),
    ),
    "Cancellations": (
        ("Cancellation process", "What is the cancellation process?"),
        ("Cancel a booking", "How do cancellation rules work?"),
    ),
    "Refunds": (
        ("Refund process", "How can I check my refund process?"),
        ("Cancellation and refunds", "What is the cancellation process?"),
    ),
    "FAQs": (
        ("Booking steps", "Explain travel booking steps"),
        ("Cancellation", "What is the cancellation process?"),
        ("Travel documents", "Explain travel documentation requirements"),
        ("Common policies", "What are common travel policies?"),
    ),
}


def policy_revision(policy_dir: str) -> str:
    """Fingerprint policy and response code so Streamlit cannot reuse stale answers."""
    digest = hashlib.sha256()
    root = Path(policy_dir)
    paths = [Path(__file__)]
    paths.extend(Path(__file__).parent.joinpath("src", name) for name in (
        "chatbot.py", "document_processor.py", "policy_retriever.py", "prompts.py"
    ))
    if root.exists():
        paths.extend(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in {".txt", ".md", ".pdf"})
    for path in sorted(set(paths), key=lambda item: str(item)):
        try:
            digest.update(str(path).encode("utf-8"))
            digest.update(path.read_bytes())
        except OSError:
            continue
    return digest.hexdigest()


@st.cache_resource(show_spinner="Loading the policy library…")
def build_chatbot(policy_dir: str, api_key: str, model: str, top_k: int, revision: str):
    # Streamlit can rerun the app while retaining imported project modules and
    # cached resources. Reload schema-dependent modules before rebuilding them.
    importlib.reload(document_processor_module)
    importlib.reload(policy_retriever_module)
    importlib.reload(chatbot_module)
    chunks = document_processor_module.load_policies(Path(policy_dir))
    client = GeminiClient(api_key, model) if api_key else None
    chatbot = chatbot_module.TravelPolicyChatbot(
        policy_retriever_module.PolicyRetriever(chunks), client, top_k
    )
    return chatbot, len(chunks)


def render_message(message: dict) -> None:
    role = message["role"]
    avatar = ":material/person:" if role == "user" else ":material/flight_takeoff:"
    with st.chat_message(role, avatar=avatar):
        if role == "assistant":
            mode = MODE_LABELS.get(message.get("mode"), "Travel guide")
            provider_label = message.get("provider_label")
            st.caption(f"{mode} · {provider_label} policy guide" if provider_label else f"{mode} · Policy guide")
        st.markdown(message["content"])
        if role == "assistant" and message.get("sources"):
            st.markdown(render_sources(message["sources"]))


def render_sources(sources: list[str]) -> str:
    links = []
    for source in sources:
        if source.startswith(("https://", "http://")):
            parsed = urlparse(source)
            label = parsed.netloc.removeprefix("www.")
            if parsed.path and parsed.path != "/":
                label += f"/{Path(parsed.path).name}"
            links.append(f"[{label}]({source})")
        else:
            links.append(f"`{source}`")
    return "**Sources:** " + " · ".join(links)


st.set_page_config(
    page_title="TripWise AI | Travel policy guide",
    page_icon=":material/travel_explore:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { --sky: #38BDF8; --sky-deep: #0369A1; --cloud: #F8FAFC; --navy: #0F172A; --muted: #475569; }
    .stApp, [data-testid="stAppViewContainer"] { color: #0F172A !important; background: linear-gradient(145deg, #F8FAFC 0%, #F1F8FE 55%, #EAF7FF 100%) !important; }
    [data-testid="stHeader"] { background: rgba(248,250,252,.96); }
    [data-testid="stSidebar"] { background: linear-gradient(180deg,#EAF7FF 0%,#F8FAFC 82%) !important; border-right: 1px solid #D7EAF6; }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1.25rem; }
    [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li, [data-testid="stMarkdownContainer"] span,
    [data-testid="stWidgetLabel"] p, [data-testid="stCaptionContainer"] p,
    label, .stRadio label, .stSelectbox label { color: #0F172A !important; }
    [data-testid="stCaptionContainer"] p, [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #475569 !important; }
    h1, h2, h3, [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2, [data-testid="stMarkdownContainer"] h3 { color: #0F172A !important; letter-spacing: -.035em; }
    .brand-mark { width: 44px; height: 44px; border-radius: 15px; display: inline-flex; align-items: center; justify-content: center; background: linear-gradient(135deg,#38BDF8,#7DD3FC); color: #0F172A; font-size: 23px; box-shadow: 0 8px 22px rgba(56,189,248,.24); }
    .hero { position: relative; overflow: hidden; padding: 2rem 2.2rem; margin: .5rem 0 1.35rem; border: 1px solid #BAE6FD; border-radius: 26px; background: linear-gradient(118deg,#FFFFFF 8%,#E0F2FE 100%); box-shadow: 0 14px 32px rgba(15,23,42,.07); }
    .hero:after { content: ""; position: absolute; right: -32px; top: -90px; width: 290px; height: 290px; border-radius: 50%; background: radial-gradient(circle,rgba(56,189,248,.22),rgba(56,189,248,0) 70%); }
    .eyebrow { color: #0284C7; font-weight: 700; font-size: .8rem; letter-spacing: .12em; text-transform: uppercase; }
    .hero h1 { color: #0F172A !important; margin: .45rem 0 .35rem; font-size: clamp(2rem,4vw,3.15rem); line-height: 1.08; }
    .hero p { max-width: 650px; margin: 0; color: #334155 !important; font-size: 1.06rem; }
    .trust-pill { display: inline-block; margin-top: 1.15rem; padding: .42rem .75rem; border: 1px solid #BAE6FD; border-radius: 99px; background: #FFFFFF; color: #075985 !important; font-size: .82rem; font-weight: 600; }
    [data-testid="stChatMessage"] { border: 1px solid #D7EAF6; border-radius: 20px; padding: .8rem 1rem; margin: .7rem 0; background: #FFFFFF; box-shadow: 0 7px 24px rgba(15,23,42,.055); color: #0F172A !important; }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"], [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] li { color: #0F172A !important; }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) { background: #EAF7FF; border-color: #BAE6FD; }
    [data-testid="stBottom"] { background: rgba(248,250,252,.97) !important; }
    [data-testid="stChatInput"] { border: 1px solid #BAE6FD !important; border-radius: 18px !important; background: #FFFFFF !important; box-shadow: 0 7px 22px rgba(15,23,42,.09) !important; }
    [data-testid="stChatInput"] > div { background: #FFFFFF !important; border-radius: 17px !important; }
    [data-testid="stChatInput"] textarea { border-radius: 17px !important; color: #0F172A !important; -webkit-text-fill-color: #0F172A !important; caret-color: #0369A1 !important; background: #FFFFFF !important; }
    [data-testid="stChatInput"] textarea::placeholder { color: #64748B !important; -webkit-text-fill-color: #64748B !important; opacity: 1 !important; }
    [data-testid="stChatInput"] button { color: #075985 !important; background: #E0F2FE !important; }
    [data-testid="stSelectbox"] [data-baseweb="select"] > div { background: #FFFFFF !important; border-color: #BAE6FD !important; color: #0F172A !important; }
    [data-testid="stSelectbox"] [data-baseweb="select"] span { color: #0F172A !important; }
    [data-baseweb="popover"] [role="option"] { color: #0F172A !important; background: #FFFFFF !important; }
    [data-baseweb="popover"] [role="option"]:hover { background: #E0F2FE !important; }
    [data-testid="stRadio"] [role="radiogroup"] { gap: .3rem; }
    [data-testid="stRadio"] [role="radiogroup"] > label { padding: .58rem .7rem; margin: 0; border: 1px solid transparent; border-radius: 13px; background: rgba(255,255,255,.55); transition: all .16s ease; }
    [data-testid="stRadio"] [role="radiogroup"] > label:hover { border-color: #BAE6FD; background: #FFFFFF; }
    [data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) { border-color: #7DD3FC; background: #FFFFFF; box-shadow: 0 4px 12px rgba(14,116,175,.09); }
    [data-testid="stRadio"] [role="radiogroup"] > label p { font-weight: 600; }
    .stButton > button { min-height: 3rem; border-radius: 15px; border: 1px solid #D7EAF6; background: #FFFFFF; color: #0F172A !important; font-weight: 600; box-shadow: 0 5px 16px rgba(15,23,42,.045); transition: all .18s ease; }
    .stButton > button p, .stButton > button span { color: #0F172A !important; }
    .stButton > button:hover { border-color: #38BDF8; background: #F0F9FF; color: #075985 !important; box-shadow: 0 7px 18px rgba(56,189,248,.17); transform: translateY(-1px); }
    [data-testid="stMetric"] { border: 1px solid #DDEBF5; border-radius: 17px; background: rgba(255,255,255,.75); padding: .75rem 1rem; }
    [data-testid="stExpander"] { border-color: #DDEBF5; border-radius: 16px; background: rgba(255,255,255,.68); }
    .section-kicker { margin: .25rem 0 .2rem; color: #0369A1 !important; font-size: .78rem; font-weight: 700; text-transform: uppercase; letter-spacing: .11em; }
    .helper-copy { color: #475569 !important; margin-top: -.3rem; }
    [data-theme="dark"] .stApp, [data-theme="dark"] [data-testid="stAppViewContainer"] { background: linear-gradient(145deg,#0F172A 0%,#111E32 58%,#10243A 100%) !important; color: #E2E8F0 !important; }
    [data-theme="dark"] [data-testid="stHeader"] { background: rgba(15,23,42,.96); }
    [data-theme="dark"] [data-testid="stSidebar"] { background: linear-gradient(180deg,#101B30 0%,#0F172A 78%) !important; border-color: #2A3B53; }
    [data-theme="dark"] [data-testid="stMarkdownContainer"], [data-theme="dark"] [data-testid="stMarkdownContainer"] p,
    [data-theme="dark"] [data-testid="stMarkdownContainer"] li, [data-theme="dark"] [data-testid="stCaptionContainer"] p,
    [data-theme="dark"] [data-testid="stWidgetLabel"] p, [data-theme="dark"] label,
    [data-theme="dark"] [data-testid="stChatMessage"] p { color: #E2E8F0 !important; }
    [data-theme="dark"] h1, [data-theme="dark"] h2, [data-theme="dark"] h3,
    [data-theme="dark"] [data-testid="stMarkdownContainer"] h1,
    [data-theme="dark"] [data-testid="stMarkdownContainer"] h2,
    [data-theme="dark"] [data-testid="stMarkdownContainer"] h3 { color: #F8FAFC !important; }
    [data-theme="dark"] [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-theme="dark"] .helper-copy { color: #B6C5D8 !important; }
    [data-theme="dark"] .hero { border-color: #2A4863; background: linear-gradient(118deg,#17243A,#113148); }
    [data-theme="dark"] .hero h1 { color: #F8FAFC !important; }
    [data-theme="dark"] .hero p { color: #D0DEEE !important; }
    [data-theme="dark"] .trust-pill { background: #17243A; border-color: #2A6487; color: #BAE6FD !important; }
    [data-theme="dark"] [data-testid="stChatMessage"] { border-color: #2A3B53; background: #17243A; }
    [data-theme="dark"] [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
    [data-theme="dark"] [data-testid="stChatMessage"] p,
    [data-theme="dark"] [data-testid="stChatMessage"] li { color: #F1F5F9 !important; }
    [data-theme="dark"] [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) { background: #112B40; border-color: #245675; }
    [data-theme="dark"] [data-testid="stBottom"] { background: rgba(15,23,42,.98) !important; }
    [data-theme="dark"] [data-testid="stChatInput"], [data-theme="dark"] [data-testid="stChatInput"] > div,
    [data-theme="dark"] [data-testid="stChatInput"] textarea { background: #17243A !important; border-color: #2A6487 !important; }
    [data-theme="dark"] [data-testid="stChatInput"] textarea { color: #F8FAFC !important; -webkit-text-fill-color: #F8FAFC !important; caret-color: #7DD3FC !important; }
    [data-theme="dark"] [data-testid="stChatInput"] textarea::placeholder { color: #B6C5D8 !important; -webkit-text-fill-color: #B6C5D8 !important; }
    [data-theme="dark"] [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-theme="dark"] [data-testid="stSelectbox"] [data-baseweb="select"] span { background: #17243A !important; color: #F8FAFC !important; }
    [data-theme="dark"] [data-testid="stRadio"] [role="radiogroup"] > label { background: rgba(23,36,58,.75); }
    [data-theme="dark"] [data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) { background: #17243A; border-color: #2A6487; }
    [data-theme="dark"] .stButton > button { border-color: #2A4863; background: #17243A; color: #F1F5F9 !important; }
    [data-theme="dark"] .stButton > button p, [data-theme="dark"] .stButton > button span { color: #F1F5F9 !important; }
    [data-theme="dark"] [data-testid="stMetric"], [data-theme="dark"] [data-testid="stExpander"] { border-color: #2A3B53; background: rgba(23,36,58,.75); }
    @media (max-width: 720px) {
      .hero { padding: 1.45rem 1.25rem; border-radius: 22px; }
      .hero:after { right: -130px; }
      [data-testid="stMainBlockContainer"] { padding-top: 1rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.markdown(
        '<div style="display:flex;gap:12px;align-items:center">'
        '<span class="brand-mark">✈</span><div><b style="font-size:1.14rem;color:#0F172A">TripWise AI</b>'
        '<div style="font-size:.78rem;color:#64748B">Your travel policy companion</div></div></div>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("#### Travel mode")
    mode_label = st.radio(
        "Choose a travel mode",
        TRAVEL_MODES,
        format_func=lambda mode: {
            "Airways": "✈️  Airways",
            "Bus": "🚌  Bus",
            "Train": "🚆  Train",
        }[mode],
        label_visibility="collapsed",
        key="travel_mode",
    )
    mode_key = MODE_KEYS[mode_label]

    provider_label = None
    provider_key = None
    if mode_key == "airways":
        provider_label = st.selectbox(
            "Airline",
            ("Choose airline", *AIRLINE_LABELS.keys()),
            key="airline_provider",
            help="Answers will use only the selected airline's policy library.",
        )
        provider_key = AIRLINE_LABELS.get(provider_label)
    elif mode_key == "bus":
        provider_label = st.selectbox(
            "Bus platform or operator",
            ("Choose platform or operator", *BUS_PROVIDER_LABELS.keys()),
            key="bus_provider",
            help="Answers will use only the selected platform/operator's policy library.",
        )
        provider_key = BUS_PROVIDER_LABELS.get(provider_label)

    # Keep chat history scoped to the selected mode and airline.
    active_scope = (mode_key, provider_key)
    if st.session_state.get("active_policy_scope") != active_scope:
        st.session_state.messages = []
        st.session_state.active_policy_scope = active_scope

    st.markdown("#### Topics")
    nav_item = st.selectbox("Choose a topic", TOPIC_ITEMS, key="topic_navigation", label_visibility="collapsed")

    st.divider()
    bot, chunk_count = build_chatbot(
        str(POLICY_DIR), GEMINI_API_KEY, GEMINI_MODEL, TOP_K,
        policy_revision(str(POLICY_DIR)),
    )
    st.markdown("#### Policy library")
    scoped_count = 0 if mode_key == "airways" else chunk_count
    if provider_key:
        scoped_count = sum(getattr(chunk, "provider", None) == provider_key for chunk in bot.retriever.chunks)
    scope_label = provider_label if provider_key else mode_label.lower()
    st.caption(f"{scoped_count} searchable passages · Answers scoped to {scope_label}")
    if st.button("New conversation", icon=":material/add_comment:", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    with st.expander("About this guide"):
        st.write(
            "TripWise explains travel steps and policy from the selected mode and, for Airways, the selected airline. "
            "It does not book, cancel, or check live ticket and refund status."
        )

hero_title = {
    "Ask anything": "Travel, made clearer.",
    "Booking Process": "Plan each step with confidence.",
    "Cancellations": "Understand your options before you act.",
    "Refunds": "Know what to check about a refund.",
    "FAQs": "Quick answers for smoother travel.",
}[nav_item]
if mode_key in {"airways", "bus"} and not provider_key:
    category = "airline" if mode_key == "airways" else "bus platform or operator"
    hero_copy = f"Choose a {category} to see its own booking, baggage, and cancellation guidance."
elif provider_label:
    hero_copy = f"Clear, practical {provider_label} guidance, grounded only in this provider's policy library."
else:
    hero_copy = f"Clear, practical {mode_label.lower()} guidance, grounded in the selected mode's policy library and easy to follow."

st.markdown(
    f'<section class="hero"><div class="eyebrow">TripWise AI · Travel booking process & policy explainer</div>'
    f'<h1>{hero_title}</h1><p>{hero_copy}</p>'
    '<span class="trust-pill">✦&nbsp; Provider-scoped guidance &nbsp;·&nbsp; Clear steps &nbsp;·&nbsp; Sources below</span></section>',
    unsafe_allow_html=True,
)

if mode_key in {"airways", "bus"} and not provider_key:
    choices = "SpiceJet, IndiGo, or Air India" if mode_key == "airways" else "redBus, AbhiBus, MakeMyTrip, or APSRTC Official Portal"
    label = "airline-specific" if mode_key == "airways" else "platform-specific"
    st.info(f"Choose {choices} in the sidebar to start a {label} conversation.", icon=":material/flight:")
elif not chunk_count:
    st.info("The policy library is empty. Add approved policy documents to continue.", icon=":material/library_books:")
else:
    questions = QUICK_QUESTIONS.get(nav_item, QUICK_QUESTIONS["FAQs"])
    if not st.session_state.messages:
        st.markdown('<div class="section-kicker">Quick actions</div>', unsafe_allow_html=True)
        st.markdown('<div class="helper-copy">Choose a topic or ask in your own words.</div>', unsafe_allow_html=True)
        quick_prompt = None
        cols = st.columns(min(2, len(questions)))
        for index, (label, question) in enumerate(questions):
            with cols[index % len(cols)]:
                if st.button(label, key=f"quick_{nav_item}_{index}", icon=":material/arrow_forward:", use_container_width=True):
                    quick_prompt = question

    for message in st.session_state.messages:
        render_message(message)

    typed_prompt = st.chat_input(
        f"Ask about {(provider_label or mode_label).lower()} {nav_item.lower()}…",
        max_chars=1200,
    )
    prompt = typed_prompt or (quick_prompt if not st.session_state.messages else None)

    if prompt:
        user_message = {"role": "user", "content": prompt, "mode": mode_key}
        st.session_state.messages.append(user_message)
        render_message(user_message)

        with st.chat_message("assistant", avatar=":material/flight_takeoff:"):
            search_label = provider_label or mode_label
            with st.status(f"Finding {search_label} guidance", expanded=False) as status:
                result = bot.answer(prompt, mode=mode_key, provider=provider_key)
                status.update(label="Answer ready", state="complete")
            st.caption(f"{mode_label} · {provider_label} policy guide" if provider_label else f"{mode_label} · Policy guide")
            st.markdown(result["answer"])
            if result["sources"]:
                st.markdown(render_sources(result["sources"]))

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": result["answer"],
                "sources": result["sources"],
                "mode": mode_key,
                "provider_label": provider_label,
            }
        )

st.markdown(
    '<div style="text-align:center;color:#94A3B8;font-size:.76rem;padding:1.6rem 0 .5rem">'
    'TripWise AI · Guidance only · Always confirm current terms with your official provider</div>',
    unsafe_allow_html=True,
)
