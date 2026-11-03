"""도형그리기 - 좌표평면과 함수 그래프 (식 계산, 식 글자)"""
import math
import re

KINDS = [("prop", "정비례  y = ax"), ("linear", "일차함수  y = ax + b"), ("quad", "이차함수  y = a(x − p)² + q"),
         ("inverse", "반비례  y = a/x"), ("expr", "식 직접 입력")]
PARAMS = {"prop": [("a", 2.0)], "linear": [("a", 2.0), ("b", 1.0)], "quad": [("a", 1.0), ("p", 0.0), ("q", 0.0)],
          "inverse": [("a", 6.0)], "expr": []}

_ALLOWED = re.compile(r"^[0-9x+\-*/^(). ]*$")
_FUNCS = {"sqrt": math.sqrt, "abs": abs, "sin": math.sin, "cos": math.cos, "tan": math.tan, "pi": math.pi}


def nice(v):
    """2.0 → 2, 0.50 → 0.5"""
    v = round(float(v), 4)
    return str(int(v)) if v == int(v) else f"{v:g}"


def _prep(text):
    """사용자 식 → 파이썬 식 (2x → 2*x, x^2 → x**2, √ → sqrt)"""
    t = (text or "").replace(" ", "").replace("×", "*").replace("÷", "/").replace("−", "-").replace("²", "^2")
    t = t.replace("√", "sqrt").replace("π", "pi")
    t = re.sub(r"^y=", "", t)
    names = "|".join(_FUNCS)
    body = re.sub(names, "", t)
    if not _ALLOWED.match(body):
        raise ValueError("쓸 수 있는 것: 숫자, x, + − × ÷ ^ ( ), sqrt, abs, sin, cos, tan, pi")
    t = t.replace("^", "**")
    t = re.sub(r"(\d|\))(x|\(|sqrt|abs|sin|cos|tan|pi)", r"\1*\2", t)
    t = re.sub(r"(x)(\d|x|\(|sqrt|abs|sin|cos|tan|pi)", r"\1*\2", t)
    t = re.sub(r"(pi)(\d|x|\()", r"\1*\2", t)
    return t


def compile_expr(text):
    code = compile(_prep(text), "<식>", "eval")
    for name in code.co_names:
        if name != "x" and name not in _FUNCS:
            raise ValueError(f"'{name}' 은(는) 쓸 수 없습니다.")
    return code


def func(o):
    """그래프 개체 → f(x) (계산할 수 없으면 None 을 돌려주는 함수)"""
    k = o.get("gkind", "linear")
    p = o.get("params", {})
    g = lambda key, d=0.0: float(p.get(key, d))
    if k == "prop":
        a = g("a")
        return lambda x: a * x
    if k == "linear":
        a, b = g("a"), g("b")
        return lambda x: a * x + b
    if k == "quad":
        a, pp, q = g("a"), g("p"), g("q")
        return lambda x: a * (x - pp) ** 2 + q
    if k == "inverse":
        a = g("a")
        return lambda x: a / x if abs(x) > 1e-12 else None
    try:
        code = compile_expr(o.get("expr", "x"))
    except Exception:
        return lambda x: None
    env = dict(_FUNCS)
    env["__builtins__"] = {}

    def f(x):
        env["x"] = x
        try:
            v = eval(code, env)
            return float(v) if isinstance(v, (int, float)) and math.isfinite(v) else None
        except Exception:
            return None
    return f


def _coef(a, var):
    """계수 a 와 변수 글자 → '2x', 'x', '−x', '0.5x'"""
    if abs(a - 1) < 1e-12:
        return var
    if abs(a + 1) < 1e-12:
        return "−" + var
    return nice(a).replace("-", "−") + var


def _const(c, first=False):
    if abs(c) < 1e-12:
        return ""
    s = nice(abs(c))
    if first:
        return ("−" if c < 0 else "") + s
    return (" − " if c < 0 else " + ") + s


def label(o):
    """그래프의 식 글자: y = 2x + 1"""
    k = o.get("gkind", "linear")
    p = o.get("params", {})
    g = lambda key, d=0.0: float(p.get(key, d))
    if k == "prop":
        return "y = " + (_coef(g("a"), "x") if abs(g("a")) > 1e-12 else "0")
    if k == "linear":
        a, b = g("a"), g("b")
        if abs(a) < 1e-12:
            return "y = " + (_const(b, True) or "0")
        return "y = " + _coef(a, "x") + _const(b)
    if k == "quad":
        a, pp, q = g("a"), g("p"), g("q")
        inner = "x" if abs(pp) < 1e-12 else f"(x {'−' if pp > 0 else '+'} {nice(abs(pp))})"
        sq = inner + "²"
        return "y = " + _coef(a, sq) + _const(q)
    if k == "inverse":
        a = g("a")
        return "y = " + ("−" if a < 0 else "") + nice(abs(a)) + "/x"
    return "y = " + (o.get("expr", "") or "")
