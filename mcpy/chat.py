from .primitive import BaseCodec

__all__ = ['ChatCodec', 'CHAT']

class ChatCodec(BaseCodec):
	def load(self, f):
		pass

	def dump(self, f, val):
		pass

CHAT = ChatCodec()

