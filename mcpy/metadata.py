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

from .primitive import BOOL, BYTE, VARINT, FLOAT, STRING, \
		       POSITION, BLOCKTYPE, DIRECTION, UUID,\
		       Direction, Position, BlockType, \
		       BaseCodec, StructCodec, BoolOptionalCodec

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
	OPTIONAL_BLOCKTYPE	= 12

Rotation = collections.namedtuple('Rotation', 'rx ry rz')

class RotationCodec(StructCodec):
	def __init__(self):
		super().__init__('>fff')

	def load(self, f):
		return Rotation(super().load(f))

	def dump(self, f, val):
		super().dump(f, (val.rx, val.ry, val.rz))

ROTATION = RotationCodec()

def follows_schema(types, schema):
	'used to validate schema after-the-fact '
	return all(item in schema for item in types.items())

class MetadataCodec(BaseCodec):
	TYPE = Type
	CODEC = {
		Type.BYTE: BYTE,
		Type.VARINT: VARINT,
		Type.FLOAT: FLOAT,
		Type.STRING: STRING,
		Type.CHAT: CHAT,
		Type.SLOT: SLOT,
		Type.BOOL: BOOL,
		Type.ROTATION: ROTATION,
		Type.POSITION: POSITION,
		Type.OPTIONAL_POSITION: BoolOptionalCodec(POSITION),
		Type.DIRECTION: DIRECTION,
		Type.OPTIONAL_UUID: BoolOptionalCodec(UUID),
		Type.OPTIONAL_BLOCKTYPE: BoolOptionalCodec(BLOCKTYPE)
		}

	def load_value(self, f, val_type):
		'loads a value of type val_type from the file f and returns it or raises an error'

	def load_hook(self, obj, types):
		'called to convert the resulting dict into a user value'
		return (obj, types)

	def load(self, f):
		'loads metadata from f see load_hook for return value'
		metadata = {}
		types = {}

		while True:
			key = self.TYPE(BYTE.load(f))

			# check for the terminal symbol
			if key < 0:
				break

			# load the value
			metadata[key] = self.CODEC[val_type].load(f)
			types[key] = val_type

		return self.load_hook(metadata, types)

	def dump_hook(self, obj, schema):
		'returns an iterable that returns (key, val_type, value)'
		for key, val in obj.items():
			yield key, schema[key], val

	def dump(self, f, obj, *args, **kwargs):
		'dumps obj into f according to schema'
		for key, val_type, value in self.dump_hook(obj, schema, *args, **kwargs):
			self.CODEC[val_type].dump(f, val)

METADATA = MetadataCodec()

