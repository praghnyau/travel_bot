"""Small dependency-free lexical retriever for policy passages."""
from collections import Counter
import re
from .document_processor import PolicyChunk

STOP_WORDS = {"a", "an", "and", "are", "as", "at", "be", "bus", "buses", "by", "can", "carry", "do", "does", "early", "e", "explain", "flight", "flights", "for", "from", "fully", "get", "getting", "happens", "how", "i", "if", "in", "is", "it", "journey", "me", "mean", "means", "my", "of", "on", "or", "please", "should", "the", "this", "that", "to", "train", "trains", "travel", "trip", "trips", "want", "was", "were", "what", "when", "where", "which", "who", "why", "with", "airway", "airways", "rail", "railway", "railways", "ticket", "tickets", "track", "tracking", "tell", "bring", "airline", "airlines", "after"}

TERM_GROUPS = (
    {"book", "books", "booking", "booked", "reserve", "reservation", "reservations"},
    {"cancel", "cancels", "cancellation", "cancellations", "cancelled", "canceled"},
    {"refund", "refunds", "refundable", "reimbursement"},
    {"reschedule", "rescheduling", "rescheduled"},
    {"change", "changes", "changed", "modify", "modified", "amend", "amended"},
    {"transfer", "transferred", "transferable"},
    {"document", "documents", "documentation", "docs"},
    {"requirement", "requirements", "required", "require", "need", "needs"},
    {"step", "steps", "procedure", "process", "guide", "guidance"},
    {"miss", "missed", "no-show", "noshow"},
    {"chart", "charting", "preparation", "prepared"},
    {"policy", "policies", "rule", "rules", "conditions"},
    {"common", "general"},
    {"baggage", "luggage", "bag", "bags", "carryon", "allowance", "allowances"},
    {"checkin", "check-in"},
    {"boarding", "board"},
    {"pickup", "pick-up"},
    {"departure", "depart"},
    {"fare", "fares"},
    {"fee", "fees"},
    {"charge", "charges"},
    {"price", "cost"},
    {"payment", "pay", "paid"},
    {"pnr"},
    {"status"},
    {"waitlist", "waitlisted", "wait-list"},
    {"rac"},
    {"confirmed", "confirmation"},
    {"delay", "delayed"},
    {"disruption", "disrupted", "diversion", "diverted"},
    {"pet", "pets"},
    {"dog", "dogs", "cat", "cats", "animal", "animals"},
    {"medical", "medicine"},
    {"assistance", "wheelchair"},
    {"minor", "infant", "child", "children"},
    {"pregnant", "pregnancy"},
    {"battery", "batteries", "lithium", "powerbank"},
    {"restricted", "dangerous", "prohibited"},
    {"item", "items"},
    {"food"},
    {"smoking", "smoke"},
    {"alcohol"},
    {"conduct", "behavior", "behaviour"},
    {"amenity", "amenities"},
    {"station"},
    {"arrive", "arrival", "reach", "early"},
    {"reporting", "report"},
    {"terminal"},
    {"gate"},
    {"platform"},
    {"passport"},
    {"visa"},
    {"id", "identity"},
)

SUPPORTED_TOPIC_GROUPS = (
    {"book", "books", "booking", "booked", "reserve", "reservation", "reservations"},
    {"cancel", "cancels", "cancellation", "cancellations", "cancelled", "canceled", "refund", "refunds", "refundable", "reschedule", "rescheduling", "change", "changes", "modify", "transfer"},
    {"refund", "refunds", "refundable", "reimbursement"},
    {"document", "documents", "documentation", "docs", "id", "passport", "visa"},
    {"requirement", "requirements", "required", "require", "need", "needs"},
    {"policy", "policies", "rule", "rules", "conditions", "common"},
    {"baggage", "luggage", "bag", "bags", "carryon", "checked", "allowance", "allowances"},
    {"board", "boarding", "checkin", "check", "pickup", "departure", "gate", "station", "arrive", "reach", "reporting", "terminal", "early"},
    {"miss", "missed", "no-show", "noshow"},
    {"chart", "charting", "preparation", "prepared"},
    {"fare", "fee", "fees", "charge", "charges", "price", "cost", "payment", "pay"},
    {"pnr", "status", "waitlist", "waitlisted", "rac", "confirmed", "confirmation"},
    {"delay", "delayed", "disruption", "diverted"},
    {"pet", "pets", "medical", "assistance", "minor", "infant", "child", "pregnant", "pregnancy", "battery", "batteries", "lithium", "restricted", "dangerous", "item", "items", "powerbank"},
    {"food", "smoking", "alcohol", "conduct", "amenity", "amenities"},
    {"step", "steps", "procedure", "process", "guide", "guidance"},
)

SUPPORTED_TOPIC_TERMS = set().union(*SUPPORTED_TOPIC_GROUPS)

SPECIFIC_ENTITY_GROUPS = (
    {"power", "bank", "banks", "powerbank", "battery", "batteries", "lithium"},
    {"pet", "pets", "dog", "dogs", "cat", "cats", "animal", "animals"},
    {"oversized", "bulky", "bicycle", "bicycles"},
    {"pnr"},
    {"rac", "waitlist", "waitlisted"},
    {"passport"},
    {"visa"},
    {"infant", "child", "children", "minor"},
    {"pregnant", "pregnancy"},
)

OUT_OF_SCOPE_TERMS = {
    "joke", "jokes", "poem", "poetry", "recipe", "weather", "forecast", "news",
    "sports", "score", "capital", "translate", "translation", "story", "riddle",
}


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

    def search(self, query: str, limit: int = 5, mode: str | None = None, provider: str | None = None) -> list[PolicyChunk]:
        groups = term_groups(query)
        query_terms = set(terms(query))
        if (
            not groups
            or limit <= 0
            or query_terms & OUT_OF_SCOPE_TERMS
            or not any(topic & query_terms for topic in SUPPORTED_TOPIC_GROUPS)
        ):
            return []
        scored = []
        for i, counts in enumerate(self.index):
            if mode and self.chunks[i].mode != mode:
                continue
            if provider and self.chunks[i].provider != provider:
                continue
            title_terms = set(terms(self.chunks[i].source.replace("-", " ").replace("_", " ").rsplit(".", 1)[0]))
            content_score = sum(min(max((counts[t] for t in group), default=0), 3) for group in groups)
            title_score = 2 * sum(bool(group & title_terms) for group in groups)
            score = content_score + title_score
            # A filename match alone is not evidence that this passage answers the question.
            if content_score:
                scored.append((score, i))
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        if scored:
            minimum_score = scored[0][0] * 0.6
            scored = [item for item in scored if item[0] >= minimum_score]
        specific_terms = query_terms - SUPPORTED_TOPIC_TERMS
        if specific_terms and not any(
            all(term in self.index[i] for term in specific_terms)
            for _, i in scored
        ):
            return []
        return [self.chunks[i] for _, i in scored[:limit]]
