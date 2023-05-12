def to_fixed(num_obj, digits=0):
    """fix decimal places"""
    if num_obj is not None and num_obj != '':
        if is_float(num_obj):
            ret_val = '{0:.{1}f}'.format(num_obj, digits)
            return ret_val
        else:
            return 'Not float'
    else:
        return 'None'


def is_int(s):
    """Check is int"""
    try:
        int(s)
        return True
    except ValueError:
        return False


def is_float(s):
    """Check is float"""
    try:
        float(s)
        return True
    except ValueError:
        return False


