import re

class MCProtoLexer:
	def __init__(self, name, src=None, no_match=None):
		if src is None:
			src = open(name, 'r').read()
		self.name = name
		self.src = src
		self.loc = (0, 1, 1)
		self.no_match = no_match
		self._token = None

	TOKEN = re.compile('|'.join([
		#comments
		'#[^\\n]*',
		#symbols
		'[{}();:,=\\.]',
		#identifier
		'[a-zA-Z_][0-9a-zA-Z_]*',
		#strings
		'"(\\\\.|[^\\"])*"',
		#numbers
		'-?(0[xX][0-9a-fA-F]+|0[oO][0-7]+|0[bB][01]+|[0-9]+)',
		#whitespace
		'[ \\t]+',
		#linefeed
		'[\\n]+'
	]))

	KEYWORDS = {'type', 'namespace', 'variant'}
	SYMBOLS = set('{}();:,=.')

	def __iter__(self):
		return self

	def __next__(self):
		if self.eof:
			self._token = None
			raise StopIteration

		while True:
			self._token = None
			match = self.TOKEN.match(self.src, self.off)

			if not match:
				if self.no_match:
					self.no_match(self)
				raise StopIteration

			token = self._token = match.group(0)

			lines = token.count('\n')
			cols = len(token)

			col = 1 if lines > 0 else self.col + cols

			self.loc = (self.off + cols, self.line + lines, col)

			if token.startswith('#') or token.isspace():
				continue

			if not self.is_constant():
				token = self._token = token.casefold()

			return token

	def expect(self, val, do_raise=None):
		if not self.accept(val):
			if do_raise:
				do_raise(self, val)
			raise ValueError('expected %s at %s' % (val, self.pos))
		return True

	def accept(self, val):
		if self.token == val:
			try:
				next(self)
			except StopIteration:
				pass
			return True
		return False

	@property
	def token(self):
		if self._token is None:
			next(self)
		return self._token

	@property
	def off(self):
		return self.loc[0]

	@property
	def line(self):
		return self.loc[1]

	@property
	def col(self):
		return self.loc[2]

	@property
	def pos(self):
		return '%s:%i col %i' % (self.name, self.line, self.col)

	@property
	def eof(self):
		return self.off >= len(self.src)

	def is_constant(self):
		return self.token[0] in '-0123456789"'

	def is_keyword(self):
		return self.token in self.KEYWORDS

	def is_symbol(self, value=None):
		return self.token in self.SYMBOLS

