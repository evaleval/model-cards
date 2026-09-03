from __future__ import annotations

from io import BytesIO
import hashlib
import json
import os
import signal
import subprocess
import unittest
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter

from model_cards.pdf_extraction import (
    PDF_EXTRACTOR_VERSION,
    PDF_PARSER_NAME,
    PDF_PARSER_VERSION,
    PdfExtractionError,
    PdfExtractionLimits,
    PdfExtractionStatus,
    extract_pdf_text,
)


def _assemble_pdf(objects: list[bytes]) -> bytes:
    payload = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, 1):
        offsets.append(len(payload))
        payload.extend(f"{index} 0 obj\n".encode("ascii"))
        payload.extend(body)
        payload.extend(b"\nendobj\n")
    xref_offset = len(payload)
    payload.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    payload.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        payload.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    payload.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(payload)


def text_pdf(*page_texts: str) -> bytes:
    page_count = len(page_texts)
    page_ids = tuple(range(4, 4 + page_count))
    content_ids = tuple(range(4 + page_count, 4 + 2 * page_count))
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode(
            "ascii"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for content_id in content_ids:
        objects.append(
            (
                "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                "/Resources << /Font << /F1 3 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            ).encode("ascii")
        )
    for text in page_texts:
        escaped = (
            text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        )
        stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("latin-1")
        objects.append(
            b"<< /Length "
            + str(len(stream)).encode("ascii")
            + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        )
    return _assemble_pdf(objects)


def image_only_pdf() -> bytes:
    drawing = b"q 1 0 0 1 0 0 cm /Im0 Do Q"
    image = b"\x00"
    return _assemble_pdf(
        [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            (
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] "
                b"/Resources << /XObject << /Im0 5 0 R >> >> /Contents 4 0 R >>"
            ),
            b"<< /Length "
            + str(len(drawing)).encode("ascii")
            + b" >>\nstream\n"
            + drawing
            + b"\nendstream",
            (
                b"<< /Type /XObject /Subtype /Image /Width 1 /Height 1 "
                b"/ColorSpace /DeviceGray /BitsPerComponent 8 /Length 1 >>\n"
                b"stream\n" + image + b"\nendstream"
            ),
        ]
    )


def encrypted_pdf() -> bytes:
    reader = PdfReader(BytesIO(text_pdf("Private text")), strict=True)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt("secret")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class FrozenPdfExtractionTests(unittest.TestCase):
    def test_valid_pdf_is_deterministic_and_preserves_references(self) -> None:
        source = text_pdf("Main finding", "References: Smith 2026")
        first = extract_pdf_text(source)
        second = extract_pdf_text(source)

        self.assertEqual(PdfExtractionStatus.EXTRACTED, first.status)
        self.assertEqual("extracted_text", first.reason_code)
        self.assertEqual(2, first.page_count)
        self.assertEqual("Main finding\n\nReferences: Smith 2026", first.text)
        self.assertEqual(first.text, second.text)
        self.assertEqual(first.output_sha256, second.output_sha256)
        self.assertEqual(
            hashlib.sha256(first.text.encode("utf-8")).hexdigest(),
            first.output_sha256,
        )
        self.assertEqual(PDF_EXTRACTOR_VERSION, first.extractor_version)
        self.assertEqual(PDF_PARSER_NAME, first.parser_name)
        self.assertEqual(PDF_PARSER_VERSION, first.parser_version)

    def test_metadata_is_body_free_and_binds_source_and_output(self) -> None:
        source = text_pdf("UNIQUE_SOURCE_DERIVED_TEXT")
        result = extract_pdf_text(source)
        metadata = result.to_dict()
        encoded = json.dumps(metadata, sort_keys=True)

        self.assertNotIn("UNIQUE_SOURCE_DERIVED_TEXT", encoded)
        self.assertNotIn("text", metadata)
        self.assertEqual(hashlib.sha256(source).hexdigest(), metadata["source_sha256"])
        self.assertEqual(len(source), metadata["source_byte_size"])
        self.assertEqual(result.canonical_bytes(), result.canonical_bytes())

    def test_encrypted_pdf_is_never_decrypted(self) -> None:
        result = extract_pdf_text(encrypted_pdf())
        self.assertEqual(PdfExtractionStatus.ENCRYPTED, result.status)
        self.assertEqual("encrypted_pdf", result.reason_code)
        self.assertIsNone(result.text)
        self.assertIsNone(result.output_sha256)

    def test_malformed_pdf_is_explicit(self) -> None:
        result = extract_pdf_text(b"%PDF-1.7\nnot a complete PDF")
        self.assertEqual(PdfExtractionStatus.MALFORMED, result.status)
        self.assertEqual("malformed_pdf", result.reason_code)

    def test_image_only_pdf_is_explicit_without_ocr(self) -> None:
        result = extract_pdf_text(image_only_pdf())
        self.assertEqual(PdfExtractionStatus.IMAGE_ONLY, result.status)
        self.assertEqual("image_only_pdf", result.reason_code)
        self.assertIsNone(result.text)

    def test_blank_pdf_is_distinct_from_image_only(self) -> None:
        result = extract_pdf_text(text_pdf(""))
        self.assertEqual(PdfExtractionStatus.EMPTY, result.status)
        self.assertEqual("no_extractable_text", result.reason_code)

    def test_byte_page_and_text_limits_fail_closed(self) -> None:
        source_limited = extract_pdf_text(
            b"12",
            limits=PdfExtractionLimits(max_source_bytes=1),
        )
        page_limited = extract_pdf_text(
            text_pdf("one", "two"),
            limits=PdfExtractionLimits(max_pages=1),
        )
        text_limited = extract_pdf_text(
            text_pdf("sixteen characters"),
            limits=PdfExtractionLimits(max_text_characters=5),
        )

        self.assertEqual(PdfExtractionStatus.SOURCE_LIMIT, source_limited.status)
        self.assertEqual("source_byte_limit", source_limited.reason_code)
        self.assertEqual(PdfExtractionStatus.PAGE_LIMIT, page_limited.status)
        self.assertEqual("page_count_limit", page_limited.reason_code)
        self.assertEqual(2, page_limited.page_count)
        self.assertEqual(PdfExtractionStatus.TEXT_LIMIT, text_limited.status)
        self.assertEqual("text_character_limit", text_limited.reason_code)

    @patch("model_cards.pdf_extraction.subprocess.run")
    def test_wall_time_and_resource_termination_are_explicit(self, run) -> None:
        run.side_effect = subprocess.TimeoutExpired(("worker",), timeout=0.1)
        timed_out = extract_pdf_text(text_pdf("text"))
        self.assertEqual(PdfExtractionStatus.TIME_LIMIT, timed_out.status)
        self.assertEqual("wall_time_limit", timed_out.reason_code)

        run.side_effect = None
        run.return_value = subprocess.CompletedProcess(
            ("worker",),
            -signal.SIGXCPU,
            stdout=b"",
        )
        resource_limited = extract_pdf_text(text_pdf("text"))
        self.assertEqual(PdfExtractionStatus.RESOURCE_LIMIT, resource_limited.status)
        self.assertEqual("worker_resource_limit", resource_limited.reason_code)

    @patch("model_cards.pdf_extraction.subprocess.run")
    def test_worker_failure_and_protocol_failure_are_explicit(self, run) -> None:
        run.return_value = subprocess.CompletedProcess(("worker",), 2, stdout=b"")
        failed = extract_pdf_text(text_pdf("text"))
        self.assertEqual(PdfExtractionStatus.FAILED, failed.status)
        self.assertEqual("worker_failed", failed.reason_code)

        run.return_value = subprocess.CompletedProcess(
            ("worker",), 0, stdout=b"not-json"
        )
        invalid = extract_pdf_text(text_pdf("text"))
        self.assertEqual(PdfExtractionStatus.FAILED, invalid.status)
        self.assertEqual("worker_protocol_invalid", invalid.reason_code)

        run.return_value = subprocess.CompletedProcess(
            ("worker",),
            0,
            stdout=json.dumps(
                {
                    "status": "page_limit",
                    "reason_code": "page_count_limit",
                    "page_count": 1,
                    "text": None,
                    "parser_version": PDF_PARSER_VERSION,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8"),
        )
        inconsistent = extract_pdf_text(text_pdf("text"))
        self.assertEqual(PdfExtractionStatus.FAILED, inconsistent.status)
        self.assertEqual("worker_protocol_invalid", inconsistent.reason_code)

    @patch("model_cards.pdf_extraction.subprocess.run")
    def test_worker_environment_does_not_inherit_credentials(self, run) -> None:
        run.return_value = subprocess.CompletedProcess(
            ("worker",),
            0,
            stdout=json.dumps(
                {
                    "status": "extracted",
                    "reason_code": "extracted_text",
                    "page_count": 1,
                    "text": "safe",
                    "parser_version": PDF_PARSER_VERSION,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8"),
        )
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "must-not-pass"}):
            result = extract_pdf_text(text_pdf("text"))

        self.assertEqual(PdfExtractionStatus.EXTRACTED, result.status)
        child_environment = run.call_args.kwargs["env"]
        self.assertNotIn("OPENROUTER_API_KEY", child_environment)
        self.assertEqual("0", child_environment["PYTHONHASHSEED"])

    def test_limits_reject_non_finite_or_unbounded_values(self) -> None:
        invalid = (
            {"max_source_bytes": True},
            {"max_pages": 0},
            {"max_text_characters": 16_000_001},
            {"wall_time_seconds": float("nan")},
            {"cpu_time_seconds": 0},
            {"max_open_files": 15},
        )
        for changes in invalid:
            with self.subTest(changes=changes):
                with self.assertRaises(PdfExtractionError):
                    PdfExtractionLimits(**changes)
        with self.assertRaises(PdfExtractionError):
            extract_pdf_text("not bytes")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
