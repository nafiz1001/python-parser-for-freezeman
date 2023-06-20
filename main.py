import re
from os import path
from tree_sitter import Language, Parser, Node

LIB_PATH = path.join("build", "languages.so")
Language.build_library(
    LIB_PATH,
    [
        path.join("..", "tree-sitter-python"),
    ],
)
PYTHON = Language(LIB_PATH, "python")

parser = Parser()
parser.set_language(PYTHON)

self_warnings_query = PYTHON.query("""
(subscript
    value: (attribute
        object: (identifier) @identifier-name (#eq? @identifier-name self)
        attribute: (identifier) @indexed-name (#eq? @indexed-name warnings))
    subscript: (string string_content: (string_content)))
""")

def is_self_warnings(node: Node):
    if node.type == "subscript":
        if node.children[0].type == "attribute" and node.children[0].children[0].text == b'self':
            attribute_node = node.children[0].children[2]
            if attribute_node.type == "identifier" and attribute_node.text == b"warnings":
                return True
    return False

# with open("sample.py", "rb") as f:
#     tree = parser.parse(f.read())

tree = parser.parse(b"""
self.warnings['hello']
self.warnings['world']
""")

print(self_warnings_query.captures(tree.root_node))