from odoo.osv import expression
import logging

logger = logging.getLogger(__name__)


def _remove_linebreaks(x):
    x = x or ""
    for c in "\n":
        while c in x:
            x = x.replace(c, " ")
    return x


class SqlAndParams(object):
    def __init__(self, sql, params):
        self.sql = sql
        self.params = params

    def __repr__(self):
        return "{} [{}]".format(self.sql, self.params)

    def __str__(self):
        return str(self.sql)

    def get_values(self):
        if self.params is not None:
            yield self.params


class Expression(object):
    def __init__(self, left, operator, right):
        self.left = left
        self.right = right
        self.operator = operator

    def __str__(self):
        return "({} {} {})".format(str(self.left), str(self.operator), str(self.right))

    def get_values(self):
        for x in (self.left, self.right):
            if hasattr(x, "get_values"):
                yield from getattr(x, "get_values")()


class WhereExpression(object):
    def __init__(self, domain, dialect="postgres"):
        self.domain = expression.distribute_not(
            expression.normalize_domain(domain or [])
        )  # NOQA
        assert dialect in ["postgres", "odbc"], f"Not so: {dialect}"
        self.dialect = dialect
        if not self.domain:
            self.domain = [(1, "=", 1)]

    @staticmethod
    def parameter(dialect):
        placeholder = "%s"
        if dialect in ["odbc", 'ibmdb2']:
            placeholder = "?"
        return placeholder

    def get_clause(self):
        sql = ""

        values = []
        sql_and_values = self._resolve(self.domain)

        def to_string(x):
            if isinstance(x, SqlAndParams):
                return x.sql
            elif isinstance(x, Expression):
                return str(x)
            return x

        def get_values(x):
            if isinstance(x, (SqlAndParams, Expression)):
                yield from x.get_values()

        sql = " ".join(map(to_string, sql_and_values))
        values = tuple(tuple(get_values(x) for x in sql_and_values)[0])

        return sql, tuple(values)

    def _resolve(self, domain):
        while (
            "&" in domain or "|" in domain or any(isinstance(x, tuple) for x in domain)
        ):

            def _get_most_right_operator(domain):
                for i, x in enumerate(reversed(domain)):
                    if x in ["&", "|"]:
                        return len(domain) - i - 1, x
                return None, None

            i_operator, operator = _get_most_right_operator(domain)
            if i_operator is not None:
                tuple_left = domain[i_operator + 1]
                tuple_right = domain[i_operator + 2]

                sql = []
                for t in (tuple_left, tuple_right):
                    if isinstance(t, tuple):
                        t_sql = self._interpret_tuple(t)
                        sql.insert(0, t_sql)
                    else:
                        sql.insert(0, t)
            else:
                if domain:
                    t_sql = self._interpret_tuple(domain[0])
                    sql = [t_sql]

            operator = {"&": "and", "|": "or", None: None}[operator]

            if i_operator is not None:
                sql = Expression(sql[0], operator, sql[1])
                domain = domain[:i_operator] + [sql] + domain[i_operator + 3 :]
            else:
                domain = sql
            sql = None
        return domain

    @staticmethod
    def _escape(expr):
        def _is_escaped(term):
            return any(x in '["' for x in (term or ""))

        terms = expr.split(".")
        final = []
        for term in terms:
            if not _is_escaped(term):
                term = '"{}"'.format(term)
                final.append(term)
            else:
                final.append(term)
        return ".".join(final)

    def _interpret_tuple(self, _tuple):
        field = _tuple[0]
        operator = self._translate_operator(_tuple[1])
        value = self._translate_value(_tuple[2])

        if _tuple[2] is None and operator == "=":
            operator = "is"
        if _tuple[2] is None and operator == "<>":
            operator = "is not"

        if isinstance(field, int):
            field = str(field)
        else:
            field = self._escape(field)

        if value:
            expr = "({} {} {})".format(field, operator, value)
            value = None
        else:
            if _tuple[1] == "in" and not _tuple[2]:
                expr = "(1=0)"
                value = None
            else:
                placeholder = self.parameter(self.dialect)
                expr = f"({field} {operator} {placeholder})"
                value = _tuple[2]
                if isinstance(value, list):
                    value = tuple(value)

        return SqlAndParams(expr, value)

    def _translate_operator(self, operator):
        if operator in [
            "=",
            "ilike",
            "like",
            "is",
            "is not",
            "in",
            "not in",
            ">",
            "<",
            "<=",
            ">=",
        ]:
            return operator
        elif operator == "!=":
            return "<>"
        raise NotImplementedError()

    def _translate_value(self, value):
        if value is None:
            return "null"
        elif value is False:
            return "false"
        elif value is True:
            return "true"
        return None
