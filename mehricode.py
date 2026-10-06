import re

# ---------- LEXER ----------
KEYWORDS = {"خلي","اذا","والا","طالما","وظيفة","ارجع","اطبع","صح","خطا","و","او","ليس"}

TOKEN_RE = re.compile(r"""
    (?P<WS>\s+)
  | (?P<NUMBER>\d+(\.\d+)?)
  | (?P<STRING>"[^"]*")
  | (?P<IDENT>[A-Za-z_\u0600-\u06FF][\w\u0600-\u06FF]*)
  | (?P<OP>==|!=|<=|>=|[+\-*/=<>(){},;])
""", re.VERBOSE)

class Token:
    def __init__(self, type, value, line):
        self.type, self.value, self.line = type, value, line

def tokenize(src):
    tokens, line, pos = [], 1, 0
    while pos < len(src):
        m = TOKEN_RE.match(src, pos)
        if not m:
            raise SyntaxError(f"سطر {line}: حرف غير معروف {src[pos]!r}")
        kind, val = m.lastgroup, m.group()
        pos = m.end()
        if kind == "WS":
            line += val.count("\n"); continue
        if kind == "NUMBER":
            tokens.append(Token("NUMBER", float(val) if "." in val else int(val), line))
        elif kind == "STRING":
            tokens.append(Token("STRING", val[1:-1], line))
        elif kind == "IDENT" and val in KEYWORDS:
            tokens.append(Token(val, val, line))
        elif kind == "OP":
            # المفتاح: الرمز يأخذ نوعه الحقيقي، لا "OP"
            tokens.append(Token(val, val, line))
        else:
            tokens.append(Token(kind, val, line))
    tokens.append(Token("EOF", None, line))
    return tokens

# ---------- PARSER ----------
class Parser:
    def __init__(self, tokens):
        self.tokens, self.pos = tokens, 0

    def peek(self): return self.tokens[self.pos]
    def next(self):
        t = self.tokens[self.pos]; self.pos += 1; return t
    def expect(self, type):
        t = self.next()
        if t.type != type:
            got = t.value if t.value is not None else t.type
            raise SyntaxError(f"سطر {t.line}: توقعت «{type}» وجدت «{got}»")
        return t
    def match(self, *types):
        if self.peek().type in types: return self.next()
        return None

    def parse(self):
        stmts = []
        while self.peek().type != "EOF":
            stmts.append(self.statement())
        return ("block", stmts)

    def block(self):
        self.expect("{")
        stmts = []
        while self.peek().type != "}":
            stmts.append(self.statement())
        self.expect("}")
        return ("block", stmts)

    def statement(self):
        t = self.peek()
        if t.type == "خلي":
            self.next()
            name = self.expect("IDENT").value
            self.expect("=")
            e = self.expression(); self.expect(";")
            return ("let", name, e)
        if t.type == "اذا":
            self.next(); self.expect("(")
            cond = self.expression(); self.expect(")")
            then = self.block()
            els = self.block() if self.match("والا") else None
            return ("if", cond, then, els)
        if t.type == "طالما":
            self.next(); self.expect("(")
            cond = self.expression(); self.expect(")")
            body = self.block()
            return ("while", cond, body)
        if t.type == "وظيفة":
            self.next()
            name = self.expect("IDENT").value
            self.expect("(")
            params = []
            if self.peek().type != ")":
                params.append(self.expect("IDENT").value)
                while self.match(","): params.append(self.expect("IDENT").value)
            self.expect(")")
            body = self.block()
            return ("func", name, params, body)
        if t.type == "ارجع":
            self.next()
            e = None if self.peek().type == ";" else self.expression()
            self.expect(";")
            return ("return", e)
        if t.type == "اطبع":
            self.next(); self.expect("(")
            e = self.expression(); self.expect(")"); self.expect(";")
            return ("print", e)
        e = self.expression(); self.expect(";")
        return ("expr", e)

    def expression(self): return self.assignment()
    def assignment(self):
        left = self.logic_or()
        if self.match("="):
            return ("assign", left, self.assignment())
        return left
    def logic_or(self):
        e = self.logic_and()
        while self.match("او"): e = ("or", e, self.logic_and())
        return e
    def logic_and(self):
        e = self.equality()
        while self.match("و"): e = ("and", e, self.equality())
        return e
    def equality(self):
        e = self.comparison()
        while True:
            t = self.match("==", "!=")
            if not t: break
            e = (t.type, e, self.comparison())
        return e
    def comparison(self):
        e = self.term()
        while True:
            t = self.match("<", ">", "<=", ">=")
            if not t: break
            e = (t.type, e, self.term())
        return e
    def term(self):
        e = self.factor()
        while True:
            t = self.match("+", "-")
            if not t: break
            e = (t.type, e, self.factor())
        return e
    def factor(self):
        e = self.unary()
        while True:
            t = self.match("*", "/")
            if not t: break
            e = (t.type, e, self.unary())
        return e
    def unary(self):
        t = self.match("ليس", "-")
        if t: return ("unary", t.type, self.unary())
        return self.primary()
    def primary(self):
        t = self.peek()
        if t.type in ("NUMBER", "STRING"):
            self.next(); return ("lit", t.value)
        if t.type == "صح": self.next(); return ("lit", True)
        if t.type == "خطا": self.next(); return ("lit", False)
        if t.type == "IDENT":
            self.next()
            if self.match("("):
                args = []
                if self.peek().type != ")":
                    args.append(self.expression())
                    while self.match(","): args.append(self.expression())
                self.expect(")")
                return ("call", t.value, args)
            return ("var", t.value)
        if t.type == "(":
            self.next(); e = self.expression(); self.expect(")"); return e
        got = t.value if t.value is not None else t.type
        raise SyntaxError(f"سطر {t.line}: تعبير غير متوقع «{got}»")

# ---------- INTERPRETER ----------
class Return(Exception):
    def __init__(self, value): self.value = value

class Env:
    def __init__(self, parent=None):
        self.vars, self.parent = {}, parent
    def get(self, name):
        if name in self.vars: return self.vars[name]
        if self.parent: return self.parent.get(name)
        raise RuntimeError(f"متغير غير معرّف: {name}")
    def set(self, name, value):
        if name in self.vars: self.vars[name] = value
        elif self.parent: self.parent.set(name, value)
        else: self.vars[name] = value
    def declare(self, name, value): self.vars[name] = value

class Interpreter:
    def __init__(self, input_lines, output_fn):
        self.input_lines = list(input_lines)
        self.output_fn = output_fn
        self.globals = Env()

    def read_input(self):
        if not self.input_lines:
            raise RuntimeError("البرنامج طلب مدخلات أكثر مما تم توفيره")
        return self.input_lines.pop(0)

    def run(self, ast): self.exec_block(ast[1], self.globals)

    def exec_block(self, stmts, env):
        for s in stmts: self.exec_stmt(s, env)

    def exec_stmt(self, node, env):
        k = node[0]
        if k == "let": env.declare(node[1], self.eval(node[2], env))
        elif k == "print": self.output_fn(str(self.eval(node[1], env)))
        elif k == "expr": self.eval(node[1], env)
        elif k == "if":
            if self.truthy(self.eval(node[1], env)): self.exec_block(node[2][1], Env(env))
            elif node[3]: self.exec_block(node[3][1], Env(env))
        elif k == "while":
            while self.truthy(self.eval(node[1], env)): self.exec_block(node[2][1], Env(env))
        elif k == "func": env.declare(node[1], ("func", node[2], node[3], env))
        elif k == "return":
            raise Return(self.eval(node[1], env) if node[1] else None)
        else: raise RuntimeError(f"عبارة غير معروفة: {k}")

    def truthy(self, v): return bool(v)

    def eval(self, node, env):
        k = node[0]
        if k == "lit": return node[1]
        if k == "var": return env.get(node[1])
        if k == "assign":
            val = self.eval(node[2], env)
            env.set(node[1][1], val); return val
        if k == "unary":
            v = self.eval(node[2], env)
            return (not self.truthy(v)) if node[1] == "ليس" else -v
        if k in ("+","-","*","/","==","!=","<",">","<=",">=","and","or"):
            return self.binop(k, self.eval(node[1], env), self.eval(node[2], env))
        if k == "call": return self.call(node[1], node[2], env)
        raise RuntimeError(f"تعبير غير معروف: {k}")

    def binop(self, op, a, b):
        if op == "+": return str(a) + str(b) if isinstance(a, str) or isinstance(b, str) else a + b
        if op == "-": return a - b
        if op == "*": return a * b
        if op == "/": return a / b
        if op == "==": return a == b
        if op == "!=": return a != b
        if op == "<": return a < b
        if op == ">": return a > b
        if op == "<=": return a <= b
        if op == ">=": return a >= b
        if op == "and": return self.truthy(a) and self.truthy(b)
        if op == "or": return self.truthy(a) or self.truthy(b)

    def call(self, name, args, env):
        # دوال مدمجة بالعربية فقط
        if name == "ادخل":
            return self.read_input()
        if name == "رقم":
            v = self.eval(args[0], env)
            try:
                return float(v) if "." in str(v) else int(v)
            except ValueError:
                raise RuntimeError(f"رقم() فشل على «{v}»")
        if name == "نص":
            return str(self.eval(args[0], env))

        # دالة معرّفة من المستخدم
        val = env.get(name)
        if not (isinstance(val, tuple) and val[0] == "func"):
            raise RuntimeError(f"«{name}» ليست دالة")
        _, params, body, closure = val
        if len(params) != len(args):
            raise RuntimeError(f"«{name}» تتوقع {len(params)} وسائط، أُعطيت {len(args)}")
        local = Env(closure)
        for p, a in zip(params, args):
            local.declare(p, self.eval(a, env))
        try:
            self.exec_block(body[1], local)
        except Return as r:
            return r.value
        return None

# ---------- PUBLIC API ----------
def run(source, input_lines, output_fn):
    tokens = tokenize(source)
    ast = Parser(tokens).parse()
    Interpreter(input_lines, output_fn).run(ast)