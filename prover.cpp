#include <string>
#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <map>
#include <queue>
#include <set>
#include <algorithm>
#include <chrono>
#include <iomanip>
using namespace std;

/*
Grammar
(simple prefix paren notation)

primitive -> '0' | '1'
id -> { <alpha> | '_' } { <alphanumeric> }*
binary_operator -> '*' | '+'
unary_operator -> '~'
int_param -> 'max_tree_size'
           | 'max_search_depth'
bool_param -> 'use_proofs_as_axioms'
formula -> <primitive>
         | <id>
         | '(' <binary_operator> <formula> <formula> ')'
         | '(' <unary_operator> <formula> ')'
command -> 'axiom' <id> ':' <formula> '=' <formula> '.'
         | 'prove' <formula> '.'
         | 'param' <int_param> <int> '.'
         | 'param' <bool_param> <bool> '.'
*/

bool is_bop_token(string tok) { return tok == "*" || tok == "+"; }
bool is_uop_token(string tok) { return tok == "~"; }
bool is_prim_token(string tok) { return tok == "0" || tok == "1"; }
bool is_id_token(string tok) {
    if (tok.size() == 0) return false;
    if (tok[0] != '_' && !isalpha(tok[0])) return false;
    for (char c : tok) {
        if (!isalnum(c) && c != '_') {
            return false;
        }
    }
    return true;
}

bool is_single_char_token(char tok) {
    string toks = string("*+~=:().");
    return toks.find(tok) != string::npos;
}

bool is_pos_int_token(string tok) {
    for (char c : tok) {
        if (!isdigit(c)) return false;
    }
    return true;
}

bool is_pos_int_param_token(string tok) {
    return tok == "max_tree_size" ||
           tok == "max_search_depth";
}

bool is_bool_param_token(string tok) {
    return tok == "use_proofs_as_axioms";
}

bool is_bool_token(string tok) {
    return tok == "true" || tok == "false";
}

void
perror(string line, string msg, int line_number, int col)
{
    cerr << line << endl;
    for (int i = 0; i < col-1; i++) cerr << ' ';
    cerr << '^' << endl;
    cerr << "Error (line " << line_number << ", column " << col << "): " << msg << endl;
}

void
rerror(string msg)
{
    cerr << "Runtime Error: " << msg << endl;
}

enum NodeType {
    /* formulas */ OP, VAR, PRIM, UNRES,
    /* commands */ AXIOM, PROVE, PARAM,
    /* program root */ ROOT
};

struct Node {
    string token;
    NodeType type;
    vector<Node> children;
};

struct Axiom {
    string name;
    Node rule_a;
    Node rule_b;
};

class VariableNameGenerator {
public:
    int idx;
    VariableNameGenerator() : idx(0) {}
    string next() {
        return "?" + to_string(idx++);
    }
};

class Tokenizer {
public:
    int idx, line_number, col;
    string line, text;
    Tokenizer(string _text) :
        idx(0), line_number(0), col(0), line(""), text(_text) {
            line = seek_line(idx);
        }
    string next() {

        skip_whitespace_and_comments();

        // is it a single character token?
        if (idx < (int)text.size()) {
            char tok = text[idx];
            if (is_single_char_token(tok)) {
                idx++;
                col++;
                return {tok};
            }
        } else {
            perror(line, "Unexpected end of statement.", line_number+1, col+1);
            exit(1);
        }

        // is it a word token?
        string word_tok;
        if (idx < (int)text.size() && (isalnum(text[idx]) || text[idx] == '_')) {
            word_tok.push_back(text[idx]);
            idx++;
            col++;

            while (idx < (int)text.size() && (text[idx] == '_' || isalnum(text[idx]))) {
                word_tok.push_back(text[idx]);
                idx++;
                col++;
            }
            return word_tok;
        }

        perror(line, "Unexpected character.", line_number+1, col+1);
        exit(1);

    }
    void skip_whitespace() {
        while (idx < (int)text.size() && isspace(text[idx])) {
            if (text[idx] == '\n') {
                // new line
                idx++;
                line_number++;
                col = 0;
                line = seek_line(idx);
            } else {
                idx++;
                col++;
            }
        }
    }
    void skip_whitespace_and_comments() {
        bool check_comment = true;
        while (check_comment) {
            skip_whitespace();

            // is it a comment?
            if (idx < (int)text.size() && text[idx] == '#') {
                while (idx < (int)text.size() && text[idx] != '\n') {
                    idx++;
                    col++;
                }
            } else {
                check_comment = false;
            }

        }
        skip_whitespace();
    }
    bool done() {
        skip_whitespace_and_comments();
        return idx == (int)text.size();
    }
private:
    string seek_line(int from) {
        int line_end = from;
        while (line_end < (int)text.size() && text[line_end] != '\n') line_end++;
        return text.substr(from, line_end-from);
    }
};


Node
parse_formula(Tokenizer &tokenizer)
{
    Node node;
    string tok = tokenizer.next();
    if (tok == "(") {
        tok = tokenizer.next();
        if (is_uop_token(tok)) {
            node.token = tok;
            node.type = OP;
            node.children.push_back(parse_formula(tokenizer));
        } else if (is_bop_token(tok)) {
            node.token = tok;
            node.type = OP;
            node.children.push_back(parse_formula(tokenizer));
            node.children.push_back(parse_formula(tokenizer));
        } else {
            perror(tokenizer.line,
                   "Expected operator token.",
                   tokenizer.line_number+1,
                   tokenizer.col);
            exit(1);
        }

        tok = tokenizer.next();
        if (tok != ")") {
            perror(tokenizer.line,
                   "Expected closing parentheses",
                   tokenizer.line_number+1,
                   tokenizer.col);
            exit(1);
        }

    } else if (is_prim_token(tok)) {
        node.token = tok;
        node.type = PRIM;

    } else if (is_id_token(tok)) {
        node.token = tok;
        node.type = VAR;

    } else {
        perror(tokenizer.line,
               "Unexpected token.",
               tokenizer.line_number+1,
               tokenizer.col);
        exit(1);
    }

    return node;
}

Node
parse_command(Tokenizer &tokenizer)
{
    Node node;
    string tok = tokenizer.next();
    if (tok == "axiom") {
        string name = tokenizer.next();
        if (!is_id_token(name)) {
            perror(tokenizer.line,
                   "Expected identifier.",
                   tokenizer.line_number+1,
                   tokenizer.col);
            exit(1);
        }
        node.token = name;
        node.type = AXIOM;

        string colon = tokenizer.next();
        if (colon != ":") {
            perror(tokenizer.line,
                   "Expected colon (:) in axiom definition.",
                   tokenizer.line_number+1,
                   tokenizer.col);
            exit(1);
        }

        node.children.push_back(parse_formula(tokenizer));

        string eq = tokenizer.next();
        if (eq != "=") {
            perror(tokenizer.line,
                   "Expected '=' token.",
                   tokenizer.line_number+1,
                   tokenizer.col);
            exit(1);
        }

        node.children.push_back(parse_formula(tokenizer));

    } else if (tok == "prove") {
        node.token = "prove";
        node.type = PROVE;
        node.children.push_back(parse_formula(tokenizer));

        string eq = tokenizer.next();
        if (eq != "=") {
            perror(tokenizer.line,
                   "Expected '=' token.",
                   tokenizer.line_number+1,
                   tokenizer.col);
            exit(1);
        }

        node.children.push_back(parse_formula(tokenizer));

    } else if (tok == "param") {
        string param_name = tokenizer.next();
        if (is_pos_int_param_token(param_name)) {
            string value = tokenizer.next();

            if (is_pos_int_token(value)) {
                node.token = param_name;
                node.type = PARAM;
                Node child = {
                    .token = value,
                    .type = VAR,
                    .children = {}
                };
                node.children.push_back(child);

            } else {
                perror(tokenizer.line,
                    "Expected integer value for hyper parameter.",
                    tokenizer.line_number+1,
                    tokenizer.col);
                exit(1);
            }

        } else if (is_bool_param_token(param_name)) {
            string value = tokenizer.next();

            if (is_bool_token(value)) {
                node.token = param_name;
                node.type = PARAM;
                Node child = {
                    .token = value,
                    .type = VAR,
                    .children = {}
                };
                node.children.push_back(child);

            } else {
                perror(tokenizer.line,
                    "Expected number value for hyper parameter.",
                    tokenizer.line_number+1,
                    tokenizer.col);
                exit(1);
            }

        } else {
            perror(tokenizer.line,
                   "Expected either 'max_tree_size' or 'max_search_depth' hyper parameter.",
                   tokenizer.line_number+1,
                   tokenizer.col);
            exit(1);
        }

    } else {
        perror(tokenizer.line,
               "Unexpected token. Command must either be 'axiom' or 'prove'",
               tokenizer.line_number+1,
               tokenizer.col);
        exit(1);
    }

    string dot = tokenizer.next();
    if (dot != ".") {
        perror(tokenizer.line,
               "Expected terminator (.) token.",
               tokenizer.line_number+1,
               tokenizer.col);
        exit(1);
    }

    return node;
}

Node
parse(string text)
{
    auto t = Tokenizer(text);
    Node root;
    root.token = "root";
    root.type = ROOT;
    while (!t.done()) {
        root.children.push_back(parse_command(t));
    }
    return root;
}

string
to_string(Node node)
{
    if (node.type == OP) {
        if (node.token == "~") {
            string child = to_string(node.children[0]);
            return "(~ " + child + ")";
        } else {
            string left = to_string(node.children[0]);
            string right = to_string(node.children[1]);
            return "(" + node.token + " " + left + " " + right + ")";
        }
    } else if (node.type == PRIM) {
        return node.token;
    } else if (node.type == VAR) {
        return node.token;
    } else if (node.type == UNRES) {
        return node.token;
    } else if (node.type == AXIOM) {
        string left = to_string(node.children[0]);
        string right = to_string(node.children[1]);
        return "axiom " + node.token + " " + left + " = " + right + ".";
    } else if (node.type == PROVE) {
        string left = to_string(node.children[0]);
        string right = to_string(node.children[1]);
        return "prove " + left + " = " + right + ".";
    } else if (node.type == ROOT) {
        string ret = "";
        for (int i = 0; i < (int)node.children.size(); i++) {
            ret += to_string(node.children[i]);
            if (i != (int)node.children.size()-1) {
                ret += "\n";
            }
        }
        return ret;
    } else {
        rerror("to_string(Node) :: Invalid node type");
        exit(1);
    }
}

Node
clone_tree(Node node)
{
    return parse(to_string(node));
}


set<string>
get_variables(Node node)
{
    set<string> variables;
    if (node.type == OP) {
        for (Node child : node.children) {
            for(string var : get_variables(child)) {
                variables.insert(var);
            }
        }
    } else if (node.type == PRIM) {
        // pass
    } else if (node.type == VAR || node.type == UNRES) {
        variables.insert(node.token);
    } else {
        rerror("get_variables() :: unexpected node type.");
        exit(1);
    }
    return variables;
}


bool
trees_have_same_structure(Node a, Node b)
{
    if (a.type == OP) if (b.type != OP) return false;
    if (a.type == PRIM) if (b.type != PRIM) return false;
    if (a.type == VAR) if (b.type != VAR && b.type != UNRES) return false;
    if (a.type == UNRES) if (b.type != VAR && b.type != UNRES) return false;
    if (a.children.size() != b.children.size()) return false;
    for (int i = 0; i < (int)a.children.size(); i++) {
        if (!trees_have_same_structure(a.children[i], b.children[i])) {
            return false;
        }
    }
    return true;
}


bool
trees_resolvable(Node a, Node b, map<string, string> &resolutions)
{
    if (a.type == OP) {
        if (b.type != OP) return false;
        if (a.token != b.token) return false;
    } else if (a.type == PRIM) {
        if (b.type != PRIM) return false;
        if (a.token != b.token) return false;
    } else if (a.type == VAR) {
        if (b.type == VAR) {
            return a.token == b.token;
        } else if (b.type == UNRES) {
            if (resolutions.find(b.token) != resolutions.end()) {
                return false;
            } else {
                resolutions[b.token] = a.token;
            }
        }
    }
    if (a.children.size() != b.children.size()) return false;
    for (int i = 0; i < (int)a.children.size(); i++) {
        if (!trees_resolvable(a.children[i], b.children[i], resolutions)) {
            return false;
        }
    }
    return true;
}


bool
trees_resolvable(Node a, Node b)
{
    set<NodeType> allowed = {OP, VAR, PRIM, UNRES};
    if (allowed.find(a.type) == allowed.end() || allowed.find(b.type) == allowed.end()) {
        rerror("trees_have_equal_structure() :: unexpected node type.");
        exit(1);
    }
    map<string, string> resolutions;
    return trees_resolvable(a, b, resolutions);
}


bool
trees_equal(Node a, Node b, map<string, string> resolutions)
{
    if (a.type == OP) {
        if (b.type == OP) {
            return a.token == b.token;
        } else {
            return false;
        }
    } else if (a.type == PRIM) {
        if (b.type == PRIM) {
            return a.token == b.token;
        } else {
            return false;
        }
    } else if (a.type == VAR) {
        if (b.type == VAR) {
            return a.token == b.token;
        } else if (b.type == UNRES) {
            if (resolutions.find(b.token) != resolutions.end()) {
                return a.token == resolutions[b.token];
            } else {
                resolutions[b.token] = a.token;
            }
        } else {
            return false;
        }
    } else if (a.type == UNRES) {
        if (b.type == VAR) {
            if (resolutions.find(a.token) != resolutions.end()) {
                return b.token == resolutions[a.token];
            } else {
                resolutions[a.token] = b.token;
            }
        } else if (b.type == UNRES) {

        }
    } else {
        rerror("trees_equal() :: Unexpected node type.");
        exit(1);
    }
}


/*
    If the rule applies at the given node, this will return the subtrees
    that match the corresponding variables in the tree as a dictionary
    of variable names to references to nodes in the original tree.
    Otherwise, this returns None.

    At each node in the subtree, use the following table:
    rule \ node  |    op          |  var/unres  |   prim
    -----------------------------------------------------------
        op       | iff same tok * |  false      |   false
        var      |      **        |    **       |     **
        prim     |    false       |  false      | iff same tok

    *   The rules must also be checked recursively for all children.
    **  The rule can be applied iff all instances of this variable
        in the scope of the rule are equivalent in the tree.
*/
bool
get_rule_replacements(Node node, Node rule, map<string, Node> &scope)
{
    if (rule.type == OP) {
        if (node.type != OP) {
            return false;
        }
        if (rule.token != node.token) {
            return false;
        }
    }

    if (rule.type == PRIM) {
        if (node.type != PRIM) {
            return false;
        }
        if (rule.token != node.token) {
            return false;
        }
    }

    if (rule.type == VAR || rule.type == UNRES) {
        if (scope.find(rule.token) != scope.end()) {
            if (!trees_equal(scope[rule.token], node)) {
                return false;
            }
        } else {
            scope[rule.token] = node;
        }
    }

    if (rule.type == OP && node.type == OP) {
        if (node.children.size() != rule.children.size()) {
            return false;
        }
        if (!get_rule_replacements(node.children[0], rule.children[0], scope)) {
            return false;
        }
        if (node.children.size() == 2) {
            if (!get_rule_replacements(node.children[1], rule.children[1], scope)) {
                return false;
            }
        }
    }

    return true;

}


Node
replace_variables(Node node, map<string, Node> &scope)
{
    if (node.type == VAR) {
        return scope[node.token];
    } else if (node.type == PRIM) {
        return node;
    } else if (node.type == OP) {
        for (int i = 0; i < (int)node.children.size(); i++) {
            node.children[i] = replace_variables(node.children[i], scope);
        }
        return node;
    } else {
        rerror("replace_variables() :: unexpected node type.");
        exit(1);
    }
}


Node
apply_transformation(bool &ok, Node node, Node rule_from, Node rule_to, VariableNameGenerator &var_gen)
{
    map<string, Node> scope;
    ok = get_rule_replacements(node, rule_from, scope);
    if (!ok) return {};
    for (string var : get_variables(rule_to)) {
        if (scope.find(var) == scope.end()) {
            // var is unused
            Node replacement = {
                .token = var_gen.next(),
                .type = UNRES,
                .children = {}
            };
            scope[var] = replacement;
        }
    }
    return replace_variables(rule_to, scope);
}


vector<pair<string, Node>>
possible_next_trees_for_rule(
    Node node,
    string rule_name,
    Node rule_from,
    Node rule_to,
    VariableNameGenerator &var_gen
) {
    vector<pair<string, Node>> possible;
    bool ok;
    Node new_node = apply_transformation(ok, node, rule_from, rule_to, var_gen);
    if (ok) {
        possible.push_back({rule_name, new_node});
    }
    for (int i = 0; i < (int)node.children.size(); i++) {
        vector<pair<string, Node>> child_possible = \
            possible_next_trees_for_rule(node.children[i], rule_name, rule_from, rule_to, var_gen);
        for (pair<string, Node> pr : child_possible) {
            Node copy = node;
            copy.children[i] = pr.second;
            possible.push_back({
                rule_name,
                copy
            });
        }
    }
    return possible;
}


vector<pair<string, Node>>
possible_next_trees(vector<Axiom> axioms, Node node, VariableNameGenerator &var_gen)
{
    vector<pair<string, Node>> possible;
    for (Axiom axiom : axioms) {
        // try a -> b
        auto poss = possible_next_trees_for_rule(node, axiom.name, axiom.rule_a, axiom.rule_b, var_gen);
        for (auto pr : poss) {
            possible.push_back(pr);
        }
        // try b -> a
        poss = possible_next_trees_for_rule(node, axiom.name, axiom.rule_b, axiom.rule_a, var_gen);
        for (auto pr : poss) {
            possible.push_back(pr);
        }
    }
    return possible;
}


vector<pair<string, Node>>
find_shortest_path(bool &ok, int &states, vector<Axiom> axioms, Node start, Node target, int max_depth=4, int max_tree_size=40)
{
    queue<Node> Q;
    set<string> vis;
    map<string, pair<string, Node>> parent;
    map<string, int> depth;
    VariableNameGenerator var_gen = VariableNameGenerator();

    string hstart = to_string(start);
    string htarget = to_string(target);
    Q.push(start);
    vis.insert(hstart);
    states = 0;

    while (!Q.empty()) {
        states++;
        Node u = Q.front();
        Q.pop();
        string hu = to_string(u);

        if (hu == htarget) {
            ok = true;
            vector<pair<string, Node>> path;
            Node cur = u;
            string hcur = hu;
            while (hcur != hstart) {
                pair<string, Node> pr = parent[hcur];
                path.push_back({pr.first, cur});
                cur = pr.second;
                hcur = to_string(pr.second);
            }
            reverse(path.begin(), path.end());
            return path;
        }

        if ((int)hu.size() > max_tree_size || depth[hu] >= max_depth) {
            continue;
        }

        for (pair<string, Node> pr : possible_next_trees(axioms, u, var_gen)) {
            Node v = pr.second;
            string hv = to_string(v);
            if (vis.find(hv) == vis.end()) {
                vis.insert(hv);
                Q.push(v);
                depth[hv] = depth[hu] + 1;
                parent[hv] = {pr.first, u};
            }
        }
    }

    ok = false;
    return {};
}


Axiom
search_axiom(vector<Axiom> axioms, string name)
{
    for (Axiom ax : axioms) {
        if (ax.name == name) {
            return ax;
        }
    }
    rerror("search_axiom() :: invalid axiom name.");
    exit(1);
}


string
read_file(string fname)
{
    ifstream f(fname);
    stringstream buffer;
    buffer << f.rdbuf();
    return buffer.str();
}


int main(int argc, char ** argv)
{
    if (argc < 2) {
        cerr << "Usage: " << argv[0] << " [filename]" << endl;
        exit(1);
    }

    // defaults
    int max_search_depth = 8;
    int max_tree_size = 20;
    bool use_proofs_as_axioms = false;

    string code = read_file(argv[1]);
    Node root = parse(code);

    vector<Axiom> axioms;

    for (Node cmd : root.children) {
        if (cmd.type == PROVE) {
            Node start = cmd.children[0];
            Node target = cmd.children[1];
            string start_string = to_string(start);
            string target_string = to_string(target);
            cout << "Prove " << to_string(start) << " = " << to_string(target) << "..." << endl;
            bool ok;
            int states;
            auto st_clock = chrono::high_resolution_clock::now();
            auto path = find_shortest_path(ok, states, axioms, start, target, max_search_depth, max_tree_size);
            auto en_clock = chrono::high_resolution_clock::now();
            auto elapsed = chrono::duration_cast<chrono::milliseconds>(en_clock - st_clock);
            double elapsed_seconds = ((double)elapsed.count()) / 1000.0;
            if (ok) {

                if (0 == (int)path.size()) {
                    cout << "Statements are the same." << endl;
                } else {
                    cout << start_string << endl;
                    for (auto pr : path) {
                        Node node = pr.second;
                        string rule_name = pr.first;
                        cout << " = " << to_string(node) << "  w/ " << rule_name << endl;
                    }
                    cout << "Done in " << setprecision(3) << fixed << elapsed_seconds
                         << " seconds after checking " << states << " states." << endl;
                }

                if (use_proofs_as_axioms) {
                    Axiom axiom = {
                        .name = "proof of " + to_string(start) + " = " + to_string(target),
                        .rule_a = start,
                        .rule_b = target
                    };
                    axioms.push_back(axiom);
                }

            } else {
                cout << "No path found within " << max_search_depth
                     << " steps after checking " << states << " states in "
                     << setprecision(3) << fixed << elapsed_seconds << " seconds." << endl;
            }

        } else if (cmd.type == AXIOM) {
            Axiom axiom = {
                .name = cmd.token,
                .rule_a = cmd.children[0],
                .rule_b = cmd.children[1]
            };
            axioms.push_back(axiom);

        } else if (cmd.type == PARAM) {
            if (cmd.token == "max_search_depth") {
                max_search_depth = stoi(cmd.children[0].token);
            } else if (cmd.token == "max_tree_size") {
                max_tree_size = stoi(cmd.children[0].token);
            } else if (cmd.token == "use_proofs_as_axioms") {
                use_proofs_as_axioms = cmd.children[0].token == "true";
            } else {
                rerror("main() :: unexpected parameter " + cmd.token);
                exit(1);
            }
        }
    }

    return 0;
}