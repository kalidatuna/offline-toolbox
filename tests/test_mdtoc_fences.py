import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cli'))
import mdtoc

class FenceTests(unittest.TestCase):
    def test_embedded_and_short_fences_do_not_end_the_block(self):
        documents = [
            '````python\n```\n## Hidden\n````\n## Visible\n',
            '```python\n~~~\n## Hidden\n```\n## Visible\n',
            '```python\n```still-code\n## Hidden\n```\n## Visible\n',
        ]
        for document in documents:
            with self.subTest(document=document):
                self.assertEqual(mdtoc.build_toc(document), '- [Visible](#visible)')
