import collections
import enum

from .primitive import BaseCodec, BytesCodec, StringCodec, ArrayCodec, \
		       BOOL, BYTE, SHORT, INT, LONG, FLOAT, DOUBLE

__all__ = ['NBTCodec', 'SlotCodec', 'Slot', 'NBT', 'SLOT']

class Type(enum.Enum):
	END		= 0
	BYTE		= 1
	SHORT		= 2
	INT		= 3
	LONG		= 4
	FLOAT		= 5
	DOUBLE		= 6
	BYTES		= 7
	STRING		= 8
	LIST		= 9
	COMPOUND	= 10
	INT_ARRAY	= 11

class NBTCodec(BaseCodec):
	CODEC = {
		Type.BYTE: BYTE,
		Type.SHORT: SHORT,
		Type.INT: INT,
		Type.LONG: LONG,
		Type.FLOAT: FLOAT,
		Type.DOUBLE: DOUBLE,
		Type.BYTES: BytesCodec(length=INT),
		Type.STRING: StringCodec(length=SHORT),
		Type.INT_ARRAY: ArrayCodec(length=INT, elem=INT)
		}

	def load_hook(self, obj):
		return obj

	def load(self, f):
		top, top_types, size = dict(), -1
		stack = [(top, size)]

		while stack:
			# read key
			if size < 0:
				# we are in a compound, read the type and key
				tag = Type(BYTE.load(f))

				# we reached the end of the current compound
				# return to the parent context
				if tag == Type.END:
					top, size = stack.pop()
					continue

				key = self.CODEC[Type.STRING].load(f)
			else:
				# we reached the end of the list
				# return to parent context
				if size == 0:
					top, size = stack.pop()
					continue

				# we are in a list, decrease the remaining size
				# and read a value
				size -= 1
				key = None

			# save top incase it gets modified by compound or list
			parent = top
			val_type = tag

			# read value
			if tag == Type.COMPOUND:
				# enter compound context
				stack.append((top, size))
				top = val = {}
				size = -1
			elif tag == Type.LIST:
				# enter list context
				stack.append((top, size))
				tag = Type(BYTE.load(f))
				size = INT.load(f)
				top = []
				val = (tag, top)
				if size < 0:
					raise ValueError('invalid nbt: negitive list size?')
			elif tag in self.CODEC:
				val = self.CODEC[tag].load(f)
			else:
				raise ValueError('invalid nbt: invalid tag type?')

			# insert value into parent
			if size < 0:
				# we are in a compound
				parent[key] = (val_type, val)
			else:
				# we are in a list so append
				parent.append(val)

		# we got an empty nbt structure
		if not top:
			top = None

		# we reached the end of the nbt data
		return self.load_hook(top)

	def dump_hook(self, val):
		'returns an iterable that yields (key, (val_type, val))'
		return val.items()

	def dump(self, f, val, detect_cycles=False):
		stack = []

		while True:
			iter(self.dump_hook(val))
		pass

NBT = NBTCodec()

Slot = collections.namedtuple('Slot', 'itemid count damage nbt')

class SlotCodec(BaseCodec):
	def load(self, f):
		itemid = SHORT.load(f)
		if itemid < 0:
			return None

		count = BYTE.load(f)
		damage = SHORT.load(f)
		tag = NBT.load(f)

		if count <= 0:
			raise ValueError('negitive quantity?')

		return Slot(itemid, count, damage, tag)

	def dump(self, f, val):
		if val is None:
			SHORT.dump(f, -1)
			return

		itemid, count, damage, tag = val.itemid, val.count, val.damage, val.tag

		if itemid < 0 or count <= 0:
			raise ValueError('invalid slot?')

		SHORT.dump(f, itemid)
		BYTE.dump(f, count)
		SHORT.dump(f, damage)
		NBT.dump(f, tag)

SLOT = SlotCodec()

