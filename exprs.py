"""
Parens for grouping
Numeric constants string constants
 | for unions
Spaces are ignored

Types:
v - Varint (32-bit signed)
V - Varlong (64-bit signed)
? - Bool (Byte that is either 1 or 0)
b, B - Byte, Unsigned Byte
h, H - Short, Unsigned Short
i, I - Int, Unsigned Int
l, L - Long, Unsigned Long
f, d - Float, Double
N - NBT data
M - Entity metadata
S - Slot (item, quantity, damage, metadata)
s - String (Varint prefixed UTF8 string)
p - Position (a bitfield: struct{int x:26, y:12, z:26;})
a - Angle (in units of 2pi/256 rad)
u, U - UUID, UUID string (with hyphens)
A.. - Length prefixed array (example: Ais an int prefixed array of strings)
A<number>. - A fixed length array
A*. - Repeat . until eof (expects stream ends on boundary)
"""

frame = 'AvB'
compressed_frame = 'vA*B'

handshake_sb = 'v0x00 vsHv'

status_sb = """
v(0x00
 |0x01 l)
"""

status_cb = """
v(0x00 s
 |0x01 l)
"""

login_sb = """
v(0x00 s
 |0x01 AvBAvB)
"""

login_cb = """
v(0x00 s
 |0x01 sAvBAvB
 |0x02 Us
 |0x03 v)
"""

mc315_sb = """
v(0x00 v
 |0x01 s?(?1p|0)
 |0x02 s
 |0x03 v
 |0x04 sbv?Bv
 |0x05 bh?
 |0x06 bb
 |0x07 BhbhvS
 |0x08 B
 |0x09 sA*B
 |0x0a vv(0v|1|2fffv)
 |0x0b v
 |0x0c ddd?
 |0x0d dddff?
 |0x0e ff?
 |0x0f ?
 |0x10 dddff
 |0x11 ??
 |0x12 bff
 |0x13 vpb
 |0x14 vvv
 |0x15 ffB
 |0x16 v
 |0x17 S
 |0x18 hS
 |0x19 pssss
 |0x1a v
 |0x1b u
 |0x1c pvvfff
 |0x1d v)
"""

mc315_cb = """
v(0x00 vubdddaihhh
 |0x01 vdddh
 |0x02 vbddd
 |0x03 vuvdddaaahhhM
 |0x04 vuspb
 |0x05 vudddaaM
 |0x06 vB
 |0x07 Av(sv)
 |0x08 vpb
 |0x09 pBN
 |0x0a pBBv
 |0x0b pv
 |0x0c uv(0sfvvB|1|2f|3s|4vv|5B)
 |0x0d B
 |0x0e Avs
 |0x0f sB
 |0x10 iiAv(BBv)
 |0x11 bh?
 |0x12 B
 |0x13 Bs('EntityHorse'sBi|sB)
 |0x14 BAhS
 |0x15 Bhh
 |0x16 bhS
 |0x17 vv
 |0x18 sA*B
 |0x19 sviiiff
 |0x1a s
 |0x1b ib
 |0x1c ffffAi(bbb)fff
 |0x1d ii
 |0x1e Uf
 |0x1f v
 |0x20 ii?vAvBAvN
 |0x21 ipi?
 |0x22 i?fffffffiA*B
 |0x23 iBiBBs?
 |0x24 vb?Av(bbb)b(0|bbbAvB)
 |0x25 vhhh?
 |0x26 vhhhaa?
 |0x27 vaa?
 |0x28 v
 |0x29 dddff
 |0x2a p
 |0x2b bff
 |0x2c v(0|1vi|2vis)
 |0x2d v(0Av(usAv(ss?(0|1s)vv?(0|1s)))|1Av(uv)|2Av(uv)|3Av(u?(0|1s))|4Avu)
 |0x2e dddffbv
 |0x2f vp
 |0x30 Avv
 |0x31 vb
 |0x32 ss
 |0x33 iBBs
 |0x34 va
 |0x35 v(0d|1ddV|2dd|3dddVvvv|4v|5v)
 |0x36 v
 |0x37 b
 |0x38 bs
 |0x39 vM
 |0x3a ii
 |0x3b vhhh
 |0x3c vvS
 |0x3d fvv
 |0x3e fvf
 |0x3f sb(0ss|1|2ss)
 |0x40 vAvv
 |0x41 sb(0sssbssbAvs|1|2sssbssb|3Avs|4Avs)
 |0x42 sb(0sv|1s)
 |0x43 p
 |0x44 ll
 |0x45 v(0s|1s|2s|3iii|4|5)
 |0x46 vviiiff
 |0x47 ss
 |0x48 vvv
 |0x49 vdddaa?
 |0x4a vAi(sdAv(udB))
 |0x4b vbbvb)
"""
