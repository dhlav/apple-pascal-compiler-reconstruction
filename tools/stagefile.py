"""Put one text file on SYSHD without rebuilding the volume.

    python tools/stagefile.py <source.text> <NAME.TEXT>

`mkharddisks.py` is the entry point for the volume's contents and stays
that way for anything the reconstruction depends on. This is for the case
it cannot serve: a file that has to arrive *between* two emulator steps,
where a rebuild would wipe the codefile the previous step just produced.

Same encoder, same 80-column check and same `PTX` attribute mkharddisks
uses, so a file staged here is indistinguishable from one it wrote. Two
things it does that a bare `cp2 add` does not:

  * deletes any existing copy first -- `cp2 add` silently skips a name
    that is already on the volume, which makes an A/B experiment report
    "no difference" when it actually compared a file against itself;
  * verifies the name is in the catalog afterwards, so a skip is an error
    here rather than a surprise three steps later.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r'C:\PascalRecon\tools')
from a2pascal.srcfmt import WIDTH, expand_tabs, over_width
from a2pascal.textfile import encode_text

CP2 = r'C:\CiderPress2\cp2.exe'
HD1 = r'C:\PascalRecon\build\disks\HD1.hdv'

src = Path(sys.argv[1])
name = sys.argv[2]


def cp2(*args: str, allow_fail: bool = False) -> str:
    r = subprocess.run([CP2, *args], capture_output=True, text=True)
    if r.returncode and not allow_fail:
        raise SystemExit(f'cp2 {" ".join(args)} failed:\n{r.stdout}{r.stderr}')
    return r.stdout


text = expand_tabs(src.read_text(encoding='ascii', errors='replace'))
text = text[:-1] if text.endswith('\n') else text
long = over_width(text.split('\n'))
if long:
    raise SystemExit(f'{name}: {len(long)} lines exceed {WIDTH} columns {long[:5]}')

cp2('delete', HD1, name, allow_fail=True)

# Not src.parent/name: Windows is case-insensitive, so a source called
# REMTEST.text and a staged name of REMTEST.TEXT are the same path, and
# writing the encoded form there overwrites the source being staged.
staging = src.parent / '_staging'
staging.mkdir(exist_ok=True)
tmp = staging / name
tmp.write_bytes(encode_text(text))
cp2('add', '--raw', '--no-strip-ext', '--strip-paths', HD1, str(tmp))
cp2('set-attr', HD1, 'type=PTX', name)

cat = cp2('catalog', HD1)
if name not in cat:
    raise SystemExit(f'{name} is not on the volume after add -- cp2 skipped it')
print(f'{name} staged on SYSHD')
for line in cat.splitlines():
    if name.split('.')[0] in line:
        print('  ' + line.strip())
