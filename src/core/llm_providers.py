"""
DroneForge AI - LLM Provider Factory
Supports multiple LLM backends: Ollama, OpenAI, Anthropic, Google, Azure
"""

import os
from typing import Optional, Dict, Any, Union
from abc import ABC, abstractmethod

import yaml
from langchain_core.language_models import BaseChatModel


def load_config() -> Dict[str, Any]:
    """Load LLM configuration from yaml file"""
    config_path = os.path.join(
        os.path.dirname(__file__), 
        "..", "..", "config", "llm_config.yaml"
    )
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def get_llm(self, **kwargs) -> BaseChatModel:
        """Get the LLM instance"""
        pass
    
    @abstractmethod
    def get_small_llm(self, **kwargs) -> BaseChatModel:
        """Get a smaller/faster LLM for simple tasks"""
        pass


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider"""
    
    def __init__(
        self,
        model: str = "llama3.1:8b",
        fallback_model: str = "llama3.1:8b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.1
    ):
        self.model = model
        self.fallback_model = fallback_model
        self.base_url = base_url
        self.temperature = temperature
    
    def get_llm(self, **kwargs) -> BaseChatModel:
        from langchain_ollama import ChatOllama
        
        return ChatOllama(
            model=kwargs.get("model", self.model),
            base_url=self.base_url,
            temperature=kwargs.get("temperature", self.temperature),
            num_ctx=kwargs.get("num_ctx", 8192),
        )
    
    def get_small_llm(self, **kwargs) -> BaseChatModel:
        from langchain_ollama import ChatOllama
        
        return ChatOllama(
            model=kwargs.get("model", self.fallback_model),
            base_url=self.base_url,
            temperature=kwargs.get("temperature", self.temperature),
            num_ctx=kwargs.get("num_ctx", 4096),
        )


class OpenAIProvider(LLMProvider):
    """OpenAI API provider"""
    
    def __init__(
        self,
        model: str = "gpt-4-turbo",
        fallback_model: str = "gpt-4o-mini",
        temperature: float = 0.1,
        api_key: Optional[str] = None
    ):
        self.model = model
        self.fallback_model = fallback_model
        self.temperature = temperature
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
    
    def get_llm(self, **kwargs) -> BaseChatModel:
        from langchain_openai import ChatOpenAI
        
        return ChatOpenAI(
            model=kwargs.get("model", self.model),
            temperature=kwargs.get("temperature", self.temperature),
            api_key=self.api_key,
            max_tokens=kwargs.get("max_tokens", 4096),
        )
    
    def get_small_llm(self, **kwargs) -> BaseChatModel:
        from langchain_openai import ChatOpenAI
        
        return ChatOpenAI(
            model=kwargs.get("model", self.fallback_model),
            temperature=kwargs.get("temperature", self.temperature),
            api_key=self.api_key,
            max_tokens=kwargs.get("max_tokens", 2048),
        )


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider"""
    
    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        fallback_model: str = "claude-3-haiku-20240307",
        temperature: float = 0.1,
        api_key: Optional[str] = None
    ):
        self.model = model
        self.fallback_model = fallback_model
        self.temperature = temperature
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    
    def get_llm(self, **kwargs) -> BaseChatModel:
        from langchain_anthropic import ChatAnthropic
        
        return ChatAnthropic(
            model=kwargs.get("model", self.model),
            temperature=kwargs.get("temperature", self.temperature),
            api_key=self.api_key,
            max_tokens=kwargs.get("max_tokens", 4096),
        )
    
    def get_small_llm(self, **kwargs) -> BaseChatModel:
        from langchain_anthropic import ChatAnthropic
        
        return ChatAnthropic(
            model=kwargs.get("model", self.fallback_model),
            temperature=kwargs.get("temperature", self.temperature),
            api_key=self.api_key,
            max_tokens=kwargs.get("max_tokens", 2048),
        )


class GoogleProvider(LLMProvider):
    """Google Gemini provider"""
    
    def __init__(
        self,
        model: str = "gemini-1.5-pro",
        fallback_model: str = "gemini-1.5-flash",
        temperature: float = 0.1,
        api_key: Optional[str] = None
    ):
        self.model = model
        self.fallback_model = fallback_model
        self.temperature = temperature
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
    
    def get_llm(self, **kwargs) -> BaseChatModel:
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        return ChatGoogleGenerativeAI(
            model=kwargs.get("model", self.model),
            temperature=kwargs.get("temperature", self.temperature),
            google_api_key=self.api_key,
            max_output_tokens=kwargs.get("max_tokens", 4096),
        )
    
    def get_small_llm(self, **kwargs) -> BaseChatModel:
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        return ChatGoogleGenerativeAI(
            model=kwargs.get("model", self.fallback_model),
            temperature=kwargs.get("temperature", self.temperature),
            google_api_key=self.api_key,
            max_output_tokens=kwargs.get("max_tokens", 2048),
        )


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI provider"""
    
    def __init__(
        self,
        deployment_name: str = "gpt-4-turbo",
        fallback_deployment: str = "gpt-4o-mini",
        api_version: str = "2024-02-01",
        temperature: float = 0.1,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None
    ):
        self.deployment_name = deployment_name
        self.fallback_deployment = fallback_deployment
        self.api_version = api_version
        self.temperature = temperature
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
    
    def get_llm(self, **kwargs) -> BaseChatModel:
        from langchain_openai import AzureChatOpenAI
        
        return AzureChatOpenAI(
            azure_deployment=kwargs.get("deployment", self.deployment_name),
            api_version=self.api_version,
            temperature=kwargs.get("temperature", self.temperature),
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            max_tokens=kwargs.get("max_tokens", 4096),
        )
    
    def get_small_llm(self, **kwargs) -> BaseChatModel:
        from langchain_openai import AzureChatOpenAI
        
        return AzureChatOpenAI(
            azure_deployment=kwargs.get("deployment", self.fallback_deployment),
            api_version=self.api_version,
            temperature=kwargs.get("temperature", self.temperature),
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            max_tokens=kwargs.get("max_tokens", 2048),
        )


class LLMProviderFactory:
    """Factory for creating LLM providers"""
    
    PROVIDERS = {
        "ollama": OllamaProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
        "azure": AzureOpenAIProvider,
    }
    
    @classmethod
    def create(
        cls,
        provider_name: str = "ollama",
        **kwargs
    ) -> LLMProvider:
        """
        Create an LLM provider instance.
        
        Args:
            provider_name: Name of the provider (ollama, openai, anthropic, google, azure)
            **kwargs: Provider-specific arguments
            
        Returns:
            LLMProvider instance
        """
        provider_name = provider_name.lower()
        
        if provider_name not in cls.PROVIDERS:
            raise ValueError(
                f"Unknown provider: {provider_name}. "
                f"Available: {list(cls.PROVIDERS.keys())}"
            )
        
        # Load config and merge with kwargs
        config = load_config()
        provider_config = config.get("providers", {}).get(provider_name, {})
        merged_config = {**provider_config, **kwargs}
        
        return cls.PROVIDERS[provider_name](**merged_config)
    
    @classmethod
    def get_available_providers(cls) -> list:
        """Get list of available providers"""
        return list(cls.PROVIDERS.keys())
    
    @classmethod
    def check_provider_available(cls, provider_name: str) -> Dict[str, Any]:
        """
        Check if a provider is available and configured.
        
        Returns:
            Dict with 'available' bool and 'message' str
        """
        provider_name = provider_name.lower()
        
        if provider_name not in cls.PROVIDERS:
            return {
                "available": False,
                "message": f"Unknown provider: {provider_name}"
            }
        
        if provider_name == "ollama":
            try:
                import requests
                response = requests.get("http://localhost:11434/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    return {
                        "available": True,
                        "message": f"Ollama running with {len(models)} models"
                    }
            except Exception as e:
                return {
                    "available": False,
                    "message": f"Ollama not running: {str(e)}"
                }
        
        elif provider_name == "openai":
            if os.getenv("OPENAI_API_KEY"):
                return {"available": True, "message": "API key configured"}
            return {"available": False, "message": "OPENAI_API_KEY not set"}
        
        elif provider_name == "anthropic":
            if os.getenv("ANTHROPIC_API_KEY"):
                return {"available": True, "message": "API key configured"}
            return {"available": False, "message": "ANTHROPIC_API_KEY not set"}
        
        elif provider_name == "google":
            if os.getenv("GOOGLE_API_KEY"):
                return {"available": True, "message": "API key configured"}
            return {"available": False, "message": "GOOGLE_API_KEY not set"}
        
        elif provider_name == "azure":
            if os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"):
                return {"available": True, "message": "API key and endpoint configured"}
            return {
                "available": False,
                "message": "AZURE_OPENAI_API_KEY or AZURE_OPENAI_ENDPOINT not set"
            }
        
        return {"available": False, "message": "Unknown error"}
