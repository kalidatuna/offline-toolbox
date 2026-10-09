import unittest

from md_link_check.parse import mask_code_spans, mask_comments, parse
from md_link_check.slug import Slugger, heading_text, slugify


def dests(text):
    return [link.dest for link in parse(text).links]


class SlugTests(unittest.TestCase):
    def test_github_rules(self):
        cases = {
            "Installation": "installation",
            "Foo & Bar": "foo--bar",
            "What's new in v2.0?": "whats-new-in-v20",
            "The `--json` flag": "the---json-flag",
            "`__init__` method": "__init__-method",
            "__Bold__ and *em*": "bold-and-em",
            "snake_case name": "snake_case-name",
            "[Linked](http://x) title": "linked-title",
            "Tom &amp; Jerry": "tom--jerry",
            "<em>Tagged</em> heading": "tagged-heading",
            "ქართული სათაური": "ქართული-სათაური",
            "Ünïcödé Straße": "ünïcödé-straße",
        }
        for heading, expected in cases.items():
            with self.subTest(heading=heading):
                self.assertEqual(slugify(heading_text(heading)), expected)

    def test_duplicates_get_suffixes(self):
        slugger = Slugger()
        got = [slugger.add(h) for h in ["Usage", "Usage", "Usage-1", "Usage"]]
        self.assertEqual(got, ["usage", "usage-1", "usage-1-1", "usage-2"])


class MaskTests(unittest.TestCase):
    def test_code_spans_keep_columns(self):
        line = "a `[x](y)` b ``c ` d`` e"
        masked = mask_code_spans(line)
        self.assertEqual(len(masked), len(line))
        self.assertNotIn("[x](y)", masked)
        self.assertTrue(masked.endswith(" e"))

    def test_unclosed_backtick_is_literal(self):
        self.assertEqual(mask_code_spans("a ` b"), "a ` b")

    def test_comments_span_lines(self):
        first, state = mask_comments("keep <!-- drop", False)
        self.assertEqual((first.rstrip(), state), ("keep", True))
        second, state = mask_comments("still --> back", state)
        self.assertEqual((second.strip(), state), ("back", False))


class LinkExtractionTests(unittest.TestCase):
    def test_inline_forms(self):
        text = (
            '[a](one.md) [b](two.md "title") [c](<with space.md>) '
            "[d](p_(1).md) [e](es\\_c.md) ![img](pic.png)"
        )
        self.assertEqual(
            dests(text), ["one.md", "two.md", "with space.md", "p_(1).md", "es_c.md", "pic.png"]
        )
        self.assertEqual(parse(text).links[-1].kind, "image")

    def test_entity_references_are_decoded(self):
        text = '[a](#agn&#x00F3;sticos) [b](x.md?a=1&copy=2) [c](a&amp;b.md) <a href="t&eacute;.md">'
        self.assertEqual(dests(text), ["#agnósticos", "x.md?a=1&copy=2", "a&b.md", "té.md"])

    def test_nested_badge(self):
        doc = parse("[![CI](badge.svg)](ci.md)")
        self.assertEqual([(l.dest, l.kind) for l in doc.links], [("badge.svg", "image"), ("ci.md", "link")])

    def test_columns_are_one_based(self):
        link = parse("x [y](z.md)").links[0]
        self.assertEqual((link.line, link.column), (1, 7))

    def test_escaped_and_spaced_brackets_are_not_links(self):
        self.assertEqual(dests(r"\[a\](b.md) [a] (b.md)"), [])

    def test_unescaped_space_is_malformed(self):
        link = parse("[a](my file.md)").links[0]
        self.assertTrue(link.malformed)
        self.assertEqual(link.dest, "my file.md")

    def test_code_and_comments_are_skipped(self):
        text = "\n".join(
            [
                "```md",
                "[a](fenced.md)",
                "```",
                "~~~~",
                "[b](tilde.md)",
                "```",
                "[c](still-fenced.md)",
                "~~~~",
                "`[d](span.md)` <!-- [e](comment.md)",
                "[f](comment-continues.md) -->",
                "> ```",
                "> [g](quoted-fence.md)",
                "> ```",
                "[ok](real.md)",
            ]
        )
        self.assertEqual(dests(text), ["real.md"])

    def test_fence_indented_in_list_item(self):
        text = "- item\n\n    ```text\n    [bad](([x](y)))\n    ```\n\n[ok](z.md)"
        self.assertEqual(dests(text), ["z.md"])

    def test_front_matter_is_skipped(self):
        self.assertEqual(dests("---\nref: [a](x.md)\n---\n[b](y.md)"), ["y.md"])

    def test_html_links(self):
        text = '<a href="a.md#x">a</a> <img src=\'b.png\' alt=""> <A HREF="c.md">'
        self.assertEqual(dests(text), ["a.md#x", "b.png", "c.md"])


class ReferenceTests(unittest.TestCase):
    def test_definitions_and_uses(self):
        doc = parse(
            "[text][Label]  [Collapsed][]  [shortcut]  a[0][1]\n\n"
            "[label]: target.md\n"
            "  [collapsed]: <other file.md> 'title'\n"
            "[^1]: a footnote, not a link"
        )
        self.assertEqual(doc.definitions, {"label": "target.md", "collapsed": "other file.md"})
        self.assertEqual([u.label for u in doc.ref_uses], ["Label", "Collapsed"])
        self.assertEqual([(l.dest, l.kind) for l in doc.links], [("target.md", "definition"), ("other file.md", "definition")])


    def test_brackets_inside_link_label_are_not_references(self):
        doc = parse("[Part 2 [Arabic] [word][other]](https://x.y) [![i][img]](a.md)")
        self.assertEqual([u.label for u in doc.ref_uses], ["img"])


class AnchorTests(unittest.TestCase):
    def test_heading_styles(self):
        doc = parse(
            "# Title #\n"
            "Setext One\n"
            "==========\n"
            "multi line\n"
            "setext\n"
            "------\n"
            "- list item\n"
            "---\n"
            "> ## Quoted\n"
            '<a name="Custom"></a><div id=\'box\'></div>\n'
            "```\n# not a heading\n```\n"
            "#hashtag\n"
        )
        self.assertEqual(
            doc.anchors, {"title", "setext-one", "multi-line-setext", "quoted", "custom", "box"}
        )


if __name__ == "__main__":
    unittest.main()
