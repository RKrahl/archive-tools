import hashlib
import stat


def checksum(fileobj, hashalg):
    """Calculate hashes for a file.
    """
    if not hashalg:
        return {}
    m = { h:hashlib.new(h) for h in hashalg }
    chunksize = 8192
    while True:
        chunk = fileobj.read(chunksize)
        if not chunk:
            break
        for h in hashalg:
            m[h].update(chunk)
    return { h: m[h].hexdigest() for h in hashalg }


def modstr(t, m):
    ftch = '-' if t == 'f' else t
    urch = 'r' if m & stat.S_IRUSR else '-'
    uwch = 'w' if m & stat.S_IWUSR else '-'
    if m & stat.S_ISUID:
        uxch = 's' if m & stat.S_IXUSR else 'S'
    else:
        uxch = 'x' if m & stat.S_IXUSR else '-'
    grch = 'r' if m & stat.S_IRGRP else '-'
    gwch = 'w' if m & stat.S_IWGRP else '-'
    if m & stat.S_ISGID:
        gxch = 's' if m & stat.S_IXGRP else 'S'
    else:
        gxch = 'x' if m & stat.S_IXGRP else '-'
    orch = 'r' if m & stat.S_IROTH else '-'
    owch = 'w' if m & stat.S_IWOTH else '-'
    if m & stat.S_ISVTX:
        oxch = 't' if m & stat.S_IXOTH else 'T'
    else:
        oxch = 'x' if m & stat.S_IXOTH else '-'
    chars = (ftch, urch, uwch, uxch, grch, gwch, gxch, orch, owch, oxch)
    return ''.join(chars)
