import os
import json
from getpass import getpass

USE_CI = bool(os.getenv("CI"))


class SecretProvider:
    def __init__(self, name: str, user: str | None = None):
        self.name = name
        self.user = user or os.getenv("USER") or "app"

    def get(self, key: str) -> str:
        # 1) keyring
        try:
            import keyring

            v = keyring.get_password(self.name, f"{self.user}:{key}")
            if v:
                return v
        except Exception:
            pass

        # 2) Облачный/внешний секрет-менеджер (пример-хук)
        v = self._get_from_cloud_secret_manager(key)
        if v:
            return v

        # 3) CI secrets/env
        v = os.getenv(key) or os.getenv(key.upper())
        if v:
            return v

        # 4) Локальный файл (пример: JSON с правами 0600)
        path = os.getenv("APP_SECRETS_FILE", "~/.config/app/secrets.json")
        v = self._get_from_file(os.path.expanduser(path), key)
        if v:
            return v

        # 5) Интерактивно (только вне CI)
        if not USE_CI:
            return getpass(f"Введите секрет {key}: ")

        raise RuntimeError(f"Секрет {key} не найден во всех источниках.")

    @staticmethod
    def _get_from_cloud_secret_manager(key: str) -> str | None:
        # Заглушка: здесь интеграция с Vault/AWS/GCP/Azure.
        return None

    @staticmethod
    def _get_from_file(path: str, key: str) -> str | None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get(key)
        except FileNotFoundError:
            return None
