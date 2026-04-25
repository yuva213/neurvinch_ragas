from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import fitz

from neurvinch.models import DocumentChunk, SourceMetadata, StructuralNode


@dataclass
class ParsedSection:
    title: str
    level: int
    content: str
    page: int | None = None


class StructuralIndexer:
    """Builds a hierarchical, metadata-rich index from markdown and PDF sources."""

    def __init__(self, kb_path: Path) -> None:
        self.kb_path = kb_path

    def index(self) -> tuple[list[StructuralNode], list[DocumentChunk]]:
        nodes: list[StructuralNode] = []
        chunks: list[DocumentChunk] = []

        all_files = [p for p in self.kb_path.rglob("*") if p.is_file() and p.suffix.lower() in {".md", ".pdf", ".txt"}]
        all_files.sort()

        for file_path in all_files:
            doc_nodes, doc_chunks = self._index_file(file_path)
            nodes.extend(doc_nodes)
            chunks.extend(doc_chunks)

        return nodes, chunks

    def _index_file(self, file_path: Path) -> tuple[list[StructuralNode], list[DocumentChunk]]:
        if file_path.suffix.lower() == ".md":
            sections = self._parse_markdown(file_path)
        elif file_path.suffix.lower() == ".pdf":
            sections = self._parse_pdf(file_path)
        else:
            sections = self._parse_text(file_path)

        return self._sections_to_models(file_path, sections)

    def _parse_markdown(self, file_path: Path) -> list[ParsedSection]:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()

        sections: list[ParsedSection] = []
        heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")

        current_title = "Document Summary"
        current_level = 1
        current_lines: list[str] = []

        for line in lines:
            match = heading_pattern.match(line.strip())
            if match:
                sections.append(
                    ParsedSection(
                        title=current_title,
                        level=current_level,
                        content="\n".join(current_lines).strip(),
                    )
                )
                current_level = len(match.group(1))
                current_title = match.group(2).strip()
                current_lines = []
                continue
            current_lines.append(line)

        sections.append(
            ParsedSection(
                title=current_title,
                level=current_level,
                content="\n".join(current_lines).strip(),
            )
        )

        return [s for s in sections if s.content]

    def _parse_text(self, file_path: Path) -> list[ParsedSection]:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        return [ParsedSection(title=file_path.stem, level=1, content=text)]

    def _parse_pdf(self, file_path: Path) -> list[ParsedSection]:
        sections: list[ParsedSection] = []
        pdf = fitz.open(file_path)

        for page_idx, page in enumerate(pdf):
            text = page.get_text("text").strip()
            if not text:
                continue
            title = f"Page {page_idx + 1}"
            first_line = text.splitlines()[0].strip()
            if 3 <= len(first_line) <= 120:
                title = first_line[:80]
            sections.append(ParsedSection(title=title, level=2, content=text, page=page_idx + 1))

        pdf.close()
        return sections

    def _sections_to_models(
        self,
        file_path: Path,
        sections: list[ParsedSection],
    ) -> tuple[list[StructuralNode], list[DocumentChunk]]:
        nodes: list[StructuralNode] = []
        chunks: list[DocumentChunk] = []

        parent_stack: list[tuple[int, str]] = []
        version = self._extract_version(file_path.name)

        for section_idx, section in enumerate(sections):
            node_id = f"{file_path.stem}-node-{section_idx}"

            while parent_stack and parent_stack[-1][0] >= section.level:
                parent_stack.pop()

            parent_id = parent_stack[-1][1] if parent_stack else None
            parent_stack.append((section.level, node_id))

            nodes.append(
                StructuralNode(
                    id=node_id,
                    title=section.title,
                    level=section.level,
                    parent_id=parent_id,
                    page=section.page,
                )
            )

            chunk_id = f"{file_path.stem}-chunk-{section_idx}"
            metadata = SourceMetadata(
                path=str(file_path).replace('\\\\', '/'),
                page=section.page,
                section=section.title,
                version=version,
                last_modified=self._last_modified(file_path),
            )
            chunks.append(DocumentChunk(id=chunk_id, text=section.content, metadata=metadata))

        return nodes, chunks

    def _extract_version(self, name: str) -> str | None:
        match = re.search(r"v(\d+(?:\.\d+)*)", name.lower())
        return match.group(1) if match else None

    def _last_modified(self, file_path: Path):
        return file_path.stat().st_mtime_ns and __import__("datetime").datetime.fromtimestamp(file_path.stat().st_mtime)
