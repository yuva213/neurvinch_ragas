from __future__ import annotations

import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from neurvinch.audit import NLIAuditor


class TestNLIAuditorRegression(unittest.TestCase):
    def setUp(self) -> None:
        self.auditor = NLIAuditor(
            embedding_model_name="sentence-transformers/all-MiniLM-L6-v2",
            embedding_backend="tfidf",
            nli_model_name="cross-encoder/nli-deberta-v3-base",
            nli_backend="heuristic",
            contradiction_threshold=0.85,
        )

    def test_numeric_window_contradiction_is_detected(self) -> None:
        text_a = "VPN credentials must be rotated every 90 days for all employees."
        text_b = "VPN credentials must be rotated every 30 days for all employees."

        probs = self.auditor._heuristic_probs(text_a, text_b)
        contradiction_prob = self.auditor._contradiction_probability(probs)

        self.assertGreaterEqual(contradiction_prob, 0.9)

    def test_similar_non_conflicting_statements_not_marked_as_contradiction(self) -> None:
        text_a = "All remote devices must run approved endpoint protection and full-disk encryption."
        text_b = "All remote devices must run approved endpoint protection, full-disk encryption, and monthly patch validation."

        probs = self.auditor._heuristic_probs(text_a, text_b)
        contradiction_prob = self.auditor._contradiction_probability(probs)

        self.assertLess(contradiction_prob, 0.5)

    def test_quantity_extraction_normalizes_units(self) -> None:
        quantities = self.auditor._extract_quantities(
            "Temporary credentials expire in 15 minutes and password rotation occurs every 30 days."
        )

        self.assertIn((15.0, "minute"), quantities)
        self.assertIn((30.0, "day"), quantities)


if __name__ == "__main__":
    unittest.main()
