import re

class ParserStack:
	'lexer with a stack for arbitrary lookahead'

	SPACES = re.compile('\\s+')

	def __init__(self, name, src=None):
		if src is None:
			with open(name, 'r') as f:
				src = f.read()
		self.src = src
		self.name = name
		self.off = 0
		self.loc = (1, 1)
		self.stack = []

	@property
	def line(self):
		return self.loc[0]

	@property
	def col(self):
		return self.loc[1]

	@property
	def eof(self):
		return self.off >= len(self.src)

	def consume_match(self, pattern, skip_spaces=True):
		match = self.match(pattern, skip_spaces)

		if not match:
			return None

		self.consume(match)

		return match.group(0)

	def match(self, pattern, skip_spaces=True, as_str=False):
		if skip_spaces:
			self.consume(self.SPACES.match(self.src, self.off))

		# if we don't have a compiled re, then it must be a pattern str
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

		if not value:
			return

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
		self.stack.append((self.off, self.loc))
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		self.off, self.loc = self.stack.pop()

	def commit(self):
		if not self.stack:
			return
		self.stack[-1] = (self.off, self.loc)

class MCProtoParser:
	'parser for mcproto grammar LR(1)'

	SYMBOL = re.compile('[,:;(){}"\']')
	WORD = re.compile('[0-9a-zA-Z_.]+')

	def __init__(self, name, src=None):
		self.stack = ParserStack(name, src)

	def _string(self, quote='"', consume=False):
		if hasattr(quote, 'group'):
			quote = quote.group(0)

		# build pattern
		non_quote = '' if len(quote) <= 1 else '|' + re.escape(quote[1:])
		pattern = re.compile('(\\\\.|[^\\\\%s]+%s)+' % (re.escape(quote[0]), non_quote))
		quote = re.compile(re.escape(quote))

		with self.stack as stack:
			# match open quote
			match = stack.match(quote)
			if not match:
				return None

			value = match.group(0)
			stack.consume(match)

			while not stack.eof:
				# match close quote
				match = stack.match(quote)
				if match:
					# we matched, consume and return
					value += match.group(0)
					stack.consume(match)
					if consume:
						stack.commit()
					return value

				# match string body
				match = stack.match(pattern)
				if not match:
					return None
				value += match.group(0)
				stack.consume(match)

	def parse(self):
		pass

