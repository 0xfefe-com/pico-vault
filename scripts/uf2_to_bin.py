import struct
import sys

UF2_MAGIC_START0        = 0x0A324655  # "UF2\n"
UF2_MAGIC_START1        = 0x9E5D5157
UF2_MAGIC_END           = 0x0AB16F30
UF2_FLAG_NOT_MAIN_FLASH = 0x00000001

def uf2_to_bin(uf2_file, bin_file):
    with open(uf2_file, "rb") as uf2, open(bin_file, "wb") as bin_out:
        while True:
            block = uf2.read(512)
            if not block:
                break
            if len(block) != 512:
                raise ValueError(f"truncated UF2 block ({len(block)} bytes)")
            (magic0, magic1, flags, _addr, payload_size,
             block_no, _num_blocks, _file_or_family) = struct.unpack("<IIIIIIII", block[:32])
            magic_end = struct.unpack("<I", block[508:512])[0]
            if magic0 != UF2_MAGIC_START0 or magic1 != UF2_MAGIC_START1 \
                    or magic_end != UF2_MAGIC_END:
                raise ValueError(f"invalid UF2 block #{block_no}")
            if payload_size > 476:
                raise ValueError(f"block #{block_no}: payload too large ({payload_size})")
            if flags & UF2_FLAG_NOT_MAIN_FLASH:
                continue
            bin_out.write(block[32:32 + payload_size])

if len(sys.argv) != 3:
    print("Usage: python uf2_to_bin.py input.uf2 output.bin")
    sys.exit(1)

uf2_to_bin(sys.argv[1], sys.argv[2])
print(f"Converted {sys.argv[1]} to {sys.argv[2]}")
