import re
from typing import List, Optional, Tuple
from dataclasses import dataclass
from langchain_core.documents import Document
from app.config import get_settings
from app.document_parser import ParsedDocument, DocumentParser, TextSegment


@dataclass
class SemanticChunk:
    content: str
    start_char: int
    end_char: int
    start_line: int
    end_line: int
    page: Optional[int] = None


class SemanticTextSplitter:
    SENTENCE_END_PATTERN = re.compile(
        r'(?<=[。！？.!?])\s+|(?<=[。！？.!?])$'
    )
    
    PARAGRAPH_PATTERN = re.compile(r'\n\s*\n')

    def __init__(self):
        settings = get_settings()
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP
        self.min_chunk_size = max(100, self.chunk_size // 4)

    def split_documents(
        self,
        documents: List[Document],
        document_id: str,
        parsed_doc: Optional[ParsedDocument] = None,
    ) -> List[Document]:
        all_chunks = []
        
        for doc in documents:
            chunks = self._split_text_with_tracking(
                text=doc.page_content,
                segments=parsed_doc.segments if parsed_doc else None,
            )
            
            for idx, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_chunk_{idx}"
                
                metadata = doc.metadata.copy()
                metadata.update({
                    "document_id": document_id,
                    "chunk_id": chunk_id,
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                })
                if chunk.page is not None:
                    metadata["page"] = chunk.page
                
                processed_chunk = Document(
                    page_content=self._clean_text(chunk.content),
                    metadata=metadata,
                )
                all_chunks.append(processed_chunk)
        
        return all_chunks

    def _split_text_with_tracking(
        self,
        text: str,
        segments: Optional[List[TextSegment]] = None,
    ) -> List[SemanticChunk]:
        chunks = []
        
        paragraphs = self._split_by_paragraphs(text)
        
        current_chunk_text = ""
        current_start_char = 0
        current_start_line = 0
        
        for para_text, para_start_char, para_end_char in paragraphs:
            sentences = self._split_by_sentences(para_text)
            
            for sent_text, sent_rel_start, sent_rel_end in sentences:
                abs_start = para_start_char + sent_rel_start
                abs_end = para_start_char + sent_rel_end
                
                if not current_chunk_text:
                    current_start_char = abs_start
                    current_start_line = self._char_to_line(abs_start, segments)
                
                test_chunk = current_chunk_text + (" " if current_chunk_text else "") + sent_text
                
                if len(test_chunk) <= self.chunk_size:
                    current_chunk_text = test_chunk
                else:
                    if len(current_chunk_text) >= self.min_chunk_size:
                        end_line = self._char_to_line(abs_start - 1, segments)
                        page = self._get_page_for_range(current_start_char, abs_start - 1, segments)
                        
                        chunks.append(SemanticChunk(
                            content=current_chunk_text,
                            start_char=current_start_char,
                            end_char=abs_start - 1,
                            start_line=current_start_line,
                            end_line=end_line,
                            page=page,
                        ))
                        
                        overlap_text = self._get_overlap_text(current_chunk_text)
                        current_chunk_text = overlap_text + sent_text if overlap_text else sent_text
                        current_start_char = abs_start - len(overlap_text) if overlap_text else abs_start
                        current_start_line = self._char_to_line(current_start_char, segments)
                    else:
                        current_chunk_text = test_chunk
            
            if len(current_chunk_text) >= self.min_chunk_size:
                end_line = self._char_to_line(para_end_char, segments)
                page = self._get_page_for_range(current_start_char, para_end_char, segments)
                
                chunks.append(SemanticChunk(
                    content=current_chunk_text,
                    start_char=current_start_char,
                    end_char=para_end_char,
                    start_line=current_start_line,
                    end_line=end_line,
                    page=page,
                ))
                current_chunk_text = ""
        
        if current_chunk_text:
            end_line = self._char_to_line(len(text) - 1, segments)
            page = self._get_page_for_range(current_start_char, len(text) - 1, segments)
            
            chunks.append(SemanticChunk(
                content=current_chunk_text,
                start_char=current_start_char,
                end_char=len(text) - 1,
                start_line=current_start_line,
                end_line=end_line,
                page=page,
            ))
        
        return chunks

    def _split_by_paragraphs(self, text: str) -> List[Tuple[str, int, int]]:
        paragraphs = []
        last_end = 0
        
        for match in self.PARAGRAPH_PATTERN.finditer(text):
            para_text = text[last_end:match.start()].strip()
            if para_text:
                paragraphs.append((para_text, last_end, match.start() - 1))
            last_end = match.end()
        
        if last_end < len(text):
            para_text = text[last_end:].strip()
            if para_text:
                paragraphs.append((para_text, last_end, len(text) - 1))
        
        if not paragraphs:
            paragraphs.append((text.strip(), 0, len(text) - 1))
        
        return paragraphs

    def _split_by_sentences(self, text: str) -> List[Tuple[str, int, int]]:
        sentences = []
        last_end = 0
        
        for match in self.SENTENCE_END_PATTERN.finditer(text):
            sent_text = text[last_end:match.start()].strip()
            if sent_text:
                sentences.append((sent_text, last_end, match.start() - 1))
            last_end = match.end()
        
        if last_end < len(text):
            sent_text = text[last_end:].strip()
            if sent_text:
                sentences.append((sent_text, last_end, len(text) - 1))
        
        if not sentences:
            sentences.append((text.strip(), 0, len(text) - 1))
        
        return sentences

    def _get_overlap_text(self, text: str) -> str:
        if self.chunk_overlap <= 0 or len(text) <= self.chunk_overlap:
            return ""
        
        sentences = self._split_by_sentences(text)
        overlap = ""
        
        for sent_text, _, _ in reversed(sentences):
            if len(overlap) + len(sent_text) + 1 <= self.chunk_overlap:
                overlap = sent_text + " " + overlap
            else:
                break
        
        return overlap.strip()

    def _char_to_line(
        self,
        char_pos: int,
        segments: Optional[List[TextSegment]],
    ) -> int:
        if not segments:
            return 0
        
        for seg in segments:
            if seg.start_char <= char_pos <= seg.end_char:
                return seg.start_line
        
        if segments:
            if char_pos < segments[0].start_char:
                return segments[0].start_line
            else:
                return segments[-1].end_line
        
        return 0

    def _get_page_for_range(
        self,
        start_char: int,
        end_char: int,
        segments: Optional[List[TextSegment]],
    ) -> Optional[int]:
        if not segments:
            return None
        
        for seg in segments:
            if seg.start_char <= end_char and seg.end_char >= start_char:
                if seg.page is not None:
                    return seg.page
        
        return None

    def _clean_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

    def split_text(self, text: str) -> List[str]:
        chunks = self._split_text_with_tracking(text, segments=None)
        return [chunk.content for chunk in chunks]
