"""Tiny INR money helpers used across automation scripts.

Formats numbers the way Indian users expect (lakh / crore separators) and
parses messy strings like 'Rs. 1,23,456.50' or 'INR 25K' back into Decimal.
"""
import re
from decimal import Decimal

_K_RE = re.compile(r'^\s*(?:Rs\.?|INR)?\s*([\d,]+(?:\.\d+)?)\s*([KkMmLlCc]?)\s*$')
_MULTIPLIERS = {
    '': Decimal(1),
    'K': Decimal(1000),
    'k': Decimal(1000),
    'L': Decimal(100000),
    'l': Decimal(100000),
    'M': Decimal(1000000),
    'm': Decimal(1000000),
    'C': Decimal(10000000),
    'c': Decimal(10000000),
}


def parse_inr(s):
    m = _K_RE.match(s)
    if not m:
        raise ValueError('Not a recognizable INR amount: ' + repr(s))
    digits = m.group(1).replace(',', '')
    suffix = m.group(2)
    return Decimal(digits) * _MULTIPLIERS[suffix]


def format_inr(value, with_symbol=True):
    d = Decimal(str(value)).quantize(Decimal('0.01'))
    sign = '-' if d < 0 else ''
    integer, _, fraction = str(abs(d)).partition('.')
    if len(integer) <= 3:
        grouped = integer
    else:
        last_three = integer[-3:]
        rest = integer[:-3]
        chunks = []
        while len(rest) > 2:
            chunks.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            chunks.append(rest)
        grouped = ','.join(reversed(chunks)) + ',' + last_three
    body = grouped + '.' + (fraction or '00')
    return (sign + 'Rs. ' + body) if with_symbol else (sign + body)


if __name__ == '__main__':
    for s in ['Rs. 1,23,456.50', '25K', '2.5L', '1.2C', 'INR 999.99']:
        v = parse_inr(s)
        print(s, '->', v, '->', format_inr(v))
