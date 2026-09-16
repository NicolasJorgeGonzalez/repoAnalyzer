"""Gemini LLM client and exception handling for repository analysis."""

from __future__ import annotations

import os
from typing import Any
import httpx

from google import genai
from google.genai import errors, types

from repo_analyzer.config import DEFAULT_MODEL


class LLMAnalysisError(Exception):
    """Base exception for errors occurring during LLM analysis."""


class MissingApiKeyError(LLMAnalysisError):
    """Raised when no Gemini API key is configured."""


class InvalidApiKeyError(LLMAnalysisError):
    """Raised when the Gemini API key is invalid or lacks required permissions."""


class APIQuotaExceededError(LLMAnalysisError):
    """Raised when the Gemini API quota or rate limit has been exceeded."""


class APIConnectionError(LLMAnalysisError):
    """Raised when network or timeout errors occur while connecting to Gemini."""


class EmptyResponseError(LLMAnalysisError):
    """Raised when Gemini returns an empty response or output was blocked by safety filters."""


class GeminiAnalyzer:
    """Client for performing repository architectural analysis using Google Gemini."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = DEFAULT_MODEL,
        client: Any | None = None,
    ) -> None:
        """Initialize the GeminiAnalyzer client.

        Args:
            api_key: Optional Gemini API key. If not provided, resolves from GEMINI_API_KEY env var.
            model_name: Gemini model name to use (defaults to DEFAULT_MODEL).
            client: Optional pre-configured genai.Client instance (useful for testing/mocking).

        Raises:
            MissingApiKeyError: If no API key can be resolved.
        """
        self.model_name = model_name
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

        if not self.api_key:
            raise MissingApiKeyError(
                "No se encontró la clave de API de Gemini. "
                "Proporciona la opción --api-key o define la variable de entorno GEMINI_API_KEY."
            )

        if client is not None:
            self.client = client
        else:
            self.client = genai.Client(api_key=self.api_key)

    def analyze_codebase(
        self,
        prompt: str,
        system_instruction: str | None = None,
    ) -> str:
        """Send repository analysis prompt to Gemini and return markdown text.

        Args:
            prompt: Structured prompt containing repository tree, metrics, and key files.
            system_instruction: Optional system instruction prompt to guide the model.

        Returns:
            String containing the generated analysis in Markdown format.

        Raises:
            EmptyResponseError: If response text is empty or blocked.
            APIQuotaExceededError: If rate limit or quota was exceeded.
            InvalidApiKeyError: If API key is invalid or rejected.
            APIConnectionError: If network error or timeout occurs.
            LLMAnalysisError: For any other unhandled API errors.
        """
        config: types.GenerateContentConfig | None = None
        if system_instruction:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
            )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
        except errors.APIError as e:
            msg = getattr(e, "message", str(e))
            code = getattr(e, "code", None)
            str_e = str(e).lower()

            if code == 429 or "resource_exhausted" in str_e or "quota" in str_e:
                raise APIQuotaExceededError(
                    f"Se ha superado el límite de cuota o peticiones de la API de Gemini: {msg}"
                ) from e
            elif code in (400, 401, 403) or "api_key_invalid" in str_e or "permission" in str_e:
                raise InvalidApiKeyError(
                    f"Error de autenticación o permisos con la clave de API de Gemini: {msg}"
                ) from e
            else:
                raise LLMAnalysisError(
                    f"Error devuelto por la API de Gemini (código {code}): {msg}"
                ) from e
        except (httpx.RequestError, TimeoutError, OSError) as e:
            raise APIConnectionError(
                f"Error de conexión o tiempo de espera al comunicarse con Gemini: {e}"
            ) from e
        except Exception as e:
            if isinstance(e, LLMAnalysisError):
                raise
            raise LLMAnalysisError(f"Error inesperado durante la llamada a Gemini: {e}") from e

        if not response or not getattr(response, "text", None):
            finish_reason = None
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                finish_reason = getattr(candidate, "finish_reason", None)

            if finish_reason:
                raise EmptyResponseError(
                    f"La respuesta de Gemini fue bloqueada o finalizó de forma anómala (motivo: {finish_reason})."
                )
            raise EmptyResponseError(
                "La respuesta recibida de Gemini está vacía o no contiene texto legible."
            )

        return response.text
