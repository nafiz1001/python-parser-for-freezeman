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


def is_self_warnings(node: Node):
    if node.type == "subscript":
        if node.children[0].type == "attribute" and node.children[0].children[0].text == b'self':
            attribute_node = node.children[0].children[2]
            if attribute_node.type == "identifier" and attribute_node.text == b"warnings":
                return True
    return False

def is_pattern_list(node: Node):
    return node.type == "pattern_list"

def is_expression_statement(node: Node):
    return node.type == "expression_statement"

def is_assignment_expression(node: Node):
    return node.type == "assignment"

def is_append_expression(node: Node):
    return (
        node.type == 'call' and
        node.children[0].type == 'attribute' and
        node.children[0].children[2].type == "identifier" and
        node.children[0].children[2].text == b'append'
    )

def is_extend_expression(node: Node):
    return (
        node.type == 'call' and
        node.children[0].type == 'attribute' and
        node.children[0].children[2].type == "identifier" and
        node.children[0].children[2].text == b'extend'
    )

with open("sample.py", "rb") as f:
    tree = parser.parse(f.read())

print(tree.root_node.sexp())