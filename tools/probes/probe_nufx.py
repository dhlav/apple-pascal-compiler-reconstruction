"""Parse the NuFX (ShrinkIt) master + record headers of ii0src.sdk."""
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
d = (ROOT / "evidence" / "disks" / "ii0src.sdk").read_bytes()

assert d[:4] == b"N\xf5F\xe9"
master_crc = struct.unpack_from("<H", d, 6)[0]
total_records = struct.unpack_from("<I", d, 8)[0]
master_version = struct.unpack_from("<H", d, 28)[0]
master_eof = struct.unpack_from("<I", d, 38)[0]
print(f"master: records={total_records} eof={master_eof} version={master_version}")

THREAD_CLASS = {0: "message", 1: "control", 2: "data", 3: "filename"}
THREAD_KIND = {
    (0, 0): "ASCII text", (0, 1): "Allocate space", (0, 2): "Disk image",
    (1, 0): "create dir",
    (2, 0): "data fork", (2, 1): "disk image", (2, 2): "resource fork",
    (3, 0): "filename",
}
FORMATS = {0: "uncompressed", 1: "SQueeze", 2: "LZW/1", 3: "LZW/2",
           4: "LZC-12", 5: "LZC-16"}

p = 48
for r in range(total_records):
    assert d[p:p + 4] == b"N\xf5F\xd8", d[p:p + 4]
    hcrc, attrib_count, version, total_threads = struct.unpack_from("<HHHI", d, p + 4)
    file_sys_id, file_sys_info = struct.unpack_from("<HH", d, p + 14)
    access, file_type, extra_type, storage_type = struct.unpack_from("<IIIH", d, p + 18)
    # attrib_count spans the record header through the filename_length field
    namelen = struct.unpack_from("<H", d, p + attrib_count - 2)[0]
    q = p + attrib_count
    name = d[q:q + namelen]
    q += namelen
    print(f"record {r}: attrib_count={attrib_count} threads={total_threads} "
          f"fsid={file_sys_id} storage={storage_type} name={name!r}")
    threads = []
    for t in range(total_threads):
        tcls, tfmt, tkind, tcrc, teof, tcomp = struct.unpack_from("<HHHHII", d, q)
        threads.append((tcls, tfmt, tkind, teof, tcomp))
        print(f"   thread {t}: class={THREAD_CLASS.get(tcls, tcls)} "
              f"kind={THREAD_KIND.get((tcls, tkind), tkind)} "
              f"format={FORMATS.get(tfmt, tfmt)} eof={teof} comp_len={tcomp} crc=0x{tcrc:04X}")
        q += 16
    data_start = q
    for tcls, tfmt, tkind, teof, tcomp in threads:
        print(f"   -> data at 0x{data_start:X}: {d[data_start:data_start + 16].hex(' ')}")
        data_start += tcomp
    p = data_start
