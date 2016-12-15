import re

from .ast import *

__all__ = ['parse']

def make_value(value, **kwargs):
	if not isinstance(value, str):
		raise TypeError('expected value as a token')

	if len(value) == 0:
		raise ValueError('value too short')

	if value[0] in '-0123456789':
		return Number(token=value, **kwargs)
	else:
		return String(token=value, **kwargs)

class MCProtoLexer:
	def __init__(self, name, src=None, no_match=None):
		if src is None:
			src = open(name, 'r').read()
		self.name = name
		self.src = src
		self.loc = (0, 1, 0)
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
		'\'(\\\\.|[^\\\\\'])*\'',
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

	def _consume(self):
		if self._token is None:
			return

		lines = self._token.count('\n')
		cols = len(self._token)

		col = 0 if lines > 0 else self.col_offset + cols

		self.loc = (self.off + cols, self.lineno + lines, col)

		self._token = None

	def __next__(self):
		while True:
			self._consume()

			if self.eof:
				raise StopIteration

			match = self.TOKEN.match(self.src, self.off)

			if not match:
				if self.no_match:
					self.no_match(self)
				raise StopIteration

			token = self._token = match.group(0)

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
	def lineno(self):
		return self.loc[1]

	@property
	def col_offset(self):
		return self.loc[2]

	@property
	def pos(self):
		return '{.name}:{.lineno} col {.col_offset}'.format(self)

	@property
	def eof(self):
		return self.off >= len(self.src) and self._token is None

	def is_constant(self):
		if self.token is None:
			return False
		return self.token[0] in '-0123456789"\''

	def is_keyword(self):
		return self.token in self.KEYWORDS

	def is_symbol(self):
		return self.token in self.SYMBOLS

	def is_ident(self):
		return not (self.token is None
				or self.is_constant() \
				or self.is_keyword() \
				or self.is_symbol())

class MCProtoParser:
	def __init__(self, name, src=None, lex=None):
		if lex is None:
			lex = MCProtoLexer(name, src)
		self.lex = lex

	@property
	def pos(self):
		return {'_srcname': self.lex.name, \
			'lineno': self.lex.lineno, \
			'col_offset': self.lex.col_offset}

	@property
	def col_offset(self):
		return self.lex.col_offset

	def identifier(self):
		if not self.lex.is_ident():
			return None
		pos = self.pos
		name = self.lex.token
		self.lex.expect(name)
		return Identifier(name, **pos)

	def value(self):
		if not self.lex.is_constant():
			return None
		pos = self.pos
		tok = self.lex.token
		self.lex.expect(tok)
		return make_value(tok, **pos)

	def name(self):
		path = []

		pos = self.pos
		name = self.identifier()
		if name is None:
			return None

		while True:
			path.append(name.name)
			if not self.lex.accept('.'):
				break

			name = self.identifier()
			if name is None:
				raise ValueError('expected identifier at %s' \
							% self.lex.pos)

		return Identifier('.'.join(path), **pos)

	def typespec(self):
		pos = self.pos
		args = []
		while True:
			if self.lex.token == '(':
				self.lex.expect('(')
				args.append(self.typespec())
				self.lex.expect(')')
				if len(args) == 1:
					return args[0]
			elif self.lex.token == '{':
				self.lex.expect('{')
				args.append(self.body())
				self.lex.expect('}')
				if len(args) == 1:
					return args[0]
			elif self.lex.is_ident():
				args.append(self.name())
			elif self.lex.is_constant():
				args.append(self.value())
			else:
				break

		if not args:
			return None

		return TypeSpec(args, **pos)

	def variantdef(self):
		pos = self.pos
		if not self.lex.accept('variant'):
			return None
		name = self.identifier()
		body = None
		if self.lex.accept('{'):
			body = self.body()
			self.lex.accept('}')
		return VariantDef(name, body, **pos)

	def namespacedef(self):
		pos = self.pos
		if not self.lex.accept('namespace'):
			return None
		name = self.identifier()
		body = None
		if name is None:
			raise ValueError('namespace expected name at %s' \
						% self.lex.pos)
		if self.lex.accept('{'):
			body = self.body()
			self.lex.accept('}')
		return NamespaceDef(name, body, **pos)

	def typedef(self):
		pos = self.pos
		if not self.lex.accept('type'):
			return None
		name = self.identifier()
		if name is None:
			raise ValueError('type expected name at %s' \
						% self.lex.pos)
		if self.lex.token in '{:':
			self.lex.accept(':')
			spec = self.typespec()
			return TypeDef(name, spec, **pos)
		else:
			return TypeDef(name, **pos)

	def field_or_constraint(self):
		pos = self.pos

		# get the first part of the definition
		if self.lex.is_ident():
			name = self.name()
		elif self.lex.is_constant():
			name = self.value()
		else:
			return None

		# if we are a constraint
		if self.lex.token == '=':
			self.lex.expect('=')
			if self.lex.is_ident():
				val = self.name()
			elif self.lex.is_constant():
				val = self.value()
			else:
				raise ValueError('value expected at %s' \
							% self.lex.pos)
			return ConstraintDef(name, val, **pos)

		if '.' in name.name:
			raise ValueError('field must have local name at %s' \
							% self.lex.pos)

		names = [name]
		while True:
			if self.lex.token == ':':
				self.lex.expect(':')
				break
			elif self.lex.token == ',':
				self.lex.expect(',')
			else:
				raise ValueError('field expected type at %s' \
							% self.lex.pos)
			if not self.lex.is_ident():
				raise ValueError('expected field name at %s' \
							% self.lex.pos)
			names.append(self.identifier())

		field_type = self.typespec()

		return FieldDef(names, field_type, **pos)

	def body(self):
		pos = self.pos
		statements = []
		while True:
			if self.lex.token == 'variant':
				statements.append(self.variantdef())
			elif self.lex.token == 'namespace':
				statements.append(self.namespacedef())
			elif self.lex.token == 'type':
				statements.append(self.typedef())
			elif self.lex.token == ';':
				pass
			elif self.lex.is_constant() or self.lex.is_ident():
				statements.append(self.field_or_constraint())
			else:
				break
			self.lex.expect(';')
		return Body(statements, **pos)

def parse(name, src=None):
	return MCProtoParser(name, src).body()

