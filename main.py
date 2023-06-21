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

new_source_lines = []

lineno_iter = range(len(source_lines))

for lineno in lineno_iter:
    source_line = source_lines[lineno]
    if lineno in appends:
        append = appends[lineno]
    if lineno in assigns:
        #     Assign(
        # targets=[
        #     Subscript(
        #         value=Attribute(
        #             value=Name(id='self', ctx=Load()),
        #             attr='warnings',
        #             ctx=Load()),
        #         slice=Constant(value='individual'),
        #         ctx=Store())],
        # value=List(elts=[], ctx=Load())),
        #     Assign(
        # targets=[
        #     Subscript(
        #         value=Attribute(
        #             value=Name(id='self', ctx=Load()),
        #             attr='warnings',
        #             ctx=Load()),
        #         slice=Constant(value='name'),
        #         ctx=Store())],
        # value=JoinedStr(
        #     values=[
        #         Constant(value='Sample with the same name ['),
        #         FormattedValue(
        #             value=Subscript(
        #                 value=Name(id='sample', ctx=Load()),
        #                 slice=Constant(value='name'),
        #                 ctx=Load()),
        #             conversion=-1),
        #         Constant(value='] already exists. A new sample with the same name will be created.')]))],
        # Assign(
        #     targets=[
        #         Tuple(
        #             elts=[
        #                 Name(id='reference_genome_obj', ctx=Store()),
        #                 Subscript(
        #                     value=Attribute(
        #                         value=Name(id='self', ctx=Load()),
        #                         attr='errors',
        #                         ctx=Load()),
        #                     slice=Constant(value='reference_genome'),
        #                     ctx=Store()),
        #                 Subscript(
        #                     value=Attribute(
        #                         value=Name(id='self', ctx=Load()),
        #                         attr='warnings',
        #                         ctx=Load()),
        #                     slice=Constant(value='reference_genome'),
        #                     ctx=Store())
        assign = assigns[lineno]
        target = assign.targets[0]
        if isinstance(target, ast.Tuple):
            pass
        elif isinstance(target, ast.Subscript):
            value = assign.value
            if isinstance(value, ast.List):
                if not value.elts:
                    # handle empty list value
                    print(source_line)
                else:
                    value_content = value.elts[0]
                    if isinstance(value_content, ast.Constant):
                        # handle string literal
                        tuple_node = ast.Tuple(elts=[ast.Constant(value_content)], ctx=ast.Load())
                        
    if lineno in extends:
        extend = extends[lineno]
    else:
        pass