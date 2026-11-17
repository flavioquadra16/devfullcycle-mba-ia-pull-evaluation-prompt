"""
Testes automatizados para validação de prompts.
"""
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from utils import validate_prompt_structure

PROMPT_PATH = ROOT / "prompts" / "bug_to_user_story_v2.yml"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def get_prompt() -> dict:
    data = load_prompts(str(PROMPT_PATH))
    assert isinstance(data, dict), "O YAML do prompt v2 deve ser um dicionário."
    if "bug_to_user_story_v2" in data:
        return data["bug_to_user_story_v2"]
    return data


def prompt_text(prompt: dict) -> str:
    return "\n".join(
        [
            str(prompt.get("system_prompt", "")),
            str(prompt.get("user_prompt", "")),
        ]
    )


class TestPrompts:
    def test_prompt_has_system_prompt(self):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        prompt = get_prompt()
        system_prompt = prompt.get("system_prompt")
        assert isinstance(system_prompt, str)
        assert system_prompt.strip()

    def test_prompt_has_role_definition(self):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        text = prompt_text(get_prompt()).lower()
        assert "você é" in text
        assert "product manager" in text

    def test_prompt_mentions_format(self):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        text = prompt_text(get_prompt()).lower()
        assert "markdown" in text or "user story" in text
        assert "como um" in text
        assert "eu quero" in text
        assert "para que" in text

    def test_prompt_has_few_shot_examples(self):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        text = prompt_text(get_prompt()).lower()
        assert "few-shot" in text or "few shot" in text
        assert "exemplo" in text
        assert "entrada" in text
        assert "saída" in text

    def test_prompt_no_todos(self):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        text = prompt_text(get_prompt())
        assert "[TODO]" not in text
        assert "TODO" not in text

    def test_minimum_techniques(self):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        prompt = get_prompt()
        techniques = prompt.get("techniques_applied")
        assert isinstance(techniques, list)
        assert len(techniques) >= 2
        is_valid, errors = validate_prompt_structure(prompt)
        assert is_valid, errors


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
