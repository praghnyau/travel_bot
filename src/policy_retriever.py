"""Small dependency-free lexical retriever for policy passages."""
from collections import Counter
import re
from .document_processor import PolicyChunk

STOP_WORDS = {"a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "explain", "for", "from", "how", "i", "if", "in", "is", "it", "me", "my", "of", "on", "or", "the", "to", "what", "when", "which", "with"}

TERM_GROUPS = (
    {"book", "books", "booking", "booked", "reserve", "reservation", "reservations"},
    {"cancel", "cancels", "cancellation", "cancellations", "cancelled", "canceled"},
    {"document", "documents", "documentation", "docs", "id", "passport", "visa"},
    {"requirement", "requirements", "required", "require", "need", "needs"},
    {"step", "steps", "procedure", "process", "guide", "guidance"},
    {"policy", "policies", "rule", "rules", "conditions"},
    {"refund", "refunds", "refundable", "reimbursement"},
)


def terms(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP_WORDS]


def term_groups(query: str) -> list[set[str]]:
    """Normalize common question wording into concepts used by the knowledge files."""
    groups = []
    for term in terms(query):
        synonyms = next((group for group in TERM_GROUPS if term in group), {term})
        if synonyms not in groups:
            groups.append(synonyms)
    return groups


class PolicyRetriever:
    def __init__(self, chunks: list[PolicyChunk]):
        self.chunks = chunks
        self.index = [Counter(terms(c.text)) for c in chunks]

    def search(self, query: str, limit: int = 5, mode: str | None = None) -> list[PolicyChunk]:
        groups = term_groups(query)
        if not groups or limit <= 0:
            return []
        scored = []
        for i, counts in enumerate(self.index):
            if mode and self.chunks[i].mode != mode:
                continue
            title_terms = set(terms(self.chunks[i].source.replace("-", " ").replace("_", " ").rsplit(".", 1)[0]))
            score = sum(min(max((counts[t] for t in group), default=0), 3) for group in groups)
            score += 4 * sum(bool(group & title_terms) for group in groups)
            if score:
                scored.append((score, i))
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        if scored:
            minimum_score = scored[0][0] * 0.5
            scored = [item for item in scored if item[0] >= minimum_score]
        return [self.chunks[i] for _, i in scored[:limit]]
