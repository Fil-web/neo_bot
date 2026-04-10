from pathlib import Path
from typing import Optional

from gigachat import GigaChat
from gigachat.models import Chat, Messages

from filka_bot.config import Settings
from filka_bot.prompts import build_system_prompt


class GigaChatService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def ask(
        self,
        history: list[dict[str, str]],
        user_text: str,
        attachments: Optional[list[str]] = None,
        mode: str = "default",
        knowledge_context: str = "",
    ) -> str:
        system_prompt = build_system_prompt(mode=mode, knowledge_context=knowledge_context)
        messages = [Messages(role="system", content=system_prompt)]
        messages.extend(Messages(role=item["role"], content=item["content"]) for item in history)
        messages.append(Messages(role="user", content=user_text, attachments=attachments))

        payload = Chat(messages=messages, model=self._settings.gigachat_model)

        async with GigaChat(
            credentials=self._settings.gigachat_credentials,
            scope=self._settings.gigachat_scope,
            model=self._settings.gigachat_model,
            verify_ssl_certs=self._settings.gigachat_verify_ssl_certs,
        ) as client:
            response = await client.achat(payload)

        return response.choices[0].message.content.strip()

    async def upload_general_file(self, file_path: Path) -> str:
        async with GigaChat(
            credentials=self._settings.gigachat_credentials,
            scope=self._settings.gigachat_scope,
            model=self._settings.gigachat_model,
            verify_ssl_certs=self._settings.gigachat_verify_ssl_certs,
        ) as client:
            uploaded = await client.aupload_file(file=(file_path.name, file_path.read_bytes()), purpose="general")
        return uploaded.id_

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        async with GigaChat(
            credentials=self._settings.gigachat_credentials,
            scope=self._settings.gigachat_scope,
            model=self._settings.gigachat_model,
            verify_ssl_certs=self._settings.gigachat_verify_ssl_certs,
        ) as client:
            response = await client.aembeddings(texts=texts)
        return [item.embedding for item in response.data]
