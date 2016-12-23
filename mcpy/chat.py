import enum
import json

from .primitive import BaseCodec, STRING

__all__ = ['ChatCodec', 'CHAT']

#TODO: an object model for chat strings
#TODO: format strings for chat

#class Chat:
#	def __str__(self):
#	def _flatten(self):

class ChatColor(enum.Enum):
	BLACK		= 0
	DARK_BLUE	= 1
	DARK_GREEN	= 2
	DARK_AQUA	= 3
	DARK_RED	= 4
	DARK_PURPLE	= 5
	GOLD		= 6
	GRAY		= 7
	DARK_GRAY	= 8
	BLUE		= 9
	GREEN		= 10
	AQUA		= 11
	RED		= 12
	PINK		= 13
	YELLOW		= 14
	WHITE		= 15

# old format
'\u00a7'

"""
plain text

{argument}

{{ escaped
and }}

***obfuscated***

*italics*
__bold__

~~strikethrough~~

(tag body)[tag name]

^translation.string^

tags used to add click and hover event handlers

# need: a way to neatly format chat messages in source code
# a way to override 
#

class ChatFragment:
	def __init__(self):
		self.text = None
		self.translate = None
		self.score = None
		self.selector = None
		self.bold = None
		self.italic = None
		self.underlined = None
		self.strikethrough = None
		self.obfuscated = None
		self.color = None
		self.insertion = None
		self.click = None
		self.hover = None
		self.children = []
"""
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

