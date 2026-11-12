"""
qr_svg.py — Generador puro en Python de Código QR (ISO/IEC 18004) en SVG
=========================================================================
Soporta modo Byte (UTF-8) con corrección de errores Nivel M para
versiones 1 a 6 (hasta 106 bytes), suficiente para URLs y folios médicos
sin requerir dependencias externas ni conexión a internet.
"""

from __future__ import annotations
import html
from typing import List, Tuple

# Tablas ISO-18004 Nivel M (total_data_codewords, ec_codewords_per_block)
_QR_SPEC_M = {
    1: (16, 10),
    2: (28, 16),
    3: (44, 26),
    4: (64, 18),  # 2 bloques de (32 data, 18 ec)
    5: (86, 24),  # 2 bloques de (43 data, 24 ec)
    6: (108, 16), # 4 bloques de (27 data, 16 ec)
}

_QR_BLOCKS_M = {
    1: 1,
    2: 1,
    3: 1,
    4: 2,
    5: 2,
    6: 4,
}

_ALIGN_POS = {
    1: [],
    2: [6, 18],
    3: [6, 22],
    4: [6, 26],
    5: [6, 30],
    6: [6, 34],
}

# GF(256) log / exp tables con polinomio primitivo 0x11D
_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def _rs_gen_poly(degree: int) -> List[int]:
    poly = [1]
    for i in range(degree):
        nxt = [0] * (len(poly) + 1)
        factor = _EXP[i]
        for j, coeff in enumerate(poly):
            nxt[j] ^= coeff
            nxt[j + 1] ^= _gf_mul(coeff, factor)
        poly = nxt
    return poly


def _rs_encode(data: List[int], ec_len: int) -> List[int]:
    gen = _rs_gen_poly(ec_len)
    res = list(data) + [0] * ec_len
    for i in range(len(data)):
        coef = res[i]
        if coef != 0:
            for j in range(1, len(gen)):
                res[i + j] ^= _gf_mul(gen[j], coef)
    return res[len(data):]


def _select_version(byte_len: int) -> int:
    for v in range(1, 7):
        cap_bytes = _QR_SPEC_M[v][0] - 2  # 4-bit mode + 8-bit len + 4-bit term <= 2 bytes overhead
        if byte_len <= cap_bytes:
            return v
    return 6


def _build_codewords(payload: bytes) -> Tuple[int, List[int]]:
    ver = _select_version(len(payload))
    data_cap, ec_per_blk = _QR_SPEC_M[ver]
    num_blocks = _QR_BLOCKS_M[ver]

    max_payload = data_cap - 2
    payload = payload[:max_payload]

    bits: List[int] = []
    # Mode 0100 (Byte)
    bits.extend([0, 1, 0, 0])
    # 8-bit length
    for b in range(7, -1, -1):
        bits.append((len(payload) >> b) & 1)
    # Data bytes
    for byte in payload:
        for b in range(7, -1, -1):
            bits.append((byte >> b) & 1)
    # Terminator
    term_len = min(4, data_cap * 8 - len(bits))
    bits.extend([0] * term_len)
    while len(bits) % 8 != 0:
        bits.append(0)

    data_bytes = []
    for i in range(0, len(bits), 8):
        val = 0
        for j in range(8):
            val = (val << 1) | bits[i + j]
        data_bytes.append(val)

    pad_cycle = [0xEC, 0x11]
    idx = 0
    while len(data_bytes) < data_cap:
        data_bytes.append(pad_cycle[idx % 2])
        idx += 1

    # Dividir en bloques e intercalar
    blk_size = data_cap // num_blocks
    data_blocks = [data_bytes[i * blk_size:(i + 1) * blk_size] for i in range(num_blocks)]
    ec_blocks = [_rs_encode(b, ec_per_blk) for b in data_blocks]

    interleaved: List[int] = []
    for i in range(blk_size):
        for blk in data_blocks:
            interleaved.append(blk[i])
    for i in range(ec_per_blk):
        for ec in ec_blocks:
            interleaved.append(ec[i])

    return ver, interleaved


def _place_function_patterns(ver: int) -> Tuple[List[List[int]], List[List[bool]]]:
    size = ver * 4 + 17
    mat = [[0] * size for _ in range(size)]
    reserved = [[False] * size for _ in range(size)]

    def _set(r: int, c: int, val: int):
        if 0 <= r < size and 0 <= c < size:
            mat[r][c] = val
            reserved[r][c] = True

    def _finder(r0: int, c0: int):
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                r, c = r0 + dr, c0 + dc
                if not (0 <= r < size and 0 <= c < size):
                    continue
                if dr in (-1, 7) or dc in (-1, 7):
                    _set(r, c, 0)
                elif dr in (0, 6) or dc in (0, 6) or (2 <= dr <= 4 and 2 <= dc <= 4):
                    _set(r, c, 1)
                else:
                    _set(r, c, 0)

    _finder(0, 0)
    _finder(0, size - 7)
    _finder(size - 7, 0)

    # Alignment patterns
    pos = _ALIGN_POS[ver]
    for r0 in pos:
        for c0 in pos:
            if reserved[r0][c0]:
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    val = 1 if (abs(dr) == 2 or abs(dc) == 2 or (dr == 0 and dc == 0)) else 0
                    _set(r0 + dr, c0 + dc, val)

    # Timing patterns
    for i in range(8, size - 8):
        val = 1 if i % 2 == 0 else 0
        if not reserved[6][i]:
            _set(6, i, val)
        if not reserved[i][6]:
            _set(i, 6, val)

    # Dark module & Format info reservation
    _set(size - 8, 8, 1)
    for i in range(9):
        if i != 6:
            reserved[8][i] = True
            reserved[i][8] = True
    for i in range(8):
        reserved[8][size - 1 - i] = True
        reserved[size - 1 - i][8] = True

    return mat, reserved


def _format_bits_m(mask: int) -> int:
    # Error correction M = 00
    data = (0b00 << 3) | (mask & 0b111)
    rem = data << 10
    gen = 0b10100110111
    for bit in range(14, 9, -1):
        if (rem >> bit) & 1:
            rem ^= gen << (bit - 10)
    fmt = ((data << 10) | rem) ^ 0b101010000010010
    return fmt


def _apply_format(mat: List[List[int]], mask: int):
    size = len(mat)
    fmt = _format_bits_m(mask)
    for i in range(6):
        bit = (fmt >> (14 - i)) & 1
        mat[8][i] = bit
        mat[size - 1 - i][8] = bit
    mat[8][7] = (fmt >> 8) & 1
    mat[size - 7][8] = (fmt >> 8) & 1
    mat[8][8] = (fmt >> 7) & 1
    mat[8][size - 8] = (fmt >> 7) & 1
    mat[7][8] = (fmt >> 6) & 1
    mat[8][size - 7] = (fmt >> 6) & 1
    for i in range(6):
        bit = (fmt >> (5 - i)) & 1
        mat[5 - i][8] = bit
        mat[8][size - 6 + i] = bit


def _place_data(mat: List[List[int]], reserved: List[List[bool]], codewords: List[int]):
    size = len(mat)
    bits: List[int] = []
    for cw in codewords:
        for b in range(7, -1, -1):
            bits.append((cw >> b) & 1)

    bit_idx = 0
    col = size - 1
    up = True
    while col > 0:
        if col == 6:
            col -= 1
        rows = range(size - 1, -1, -1) if up else range(size)
        for r in rows:
            for c in (col, col - 1):
                if not reserved[r][c]:
                    val = bits[bit_idx] if bit_idx < len(bits) else 0
                    mat[r][c] = val
                    bit_idx += 1
        col -= 2
        up = not up


def _mask_penalty(mat: List[List[int]]) -> int:
    size = len(mat)
    penalty = 0
    # Regla 1: 5+ módulos iguales consecutivos
    for r in range(size):
        run = 1
        for c in range(1, size):
            if mat[r][c] == mat[r][c - 1]:
                run += 1
            else:
                if run >= 5:
                    penalty += 3 + (run - 5)
                run = 1
        if run >= 5:
            penalty += 3 + (run - 5)
    for c in range(size):
        run = 1
        for r in range(1, size):
            if mat[r][c] == mat[r - 1][c]:
                run += 1
            else:
                if run >= 5:
                    penalty += 3 + (run - 5)
                run = 1
        if run >= 5:
            penalty += 3 + (run - 5)
    # Regla 2: bloques 2x2
    for r in range(size - 1):
        for c in range(size - 1):
            v = mat[r][c]
            if v == mat[r][c + 1] == mat[r + 1][c] == mat[r + 1][c + 1]:
                penalty += 3
    return penalty


def _mask_cond(mask: int, r: int, c: int) -> bool:
    if mask == 0:
        return (r + c) % 2 == 0
    if mask == 1:
        return r % 2 == 0
    if mask == 2:
        return c % 3 == 0
    if mask == 3:
        return (r + c) % 3 == 0
    if mask == 4:
        return ((r // 2) + (c // 3)) % 2 == 0
    if mask == 5:
        return ((r * c) % 2 + (r * c) % 3) == 0
    if mask == 6:
        return (((r * c) % 2) + ((r * c) % 3)) % 2 == 0
    return (((r + c) % 2) + ((r * c) % 3)) % 2 == 0


def generate_qr_matrix(text: str) -> List[List[int]]:
    ver, codewords = _build_codewords(text.encode("utf-8"))
    base_mat, reserved = _place_function_patterns(ver)
    _place_data(base_mat, reserved, codewords)

    best_mat = None
    best_score = 10**9
    size = len(base_mat)
    for mask in range(8):
        cand = [row[:] for row in base_mat]
        for r in range(size):
            for c in range(size):
                if not reserved[r][c] and _mask_cond(mask, r, c):
                    cand[r][c] ^= 1
        _apply_format(cand, mask)
        sc = _mask_penalty(cand)
        if sc < best_score:
            best_score = sc
            best_mat = cand
    return best_mat or base_mat


def generate_qr_svg(text: str, size_px: int = 108, quiet: int = 2) -> str:
    """Devuelve un <svg> compacto y válido con el código QR para embeber en HTML."""
    mat = generate_qr_matrix(text)
    dim = len(mat) + 2 * quiet
    rects = []
    for r, row in enumerate(mat):
        for c, val in enumerate(row):
            if val:
                rects.append(f'<rect x="{c + quiet}" y="{r + quiet}" width="1" height="1"/>')
    label = html.escape(text, quote=True)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {dim} {dim}" '
        f'width="{size_px}" height="{size_px}" shape-rendering="crispEdges" '
        f'role="img" aria-label="QR Verificación: {label}">'
        f'<rect width="{dim}" height="{dim}" fill="#ffffff"/>'
        f'<g fill="#0f172a">{"".join(rects)}</g>'
        f'</svg>'
    )
