def byte_and(x, y):
    assert(len(x) == len(y))
    #return bytes([x[i] & y[i] for i in range(len(x))])
    return bytes([a & b for a, b in zip(x, y)])

def byte_or(x, y):
    assert(len(x) == len(y))
    #return bytes([x[i] | y[i] for i in range(len(x))])
    return bytes([a | b for a, b in zip(x, y)])

def byte_xor(x, y):
    assert(len(x) == len(y))
    #return bytes([x[i] ^ y[i] for i in range(len(x))])
    return bytes([a ^ b for a, b in zip(x, y)])

