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
		'"(\\\\.|[^\\\\"])*"',
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
			raise ValueError('expected %r at %s' % (val, self.pos))
		return True

	def accept(self, val):
		if self.eof:
			return False
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
			try:
				next(self)
			except StopIteration:
				pass
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
		return self.off >= len(self.src) and self._token is None

	def is_constant(self):
		if self.token is None:
			return False
		return self.token[0] in '-0123456789"'

	def is_keyword(self):
		return self.token in self.KEYWORDS

	def is_symbol(self):
		return self.token in self.SYMBOLS

	def is_identifier(self):
		return not (self.token is None
				or self.is_constant() \
				or self.is_keyword() \
				or self.is_symbol())

class MCProtoParser:
	def __init__(self, name, src=None, lex=None):
		if lex is None:
			lex = MCProtoLexer(name, src)
		self.lex = lex

	def identifier(self):
		if not self.lex.is_identifier():
			return None
		name = self.lex.token
		self.lex.expect(name)
		return name

	def name(self):
		path = []

		name = self.identifier()
		if name is None:
			return None

		while True:
			path.append(name)
			if not self.lex.accept('.'):
				break

			name = self.identifier()
			if name is None:
				raise ValueError('expected identifier at %s' % self.lex.pos)

		return '.'.join(path)

	def value(self):
		if self.lex.is_constant():
			val = self.lex.token
			self.lex.expect(val)
			return val
		elif self.lex.token == '{':
			self.lex.expect('{')
			val = self.body()
			self.lex.expect('}')
			return val
		else:
			return None

	def typespec(self):
		args = []
		while True:
			case = self.lex.token
			if case == '(':
				self.lex.expect('(')
				args.append(self.typespec())
				self.lex.expect(')')
				if len(args) == 1:
					return args[0]
			elif case == '{':
				self.lex.expect('{')
				args.append(self.body())
				self.lex.expect('}')
				if len(args) == 1:
					return args[0]
			elif self.lex.is_identifier():
				args.append(self.name())
			elif self.lex.is_constant():
				val = self.lex.token
				self.lex.expect(val)
				args.append(val)
			else:
				break

		if not args:
			return None

		return args

	def variantdef(self):
		if not self.lex.accept('variant'):
			return None
		name = self.identifier()
		body = None
		if self.lex.accept('{'):
			body = self.body()
			self.lex.accept('}')
		return (name, body)

	def namespacedef(self):
		if not self.lex.accept('namespace'):
			return None
		name = self.identifier()
		body = None
		if name is None:
			raise ValueError('namespace expected name at %s' % self.lex.pos)
		if self.lex.accept('{'):
			body = self.body()
			self.lex.accept('}')
		return (name, body)

	def typedef(self):
		if not self.lex.accept('type'):
			return None
		name = self.identifier()
		if name is None:
			raise ValueError('type expected name at %s' % self.lex.pos)
		if self.lex.token == '{':
			self.lex.expect('{')
			body = self.body()
			self.lex.expect('}')
			return (name, 'struct', body)
		elif self.lex.token == ':':
			self.lex.expect(':')
			body = self.typespec()
			return (name, 'alias', body)
		else:
			return (name, 'forward', None)

	def field_or_constraint(self):
		# get the first part of the definition
		if self.lex.is_identifier():
			name = self.name()
		elif self.lex.is_constant():
			name = self.lex.token
			self.lex.expect(name)
		else:
			return None

		# if we are a constraint
		if self.lex.token == '=':
			self.lex.expect('=')
			if self.lex.is_identifier():
				val = self.name()
			elif self.lex.is_constant():
				val = self.lex.token
				self.lex.expect(val)
			else:
				raise ValueError('constraint expected name or value at %s' % self.lex.pos)
			return (name, '=', val)

		if '.' in name:
			raise ValueError('field must have local name at %s' % self.lex.pos)

		names = [name]
		while True:
			if self.lex.token == ':':
				self.lex.expect(':')
				break
			elif self.lex.token == ',':
				self.lex.expect(',')
			else:
				raise ValueError('field expected , or : at %s' % self.lex.pos)
			if not self.lex.is_identifier():
				raise ValueError('expected field name at %s' % self.lex.pos)
			name = self.lex.token
			self.lex.expect(name)
			names.append(name)

		field_type = self.typespec()

		return (names, field_type)

	def body(self):
		statements = []
		while True:
			if self.lex.token == 'variant':
				val = self.variantdef()
			elif self.lex.token == 'namespace':
				val = self.namespacedef()
			elif self.lex.token == 'type':
				val = self.typedef()
			elif self.lex.is_constant() or self.lex.is_identifier():
				val = self.field_or_constraint()
			else:
				break
			statements.append(val)
			self.lex.expect(';')
		return statements

