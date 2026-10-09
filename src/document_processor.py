"""Load local travel policy documents and split them into searchable passages."""
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class PolicyChunk:
    text: str
    source: str
    index: int
    mode: str | None = None


def read_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".pdf":
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    return ""


def _is_heading(line: str) -> bool:
    value = line.strip()
    if not value or len(value) > 110:
        return False
    letters = [char for char in value if char.isalpha()]
    return bool(letters) and all(char.isupper() for char in letters) and not value.endswith((".", ";", ","))


def split_text(text: str, source: str, chunk_size: int = 900, overlap: int = 120, mode: str | None = None) -> list[PolicyChunk]:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    if not any(lines):
        return []
    if chunk_size < 1 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Require chunk_size > overlap >= 0.")
    chunks, index = [], 0
    section_heading = ""
    section_lines = []

    def emit_section(heading: str, content_lines: list[str]) -> None:
        nonlocal index
        body = "\n".join(content_lines).strip()
        if not body:
            return
        prefix = f"{heading}\n" if heading else ""
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        current = prefix
        for paragraph in paragraphs:
            if len(paragraph) > chunk_size:
                pieces = re.split(r"(?<=[.!?])\s+|(?<=;)\s+", paragraph)
            else:
                pieces = [paragraph]
            for piece in pieces:
                piece = piece.strip()
                if not piece:
                    continue
                candidate = f"{current}\n{piece}" if current.strip() else piece
                if len(candidate) > chunk_size and current.strip():
                    chunks.append(PolicyChunk(current.strip(), source, index, mode))
                    index += 1
                    tail = current[-overlap:] if overlap else ""
                    if tail and " " in tail:
                        tail = tail[tail.find(" ") + 1:]
                    continuation = f"[continued] {tail}\n" if tail else ""
                    current = f"{prefix}{continuation}{piece}" if prefix else f"{continuation}{piece}"
                else:
                    current = candidate
        if current.strip():
            chunks.append(PolicyChunk(current.strip(), source, index, mode))
            index += 1

    for line in lines:
        if _is_heading(line):
            emit_section(section_heading, section_lines)
            section_heading, section_lines = line, []
        else:
            section_lines.append(line)
    emit_section(section_heading, section_lines)
    return chunks


def load_policies(directory: Path) -> list[PolicyChunk]:
    directory = Path(directory)
    if not directory.exists():
        return []
    chunks = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".txt", ".md", ".pdf"}:
            path_parts = {part.lower() for part in path.relative_to(directory).parts[:-1]}
            stem = path.stem.lower()
            mode = None
            if path_parts & {"air", "airway", "airways", "flight", "flights"} or stem in {"air", "airway", "airways", "flight", "flights"}:
                mode = "airways"
            elif path_parts & {"rail", "railway", "railways", "train", "trains"} or stem in {"rail", "railway", "railways", "train", "trains"}:
                mode = "railways"
            elif path_parts & {"bus", "buses"} or stem in {"bus", "buses"}:
                mode = "bus"
            try:
                chunks.extend(split_text(read_document(path), path.name, mode=mode))
            except (OSError, ValueError):
                continue
    return chunks
