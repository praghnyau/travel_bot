"""Policy-grounded response orchestration."""
import re
from .prompts import SYSTEM_PROMPT
from .policy_retriever import PolicyRetriever, term_groups
from .validators import is_transaction_request, validate_question


def _compact_points(question: str, chunks, limit: int = 5) -> list[tuple[str, str]]:
    """Select matching complete sentences instead of returning full passages."""
    query_groups = term_groups(question)
    candidates = []
    for chunk in chunks:
        for sentence in re.split(r"(?<=[.!?])\s+|\n+|(?<=;)\s+", chunk.text):
            sentence = sentence.strip(" -•\t")
            if len(sentence) < 20:
                continue
            sentence_terms = set(re.findall(r"[a-z0-9]+", sentence.lower()))
            overlap = sum(bool(group & sentence_terms) for group in query_groups)
            if overlap:
                candidates.append((overlap, chunk.source, sentence))
    candidates.sort(key=lambda row: (-row[0], row[1], len(row[2])))
    selected, seen = [], set()
    for _, source, sentence in candidates:
        normalized = sentence.casefold()
        if normalized not in seen:
            selected.append((source, sentence))
            seen.add(normalized)
        if len(selected) >= limit:
            break
    return selected


class TravelPolicyChatbot:
    def __init__(self, retriever: PolicyRetriever, client=None, top_k: int = 5):
        self.retriever, self.client, self.top_k = retriever, client, top_k

    def answer(self, question: str, mode: str | None = None) -> dict:
        question = validate_question(question)
        if is_transaction_request(question):
            return {"answer": "I can provide travel policy information, but I cannot make, cancel, or change bookings. Please use the company travel portal or contact the travel desk.", "sources": []}
        chunks = self.retriever.search(question, self.top_k, mode=mode)
        sources = list(dict.fromkeys(chunk.source for chunk in chunks))
        if not chunks:
            return {"answer": "I couldn't find a relevant policy passage in the documents available here. Please check the company travel portal or contact the travel desk.", "sources": []}
        if self.client:
            try:
                scoped_question = f"Selected travel mode: {mode}. Answer only for this mode.\nEmployee question: {question}" if mode else question
                answer = self.client.generate(SYSTEM_PROMPT, scoped_question, [f"[{c.source}] {c.text}" for c in chunks])
                if answer:
                    return {"answer": answer, "sources": sources}
            except Exception:
                pass
        points = _compact_points(question, chunks)
        if not points:
            return {"answer": "I found related policy text, but couldn't extract clear points for this question. Please check the cited documents or contact the travel desk.", "sources": sources}
        answer = "**Relevant policy points**\n\n" + "\n".join(f"- {sentence} *({source})*" for source, sentence in points)
        return {"answer": answer, "sources": sources}
