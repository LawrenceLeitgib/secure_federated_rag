# app/retrieval/llm.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


@dataclass
class LLMResponse:
    answer: str
    prompt_tokens: int | None = None
    generated_tokens: int | None = None


class QwenLLM:
    """
    Small wrapper around Qwen/Qwen3-0.6B for RAG generation.

    Keeps model loading isolated so the rest of the system can just call:
        llm.generate_answer(query="...", contexts=[...])
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-0.6B",
        max_context_chunks: int = 3,
        max_context_chars_per_chunk: int = 1200,
        max_new_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.8,
        thinking: bool = False,
    ) -> None:
        self.model_name = model_name
        self.max_context_chunks = max_context_chunks
        self.max_context_chars_per_chunk = max_context_chars_per_chunk
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.thinking = thinking

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        # "device_map='auto'" is the standard HF way to place the model on
        # available devices. If you only run on CPU, it still works.
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype="auto",
            device_map="auto",
        )
        self.model.eval()

    def _normalize_contexts(self, contexts: Iterable[str]) -> list[str]:
        cleaned: list[str] = []
        for ctx in contexts:
            text = (ctx or "").strip()
            if not text:
                continue
            cleaned.append(text[: self.max_context_chars_per_chunk])
            if len(cleaned) >= self.max_context_chunks:
                break
        return cleaned

    def _build_messages(self, query: str, contexts: list[str]) -> list[dict[str, str]]:
        context_block = "\n\n".join(
            f"[Context {i + 1}]\n{ctx}"
            for i, ctx in enumerate(contexts)
        )

        system_prompt = (
            "You are a retrieval-augmented assistant.\n"
            "Answer the user's question only using the provided context when possible.\n"
            "If the context is insufficient, say clearly what is missing.\n"
            "Be precise and concise.\n"
        )

        user_prompt = (
            f"Question:\n{query}\n\n"
            f"Retrieved context:\n{context_block}\n\n"
            "Please provide the final answer."
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def generate_answer(
        self,
        query: str,
        contexts: list[str],
    ) -> LLMResponse:
        contexts = self._normalize_contexts(contexts)
        messages = self._build_messages(query=query, contexts=contexts)

        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=self.thinking,
        )

        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        input_len = model_inputs.input_ids.shape[1]

        with torch.no_grad():
            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=True,
                temperature=self.temperature,
                top_p=self.top_p,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        output_ids = generated_ids[0][input_len:]
        answer = self.tokenizer.decode(output_ids, skip_special_tokens=True).strip()

        # If thinking mode is enabled, Qwen may emit <think>...</think>.
        # We remove it from the final answer returned to your app.
        if "</think>" in answer:
            answer = answer.split("</think>", 1)[1].strip()

        return LLMResponse(
            answer=answer,
            prompt_tokens=int(input_len),
            generated_tokens=int(len(output_ids)),
        )