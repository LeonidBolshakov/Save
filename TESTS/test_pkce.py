
from SRC.YADISK.OAUTH.generate_pkce_pair import generate_pkce_params

def test_generate_pkce_params_format():
    verifier, challenge = generate_pkce_params()
    assert isinstance(verifier, str) and isinstance(challenge, str)
    assert verifier and challenge and verifier != challenge
    # base64url safe characters
    assert all(c.isalnum() or c in "-._~" or c in "_-" for c in challenge)
