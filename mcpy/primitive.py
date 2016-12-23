"""
Primitive types used by the MC protocol

Integer types:
 - Bool
 - varint
 - varlong
 - ubyte/byte
 - ushort/short
 - uint/int
 - ulong/long

Fractional:
 - float/double
 - angle
 - fixed point numbers

String types:
 - string
 - chat (see chat.py)
 - bytes
 - uuid

Complex:
 - metadata (see metadata.py)
 - nbt (see nbt.py)
 - array

Utility:
 - slot (see nbt.py)
 - position
 - blocktype (blockid + meta)

"""

import collections
import enum
import io
import struct
import math
import uuid

Position = collections.namedtuple('Position', 'x y z')
BlockType = collections.namedtuple('BlockType', 'blockid meta')

class BaseCodec:
	def loads(self, s):
		f = io.BytesIO(s)
		return self.load(f)

	def dumps(self, val):
		f = io.BytesIO()
		self.dump(f, val)
		return bytes(f.getbuffer())

	def load(self, f):
		raise NotImplementedError

	def dump(self, f, val):
		raise NotImplementedError

class IntCodec(BaseCodec):
	pass

class StructCodec(BaseCodec):
	def __init__(self, pattern):
		self.struct = struct.Struct(pattern)

	def load(self, f):
		temp = f.read(self.struct.size)

		if len(temp) < self.struct.size:
			raise EOFError

		return self.struct.unpack(temp)

	def dump(self, f, val):
		f.write(self.struct.pack(*val))

class SimpleStructCodec(StructCodec):
	def load(self, f):
		return super().load(f)[0]

	def dump(self, f, val):
		super().dump(f, (val,))

class StructIntCodec(SimpleStructCodec, IntCodec):
	pass

BOOL = StructIntCodec('>?')

BYTE = StructIntCodec('>b')
UBYTE = StructIntCodec('>B')

SHORT = StructIntCodec('>h')
USHORT = StructIntCodec('>H')

INT = StructIntCodec('>i')
UINT = StructIntCodec('>I')

LONG = StructIntCodec('>l')
ULONG = StructIntCodec('>L')

FLOAT = SimpleStructCodec('>f')
DOUBLE = SimpleStructCodec('>d')

class VarintCodec(IntCodec):
	def __init__(self, nbits=32):
		assert nbits > 1
		self.nbits = nbits
		self.sign = 1 << (nbits - 1)
		self.max_unsigned = self.sign | (self.sign - 1)

	def load(self, f):
		val = 0
		shift = 0

		while shift < self.nbits:
			byte = f.read(1)
			if byte == b'':
				raise EOFError

			val |= (byte[0] & 0x7f) << shift
			shift += 7

			if not (byte[0] & 0x80):
				# it could be that the last byte put us over
				# the max, check that
				if val > self.max_unsigned:
					break

				# convert to signed
				if val & self.sign:
					val -= self.sign

				return val

		raise ValueError('varint value exceeds max')

	def dump(self, f, val):
		temp = []
		val = int(val)

		# range check
		if val < -self.sign or val >= self.sign:
			raise ValueError('varint out of range')

		# convert to unsigned
		if val < 0:
			val += self.sign

		# encode the varint into temp
		while True:
			if val > 0x7f:
				temp.append(0x80 | (val & 0x7f))
				val >>= 7
			else:
				temp.append(val)
				break

		# write value
		f.write(bytes(temp))

VARINT = VarintCodec(32)
VARLONG = VarintCodec(64)

class AngleCodec(BaseCodec):
	def load(self, f):
		val = UBYTE.load(f)
		# convert from 1/256 steps to radians
		return val * (2 * math.pi / 256)

	def dump(self, f, val):
		# convert from radians to 1/256 steps
		val = (val * (256  / 2 * math.pi)) % 256
		# round to nearest
		UBYTE.dump(int(round(val)) % 256)

class PositionCodec(BaseCodec):
	def load(self, f):
		val = ULONG.load(f)
		x = val >> 38
		y = (val >> 26) & 0xfff
		z = val & 0x3ffffff

		if x & 0x2000000:
			x -= 0x2000000

		if y & 0x800:
			y -= 0x800

		if z & 0x2000000:
			z -= 0x2000000

		return Position(x, y, z)

	def dump(self, f, val):
		x, y, z = int(val.x), int(val.y), int(val.z)

		# bounds check
		if x < -0x2000000 or x >= 0x2000000:
			raise ValueError('x out of range must be 26 bits signed')

		if y < -0x800 or y >= 0x800:
			raise ValueError('y out of range must be 12 bits signed')

		if z < -0x2000000 or z >= 0x2000000:
			raise ValueError('z out of range must be 26 bits signed')

		# convert sign
		ULONG.dump(f, ((x & 0x3ffffff) << 38) | ((y & 0xfff) << 26) | (z & 0x3ffffff))

class BlockTypeCodec(BaseCodec):
	def load(self, f):
		val = VARINT.load(f)

		if val < 0:
			raise ValueError('invalid blocktype')

		if val == 0:
			return None

		return BlockType(val >> 4, val & 0x0f)

	def dump(self, f, val):
		if val is None:
			VARINT.dump(0)

		blockid = int(val.blockid)
		meta = int(val.meta)

		if blockid < 0 or blockid > 0x7ffffff:
			raise ValueError('blockid out of range?')

		if meta < 0 or meta > 0x0f:
			raise ValueError('meta out of range?')

		VARINT.dump(f, (blockid << 4) | meta)

class BytesCodec(BaseCodec): 
	def __init__(self, length=None):
		if length is None:
			self.length = length
		elif isinstance(length, int):
			self.length = length
		elif isinstance(length, IntCodec):
			self.length = length
		else:
			raise TypeError('length must be None or an int or an IntCodec got %r' % length.__class__)

	def load(self, f):
		if self.length is None:
			return f.read()

		if isinstance(self.length, int):
			length = self.length
		else:
			length = self.length.load(f)

		val = f.read(length)
		if len(val) != length:
			raise EOFError

		return val

	def dump(self, f, val):
		if isinstance(self.length, int):
			if len(val) != self.length:
				raise ValueError('expected %r bytes got %r' % (self.length, len(val)))
		elif self.length is not None:
			self.length.dump(f, len(val))
		f.write(val)

class StringCodec(BaseCodec):
	def __init__(self, length=None, encoding='utf8'):
		self.codec = BytesCodec(length)
		self.encoding = encoding
		''.encode(encoding)

	def load(self, f):
		return self.codec.load().decode(self.encoding)

	def dump(self, f, val):
		if not isinstance(val, str):
			raise TypeError('expected str got %r' % val.__class__)
		self.codec.dump(f, val.encode(self.encoding))

class UUIDCodec(BaseCodec):
	"""
	Supports the encodings:
	 - "bin" or "bytes"		(raw uuid big-endian order)
	 - "hex"			(without the dashes)
	 - "rfc" or "std" or "uuid"	(standard format with dashes)
	"""

	def __init__(self, encoding='bin', length=None):
		encoding = encoding.lower()

		if encoding in ['bin', 'bytes']:
			self.codec = BytesCodec(length or 16)
			self.encoding = 'bin'
		elif encoding in ['hex']:
			self.codec = StringCodec(length or 32, 'utf8')
			self.encoding = 'hex'
		elif encoding in ['rfc', 'std', 'uuid']:
			self.codec = StringCodec(length or 36, 'utf8')
			self.encoding = 'rfc'
		else:
			raise ValueError('unknown uuid encoding %r' % encoding)

	def load(self, f):
		val = self.codec.load(f)
		if self.encoding == 'bin':
			return uuid.UUID(bytes=val)
		elif self.encoding == 'hex':
			return uuid.UUID(val)
		elif self.encoding == 'rfc'
			return uuid.UUID(val)
		else:
			raise AssertionError('unknown encoding?')

	def dump(self, f, val):
		if not isinstance(val, uuid.UUID):
			raise ValueError('expected uuid.UUID got %r' % val.__class__)

		if self.encoding == 'bin':
			self.codec.dump(val.bytes)
		elif self.encoding == 'hex':
			self.codec.dump(val.hex)
		elif self.encoding == 'rfc':
			self.codec.dump(str(val))
		else:
			raise AssertionError('unknown encoding?')

ANGLE = AngleCodec()
POSITION = PositionCodec()
BLOCKTYPE = BlockTypeCodec()
STRING = StringCodec()
BYTES = BytesCodec()
UUID = UUIDCodec()

class ArrayCodec(BaseCodec):
	def __init__(self, elem, length=VARINT):
		self.elem = elem

		if isinstance(length, int) or isinstance(length, IntCodec):
			self.length = length
		else:
			raise TypeError('expected an integer or a integer codec for length, got %r' % length.__class__)

	def load(self, f):
		if isinstance(self.length, int):
			length = self.length
		else:
			length = self.length.load(f)

		if length < 0:
			raise ValueError('negitive length?')

		return [self.elem.load(f) for _ in range(length)]

	def dump(self, f, val):
		# we also support None as a zero length array
		if val is None:
			val = tuple()

		# if we got an iterable that does not support len(), then
		# evaluate it.
		if not hasattr(val, '__len__'):
			val = tuple(val)

		# write out the length
		if isinstance(self.length, int):
			if self.length != len(val):
				raise ValueError('expected an iterable of length %i got %i elements' % (self.length, len(val)))
		else:
			self.length.dump(f, len(val))

		# write out the elements
		for item in val:
			self.elem.dump(f, item)

class EnumCodec(BaseCodec):
	def __init__(self, enum, codec):
		self.enum = enum
		self.codec = codec

	def load(self, f):
		# load value
		val = self.codec.load(f)

		# ensure val is in enum
		return self.enum(val)

	def dump(self, f, val):
		# ensure val is in enum
		val = self.enum(val)

		# dump val
		self.codec.dump(f, val)

class IntEnumCodec(EnumCodec, IntCodec):
	def __init__(self, enum, codec=VARINT):
		if not isinstance(codec, IntCodec):
			raise TypeError('expceted an integer codec as the codec of %r' % enum)
		super().__init__(enum, codec)

class Direction(enum.IntEnum):
	DOWN	= 0
	UP	= 1
	NORTH	= 2
	SOUTH	= 3
	WEST	= 4
	EAST	= 5

DIRECTION = IntEnumCodec(Direction)

