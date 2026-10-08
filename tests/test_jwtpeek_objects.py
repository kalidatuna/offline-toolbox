import base64, json, os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cli'))
import jwtpeek

def encode(value):
    return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip('=')

class ObjectTests(unittest.TestCase):
    def test_header_and_payload_must_be_json_objects(self):
        for header, payload in (([], {}), ({}, []), ({}, None), ('text', {}), ({}, 3)):
            with self.subTest(header=header, payload=payload), self.assertRaisesRegex(ValueError, 'JSON objects'):
                jwtpeek.decode(encode(header) + '.' + encode(payload) + '.')
