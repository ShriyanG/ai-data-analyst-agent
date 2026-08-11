import unittest

from agent import llm


class LLMIntegrationTests(unittest.TestCase):
    def test_classify_query_falls_back_to_heuristics_when_model_is_unavailable(self) -> None:
        def broken_runner(*args, **kwargs):
            raise RuntimeError("model unavailable")

        result = llm.classify_query(
            "What is total sales by region?",
            "descriptive",
            "duckdb",
            runner=broken_runner,
        )

        self.assertEqual(result, ("descriptive", "duckdb"))


if __name__ == "__main__":
    unittest.main()
