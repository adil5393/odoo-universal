import hashlib
import hmac


def valid_signature(api_key, body, signature):
    if not isinstance(signature, str):
        return False
    expected = hmac.new(hashlib.sha256(api_key.encode('utf-8')).digest(), body, hashlib.sha256).hexdigest()
    try:
        return hmac.compare_digest(signature, expected)
    except TypeError:
        return False
