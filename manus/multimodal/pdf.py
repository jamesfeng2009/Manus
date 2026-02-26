"""PDF processing tools."""

import base64
from pathlib import Path

from manus.tools.base import Tool, ToolResult, ToolStatus


class PDFTool(Tool):
    """PDF processing tool for text extraction and analysis."""

    def __init__(self):
        super().__init__(
            name="pdf",
            description="Process PDF documents: extract text or analyze with vision model.",
            parameters={
                "pdf_path": {
                    "schema": {"type": "string", "description": "Path to PDF file"},
                    "required": True,
                },
                "mode": {
                    "schema": {
                        "type": "string",
                        "enum": ["extract", "analyze", "info"],
                        "description": "Mode: 'extract' (text), 'analyze' (vision), 'info' (metadata)",
                    },
                    "required": True,
                },
                "pages": {
                    "schema": {"type": "array", "items": {"type": "integer"}},
                    "description": "Specific pages to process",
                    "required": False,
                },
                "question": {
                    "schema": {"type": "string", "description": "Question for analyze mode"},
                    "required": False,
                },
            },
        )

    async def execute(
        self,
        pdf_path: str,
        mode: str,
        pages: list[int] | None = None,
        question: str | None = None,
        **kwargs,
    ) -> ToolResult:
        """Execute PDF processing."""
        try:
            p = Path(pdf_path)
            if not p.exists():
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error=f"PDF file not found: {pdf_path}",
                )

            if mode == "extract":
                return await self._extract_text(str(p), pages)
            elif mode == "analyze":
                return await self._analyze_pdf(str(p), pages, question)
            elif mode == "info":
                return await self._get_pdf_info(str(p))
            else:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error=f"Unknown mode: {mode}",
                )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )

    async def _extract_text(self, pdf_path: str, pages: list[int] | None) -> ToolResult:
        """Extract text from PDF."""
        try:
            from pypdf import PdfReader

            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)

            if pages:
                page_texts = []
                for page_num in pages:
                    if 0 < page_num <= total_pages:
                        page = reader.pages[page_num - 1]
                        page_texts.append(f"--- Page {page_num} ---\n{page.extract_text()}")
                    else:
                        page_texts.append(f"--- Page {page_num} (out of range) ---")
                text = "\n\n".join(page_texts)
            else:
                text = "\n".join(page.extract_text() for page in reader.pages)

            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                content=text[:10000],
                metadata={
                    "total_pages": total_pages,
                    "pages_extracted": len(pages) if pages else total_pages,
                    "char_count": len(text),
                },
            )
        except ImportError:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="pypdf not installed. Run: pip install pypdf",
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Text extraction failed: {str(e)}",
            )

    async def _analyze_pdf(
        self, pdf_path: str, pages: list[int] | None, question: str | None
    ) -> ToolResult:
        """Analyze PDF pages using vision model."""
        try:
            from pypdf import PdfReader
            import fitz

            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            page_nums = pages if pages else [1]

            prompt = question or "Describe the content of this PDF page."

            results = []
            for page_num in page_nums:
                if 0 < page_num <= total_pages:
                    page = reader.pages[page_num - 1]
                    text = page.extract_text()

                    doc = fitz.open(pdf_path)
                    pdf_page = doc[page_num - 1]
                    pix = pdf_page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img_bytes = pix.tobytes("jpeg")
                    img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                    doc.close()

                    try:
                        from manus.models import get_adapter

                        adapter = get_adapter("gpt-4o")
                        from manus.core.types import Message, MessageRole

                        content = [
                            {"type": "text", "text": f"{prompt}\n\nPage text:\n{text[:2000]}"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_b64}",
                                    "detail": "high",
                                },
                            },
                        ]

                        messages = [Message(role=MessageRole.USER, content=content)]
                        response = await adapter.chat(messages=messages, max_tokens=1024)

                        results.append(
                            {
                                "page": page_num,
                                "analysis": response.get("content", ""),
                            }
                        )
                    except Exception as e:
                        results.append(
                            {
                                "page": page_num,
                                "text": text[:2000],
                                "error": str(e),
                            }
                        )

            analysis_text = "\n\n".join(
                f"--- Page {r['page']} ---\n{r.get('analysis', r.get('error', ''))}"
                for r in results
            )

            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                content=analysis_text,
                metadata={"pages_analyzed": len(results)},
            )
        except ImportError:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="pypdf or pymupdf not installed. Run: pip install pypdf pymupdf",
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"PDF analysis failed: {str(e)}",
            )

    async def _get_pdf_info(self, pdf_path: str) -> ToolResult:
        """Get PDF metadata."""
        try:
            from pypdf import PdfReader

            reader = PdfReader(pdf_path)
            metadata = reader.metadata or {}

            info = {
                "title": metadata.get("/Title", "Unknown"),
                "author": metadata.get("/Author", "Unknown"),
                "subject": metadata.get("/Subject", "Unknown"),
                "creator": metadata.get("/Creator", "Unknown"),
                "pages": len(reader.pages),
            }

            try:
                import fitz

                doc = fitz.open(pdf_path)
                info["pdf_version"] = doc.pdf_version
                info["encrypted"] = doc.is_encrypted
                doc.close()
            except ImportError:
                pass

            info_text = "\n".join(f"{k}: {v}" for k, v in info.items())

            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                content=info_text,
                metadata=info,
            )
        except ImportError:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="pypdf not installed. Run: pip install pypdf",
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Failed to get PDF info: {str(e)}",
            )
