"""Put one text file, or one codefile, on SYSHD without rebuilding the volume.

    python tools/stagefile.py <source.text> <NAME.TEXT>
    python tools/stagefile.py <file.CODE>   <NAME.CODE>
    python tools/stagefile.py --vol WORKHD <source.text> <NAME.TEXT>

A name ending in .CODE is staged byte for byte with the `PCD` attribute:
a codefile an earlier emulator step produced, going back on the volume for
the next tool -- the Librarian, finding 267. Anything else is text, encoded
and width-checked exactly as before.

`mkharddisks.py` is the entry point for the volume's contents and stays
that way for anything the reconstruction depends on. This is for the case
it cannot serve: a file that has to arrive *between* two emulator steps,
where a rebuild would wipe the codefile the previous step just produced.

Same encoder, same 80-column check (assembler source only, finding 272e)
and same `PTX` attribute mkharddisks uses, so a file staged here is indistinguishable from one it wrote. Two
things it does that a bare `cp2 add` does not:

  * deletes any existing copy first -- `cp2 add` silently skips a name
    that is already on the volume, which makes an A/B experiment report
    "no difference" when it actually compared a file against itself;
  * verifies the name is in the catalog afterwards, so a skip is an error
    here rather than a surprise three steps later.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))

from a2pascal.srcfmt import WIDTH, expand_tabs, over_width
from a2pascal.textfile import Layout, encode_text

CP2 = Path(r'C:\CiderPress2\cp2.exe')
HD1 = ROOT / 'build' / 'disks' / 'HD1.hdv'

IMAGES = {'SYSHD': (HD1, 'mkharddisks.py'),
          'WORKHD': (ROOT / 'build' / 'disks' / 'HD2.hdv', 'mkworkhd.py')}

argv = sys.argv[1:]
vol = 'SYSHD'
if len(argv) == 4 and argv[0] == '--vol':
    vol, argv = argv[1].upper().rstrip(':'), argv[2:]
if len(argv) != 2 or vol not in IMAGES:
    raise SystemExit('usage: python tools/stagefile.py [--vol SYSHD|WORKHD] '
                     '<source> <NAME.TEXT | NAME.CODE>')
HD1, builder = IMAGES[vol]
if not HD1.exists():
    raise SystemExit(f'{HD1.relative_to(ROOT)} has not been built '
                     f'(python tools/{builder})')

src = Path(argv[0])
name = argv[1]


def cp2(*args: str, allow_fail: bool = False) -> str:
    r = subprocess.run([str(CP2), *args], capture_output=True, text=True)
    if r.returncode and not allow_fail:
        raise SystemExit(f'cp2 {" ".join(args)} failed:\n{r.stdout}{r.stderr}')
    return r.stdout


CODE = name.upper().endswith('.CODE')
if CODE:
    payload = src.read_bytes()
else:
    text = expand_tabs(src.read_text(encoding='ascii', errors='replace'))
    text = text[:-1] if text.endswith('\n') else text
    long = over_width(text.split('\n'))
    if long:
        raise SystemExit(f'{name}: {len(long)} lines exceed {WIDTH} columns '
                         f'{long[:5]}')
    # A unit's interface lands in its codefile still encoded, so a unit
    # source carries a .layout beside it saying how Apple's editor stored
    # its lines (finding 285).
    payload = encode_text(text, layout=Layout.beside(src))

cp2("delete", str(HD1), name, allow_fail=True)

# A temp directory, not src.parent: Windows is case-insensitive, so a
# source called REMTEST.text and a staged name of REMTEST.TEXT are the
# same path, and writing the encoded form beside the source overwrites
# the source being staged. Staging beside it also drops build litter into
# whatever directory the source lives in, which for tools/remote/ is the
# repository.
staging = Path(tempfile.mkdtemp(prefix='stagefile-'))
tmp = staging / name
tmp.write_bytes(payload)
cp2("add", "--raw", "--no-strip-ext", "--strip-paths", str(HD1), str(tmp))
cp2("set-attr", str(HD1), f"type={'PCD' if CODE else 'PTX'}", name)

cat = cp2("catalog", str(HD1))
if name not in cat:
    raise SystemExit(f'{name} is not on the volume after add -- cp2 skipped it')
shutil.rmtree(staging, ignore_errors=True)
print(f'{name} staged on {vol}')
for line in cat.splitlines():
    if name.split('.')[0] in line:
        print('  ' + line.strip())
