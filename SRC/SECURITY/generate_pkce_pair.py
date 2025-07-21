import secrets
import base64
import hashlib


def generate_pkce_params() -> tuple[str, str]:
    """Генерирует пару code_verifier и code_challenge для PKCE."""
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
        .decode()
        .replace("=", "")
    )
    return code_verifier, code_challenge
