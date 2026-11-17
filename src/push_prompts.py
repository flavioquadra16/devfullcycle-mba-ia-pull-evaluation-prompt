"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langsmith import Client

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from utils import check_env_vars, load_yaml, print_section_header

load_dotenv(ROOT / ".env")

PROMPT_FILE = ROOT / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_NAME = "bug_to_user_story_v2"


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    errors = []

    if not isinstance(prompt_data, dict):
        return False, ["Estrutura do prompt inválida: esperado um dicionário."]

    required_fields = ["description", "system_prompt", "user_prompt", "version"]
    for field in required_fields:
        value = prompt_data.get(field, "")
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Campo obrigatório ausente ou vazio: {field}")

    system_prompt = str(prompt_data.get("system_prompt", ""))
    user_prompt = str(prompt_data.get("user_prompt", ""))
    combined = f"{system_prompt}\n{user_prompt}"

    if "{bug_report}" not in user_prompt:
        errors.append("user_prompt precisa da variável {bug_report}.")

    if "TODO" in combined or "[TODO]" in combined:
        errors.append("O prompt ainda contém TODO.")

    techniques = prompt_data.get("techniques_applied", [])
    if not isinstance(techniques, list) or len(techniques) < 2:
        found = len(techniques) if isinstance(techniques, list) else 0
        errors.append(f"Mínimo de 2 técnicas em techniques_applied. Encontradas: {found}.")

    lowered = combined.lower()
    if "exemplo" not in lowered or "entrada" not in lowered or "saída" not in lowered:
        errors.append("O prompt precisa de exemplos few-shot com Entrada e Saída.")

    if "você é" not in lowered:
        errors.append("O system prompt precisa definir uma persona.")

    return len(errors) == 0, errors


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    username = os.getenv("USERNAME_LANGSMITH_HUB", "").strip()
    if not username:
        print("❌ USERNAME_LANGSMITH_HUB não configurado no .env.")
        return False

    prompt_identifier = f"{username}/{prompt_name}"
    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_data["system_prompt"]),
            ("user", prompt_data["user_prompt"]),
        ]
    )

    input_variables = set(chat_prompt.input_variables)
    if input_variables != {"bug_report"}:
        print(
            "❌ O template deve expor somente a variável bug_report. "
            f"Encontradas: {sorted(input_variables)}"
        )
        return False

    techniques = [str(item) for item in prompt_data.get("techniques_applied", [])]
    tags = [str(item) for item in prompt_data.get("tags", [])]
    for technique in techniques:
        tag = technique.lower().replace(" ", "-")
        if tag not in tags:
            tags.append(tag)

    description = prompt_data.get("description", "").strip()
    if techniques:
        description = f"{description} Técnicas: {', '.join(techniques)}."

    print(f"Publicando prompt público: {prompt_identifier}")
    client = Client()
    url = client.push_prompt(
        prompt_identifier,
        object=chat_prompt,
        is_public=True,
        description=description,
        tags=tags,
    )

    print(f"✓ Push concluído: {prompt_identifier}")
    print(f"✓ URL: {url}")
    print(f"✓ Tags: {', '.join(tags)}")
    return True


def _extract_prompt_data(raw: dict) -> dict:
    if PROMPT_NAME in raw and isinstance(raw[PROMPT_NAME], dict):
        return raw[PROMPT_NAME]
    return raw


def main() -> int:
    """Função principal"""
    print_section_header("PUSH DE PROMPTS OTIMIZADOS")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    raw = load_yaml(str(PROMPT_FILE))
    if not raw:
        return 1

    prompt_data = _extract_prompt_data(raw)
    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido. Corrija prompts/bug_to_user_story_v2.yml:")
        for error in errors:
            print(f"   - {error}")
        return 1

    print("✓ Estrutura do prompt validada.")

    try:
        return 0 if push_prompt_to_langsmith(PROMPT_NAME, prompt_data) else 1
    except Exception as exc:
        message = str(exc)
        print(f"❌ Erro ao fazer push do prompt: {message}")
        if "handle" in message.lower() or "not found" in message.lower() or "404" in message:
            print(
                "Confirme se USERNAME_LANGSMITH_HUB é o handle público criado "
                "em LangSmith > Prompts > Make Public."
            )
        return 1


if __name__ == "__main__":
    sys.exit(main())
