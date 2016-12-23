import json

from .primitive import BaseCodec, STRING

__all__ = ['ChatCodec', 'CHAT']

#TODO: an object model for chat strings
#TODO: format strings for chat

#class Chat:
#	def __str__(self):
#	def _flatten(self):

class ChatCodec(BaseCodec):
	def __init__(self, codec=STRING):
		self.codec = codec

	def load(self, f):
		json.loads(self.codec.load(f))

	def dump(self, f, val):
		if not isinstance(val, str):
			raise TypeError('expeceted string')
		self.codec.dump(f, json.dumps(dict(text=val)))

CHAT = ChatCodec()

