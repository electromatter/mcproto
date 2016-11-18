import collections
import copy
import enum
import io
import struct
import uuid

from nbt import nbt

#TODO POSITION, FIXEDPOINT, AND ANGLES

__all__ = [
	'FieldType',
	'EnumFieldType', 'EnumType', 'FlagType',
	'StructType', 'ScalarStructType', 'IntStructType',
	'VarintType',
	'RawType', 'StringType', 'UUIDType',
	'Array',
	'BoolOptional',
	'NBTType', 'SlotType',

	'Slot',

	'VARINT', 'VARLONG', 'BOOL',
	'BYTE', 'SHORT', 'INT', 'LONG',
	'UBYTE', 'USHORT', 'UINT', 'ULONG',

	'FLOAT', 'DOUBLE',

	'RAW', 'BYTES', 'STRING', 'UUID',

	'NBT', 'SLOT',

	'POSITION',
	'ANGLE',
	'FIXED_BYTE', 'FIXED_INT']

class FieldType:
	def load(self, f):
		raise NotImplementedError

	def loads(self, s):
		f = io.BytesIO(s)
		return self.load(f)

	def dump(self, f, val):
		raise NotImplementedError

	def dumps(self, val):
		f = io.BytesIO()
		self.dump(f, val)
		return bytes(f.getbuffer())

	def _clone(self):
		return copy.deepcopy(self)

class EnumFieldType(FieldType):
	def __init__(self, base, enum):
		self.base = base
		self.enum = enum

	def load(self, f):
		val = self.base.load(f)
		return self.enum(val)

	def dump(self, f, val):
		val = self.enum(val)
		self.base.dump(f, val.value)

class ClassProperty:
	def __init__(self, fget):
		self.fget = fget

	def __get__(self, obj, cls):
		return self.fget(cls)

class EnumType(FieldType):
	def __init__(self):
		super().__init__()
		self.Enum = self._make_enumtype()

	def _make_enumtype(field):
		class _Enum(enum.Enum):
			@ClassProperty
			def _TYPE(cls):
				return EnumFieldType(field, cls)

		return _Enum

class FlagType(EnumType):
	def __init__(self):
		super().__init__()
		self.Flag = self._make_flagtype()

	def _make_enumtype(field):
		class _Enum(enum.IntEnum):
			@ClassProperty
			def _TYPE(cls):
				return EnumFieldType(field, cls)

		return _Enum

	def _make_flagtype(field):
		class _Flag(enum.Flag):
			@ClassProperty
			def _TYPE(cls):
				return EnumFieldType(field, _Flag)

		return _Flag

class StructType(struct.Struct, EnumType):
	def __init__(self, _format):
		struct.Struct.__init__(self, _format)
		EnumType.__init__(self)

	def load(self, f):
		raw = f.read(self.size)
		if len(raw) != self.size:
			raise EOFError()
		return self.unpack(raw)

	def dump(self, f, val):
		f.write(self.pack(val))

	def size(self, val):
		return len(self.pack(val))

class ScalarStructType(StructType):
	def load(self, f):
		val, = super().load(f)

	def dump(self, f, val):
		super().dump(f, val)

class IntStructType(ScalarStructType, FlagType):
	def __init__(self, _format):
		ScalarStructType.__init__(self, _format)
		FlagType.__init__(self)

class VarintType(FlagType):
	def __init__(self, bits=None, sign='twos'):
		super().__init__()
		sign.lower()
		if sign not in ('twos', 'unsigned', 'zigzag'):
			raise TypeError('unknown sign type %r' % sign)

		if sign == 'twos' and bits is None:
			raise TypeError('bits must be specified for twos complement sign mode')

		self.sign = sign
		self.bits = bits

		if self.bits:
			if self.sign in ('twos', 'zigzag'):
				self.sign_bit = 1 << (bits - 1)
				self.umax = (1 << bits) - 1
				self.min = -self.sign_bit
				self.max = self.sign_bit - 1
			else:
				self.umax = self.max = (1 << bits) - 1
				self.min = 0

	def hton(self, val):
		if val < self.min or val > self.max:
			raise ValueError('value out of range')

		if self.sign == 'twos':
			if val < 0:
				return val + self.sign_bit
			return val
		elif self.sign == 'zigzag':
			if val < 0:
				return ((-val) << 1) | 1
			else:
				return val << 1
		elif self.sign == 'unsigned':
			return val

	def ntoh(self, val):
		if val > self.umax:
			raise ValueError('value out of range')
		if self.sign == 'twos':
			if val & self.sign_bit:
				return val - self.sign_bit
			return val
		elif self.sign == 'zigzag':
			if val & 1:
				return -(val >> 1)
			return val >> 1
		elif self.sign == 'unsigned':
			return val

	def size(self, val):
		val = self.hton(val)
		size = 0
		while True:
			size += 1
			val >>= 7
			if val == 0:
				break
		return size

	def load(self, f):
		val = 0
		shift = 0

		while True:
			byte = f.read(1)
			if byte == b'':
				raise EOFError()

			val |= (byte[0] & 0x7f) << shift
			shift += 7

			if not (byte[0] & 0x80):
				break

		return self.ntoh(val)

	def dump(self, f, val):
		val = self.hton(val)
		while True:
			if val > 0x7f:
				f.write(bytes([(val & 0x7f) | 0x80]))
			else:
				f.write(bytes([val]))

			val >>= 7

			if val == 0:
				break

# Default integer types
VARINT = VarintType(32)
VARLONG = VarintType(64)

BOOL = ScalarStructType('>?')

BYTE = IntStructType('>b')
SHORT = IntStructType('>h')
INT = IntStructType('>i')
LONG = IntStructType('>l')

UBYTE = IntStructType('>B')
USHORT = IntStructType('>H')
UINT = IntStructType('>I')
ULONG = IntStructType('>L')

FLOAT = ScalarStructType('>f')
DOUBLE = ScalarStructType('>d')

class RawType(FieldType):
	def __init__(self, length=None):
		self.length = length

	def load(self, f):
		if self.length is None:
			return f.read()

		if isinstance(self.length, int):
			size = self.length
		else:
			size = self.length.load(f)

		raw = f.read(size)

		if len(raw) != size:
			raise EOFError()

		return raw

	def dump(self, f, val):
		if self.length is None:
			f.write(val)
			return

		if isinstance(self.length, int):
			# truncate to self.length
			val = val[:self.length]
			f.write(val)
			# pad with zeros up to self.length
			f.write(b'\x00' * (self.length - len(val)))
			return

		self.length.dump(f, len(val))
		f.write(val)

class StringType(EnumType):
	def __init__(self, length=VARINT, encoding='utf8'):
		super().__init__()

		self.encoding = encoding
		self.bytes = RawType(length)

	def load(self, f):
		return self.bytes.load(f).decode(self.encoding)

	def dump(self, f, val):
		self.bytes.dump(f, val.encode(self.encoding))

class UUIDType(FieldType):
	def __init__(self, **kwargs):
		self.string = kwargs.pop('string', False)
		if self.string:
			self.hyphens = kwargs.pop('hyphens', True)
			self.field = StringType(**kwargs)
		else:
			self.field = RawType()

	def load(self, f):
		val = self.field.load(f)
		return uuid.UUID(val)

	def dump(self, f, val):
		if not isinstance(val, uuid.UUID):
			val = uuid.UUID(val)
		if self.string:
			if self.hyphens:
				val = str(val)
			else:
				val = val.hex
		else:
			val = val.bytes
		self.field.dump(f, val)

# Default String Types
RAW = RawType()
BYTES = RawType(VARINT)
STRING = StringType()
UUID = UUIDType()

# Compound types
class Array(FieldType):
	def __init__(self, elem, length=VARINT):
		self.length = length
		self.elem = elem

	def load(self, f):
		if isinstance(self.length, int):
			size = self.length
		else:
			size = self.length.load(f)

		if size < 0:
			raise ValueError('size is negative?')

		return [self.elem.load(f) for _ in range(size)]

	def dump(self, f, val):
		if not hasattr(val, '__len__'):
			val = tuple(val)

		if isinstance(self.length, int):
			if len(val) != self.length:
				raise ValueError('fixed length array expected %i elements got %i' % (self.len, len(val)))
		else:
			self.length.dump(f, len(val))

		for elem in val:
			self.elem.dump(f, elem)

class BoolOptional(FieldType):
	def __init__(self, base, false=None, bool=BOOL):
		self.base = base
		self.bool = bool
		self.false = false

	def load(self, f):
		if self.bool.load(f):
			return self.base.load(f)
		return self.false

	def dump(self, f, val):
		if val == self.false:
			self.bool.dump(f, False)
		else:
			self.bool.dump(f, True)
			self.base.dump(f, val)

class NBTType(FieldType):
	def load(self, f):
		tag = nbt.TAG_Compound(buffer=f)
		if not tag:
			return None
		return tag

	def dump(self, f, val):
		if not val:
			BYTE.dump(f, 0)
			return
		val._render_buffer(f)

Slot = collections.namedtuple('Slot', 'item count damage tag')

class SlotType(FieldType):
	def load(self, f):
		item = SHORT.load(f)
		if item < 0:
			return None
		count = BYTE.load(f)
		damage = SHORT.load(f)
		tag = NBT.load(f)
		return Slot(item, count, damage, tag)

	def dump(self, f, val):
		if not val:
			SHORT.dump(f, -1)
			return

		item, count, damage, tag = val

		if item < 0:
			SHORT.dump(f, -1)
			return

		SHORT.dump(f, item)
		BYTE.dump(f, count)
		SHORT.dump(f, damage)
		NBT.dump(f, tag)

NBT = NBTType()
SLOT = SlotType()

#TODO MAKE THIS BETTER
POSITION = LONG
ANGLE = BYTE
FIXED_BYTE = BYTE
FIXED_INT = INT

