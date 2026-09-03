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
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))

from a2pascal.srcfmt import WIDTH, expand_tabs, over_width
from a2pascal.textfile import encode_text

CP2 = Path(r'C:\CiderPress2\cp2.exe')
HD1 = ROOT / 'build' / 'disks' / 'HD1.hdv'

if len(sys.argv) != 3:
    raise SystemExit('usage: python tools/stagefile.py <source.text> <NAME.TEXT>')
if not HD1.exists():
    raise SystemExit(f'{HD1.relative_to(ROOT)} has not been built '
                     '(python tools/mkharddisks.py)')

src = Path(sys.argv[1])
name = sys.argv[2]


def cp2(*args: str, allow_fail: bool = False) -> str:
    r = subprocess.run([str(CP2), *args], capture_output=True, text=True)
    if r.returncode and not allow_fail:
        raise SystemExit(f'cp2 {" ".join(args)} failed:\n{r.stdout}{r.stderr}')
    return r.stdout


text = expand_tabs(src.read_text(encoding='ascii', errors='replace'))
text = text[:-1] if text.endswith('\n') else text
long = over_width(text.split('\n'))
if long:
    raise SystemExit(f'{name}: {len(long)} lines exceed {WIDTH} columns {long[:5]}')

cp2("delete", str(HD1), name, allow_fail=True)

# A temp directory, not src.parent: Windows is case-insensitive, so a
# source called REMTEST.text and a staged name of REMTEST.TEXT are the
# same path, and writing the encoded form beside the source overwrites
# the source being staged. Staging beside it also drops build litter into
# whatever directory the source lives in, which for tools/remote/ is the
# repository.
staging = Path(tempfile.mkdtemp(prefix='stagefile-'))
tmp = staging / name
tmp.write_bytes(encode_text(text))
cp2("add", "--raw", "--no-strip-ext", "--strip-paths", str(HD1), str(tmp))
cp2("set-attr", str(HD1), "type=PTX", name)

cat = cp2("catalog", str(HD1))
if name not in cat:
    raise SystemExit(f'{name} is not on the volume after add -- cp2 skipped it')
shutil.rmtree(staging, ignore_errors=True)
print(f'{name} staged on SYSHD')
for line in cat.splitlines():
    if name.split('.')[0] in line:
        print('  ' + line.strip())
