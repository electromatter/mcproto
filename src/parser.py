import re

class ParserStack:
	SPACES = re.compile(r'\s+')

	def __init__(self, name, src=None):
		if src is None:
			with open(name, 'r') as f:
				src = f.read()
		self.src = src
		self.name = name
		self.off = 0
		self.loc = (1, 1)
		self.stack = []

	def match(self, pattern, skip_spaces=True, as_str=False):
		if skip_spaces:
			self.consume(self.SPACES.match(self.src, self.off))

		if not hasattr(pattern, 'match'):
			pattern = re.compile(pattern)

		match = pattern.match(self.src, self.off)

		if not match:
			return None

		if as_str:
			return match.group(0)

		return match

	def consume(self, value):
		if not value:
			return

		# intrepret the input and coearse it into a string
		if isinstance(value, str):
			pass
		elif hasattr(value, '__int__'):
			value = int(value)
			if value < 0:
				raise ValueError('consume negitive size?')
			if self.off + value > len(self.src):
				raise ValueError('consume past end?')
			value = self.src[self.off:self.off + value]
		elif hasattr(value, 'group'):
			value = value.group(0)
		else:
			raise TypeError('must be a string, size, or match')

		# ensure value is a substring starting at self.off
		if self.src.count(value, self.off, self.off + len(value)) != 1:
			raise ValueError('value not found?')

		# compute the new offsets
		off = len(value)
		lines = value.count('\n')
		if lines > 0:
			col = len(value) - value.rfind('\n')
		else:
			col = self.loc[1] + off

		# update offsets
		self.off += off
		self.loc = (self.loc[0] + lines, col)

	def __enter__(self):
		self.stack.push(self.off, self.loc)

	def __exit__(self, exc_type, exc_value, traceback):
		self.off, self.loc = self.stack.pop()
#whitespace
#identifier
#keyword
#parenthesis, braces
#simicolon, colon, comma
