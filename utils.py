def literal(x):
    if type(x) == str:
        return 'Literal_'
    else:
        return x.is_a