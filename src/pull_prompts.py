"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt semente do desafio
3. Salva localmente em prompts/bug_to_user_story_v1.yml
"""

import sys
from pathlib import Path

from dotenv import load_dotenv
from langsmith import Client

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from utils import check_env_vars, print_section_header, save_yaml

load_dotenv(ROOT / ".env")

SEED_PROMPT = "leonanluppi/bug_to_user_story_v1"
OUTPUT_PATH = ROOT / "prompts" / "bug_to_user_story_v1.yml"


def _message_role(message) -> str:
    role = getattr(message, "role", None)
    if isinstance(role, str) and role.strip():
        return role.strip().lower()

    class_name = message.__class__.__name__.lower()
    if "system" in class_name:
        return "system"
    if "human" in class_name or "user" in class_name:
        return "user"
    if "ai" in class_name or "assistant" in class_name:
        return "assistant"
    return "unknown"


def _message_template(message) -> str:
    prompt = getattr(message, "prompt", None)
    template = getattr(prompt, "template", None)
    if isinstance(template, str):
        return template

    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content

    return str(message)


def pull_prompts_from_langsmith() -> bool:
    """Conecta ao LangSmith, puxa o prompt semente e grava o YAML local."""
    print_section_header("PULL DE PROMPTS DO LANGSMITH")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return False

    print(f"Puxando prompt público: {SEED_PROMPT}")
    client = Client()
    prompt = client.pull_prompt(
        SEED_PROMPT,
        dangerously_pull_public_prompt=True,
    )

    messages = getattr(prompt, "messages", None)
    if not messages:
        print("❌ O prompt retornado não contém mensagens de chat.")
        return False

    system_prompt = ""
    user_prompt = ""
    for message in messages:
        role = _message_role(message)
        template = _message_template(message)
        if role == "system" and not system_prompt:
            system_prompt = template
        elif role in {"user", "human"} and not user_prompt:
            user_prompt = template

    if not system_prompt:
        print("❌ Não foi possível extrair o system prompt.")
        return False

    if not user_prompt:
        user_prompt = "{bug_report}"

    data = {
        "bug_to_user_story_v1": {
            "description": "Prompt para converter relatos de bugs em User Stories",
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "version": "v1",
            "created_at": "2025-01-15",
            "tags": ["bug-analysis", "user-story", "product-management"],
            "source": SEED_PROMPT,
        }
    }

    if not save_yaml(data, str(OUTPUT_PATH)):
        return False

    print(f"✓ Prompt salvo em {OUTPUT_PATH}")
    print(f"✓ System prompt: {len(system_prompt)} caracteres")
    print(f"✓ User prompt: {len(user_prompt)} caracteres")
    return True


def main() -> int:
    """Função principal"""
    try:
        return 0 if pull_prompts_from_langsmith() else 1
    except Exception as exc:
        print(f"❌ Erro ao fazer pull do prompt: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
