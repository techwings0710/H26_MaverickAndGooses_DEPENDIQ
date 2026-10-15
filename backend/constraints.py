"""Conservative PEP 440 conflict proofs. Lack of a witness is not a proof."""
from packaging.specifiers import SpecifierSet
from packaging.version import Version, InvalidVersion


def compatible(constraints: list[str]) -> tuple[str, str]:
    combined = SpecifierSet(','.join(c for c in constraints if c))
    specs = list(combined)
    pins = [s.version for s in specs if s.operator == '==' and '*' not in s.version]
    if pins:
        pin = next((p for p in pins if combined.contains(p, prereleases=True)), None)
        if pin is None:
            return 'conflict', f'Exact pins {pins} cannot satisfy the combined constraints {combined}.'
        return 'compatible', f'{pin} is a PEP 440 witness; release availability is not checked.'
    lower, upper = None, None
    complex_form = False
    candidates = {'0', '1', '2', '10', '100'}
    for s in specs:
        try:
            v = Version(s.version.removesuffix('.*'))
        except InvalidVersion:
            complex_form = True
            continue
        candidates.add(str(v))
        release = list(v.release)
        candidates.add('.'.join(map(str, release + [1])))
        candidates.add('.'.join(map(str, release[:-1] + [release[-1] + 1])))
        if v.pre or v.post or v.dev or v.local or v.epoch:
            complex_form = True
        lo = hi = None
        if s.operator in ('>=', '>'):
            lo = (v, s.operator == '>=')
        elif s.operator in ('<=', '<'):
            hi = (v, s.operator == '<=')
        elif s.operator == '~=' or (s.operator == '==' and s.version.endswith('.*')):
            lo = (v, True)
            prefix = list(v.release[:-1] if s.operator == '~=' else v.release)
            prefix[-1] += 1
            hi = (Version('.'.join(map(str, prefix))), False)
        elif s.operator not in ('!=',):
            complex_form = True
        if lo and (lower is None or lo[0] > lower[0] or (lo[0] == lower[0] and not lo[1])):
            lower = lo
        if hi and (upper is None or hi[0] < upper[0] or (hi[0] == upper[0] and not hi[1])):
            upper = hi
    # A witness is useful even for complex forms; never assert a release exists.
    for value in sorted(candidates):
        if combined.contains(value, prereleases=True):
            return 'compatible', f'{value} satisfies the declared specifiers; release availability is not checked.'
    if lower and upper and not complex_form:
        if lower[0] > upper[0] or (lower[0] == upper[0] and (not lower[1] or not upper[1] or not combined.contains(lower[0], prereleases=True))):
            return 'conflict', f'Empty PEP 440 range: lower {lower}, upper {upper}, with exclusions {combined}.'
    return 'unknown', 'No satisfying witness found. Complex exclusions or version forms need a package resolver.'
