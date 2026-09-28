"""纯标准库 Ed25519（RFC 8032）实现 —— 注册码验签用，无第三方依赖。

为什么要自己带一份：本项目的应用端要保持"零第三方依赖"（PyInstaller 打包、跨 Win7+），
不能为了验签去装 cryptography / PyNaCl。此实现只依赖 hashlib。

正确性：已通过 RFC 8032 官方测试向量（TEST 1），并与 Node.js crypto 的签名逐字节一致。
注意：Ed25519 的散列输出必须按**小端**解释为整数（见 _le_int），这是最容易写错的地方。
"""
import hashlib

b = 256
q = 2 ** 255 - 19
l = 2 ** 252 + 27742317777372353535851937790883648493


def H(m):
    return hashlib.sha512(m).digest()


def inv(x):
    return pow(x, q - 2, q)


d = -121665 * inv(121666) % q
I = pow(2, (q - 1) // 4, q)


def xrecover(y):
    xx = (y * y - 1) * inv(d * y * y + 1)
    x = pow(xx, (q + 3) // 8, q)
    if (x * x - xx) % q != 0:
        x = (x * I) % q
    if x % 2 != 0:
        x = q - x
    return x


By = 4 * inv(5) % q
Bx = xrecover(By)
B = [Bx % q, By % q]


def edwards(P, Q):
    x1, y1 = P
    x2, y2 = Q
    k = d * x1 * x2 * y1 * y2
    x3 = (x1 * y2 + x2 * y1) * inv(1 + k)
    y3 = (y1 * y2 + x1 * x2) * inv(1 - k)
    return [x3 % q, y3 % q]


def scalarmult(P, e):
    """迭代式 double-and-add（不用递归，避免深递归开销/爆栈）"""
    Q = [0, 1]
    while e:
        if e & 1:
            Q = edwards(Q, P)
        P = edwards(P, P)
        e >>= 1
    return Q


def encodepoint(P):
    """RFC 8032 小端编码：字节 i 的第 j 位 = bits[8i+j]；末字节最高位是 x 的符号位。"""
    x, y = P
    bits = [(y >> i) & 1 for i in range(b - 1)] + [x & 1]
    return bytes(sum(bits[i * 8 + j] << j for j in range(8)) for i in range(b // 8))


def bit(h, i):
    return (h[i // 8] >> (i % 8)) & 1


def decodeint(s):
    return sum(2 ** i * bit(s, i) for i in range(0, b))


def decodepoint(s):
    y = sum(2 ** i * bit(s, i) for i in range(0, b - 1))
    x = xrecover(y)
    if x & 1 != bit(s, b - 1):
        x = q - x
    P = [x, y]
    if (-x * x + y * y - 1 - d * x * x * y * y) % q != 0:
        raise ValueError("point not on curve")
    return P


def _le_int(buf):
    """RFC 8032：散列输出按小端解释为整数（不是 .hex() 的大端解释）"""
    return int.from_bytes(buf, 'little')


def publickey_from_seed(seed):
    """由 32 字节私钥种子算出 32 字节公钥"""
    h = H(seed)
    a = 2 ** (b - 2) + sum(2 ** i * bit(h, i) for i in range(3, b - 2))
    return encodepoint(scalarmult(B, a))


def sign(m, seed):
    """签名：seed 为 32 字节私钥种子，返回 64 字节签名（仅开发者发码使用）"""
    pk = publickey_from_seed(seed)
    h = H(seed)
    a = 2 ** (b - 2) + sum(2 ** i * bit(h, i) for i in range(3, b - 2))
    r = _le_int(H(h[b // 8:b // 8 + 32] + m)) % l
    R = scalarmult(B, r)
    S = (r + _le_int(H(encodepoint(R) + pk + m)) * a) % l
    return encodepoint(R) + S.to_bytes(32, 'little')


def verify(sig, m, pk):
    """验签：sig 64 字节、pk 32 字节；任何异常都返回 False（不向上抛）"""
    if len(sig) != 64 or len(pk) != 32:
        return False
    try:
        R = decodepoint(sig[:32])
        A = decodepoint(pk)
    except ValueError:
        return False
    S = decodeint(sig[32:])
    if S >= l:
        return False
    h = _le_int(H(sig[:32] + pk + m))
    return scalarmult(B, S) == edwards(R, scalarmult(A, h))
