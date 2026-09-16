"""Unit tests for GeminiAnalyzer and LLM client error handling."""

import os
import unittest
from unittest.mock import MagicMock, patch

import httpx
from google.genai import errors

from repo_analyzer.llm_client import (
    APIConnectionError,
    APIQuotaExceededError,
    EmptyResponseError,
    GeminiAnalyzer,
    InvalidApiKeyError,
    MissingApiKeyError,
)


class TestGeminiAnalyzer(unittest.TestCase):
    """Test suite for GeminiAnalyzer client."""

    def test_missing_api_key_raises_error(self):
        """Should raise MissingApiKeyError when no key is in args or environment."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(MissingApiKeyError):
                GeminiAnalyzer(api_key=None)

    def test_api_key_from_argument(self):
        """Should use explicit api_key argument."""
        with patch.dict(os.environ, {}, clear=True):
            mock_client = MagicMock()
            analyzer = GeminiAnalyzer(api_key="arg-key-123", client=mock_client)
            self.assertEqual(analyzer.api_key, "arg-key-123")
            self.assertEqual(analyzer.client, mock_client)

    def test_api_key_from_environment(self):
        """Should read api_key from GEMINI_API_KEY environment variable."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "env-key-456"}):
            mock_client = MagicMock()
            analyzer = GeminiAnalyzer(client=mock_client)
            self.assertEqual(analyzer.api_key, "env-key-456")

    def test_successful_analysis(self):
        """Should return generated text on successful model call."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "# Reporte de Arquitectura\nTodo en orden."
        mock_client.models.generate_content.return_value = mock_response

        analyzer = GeminiAnalyzer(api_key="valid-key", client=mock_client)
        result = analyzer.analyze_codebase("prompt content", system_instruction="system instruction")

        self.assertEqual(result, "# Reporte de Arquitectura\nTodo en orden.")
        mock_client.models.generate_content.assert_called_once()
        kwargs = mock_client.models.generate_content.call_args.kwargs
        self.assertEqual(kwargs["contents"], "prompt content")
        self.assertEqual(kwargs["config"].system_instruction, "system instruction")

    def test_empty_response_raises_error(self):
        """Should raise EmptyResponseError if model returns empty text."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = ""
        mock_response.candidates = []
        mock_client.models.generate_content.return_value = mock_response

        analyzer = GeminiAnalyzer(api_key="valid-key", client=mock_client)
        with self.assertRaises(EmptyResponseError):
            analyzer.analyze_codebase("prompt content")

    def test_blocked_response_raises_error(self):
        """Should raise EmptyResponseError if finish_reason indicates safety block."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = None
        mock_candidate = MagicMock()
        mock_candidate.finish_reason = "SAFETY"
        mock_response.candidates = [mock_candidate]
        mock_client.models.generate_content.return_value = mock_response

        analyzer = GeminiAnalyzer(api_key="valid-key", client=mock_client)
        with self.assertRaises(EmptyResponseError) as ctx:
            analyzer.analyze_codebase("prompt content")
        self.assertIn("SAFETY", str(ctx.exception))

    def test_quota_exceeded_error_mapping(self):
        """Should map HTTP 429 / RESOURCE_EXHAUSTED to APIQuotaExceededError."""
        mock_client = MagicMock()
        api_err = errors.ClientError(429, {"error": {"message": "Resource exhausted / quota exceeded"}})
        mock_client.models.generate_content.side_effect = api_err

        analyzer = GeminiAnalyzer(api_key="valid-key", client=mock_client)
        with self.assertRaises(APIQuotaExceededError):
            analyzer.analyze_codebase("prompt content")

    def test_invalid_key_error_mapping(self):
        """Should map HTTP 401 / 403 to InvalidApiKeyError."""
        mock_client = MagicMock()
        api_err = errors.ClientError(403, {"error": {"message": "API key not valid. Please pass a valid API key."}})
        mock_client.models.generate_content.side_effect = api_err

        analyzer = GeminiAnalyzer(api_key="invalid-key", client=mock_client)
        with self.assertRaises(InvalidApiKeyError):
            analyzer.analyze_codebase("prompt content")

    def test_network_connection_error_mapping(self):
        """Should map httpx network errors to APIConnectionError."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = httpx.ConnectError("Network unreachable")

        analyzer = GeminiAnalyzer(api_key="valid-key", client=mock_client)
        with self.assertRaises(APIConnectionError):
            analyzer.analyze_codebase("prompt content")

    def test_network_timeout_error_mapping(self):
        """Should map TimeoutError to APIConnectionError."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = TimeoutError("Connection timed out")

        analyzer = GeminiAnalyzer(api_key="valid-key", client=mock_client)
        with self.assertRaises(APIConnectionError):
            analyzer.analyze_codebase("prompt content")


if __name__ == "__main__":
    unittest.main()
