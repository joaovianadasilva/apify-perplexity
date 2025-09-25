"""Actor do Apify que envia prompts ao Perplexity."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Mapping, MutableMapping, Optional, Tuple, List

from apify import Actor
from perplexity import Perplexity

DEFAULT_MODEL = "llama-3.1-sonar-small-128k-online"
RAW_KEY = "PERPLEXITY_COMPLETION"


def _build_request_payload(
    actor_input: Mapping[str, Any]
) -> Tuple[Dict[str, Any], str, List[Dict[str, str]]]:
    """Constrói payload para a API do Perplexity a partir do schema simplificado."""

    prompt_text = actor_input.get("prompt")
    if not isinstance(prompt_text, str) or not prompt_text.strip():
        raise ValueError("O campo 'prompt' é obrigatório e deve conter texto.")

    system_prompt = actor_input.get("systemPrompt")
    messages: List[Dict[str, str]] = []

    if system_prompt:
        messages.append({"role": "system", "content": str(system_prompt)})

    messages.append({"role": "user", "content": prompt_text})

    # Converte valores string → float/int com fallback
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

    return payload, prompt_text, messages


async def _call_perplexity(payload: Mapping[str, Any]) -> Any:
    client = Perplexity()
    return await asyncio.to_thread(client.chat.completions.create, **payload)


async def main() -> None:
    async with Actor:
        log = Actor.log

        actor_input: MutableMapping[str, Any] = await Actor.get_input() or {}
        log.info("Executando Actor Apify -> Perplexity", extra={"input": actor_input})

        payload, prompt_summary, messages = _build_request_payload(actor_input)
        log.debug("Payload preparado para envio", extra={"payload": payload})

        completion = await _call_perplexity(payload)

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
