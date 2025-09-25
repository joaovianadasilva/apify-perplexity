"""Actor do Apify que envia prompts ao Perplexity."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from apify import Actor
from perplexity import Perplexity

DEFAULT_MODEL = "llama-3.1-sonar-small-128k-online"
VALID_ROLES = {"system", "user", "assistant", "tool"}
RAW_KEY = "PERPLEXITY_COMPLETION"


def _normalise_messages(
    actor_input: Mapping[str, Any],
) -> Tuple[List[Dict[str, str]], Optional[str]]:
    """Cria a lista de mensagens a partir do input fornecido.

    Retorna um tuplo com (messages, prompt_principal).
    """

    system_prompt = actor_input.get("systemPrompt")
    explicit_messages = actor_input.get("messages")
    messages: List[Dict[str, str]] = []

    if explicit_messages:
        if not isinstance(explicit_messages, Sequence) or isinstance(explicit_messages, (str, bytes)):
            raise ValueError("O campo 'messages' deve ser uma lista de objetos.")

        for idx, message in enumerate(explicit_messages):
            if not isinstance(message, Mapping):
                raise ValueError(
                    f"A mensagem na posição {idx} deve ser um objeto com 'role' e 'content'."
                )

            role = str(message.get("role", "")).strip().lower()
            content = message.get("content")

            if role not in VALID_ROLES:
                raise ValueError(
                    f"Role inválido na posição {idx}: '{role}'. Valores aceitos: {sorted(VALID_ROLES)}"
                )
            if not isinstance(content, str) or not content.strip():
                raise ValueError(f"A mensagem na posição {idx} deve possuir 'content' textual.")

            messages.append({"role": role, "content": content})

        if system_prompt:
            messages.insert(0, {"role": "system", "content": str(system_prompt)})

        first_user = next((m["content"] for m in messages if m["role"] == "user"), None)
        return messages, first_user

    prompt_text = actor_input.get("prompt")
    if not isinstance(prompt_text, str) or not prompt_text.strip():
        raise ValueError("Informe ao menos um 'prompt' ou uma lista de 'messages'.")

    if system_prompt:
        messages.append({"role": "system", "content": str(system_prompt)})

    messages.append({"role": "user", "content": prompt_text})
    return messages, prompt_text


def _build_request_payload(
    actor_input: Mapping[str, Any]
) -> Tuple[Dict[str, Any], Optional[str], List[Dict[str, str]]]:
    messages, prompt_summary = _normalise_messages(actor_input)

    # Conversões seguras de string → float/int
    temp_val = actor_input.get("temperature")
    top_p_val = actor_input.get("topP")
    max_tokens_val = actor_input.get("maxTokens")

    payload: Dict[str, Any] = {
        "model": actor_input.get("model") or DEFAULT_MODEL,
        "messages": messages,
        "temperature": float(temp_val) if temp_val is not None else 0.2,
        "top_p": float(top_p_val) if top_p_val is not None else 0.95,
        "search_mode": actor_input.get("searchMode") or "auto",
    }

    if max_tokens_val is not None:
        payload["max_tokens"] = int(max_tokens_val)

    # Remove chaves com valor None
    payload = {key: value for key, value in payload.items() if value is not None}

    return payload, prompt_summary, messages


async def _call_perplexity(payload: Mapping[str, Any]) -> Any:
    client = Perplexity()
    # roda em thread para não travar o loop do Actor
    return await asyncio.to_thread(client.chat.completions.create, **payload)


async def main() -> None:
    async with Actor:
        log = Actor.log

        actor_input: MutableMapping[str, Any] = await Actor.get_input() or {}
        log.info("Executando Actor Apify -> Perplexity", extra={"input": actor_input})

        try:
            payload, prompt_summary, messages = _build_request_payload(actor_input)
            log.debug("Payload preparado para envio", extra={"payload": payload})
        except Exception as e:
            log.error(f"Erro ao construir payload: {e}")
            raise

        try:
            completion = await _call_perplexity(payload)
        except Exception as e:
            log.error(f"Erro ao chamar a API do Perplexity: {e}")
            raise

        if hasattr(completion, "model_dump"):
            completion_dict = completion.model_dump()
        elif isinstance(completion, Mapping):
            completion_dict = dict(completion)
        else:
            raise TypeError("Resposta inesperada do cliente Perplexity.")

        primary_choice = None
        choices = completion_dict.get("choices")
        if isinstance(choices, list) and choices:
            primary_choice = choices[0]

        response_payload: Any = None
        if isinstance(primary_choice, Mapping):
            message_block = primary_choice.get("message")
            if isinstance(message_block, Mapping):
                response_payload = message_block.get("content")
            else:
                response_payload = message_block
        else:
            response_payload = primary_choice

        dataset_item = {
            "prompt": prompt_summary,
            "messages": messages,
            "model": completion_dict.get("model"),
            "response": response_payload,
            "citations": completion_dict.get("citations"),
            "usage": completion_dict.get("usage"),
        }

        await Actor.push_data(dataset_item)
        log.info("Resposta registrada no dataset padrão.")

        if actor_input.get("returnRaw"):
            await Actor.set_value(RAW_KEY, completion_dict)
            log.info("Resposta completa armazenada no Key-value store padrão.", extra={"key": RAW_KEY})


if __name__ == "__main__":
    asyncio.run(main())
