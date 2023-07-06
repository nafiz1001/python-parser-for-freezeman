from _ast import Attribute
import ast
from typing import Any, Callable, Generic, TypeVar
import itertools
import re
import sys

with open(sys.argv[1]) as f:
    source = f.read()
source_lines = source.splitlines()

tree = ast.parse(source)
# print(ast.dump(tree, indent=4))

T_AST = TypeVar('T_AST', ast.Call, ast.Assign, ast.Subscript)

class MyNodeVisitor(ast.NodeVisitor, Generic[T_AST]):
    def __init__(self) -> None:
        self.matches: list[T_AST] = []
    
    def visit(self, node) -> list[T_AST]:
        super().visit(node)
        return self.matches

class WarningsVisitor(MyNodeVisitor[ast.Name]):
    def visit_Name(self, name: ast.Name) -> Any:
        if name.id == 'warnings':
            self.matches.append(name)

class AppendWarningsVisitor(MyNodeVisitor[ast.Call]):
    def visit_Call(self, node: ast.Call) -> Any:
        if isinstance(node.func, ast.Attribute):
            attribute = node.func
            if attribute.attr == 'append' and WarningsVisitor().visit(attribute.value):
                self.matches.append(node)


def to_dict_with_lineno(nodes: list[T_AST]) -> dict[int, T_AST]:
    result = {}
    for node in nodes:
        result[node.lineno] = node
    return result

appends = to_dict_with_lineno(AppendWarningsVisitor().visit(tree))

new_source_lines = []

source_lines_iter = enumerate(source_lines)

def handle_joinedstr(js: ast.JoinedStr) -> tuple[str, list[ast.FormattedValue]]:
    format_args: list[ast.FormattedValue] = []
    for v in js.values:
        if isinstance(v, ast.FormattedValue):
            format_args.append(v)

    formatted_string = ast.get_source_segment(source, js)[1:]
    forextralines = re.findall(r'\n\s*', formatted_string)
    if forextralines:
        formatted_string = formatted_string.replace(forextralines[0] + 'f', forextralines[0])
    for i, format_arg in enumerate(format_args):
        formatted_string = formatted_string.replace('{' + ast.get_source_segment(source, format_arg.value) + '}', '{'f'{i}''}')
    
    return formatted_string, format_args

for source_line_index, source_line in source_lines_iter:
    lineno = source_line_index + 1

    def skip_node(node: ast.AST, append=True):
        global source_line

        if append:
            new_source_lines.append(source_line)
        skipcount = node.end_lineno - node.lineno
        for _ in range(skipcount):
            _, source_line = next(source_lines_iter)
            if append:
                new_source_lines.append(source_line)

    if lineno in appends:
        # Append
        append = appends[lineno]
        func = ast.get_source_segment(source, append.func)
        arg = append.args[0]
        if isinstance(arg, ast.JoinedStr):
            # append f-string
            formatted_string, format_args = handle_joinedstr(arg)
            formatted_string = formatted_string.splitlines()
            new_source_lines.append(f'{" " * append.col_offset}{func}(({formatted_string[0]}')
            for s in formatted_string[1:]:
                new_source_lines.append(s)
                next(source_lines_iter)
            new_source_lines[-1] += f', [{", ".join([ast.get_source_segment(source, f.value) for f in format_args])}]))'
        if isinstance(arg, ast.Constant):
            # append string
            func = ast.get_source_segment(source, append.func)
            arg = append.args[0]
            lines = f'{" " * append.col_offset}{func}(({ast.get_source_segment(source, arg)}, []))'.splitlines()
            new_source_lines.append(lines[0])
            for line in lines[1:]:
                new_source_lines.append(line)
                next(source_lines_iter)
    else:
        new_source_lines.append(source_line)
    
# print("\n".join(new_source_lines))
with open(sys.argv[1], 'w') as f:
    f.write("\n".join(new_source_lines))