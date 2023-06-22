import ast
from typing import Any, Callable, Generic, TypeVar
import itertools

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

source_lines_iter = enumerate(source_lines)

def handle_joinedstr(js: ast.JoinedStr) -> tuple[str, list[ast.FormattedValue]]:
    format_args: list[ast.FormattedValue] = []
    for v in js.values:
        if isinstance(v, ast.FormattedValue):
            format_args.append(v)

    formatted_string = ast.get_source_segment(source, js)
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
        append = appends[lineno]
        func = ast.get_source_segment(source, append.func)
        arg = append.args[0]
        if isinstance(arg, ast.JoinedStr):
            formatted_string, format_args = handle_joinedstr(arg)
            formatted_string = formatted_string.splitlines()
            new_source_lines.append(f'{" " * append.col_offset}{func}(({formatted_string[0]}')
            for s in formatted_string[1:]:
                new_source_lines.append(s)
                next(source_lines_iter)
            new_source_lines[-1] += f', [{", ".join([ast.get_source_segment(source, f.value) for f in format_args])}]))'
        if isinstance(arg, ast.Constant):
            func = ast.get_source_segment(source, append.func)
            arg = append.args[0]
            lines = f'{" " * append.col_offset}{func}(({ast.get_source_segment(source, arg)}, [])'.splitlines()
            new_source_lines.append(lines[0])
            for line in lines[1:]:
                new_source_lines.append(line)
                next(source_lines_iter)
            new_source_lines[-1] += ", []))"
    elif lineno in assigns:
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
            self_warning = SelfWarningsVisitor().visit(target)[0]
            self_warning_text = ast.get_source_segment(source, self_warning)
            new_source_lines.append(source_line)
            new_source_lines.append(f'{" " * target.col_offset}{self_warning_text} = [(x, []) for x in {self_warning_text}]')
        elif isinstance(target, ast.Subscript):
            # assigning to self.warnings[somekey]
            value_obj = assign.value
            if isinstance(value_obj, ast.List):
                if not value_obj.elts:
                    # handle empty list value
                    skip_node(assign)
                else:
                    # assume only one value present in list literal
                    value_obj = value_obj.elts[0]
                    if isinstance(value_obj, ast.Constant):
                        splitted_formatted_string = f'{source_line[0:target.end_col_offset]} = [({ast.get_source_segment(source, value_obj)}, [])]'.splitlines()
                        new_source_lines.append(splitted_formatted_string[0])
                        for s in splitted_formatted_string[1:]:
                            new_source_lines.append(s)
                            next(source_lines_iter)
                    if isinstance(value_obj, ast.JoinedStr):
                        formatted_string, format_args = handle_joinedstr(value_obj)

                        splitted_formatted_string = formatted_string.splitlines()
                        new_source_lines.append(f'{source_line[0:target.end_col_offset]} = [({splitted_formatted_string[0]}')
                        for s in splitted_formatted_string[1:]:
                            new_source_lines.append(s)
                            next(source_lines_iter)
                        new_source_lines[-1] += (f', [{", ".join([ast.get_source_segment(source, f.value) for f in format_args])}])]')
            elif isinstance(value_obj, ast.Constant):
                splitted_formatted_string = f'{source_line[0:target.end_col_offset]} = ({ast.get_source_segment(source, value_obj)}, [])'.splitlines()
                new_source_lines.append(splitted_formatted_string[0])
                for s in splitted_formatted_string[1:]:
                    new_source_lines.append(s)
                    next(source_lines_iter)
            elif isinstance(value_obj, ast.JoinedStr):
                formatted_string, format_args = handle_joinedstr(value_obj)

                splitted_formatted_string = formatted_string.splitlines()
                new_source_lines.append(f'{source_line[0:target.end_col_offset]} = ({splitted_formatted_string[0]}')
                for s in splitted_formatted_string[1:]:
                    new_source_lines.append(s)
                    next(source_lines_iter)
                new_source_lines[-1] += f', [{", ".join([ast.get_source_segment(source, f.value) for f in format_args])}])'
    elif lineno in extends:
        extend = extends[lineno]
    else:
        new_source_lines.append(source_line)
    
print("\n".join(new_source_lines))