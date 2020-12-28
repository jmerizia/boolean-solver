from fire import Fire

"""
Grammar
(simple prefix paren notation)

PRIMITIVE := '0' | '1'
VARIABLE := ['a-zA-Z']
OPERATOR := '*' | '+' | '~
STATEMENT := PRIMITIVE
          |  VARIABLE
          |  '(' OPERATOR ' ' STATEMENT ' ' STATEMENT ')'
"""

primitive_tokens = '10'
variable_tokens = 'abcdefghijklmnopqrstuvwxyz' + \
                  'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
operator_tokens = '*+~'
all_tokens = '()' + primitive_tokens + variable_tokens + operator_tokens

class Node:
    def __init__(self, token, typ):
        self.token = token
        self.typ = typ
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def __str__(self):
        return f'{self.token} : {self.typ}'


def perror(text, msg, idx):
    print(text)
    print(' '*idx + '^')
    print('Error:', msg)
    quit()


def tokenize(text):
    idx = 0

    while idx < len(text):

        # skip whitespace
        while idx < len(text) and text[idx] == ' ':
            idx += 1

        if idx < len(text) and text[idx] in all_tokens:
            tok = text[idx]
            idx += 1
            yield tok, idx

        else:
            perror(text, f'Unexpected character at {idx}.', idx)


def parse(text, tokens, root_node=None):

    try:
        tok, idx = next(tokens)
    except StopIteration:
        perror(text, f'Unexpected end of line.', None)

    if tok == '(':
        tok, idx = next(tokens)
        node = Node(tok, 'op')
        if tok not in operator_tokens:
            perror(text, f'Unexpected operator at column {idx-1}', idx-1)
        parse(text, tokens, root_node=node)
        if tok in '+*':
            parse(text, tokens, root_node=node)
        tok, idx = next(tokens)
        if tok != ')':
            perror(text, f'Expected closing paren at column {idx-1}', idx-1)
    elif tok in primitive_tokens:
        node = Node(tok, 'prim')
    elif tok in variable_tokens:
        node = Node(tok, 'var')
    else:
        perror(text, f'Unexpected token at column {idx-1}', idx-1)

    if root_node is None:
        try:
            tok, idx = next(tokens)
        except StopIteration:
            return node
        else:
            perror(text, f'Expected end of statement at column {idx-1}', idx-1)
    else:
        root_node.add_child(node)
        return root_node


def print_tree(root, depth=0):
    print('  '*depth + str(root))
    for node in root.children:
        print_tree(node, depth=depth+1)


def infix(root) -> str:
    if root.typ == 'op':
        if root.token == '~':
            child = infix(root.children[0])
            return f'({root.token} {child})'
        else:
            left = infix(root.children[0])
            right = infix(root.children[1])
            return f'({root.token} {left} {right})'
    if root.typ in ['var', 'prim']:
        return root.token

def main(fname):
    with open(fname, 'r') as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if len(line) == 0 or line[0] == '#':
                continue
            tokens = tokenize(line)
            tree = parse(line, tokens)
            print(f'Tree for line #{idx}:')
            print_tree(tree)
            print(infix(tree))

if __name__ == '__main__':
    Fire(main)
