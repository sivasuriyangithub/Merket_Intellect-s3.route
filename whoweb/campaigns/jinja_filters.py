from jinja2 import Environment


def first_match(alpha, beta, *args, **kwargs):
    if not isinstance(beta, (list, tuple)):
        if alpha and alpha == beta:
            return alpha
    shared = list(set(alpha).intersection(beta))
    if shared:
        return shared[0]
    return False


def environment(**options):
    env = Environment(**options)
    env.filters["shared_element"] = first_match
    return env
