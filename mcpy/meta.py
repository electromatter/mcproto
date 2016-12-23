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

import collections
import enum
import io

from .primitive import BOOL, BYTE, VARINT, FLOAT, STRING, SLOT, POSITION, BLOCKTYPE, \
		       Direction, Position, BlockType, BaseCodec

from .chat	import CHAT

from .nbt	import SLOT

__all__ = ['Rotation', 'MetadataCodec', 'METADATA']

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

Rotation = collections.namedtuple('Rotation', 'rx ry rz')

class MetadataCodec(BaseCodec):
	def load_value(self, f, val_type):
		'loads a value of type val_type from the file f and returns it or raises an error'

		if val_type == Type.BYTE:
			return BYTE.load(f)
		elif val_type == Type.VARINT:
			return VARINT.load(f)
		elif val_type == Type.FLOAT:
			return FLOAT.load(f)
		elif val_type == Type.STRING:
			return STRING.load(f)
		elif val_type == Type.CHAT:
			return CHAT.load(f)
		elif val_type == Type.SLOT:
			return SLOT.load(f)
		elif val_type == Type.BOOL:
			return BOOL.load(f)
		elif val_type == Type.ROTATION:
			return Rotation(FLOAT.load(f),
					FLOAT.load(f),
					FLOAT.load(f))
		elif val_type == Type.OPTIONAL_POSITION:
			if not BOOL.load(f):
				return None
			else:
				return POSITION.load(f)
		elif val_type == Type.DIRECTION:
			return Direction(BYTE.load(f))
		elif val_type == Type.OPTIONAL_UUID:
			if not BOOL.load(f):
				return None
			else:
				return UUID.load(f)
		elif val_type == Type.OPTIONAL_BLOCK_TYPE:
			return BLOCKTYPE.load(f)
		else:
			raise ValueError('invalid type %r' % val_type)

	def load_hook(self, obj, schema):
		'called to convert the resulting dict into a user value'
		return schema

	def load(self, f, schema=None, strict=True, schema_readonly=True):
		'loads metadata from '
		metadata = {}

		while True:
			key = BYTE.load(f)

			# check for the terminal symbol
			if key == 0xff:
				break

			# read the value
			val_type = BYTE.load(f)

			# try to find the expected type in our schema
			if schema is not None:
				expceted_type = schema.get(key, None)
				if strict and expected_type is None:
					raise ValueError('unknown key %r' % key)

				# type check
				if expceted_type is not None and val_type != expected_type:
					raise ValueError('expected %r for key %r' % expected_type, key)

			# load the value
			metadata[key] = self.load_value(f, val_type)

			if not schema_readonly:
				schema[key] = val_type

		return self.load_hook(metadata)

	def dump_value(self, f, val_type, val):
		'dumps val into f according to val_type'

		if val_type == Type.BYTE:
			BYTE.dump(f, val)
		elif val_type == Type.VARINT:
			VARINT.dump(f, val)
		elif val_type == Type.FLOAT:
			FLOAT.dump(f, val)
		elif val_type == Type.STRING:
			STRING.dump(f, val)
		elif val_type == Type.CHAT:
			CHAT.dump(f, val)
		elif val_type == Type.SLOT:
			SLOT.dump(f, val)
		elif val_type == Type.BOOL:
			BOOL.dump(f, val)
		elif val_type == Type.ROTATION:
			FLOAT.dump(f, val.rx)
			FLOAT.dump(f, val.ry)
			FLOAT.dump(f, val.rz)
		elif val_type == Type.OPTIONAL_POSITION:
			BOOL.dump(f, val)
			if val:
				return POSITION.dump(f)
		elif val_type == Type.DIRECTION:
			BYTE.dump(Direction(val))
		elif val_type == Type.OPTIONAL_UUID:
			BOOL.dump(f, val)
			if val:
				return UUID.dump(f)
		elif val_type == Type.OPTIONAL_BLOCK_TYPE:
			if not val:
				VARINT.dump(0)
			val = (val.blockid << 4) | (val.meta & 0x0f)
			VARINT.dump(val)
		else:
			raise ValueError('invalid type %r' % val_type)

	def dump_hook(self, obj, schema):
		'returns an iterable that returns (key, type, value)'

		for key in obj:
			try:
				val_type = schema[key]
			except KeyError:
				raise ValueError('unknown key %r' % key)

			yield (key, val_type, obj[key])

	def dump(self, f, obj, schema):
		'dumps obj into f according to schema'

		for key, val_type, value in obj.dump_hook(obj):
			self.dump_value(f, val_type, val, schema)

METADATA = MetadataCodec()

