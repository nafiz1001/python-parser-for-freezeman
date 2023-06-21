from _ast import AST, Assign, Call, FunctionDef, Name, Subscript, Attribute
import ast
from typing import Any, Callable

with open("sample.py") as f:
    source = f.read()
source_lines = source.splitlines()

tree = ast.parse(source)

class MyNodeVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.matches: list[Subscript] = []
    
    def visit(self, node):
        super().visit(node)
        return self.matches

class SelfWarningsVisitor(MyNodeVisitor):    
    def visit_Subscript(self, node: Subscript) -> Any:
        if isinstance(node.value, Attribute):
            attribute = node.value
            if isinstance(attribute.value, Name):
                name = attribute.value
                if name.id == 'self' and attribute.attr == 'warnings':
                    self.matches.append(node)

class AppendSelfWarningsVisitor(MyNodeVisitor):
    def visit_Call(self, node: Call) -> Any:
        if isinstance(node.func, Attribute):
            attribute = node.func
            if attribute.attr == 'append' and SelfWarningsVisitor().visit(node):
                self.matches.append(node)

class AssignSelfWarningsVisitor(MyNodeVisitor):
    def visit_Assign(self, node: Assign) -> Any:
        if SelfWarningsVisitor().visit(node.targets[0]):
            self.matches.append(node)

class ExtendSelfWarningsVisitor(MyNodeVisitor):
    def visit_Call(self, node: Call) -> Any:
        if isinstance(node.func, Attribute):
            attribute = node.func
            if attribute.attr == 'extend' and SelfWarningsVisitor().visit(node):
                self.matches.append(node)


for node in AssignSelfWarningsVisitor().visit(tree) + AppendSelfWarningsVisitor().visit(tree) + ExtendSelfWarningsVisitor().visit(tree):
    print(source_lines[node.lineno-1][node.col_offset:])