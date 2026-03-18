import json
from pathlib import Path

from bankstatements_core.config.processor_config import ExtractionConfig
from bankstatements_core.patterns.repositories import FileSystemTransactionRepository
from bankstatements_core.services.pdf_processing_orchestrator import PDFProcessingOrchestrator


def test_ibans_file_masks_ibans(tmp_path: Path):
    """Ensure ibans.json contains only masked IBANs and no raw IBANs."""
    repository = FileSystemTransactionRepository()
    orchestrator = PDFProcessingOrchestrator(
        extraction_config=ExtractionConfig(),
        column_names=["Date"],
        output_dir=tmp_path,
        repository=repository,
    )

    pdf_ibans = {
        "one.pdf": "IE29AIBK93115212345678",
        "two.pdf": "DE89370400440532013000",
    }

    orchestrator._save_ibans(pdf_ibans)

    ibans_path = tmp_path / "ibans.json"
    assert ibans_path.exists()

    data = json.loads(ibans_path.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) == 2

    for item in data:
        # Raw IBAN should not be stored
        assert "iban" not in item
        # Masked IBAN must exist and contain asterisks
        assert "iban_masked" in item and "*" in item["iban_masked"]
        # Digest should be a 64-character SHA256 hex string
        assert "iban_digest" in item and len(item["iban_digest"]) == 64
