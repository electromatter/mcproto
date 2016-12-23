import collections

from .primitive import BaseCodec, SHORT, BYTE

__all__ = ['NBTCodec', 'SlotCodec', 'Slot', 'NBT', 'SLOT']


class NBTCodec(BaseCodec):
	def load(self, f):
		pass

	def dump(self, f, val):
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

