"""Policy-grounded response orchestration."""
import re
from pathlib import Path
from config import POLICY_DIR
from .prompts import SYSTEM_PROMPT
from .policy_retriever import PolicyRetriever, SPECIFIC_ENTITY_GROUPS, term_groups, terms
from .validators import is_transaction_request, validate_question


ANSWER_FILES = {
    "bus": "bus/00_bus_policy_answers.txt",
    "railways": "railways/00_railway_policy_answers.txt",
}
AIRLINE_ANSWER_FILES = {
    "spicejet": "airways/spicejet/00_spicejet_policy_answers.txt",
    "indigo": "airways/indigo/00_indigo_policy_answers.txt",
    "air_india": "airways/air_india/00_air_india_policy_answers.txt",
}
BUS_PROVIDER_ANSWER_FILES = {
    "redbus": "bus/redbus/00_redbus_policy_answers.txt",
    "abhibus": "bus/abhibus/00_abhibus_policy_answers.txt",
    "makemytrip": "bus/makemytrip/00_makemytrip_policy_answers.txt",
    "apsrtc": "bus/apsrtc/00_apsrtc_policy_answers.txt",
}
ANSWER_HEADINGS = {
    "booking": "TRAVEL BOOKING STEPS",
    "cancellation": "CANCELLATION PROCESS",
    "documents": "TRAVEL DOCUMENTATION REQUIREMENTS",
    "policies": "COMMON",
}
ANSWER_INTENT_TERMS = {
    "booking": {"book", "books", "booking", "booked", "reserve", "reservation", "reservations", "step", "steps", "procedure", "process", "guide", "guidance", "spicejet", "indigo", "air", "india"},
    "cancellation": {"cancel", "cancels", "cancellation", "cancellations", "cancelled", "canceled", "refund", "refunds", "refundable", "reimbursement", "step", "steps", "procedure", "process", "spicejet", "indigo", "air", "india"},
    "documents": {"document", "documents", "documentation", "docs", "requirement", "requirements", "required", "require", "need", "needs", "spicejet", "indigo", "air", "india"},
    "policies": {"common", "general", "policy", "policies", "rule", "rules", "conditions", "spicejet", "indigo", "air", "india"},
}


def _not_in_database(mode: str | None, provider: str | None = None) -> dict:
    mode_name = {"airways": "Airways", "bus": "Bus", "railways": "Train"}.get(mode, "selected travel mode")
    if mode == "airways" and provider:
        mode_name = {"spicejet": "SpiceJet", "indigo": "IndiGo", "air_india": "Air India"}.get(provider, mode_name)
    elif mode == "bus" and provider:
        mode_name = {"redbus": "redBus", "abhibus": "AbhiBus", "makemytrip": "MakeMyTrip", "apsrtc": "APSRTC"}.get(provider, mode_name)
    return {
        "answer": (
            f"I can answer only questions covered by the {mode_name} policy database. "
            "This question isn't covered there. Try asking about booking, cancellations or refunds, "
            "travel documents, baggage, boarding, or listed travel policies."
        ),
        "sources": [],
    }


def _question_intent(question: str) -> str | None:
    words = set(terms(question))
    if words & {"cancel", "cancellation", "cancelled", "canceled", "refund", "refunds"}:
        intent = "cancellation"
    elif words & {"document", "documents", "documentation", "docs", "requirement", "requirements"}:
        intent = "documents"
    elif words & {"book", "booking", "reserve", "reservation", "steps", "step"}:
        intent = "booking"
    elif "common" in words and words & {"policy", "policies", "rule", "rules"}:
        intent = "policies"
    else:
        return None
    return intent if words <= ANSWER_INTENT_TERMS[intent] else None


def _format_step_answer(answer: str) -> str:
    """Make step headings and their explanatory lines render distinctly in Streamlit."""
    formatted = []
    for line in answer.strip().splitlines():
        value = line.rstrip()
        if not value:
            formatted.append("")
        elif re.match(r"^Step\s+\d+:", value, re.I):
            formatted.append(f"**{value}**  ")
        else:
            formatted.append(f"{value}  ")
    return "\n".join(formatted).strip()


def _curated_answer(question: str, mode: str | None, provider: str | None = None) -> dict | None:
    """Return concise, reviewed steps for the four common questions when available."""
    if mode == "airways":
        relative_path = AIRLINE_ANSWER_FILES.get(provider)
    elif mode == "bus":
        relative_path = BUS_PROVIDER_ANSWER_FILES.get(provider)
    else:
        relative_path = ANSWER_FILES.get(mode)
    intent = _question_intent(question)
    if not relative_path or not intent:
        return None

    path = Path(POLICY_DIR) / relative_path
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    target_heading = ANSWER_HEADINGS[intent]
    active = False
    answer_lines, source_urls = [], []
    for line in lines:
        value = line.strip()
        if not active:
            if value.upper().startswith(target_heading):
                active = True
            continue
        if value.upper().startswith(("SOURCE:", "SOURCES:")):
            source_urls.extend(re.findall(r"https?://[^\s;]+", value))
            continue
        if value and value == value.upper() and re.search(r"[A-Z]", value):
            break
        if not value:
            if answer_lines and answer_lines[-1]:
                answer_lines.append("")
            continue
        item = re.match(r"^(?:Step\s+)?(\d+)[.:]\s+(.+)$", value, re.I)
        if item:
            answer_lines.append(f"Step {item.group(1)}: {item.group(2).strip()}")
        else:
            answer_lines.append(value)

    if not answer_lines:
        return None
    answer = _format_step_answer("\n".join(answer_lines))
    return {"answer": answer, "sources": list(dict.fromkeys(source_urls))}


def _compact_points(question: str, chunks, limit: int = 5) -> list[tuple[str, str]]:
    """Select matching complete sentences instead of returning full passages."""
    query_groups = term_groups(question)
    candidates = []
    query_terms = set(re.findall(r"[a-z0-9]+", question.lower()))
    specific_groups = [group for group in SPECIFIC_ENTITY_GROUPS if group & query_terms]
    for chunk in chunks:
        first_line = chunk.text.splitlines()[0].strip() if chunk.text.splitlines() else ""
        section_terms = set(terms(first_line)) if first_line.isupper() else set()
        # Keep numbered list markers (for example, "1. Do this") attached to their step.
        # Keep semicolon-connected actions together; splitting there creates
        # fragments such as "choose change if available" without their context.
        for sentence in re.split(r"(?<!\d)(?<=[.!?])\s+|\n+", chunk.text):
            sentence = sentence.strip(" -•\t")
            if len(sentence) < 20:
                continue
            if "[continued]" in sentence or sentence.isupper():
                continue
            if sentence.lower().startswith(("q:", "a:", "source:", "sources:")):
                continue
            sentence_terms = set(re.findall(r"[a-z0-9]+", sentence.lower()))
            if specific_groups and not any(group & sentence_terms for group in specific_groups):
                continue
            overlap = sum(bool(group & (sentence_terms | section_terms)) for group in query_groups)
            if not overlap:
                continue
            direct_overlap = len(query_terms & sentence_terms)
            candidates.append((overlap, direct_overlap, chunk.source, sentence))
    candidates.sort(key=lambda row: (-row[0], -row[1], len(row[3]), row[2]))
    selected, seen = [], []
    for _, _, source, sentence in candidates:
        normalized = set(re.findall(r"[a-z0-9]+", sentence.casefold()))
        # Overlapping chunks repeat the same source sentence with slight
        # punctuation differences. Suppress near duplicates, not just exact ones.
        if normalized and any(
            len(normalized & prior) / max(1, len(normalized | prior)) >= 0.78
            for prior in seen
        ):
            continue
        selected.append((source, sentence))
        seen.append(normalized)
        if len(selected) >= limit:
            break
    return selected


class TravelPolicyChatbot:
    def __init__(self, retriever: PolicyRetriever, client=None, top_k: int = 5):
        self.retriever, self.client, self.top_k = retriever, client, top_k

    def answer(self, question: str, mode: str | None = None, provider: str | None = None) -> dict:
        question = validate_question(question)
        if mode == "airways" and not provider:
            return {"answer": "Choose SpiceJet, IndiGo, or Air India first so I can use only that airline's policy database.", "sources": []}
        if mode == "airways" and provider not in AIRLINE_ANSWER_FILES:
            return {"answer": "That airline is not in the current policy library. Choose SpiceJet, IndiGo, or Air India.", "sources": []}
        if mode == "bus" and not provider:
            return {"answer": "Choose redBus, AbhiBus, MakeMyTrip, or APSRTC Official Portal first so I can use only that platform's policy database.", "sources": []}
        if mode == "bus" and provider not in BUS_PROVIDER_ANSWER_FILES:
            return {"answer": "That bus platform is not in the current policy library. Choose redBus, AbhiBus, MakeMyTrip, or APSRTC Official Portal.", "sources": []}
        if mode not in ANSWER_FILES and mode not in {"airways", "bus"}:
            return {
                "answer": "Choose Airways, Bus, or Train first so I can search only that mode's policy database.",
                "sources": [],
            }
        if is_transaction_request(question):
            return _not_in_database(mode, provider)
        intent = _question_intent(question)
        if intent:
            curated = _curated_answer(question, mode, provider)
            # Never answer a canonical question with loosely matched fragments
            # if its reviewed mode/provider answer could not be loaded.
            return curated if curated else _not_in_database(mode, provider)
        chunks = self.retriever.search(question, self.top_k, mode=mode, provider=provider)
        sources = list(dict.fromkeys(chunk.source for chunk in chunks))
        if not chunks:
            return _not_in_database(mode, provider)
        if self.client:
            try:
                scope = f"Selected travel mode: {mode}."
                if provider:
                    provider_kind = "airline" if mode == "airways" else "bus platform/operator"
                    scope += f" Selected {provider_kind}: {provider}. Answer only using this provider's policies."
                scoped_question = f"{scope}\nEmployee question: {question}" if mode else question
                answer = self.client.generate(SYSTEM_PROMPT, scoped_question, [f"[{c.source}] {c.text}" for c in chunks])
                if answer:
                    if answer.strip().upper().strip(" .!\n") == "NOT_IN_DATABASE":
                        return _not_in_database(mode, provider)
                    return {"answer": _format_step_answer(answer), "sources": sources}
            except Exception:
                pass
        points = _compact_points(question, chunks)
        if not points:
            return _not_in_database(mode, provider)
        answer = "\n\n".join(f"Step {index}: {sentence}" for index, (_, sentence) in enumerate(points, start=1))
        answer = _format_step_answer(answer)
        used_sources = list(dict.fromkeys(source for source, _ in points))
        return {"answer": answer, "sources": used_sources}
