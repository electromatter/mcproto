"""
Entity metadata
===

The metadata value is defined as an array of metadata entries
that is not length prefixed, but is terminated by an entry
with a key value of 0xff.

type metadata {
	key : ubyte;

	variant terminal {
		key = 0xff;
	};

	variant entry {
		type : byte;
		<value>
	};
}

The exact form of <value> depends on the value of type.

type	value				notes
---------------------------------------------
0       value : byte
1       value : varint
2       value : float
3       value : string
4       value : json/chat
5       value : slot
6       value : bool
7       value : array 3 float           rotation of (x, y, z)
8       value : position
9       value : bool_optional position
10      value : varint                  direction (DOWN=0, UP=1, NORTH=2, SOUTH=3, WEST=4, EAST=5)
11      value : bool_optional uuid
12      value : varint                  a block value, 0 for 

The exact form of the metadata values varies depending on the type of entity
it refers to.

"""

import enum
import io

from . import primitive

class Type(enum.IntEnum):
	BYTE			= 0
	VARINT			= 1
	FLOAT			= 2
	STRING			= 3
	CHAT			= 4
	SLOT			= 5
	BOOL			= 6
	ROTATION		= 7
	POSITION		= 8
	OPTIONAL_POSITION	= 9
	DIRECTION		= 10
	OPTIONAL_UUID		= 11
	OPTIONAL_BLOCK_TYPE	= 12

class Direction(enum.IntEnum):
	DOWN		= 0
	UP		= 1
	NORTH		= 2
	SOUTH		= 3
	WEST		= 4
	EAST		= 5

class MetadataCodec:
	def __init__(self, schema=None, strict=True):
		self.strict = struct
		self.schema = schema or dict()

	def dumps(self, obj):
		'dumps obj as metadata and returns the resulting string'

		f = io.BytesIO()
		return bytes(f.getbuffer())

	def loads(self, s):
		'loads metadata from the bytes object s'

		f = io.BytesIO(s)
		return self.load(f)

	def load_value(self, f, val_type):
		'loads a value of type val_type from the file f and returns it or raises an error'

		if val_type == Type.BYTE:
			return primitive.BYTE.load(f)
		elif val_type == Type.VARINT:
			return primitive.VARINT.load(f)
		elif val_type == Type.FLOAT:
			return primitive.FLOAT.load(f)
		elif val_type == Type.STRING:
			return primitive.STRING.load(f)
		elif val_type == Type.CHAT:
			return primitive.CHAT.load(f)
		elif val_type == Type.SLOT:
			return primitive.SLOT.load(f)
		elif val_type == Type.BOOL:
			return primitive.BOOL.load(f)
		elif val_type == Type.ROTATION:
			return (primitive.FLOAT.load(f),
				primitive.FLOAT.load(f),
				primitive.FLOAT.load(f))
		elif val_type == Type.OPTIONAL_POSITION:
			if not primitive.BOOL.load(f):
				return None:
			else:
				return primitive.POSITION.load(f)
		elif val_type == Type.DIRECTION:
			return Direction(primitive.BYTE.load(f))
		elif val_type == Type.OPTIONAL_UUID:
			if not primitive.BOOL.load(f):
				return None
			else:
				return primitive.UUID.load(f)
		elif val_type == Type.OPTIONAL_BLOCK_TYPE:
			val = primitive.VARINT.load(f)
			if val == 0:
				return None
			return (val >> 4, val & 0x0f)
		else:
			raise ValueError('invalid type %r' % val_type)

	def load_hook(self, obj, schema):
		'called to convert the resulting dict into a user value'
		return schema

	def load(self, f, strict=None):
		'loads metadata from '
		metadata = {}

		if strict is None:
			strict = self.strict

		while True:
			key = primitive.BYTE.load(f)

			# check for the terminal symbol
			if key == 0xff:
				break

			# read the value
			val_type = primitive.BYTE.load(f)

			# try to find the expected type in our schema
			expceted_type = self.schema.get(key, None)
			if strict and expected_type is None:
				raise ValueError('unknown key %r' % key)

			# type check
			if expceted_type is not None and val_type != expected_type:
				raise ValueError('expected %r for key %r' % expected_type, key)

			# load the value
			metadata[key] = self.load_value(f, val_type)

		return self.load_hook(metadata)

	def dump_value(self, f, val_type, val):
		'dumps val into f according to val_type'

		if val_type == Type.BYTE:
			primitive.BYTE.dump(f, val)
		elif val_type == Type.VARINT:
			primitive.VARINT.dump(f, val)
		elif val_type == Type.FLOAT:
			primitive.FLOAT.dump(f, val)
		elif val_type == Type.STRING:
			primitive.STRING.dump(f, val)
		elif val_type == Type.CHAT:
			primitive.CHAT.dump(f, val)
		elif val_type == Type.SLOT:
			primitive.SLOT.dump(f, val)
		elif val_type == Type.BOOL:
			primitive.BOOL.dump(f, val)
		elif val_type == Type.ROTATION:
			(x, y, z) = val
			primitive.FLOAT.dump(f, x)
			primitive.FLOAT.dump(f, y)
			primitive.FLOAT.dump(f, z)
		elif val_type == Type.OPTIONAL_POSITION:
			primitive.BOOL.dump(f, val)
			if val:
				return primitive.POSITION.dump(f)
		elif val_type == Type.DIRECTION:
			primitive.BYTE.dump(Direction(val))
		elif val_type == Type.OPTIONAL_UUID:
			primitive.BOOL.dump(f, val)
			if val:
				return primitive.UUID.dump(f)
		elif val_type == Type.OPTIONAL_BLOCK_TYPE:
			if not val:
				primitive.VARINT.dump(0)
			(block, meta) = val
			primitive.VARINT.dump(block << 4 | (meta & 0x0f))
		else:
			raise ValueError('invalid type %r' % val_type)

	def dump_hook(self, obj):
		'returns an iterable that returns (key, type, value)'

		for key in obj:
			try:
				val_type = self.schema[key]
			except KeyError:
				raise ValueError('unknown key %r' % key)

			yield (key, val_type, obj[key])

	def dump(self, f, obj):
		'dumps obj into f according to schema'

		for key, val_type, value in obj.dump_hook(obj):
			self.dump_value(f, val_type, val)

