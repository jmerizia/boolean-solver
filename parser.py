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

axioms = [
    # Associativity
    { 'name': 'assoc-add', 'rule': ['(+ a (+ b c))', '(+ (+ a b) c)'] },
    { 'name': 'assoc-mul', 'rule': ['(* a (* b c))', '(* (* a b) c)'] },
    # Commutativity
    { 'name': 'comm-add', 'rule': ['(+ a b)', '(+ b a)'] },
    { 'name': 'comm-mul', 'rule': ['(* a b)', '(* b a)'] },
    # Absorption
    { 'name': 'abs-add', 'rule': ['(+ a (* a b))', 'a'] },
    { 'name': 'abs-mul', 'rule': ['(* a (+ a b))', 'a'] },
    # Identity
    { 'name': 'iden-add', 'rule': ['(+ a 0)', 'a'] },
    { 'name': 'iden-mul', 'rule': ['(* a 1)', 'a'] },
    # Distributive
    { 'name': 'dist-add', 'rule': ['(+ a (* b c))', '(* (+ a b) (+ a c))'] },
    { 'name': 'dist-mul', 'rule': ['(* a (+ b c))', '(+ (* a b) (* a c))'] },
    # Complements
    { 'name': 'comp-add', 'rule': ['(+ a (~ a))', '1'] },
    { 'name': 'comp-mul', 'rule': ['(* a (~ a))', '0'] },
]

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
    "Parsing error"
    print(text)
    print(' '*idx + '^')
    print('Error:', msg)
    quit(1)

def rerror(msg):
    "General runtime error"
    print('Error:', msg)
    quit(1)

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


def parse(text, tokens=None, root_node=None):

    if tokens is None:
        tokens = tokenize(text)

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


def infix_string(root) -> str:
    if root.typ == 'op':
        if root.token == '~':
            child = infix_string(root.children[0])
            return f'({root.token} {child})'
        else:
            left = infix_string(root.children[0])
            right = infix_string(root.children[1])
            return f'({root.token} {left} {right})'
    if root.typ in ['var', 'prim']:
        return root.token


def generate_variable_names():
    idx = 0
    while True:
        yield f'_{idx}'
        idx += 1


def clone_tree(node):
    new_node = Node(node.token, node.typ)
    for child in node.children:
        new_child = clone_tree(child)
        new_node.add_child(new_child)
    return new_node


def trees_equal_weak(tree_a, tree_b):
    """
    Returns true if the given trees could be made equivalent if
    variable names are modified.
    """
    # TODO
    pass


def trees_equal(tree_a, tree_b):
    # memoize? are there ever repeated calls?
    if tree_a.typ != tree_b.typ:
        return False
    if tree_a.token != tree_b.token:
        return False
    if len(tree_a.children) != len(tree_b.children):
        return False
    for child_a, child_b in zip(tree_a.children, tree_b.children):
        if not trees_equal(child_a, child_b):
            return False
    return True


def rule_applies_at_node(node, rule, scope={}):
    """
    If the rule applies at the given node, this will return the subtrees
    that match the corresponding variables in the tree as a dictionary
    of variable names to references to nodes in the original tree.
    Otherwise, this returns None.

    At each node in the subtree, use the following table:
    rule \ node  |    op          |   var      |   prim  
    -----------------------------------------------------------
        op       | iff same tok * |   False    |   False
        var      |      **        |     **     |     **
        prim     |    False       |   False    | iff same tok

    *   The rules must also be checked recursively for all children.
    **  The rule can be applied iff all instances of this variable
        in the scope of the rule are equivalent in the tree.
    """

    if rule.typ == 'op':
        if node.typ != 'op':
            return None
        if node.token != rule.token:
            return None
    if rule.typ == 'prim':
        if node.typ != 'prim':
            return None
        if rule.token != node.token:
            return None
    if rule.typ == 'var':
        if rule.token in scope:
            if not trees_equal(scope[rule.token], node):
                return None
        else:
            scope[rule.token] = node

    if rule.typ == 'op' and node.typ == 'op':
        for rule_child, node_child in zip(rule.children, node.children):
            if rule_applies_at_node(node_child, rule_child, scope) is None:
                return None
    return scope


def replace_variables(node, scope, variable_name_generator):
    """
    Given a tree, replaces all variables in the tree with (copies) of trees
    as provided in the scope.
    If the variable is not in the scope, then a new variable node is created,
    with a distinct variable name.
    """
    if node.typ == 'var':
        if node.token not in scope:
            name = next(variable_name_generator)
            return Node(name, typ='var')
        else:
            return clone_tree(scope[node.token])
    elif node.typ == 'prim':
        return node
    elif node.typ == 'op':  # node.typ == 'op'
        for i in range(len(node.children)):
            child = node.children[i]
            node.children[i] = replace_variables(child, scope, variable_name_generator)
        return node
    else:
        perror('replace_variables() :: Internal error')


def apply_transformation(node, rule_from, rule_to, variable_name_generator):
    """
    Returns a copy of the given tree with the rule applied to it. 
    If it is not possible to apply the rule at this node, return None.
    Applying a rule is simple:
        First, for each variable in the rule_from, determine
        the corresponding subtree of the given tree (called the "scope").
        Then, clone the rule_to tree, replacing all variables from the "scope"
        with copies of the corresponding subtrees.
        (Note: Technically these subtrees need-not be copied, but for simplicity,
               I will do so for now.)
    """
    scope = rule_applies_at_node(node, rule_from)
    if scope is None:
        return None
    new_node = clone_tree(rule_to)
    new_node = replace_variables(new_node, scope, variable_name_generator)
    return new_node


def possible_next_trees_for_rule(node, rule_from, rule_to, variable_name_generator):
    """
    Return a list of all possible next trees for a given rule.
    """
    possible = []
    new_node = apply_transformation(node, rule_from, rule_to, variable_name_generator)
    if new_node is not None:
        possible.append(new_node)
    for child in node.children:
        possible += possible_next_trees_for_rule(child, rule_from, rule_to, variable_name_generator)
    return possible


def possible_next_trees(node, variable_name_generator):
    """
    Returns a list of all possible next trees (across all axioms).
    Reports as a list of tuples, where each tuple has two values:
        [ ( axiom name, new tree ), ... ]
    """
    possible = []
    for axiom in axioms:
        rule_a, rule_b = axiom['rule']
        # try a -> b
        possible += possible_next_trees_for_rule(node,
                                                 rule_from=rule_a,
                                                 rule_to=rule_b,
                                                 variable_name_generator=variable_name_generator)
        
        # try b -> a
        possible += possible_next_trees_for_rule(node,
                                                 rule_from=rule_b,
                                                 rule_to=rule_a,
                                                 variable_name_generator=variable_name_generator)
    return possible


def main(fname, verbose=False):

    for axiom in axioms:
        if axiom['name'] == 'comp-mul':
            break
    rule_from, rule_to = axiom['rule']
    # print(rule_from)
    # node = apply_transformation(
    #     node=parse('(+ a (~ 0))'),
    #     rule_from=parse(rule_from),
    #     rule_to=parse(rule_to),
    #     variable_name_generator=variable_name_generator,
    # )
    # if node is not None:
    #     print(infix_string(node))
    # else:
    #     print('Cannot be done.')
    variable_name_generator = generate_variable_names()
    p = possible_next_trees(
        node=parse('(* 0 (~ 0))'),
        variable_name_generator=variable_name_generator,
    )
    for node in p:
        print(infix_string(node))
    
    quit()
    # Load axioms
    for axiom in axioms:
        name = axiom['name']
        print(f'Tree for axiom {name}')
        rule_a, rule_b = axiom['rule']
        tree_a, tree_b = parse(rule_a), parse(rule_b)
        print_tree(tree_a)
        print_tree(tree_b)

    with open(fname, 'r') as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if len(line) == 0 or line[0] == '#':
                continue
            tree = parse(line)
            print(f'Tree for line #{idx}:')
            print_tree(tree)
            print(infix_string(tree))

if __name__ == '__main__':
    Fire(main)
