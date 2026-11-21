import hashlib
import hmac
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'signature.py'
spec = importlib.util.spec_from_file_location('pos_signature', path)
signature = importlib.util.module_from_spec(spec)
spec.loader.exec_module(signature)


class StageASignatureTests(unittest.TestCase):
    def test_exact_raw_body_and_binary_key_digest(self):
        key = 'odoo_test_key'
        body = b'{"amount_paise":4000,"event":"payment.captured"}'
        signed = hmac.new(hashlib.sha256(key.encode()).digest(), body, hashlib.sha256).hexdigest()
        self.assertTrue(signature.valid_signature(key, body, signed))
        self.assertFalse(signature.valid_signature(key, body + b' ', signed))
        self.assertFalse(signature.valid_signature('wrong', body, signed))
        self.assertFalse(signature.valid_signature(key, body, signed.upper()))
        self.assertFalse(signature.valid_signature(key, body, '\u2603'))
        self.assertFalse(signature.valid_signature(key, body, None))

    def test_hex_digest_is_not_the_hmac_key(self):
        key, body = 'odoo_test_key', b'{}'
        wrong = hmac.new(hashlib.sha256(key.encode()).hexdigest().encode(), body, hashlib.sha256).hexdigest()
        self.assertFalse(signature.valid_signature(key, body, wrong))


if __name__ == '__main__':
    unittest.main()
