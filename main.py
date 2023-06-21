import ast
from typing import Any, Callable, Generic, TypeVar

with open("sample.py") as f:
    source = f.read()
source_lines = source.splitlines()

tree = ast.parse(source)

T_AST = TypeVar('T_AST', ast.Call, ast.Assign, ast.Subscript)

class MyNodeVisitor(ast.NodeVisitor, Generic[T_AST]):
    def __init__(self) -> None:
        self.matches: list[T_AST] = []
    
    def visit(self, node) -> list[T_AST]:
        super().visit(node)
        return self.matches

class SelfWarningsVisitor(MyNodeVisitor[ast.Subscript]):    
    def visit_Subscript(self, node: ast.Subscript) -> Any:
        if isinstance(node.value, ast.Attribute):
            attribute = node.value
            if isinstance(attribute.value, ast.Name):
                if attribute.value.id == 'self' and attribute.attr == 'warnings':
                    self.matches.append(node)

class AppendSelfWarningsVisitor(MyNodeVisitor[ast.Call]):
    def visit_Call(self, node: ast.Call) -> Any:
        if isinstance(node.func, ast.Attribute):
            attribute = node.func
            if attribute.attr == 'append' and SelfWarningsVisitor().visit(attribute.value):
                self.matches.append(node)

class AssignSelfWarningsVisitor(MyNodeVisitor[ast.Assign]):
    def visit_Assign(self, node: ast.Assign) -> Any:
        if SelfWarningsVisitor().visit(node.targets[0]):
            self.matches.append(node)

class ExtendSelfWarningsVisitor(MyNodeVisitor[ast.Call]):
    def visit_Call(self, node: ast.Call) -> Any:
        if isinstance(node.func, ast.Attribute):
            attribute = node.func
            if attribute.attr == 'extend' and SelfWarningsVisitor().visit(attribute.value):
                self.matches.append(node)

def to_dict_with_lineno(nodes: list[T_AST]) -> dict[int, T_AST]:
    result = {}
    for node in nodes:
        result[node.lineno] = node
    return result

appends = to_dict_with_lineno(AppendSelfWarningsVisitor().visit(tree))
assigns = to_dict_with_lineno(AssignSelfWarningsVisitor().visit(tree))
extends = to_dict_with_lineno(ExtendSelfWarningsVisitor().visit(tree))
