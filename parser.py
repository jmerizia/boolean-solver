from collections import deque
import itertools
import time
import cProfile
from functools import lru_cache
import random
import sys

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

LARGE_PRIME = 1000_000_007

# primes = []
# def generate_primes(n=10000):
#     is_prime = [True] * n
#     is_prime[0] = False
#     is_prime[1] = False
#     for i in range(2, n):
#         for k in range(i*i, n, i):
#             is_prime[k] = False
#     for i in range(2, n):
#         if is_prime[i]:
#             primes.append(i)
# generate_primes(n=1000)


@lru_cache(10000)
def hash_string(s):
    h = 0
    n = len(s)
    for i, c in enumerate(s):
        h += ord(c) * pow(31, n-i-1, LARGE_PRIME)
    return h % LARGE_PRIME


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


def get_axiom(name):
    for axiom in axioms:
        if axiom['name'] == name:
            return axiom
    rerror(f'No such axiom {name}')


class Node:
    def __init__(self, token, typ):
        self.token = token
        self.typ = typ
        self.children = []

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
        root_node.children.append(node)
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


c = 0
def clone_tree(node):
    global c
    c += 1
    new_node = Node(node.token, node.typ)
    for child in node.children:
        new_child = clone_tree(child)
        new_node.children.append(new_child)
    return new_node


def trees_equal_weak(tree_a, tree_b, replacements=None):
    """
    Returns true if the given trees could be made equivalent if
    variable names are modified.
    """

    if replacements is None:
        replacements = {}

    if tree_a.typ != tree_b.typ:
        return False
    if tree_a.typ == 'var':
        if tree_a.token in replacements:
            if replacements[tree_a.token] != tree_b.token:
                return False
        else:
            replacements[tree_a.token] = tree_b.token
    else:
        if tree_a.token != tree_b.token:
            return False
        if len(tree_a.children) != len(tree_b.children):
            return False
        for child_a, child_b in zip(tree_a.children, tree_b.children):
            if not trees_equal_weak(child_a, child_b):
                return False
    return True


# memoize? are there ever repeated calls?
def trees_equal(tree_a, tree_b):
    """
    Returns true if the given trees are strictly equal.
    Each tree must have the same structure, and each pair
    of corresponding nodes in each tree must have the same typ and token.
    """
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



def hash_tree(node, depth=1):
    """
    Hashes a tree in a strict fashion so that the tree structures should be
    equal and typ and token for all corresponding nodes should be equal.
    """
    h = 0
    if node.typ == 'var':
        h += pow(37, depth, LARGE_PRIME)
        h += hash_string(node.token)
    elif node.typ == 'prim':
        h += pow(41, depth, LARGE_PRIME)
        if node.token == '1':
            h += pow(43, depth, LARGE_PRIME)
        else:
            h += pow(47, depth, LARGE_PRIME)
    elif node.typ == 'op':
        if node.token == '*':
            h += pow(53, depth, LARGE_PRIME)
        else:
            h += pow(59, depth, LARGE_PRIME)
        for idx, child in enumerate(node.children):
            h += hash_tree(child, depth=depth+1)
    return h % LARGE_PRIME


def hash_tree_weak(node, index_generator=None, variable_hashes=None):
    """
    Return an integer hash of the given tree in such a way that two trees that are strictly equal
    (including correct variable names) have the same hash.
    """

    if index_generator is None:
        index_generator = itertools.count(4)
    if variable_hashes is None:
        variable_hashes = {}

    h = 1
    if node.typ == 'op':
        h = (h * primes[0]) % LARGE_PRIME
        h = (h * ord(node.token)) % LARGE_PRIME
        for idx, child in enumerate(node.children):
            child_hash = hash_tree_weak(child,
                                   index_generator=index_generator,
                                   variable_hashes=variable_hashes)
            h = (h * (idx + child_hash)) % LARGE_PRIME
    elif node.typ == 'prim':
        h = (h * primes[1]) % LARGE_PRIME
        h = (h * ord(node.token)) % LARGE_PRIME
    elif node.typ == 'var':
        h = (h * primes[2]) % LARGE_PRIME
        if node.token not in variable_hashes:
            idx = next(index_generator)
            if idx > len(primes):
                rerror('hash_tree_weak() :: We need more primes!')
            variable_hashes[node.token] = primes[idx]
        h = (h * variable_hashes[node.token]) % LARGE_PRIME
    return h


def rule_applies_at_node(node, rule, scope=None):
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

    if scope is None:
        scope = {}

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


def possible_next_trees_for_rule(node, rule_name, rule_from, rule_to, variable_name_generator):
    """
    Return a list of all possible next trees for a given rule.
    """
    possible = []
    new_node = apply_transformation(node, rule_from, rule_to, variable_name_generator)
    if new_node is not None:
        possible.append((rule_name, new_node))
    for i in range(len(node.children)):
        child = node.children[i]
        child_possible = possible_next_trees_for_rule(child, rule_name, rule_from, rule_to, variable_name_generator)
        for child_rule_name, child_transformed in child_possible:
            copy = clone_tree(node)
            copy.children[i] = child_transformed
            possible.append((child_rule_name, copy))
    return possible


def possible_next_trees(node, variable_name_generator=None):
    """
    Returns a list of all possible next trees (across all axioms).
    Reports as a list of tuples, where each tuple has two values:
        [ ( axiom name, new tree ), ... ]
    """

    if variable_name_generator is None:
        variable_name_generator = generate_variable_names()

    possible = []
    for axiom in axioms:
        rule_a, rule_b = axiom['rule']
        rule_tree_a, rule_tree_b = parse(rule_a), parse(rule_b)
        # try a -> b
        possible += possible_next_trees_for_rule(node,
                                                 rule_name=axiom['name'],
                                                 rule_from=rule_tree_a,
                                                 rule_to=rule_tree_b,
                                                 variable_name_generator=variable_name_generator)

        # try b -> a
        possible += possible_next_trees_for_rule(node,
                                                 rule_name=axiom['name'],
                                                 rule_from=rule_tree_b,
                                                 rule_to=rule_tree_a,
                                                 variable_name_generator=variable_name_generator)
    return possible


def find_shortest_path(start_tree, target_tree, max_size=100, max_depth=8):
    """
    Attempts to find a shortest path from the start tree to the target tree.
    If no path of length less than or equal to max_depth exists,
    or where a tree of size greater than max_size is required in all shortest paths,
    then None is return.
    """

    Q = deque()
    visited = set()
    parent = {}
    depth = {}

    htarget = infix_string(target_tree)
    hstart = infix_string(start_tree)
    Q.append(start_tree)
    depth[hstart] = 0

    while len(Q) > 0:
        u = Q.popleft()
        hu = infix_string(u)

        if hu == htarget:
            path = []
            cur = u
            hcur = hu
            while hcur != hstart:
                par, rule_name = parent[hcur]
                path.append((cur, rule_name))
                cur = par
                hcur = infix_string(par)
            return list(reversed(path))

        if depth[hu] >= max_depth:
            continue

        for rule_name, v in possible_next_trees(u):
            hv = infix_string(v)
            if hv not in visited:
                visited.add(hv)
                depth[hv] = depth[hu] + 1
                parent[hv] = (u, rule_name)
                Q.append(v)
    return None

def main(fname):

    # node = parse('1')
    # for i in range(10):
    #     name, node = random.choice(possible_next_trees(node))
    # print(len(infix_string(node)))
    # for i in range(10000):
    #     infix_string(node)
    # quit()

    #axiom = get_axiom('abs-add')
    #a = parse(axiom['rule'][0])
    #b = parse(axiom['rule'][1])
    #res = apply_transformation(parse('(* 0 1)'), b, a, variable_name_generator=generate_variable_names())
    #print(infix_string(res))
    # p = possible_next_trees(parse('(* 0 1)'))
    # for rule_name, node in p:
    #     print(infix_string(node), rule_name)
    # quit()

    # start = parse('(+ a (+ b c))')
    # target = parse('(+ (+ a b) c)')
    start = parse('1')
    target = parse('0')
    max_depth = 5
    st = time.time()
    path = find_shortest_path(start, target, max_depth=max_depth)
    en = time.time()
    print(f'prove {infix_string(start)} = {infix_string(target)}')
    if path is None:
        print(f'No path of length <= {max_depth}.')
    else:
        for idx, (node, rule_name) in enumerate(path):
            print(f'  #{idx+1}  {infix_string(node)}  w/ {rule_name}')
    print(f'Done in {en-st:0.2f} seconds.')

    print(c)

    quit()

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
    # cProfile.run('main(fname=\'example.txt\')')
    # Fire(main)
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} [filename]')
        quit(1)
    main(fname=sys.argv[1])
