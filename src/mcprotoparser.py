import ast
import re

__all__ = ['parse', 'Node', 'Value', 'Number', 'String', 'Identifier',
		'Body', 'TypeSpec', 'TypeDef', 'VariantDef', 'NamespaceDef',
		'ConstraintDef', 'FieldDef']

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
		return self.token[0] in '-0123456789"\''

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
		return Identifier(name)

	def value(self):
		if not self.lex.is_constant():
			return None
		tok = self.lex.token
		self.lex.expect(tok)
		val = make_value(tok)
		return tok

	def name(self):
		path = []

		name = self.identifier()
		if name is None:
			return None

		while True:
			path.append(name.name)
			if not self.lex.accept('.'):
				break

			name = self.identifier()
			if name is None:
				raise ValueError('expected identifier at %s' % self.lex.pos)

		return Identifier('.'.join(path))

	def typespec(self):
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
			elif self.lex.is_identifier():
				args.append(self.name())
			elif self.lex.is_constant():
				args.append(self.value())
			else:
				break

		if not args:
			return None

		return TypeSpec(args)

	def variantdef(self):
		if not self.lex.accept('variant'):
			return None
		name = self.identifier()
		body = None
		if self.lex.accept('{'):
			body = self.body()
			self.lex.accept('}')
		return VariantDef(name, body)

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
		return NamespaceDef(name, body)

	def typedef(self):
		if not self.lex.accept('type'):
			return None
		name = self.identifier()
		if name is None:
			raise ValueError('type expected name at %s' % self.lex.pos)
		if self.lex.token in '{:':
			self.lex.accept(':')
			spec = self.typespec()
			return TypeDef(name, spec)
		else:
			return TypeDef(name)

	def field_or_constraint(self):
		# get the first part of the definition
		if self.lex.is_identifier():
			name = self.name()
		elif self.lex.is_constant():
			name = self.value()
		else:
			return None

		# if we are a constraint
		if self.lex.token == '=':
			self.lex.expect('=')
			if self.lex.is_identifier():
				val = self.name()
			elif self.lex.is_constant():
				val = self.value()
			else:
				raise ValueError('constraint expected name or value at %s' % self.lex.pos)
			return ConstraintDef(name, val)

		if '.' in name.name:
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
			names.append(self.identifier())

		field_type = self.typespec()

		return FieldDef(names, field_type)

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
		return Body(statements)

def parse(name, src=None):
	return MCProtoParser(name, src).body()

def make_value(value):
	if not isinstance(value, str):
		raise TypeError('expected value as a token')

	if len(value) == 0:
		raise ValueError('value too short')

	if value[0] in '-0123456789':
		return Number(token=value)
	else:
		return String(token=value)

def make_name(name):
	if isinstance(name, Identifier):
		return name
	elif isinstance(name, str) or hasattr(name, '__str__'):
		return Identifier(str(name))
	else:
		raise TypeError('name must be a string')

class Node:
	pass

class Identifier(Node):
	def __init__(self, name):
		self.name = name

	def __repr__(self):
		return 'Identififer(%r)' % self.name

	def __str__(self):
		return self.value

class Value(Node):
	pass

class Number(Value):
	def __init__(self, value=None, token=None):
		if value is None and token is None:
			raise ValueError('no value specified')

		if token is None:
			token = str(value)

		self.value = ast.literal_eval(token)
		self.token = token

		if not isinstance(self.value, int):
			raise ValueError('token was not an integer')

	def __repr__(self):
		return 'Number(%r)' % self.value

	def __int__(self):
		return self.value

class String(Value):
	def __init__(self, value=None, token=None):
		if value is None and token is None:
			raise ValueError('no value specified')

		if token is None:
			token = str(value)

		self.value = ast.literal_eval(token)
		self.token = token

		if not isinstance(self.value, str):
			raise ValueError('token was not a string')

	def __repr__(self):
		return 'String(%r)' % self.value

	def __str__(self):
		return self.value

class Body(Node):
	def __init__(self, children):
		self.children = children

	def __repr__(self):
		return 'Body(%r)' % self.children

class TypeSpec(Node):
	def __init__(self, args):
		self.args = args

	def __repr__(self):
		return 'TypeSpec(%r)' % self.args

class TypeDef(Node):
	def __init__(self, name, spec=None):
		self.name = make_name(name)
		self.spec = spec

	def __repr__(self):
		return 'TypeDef(%r, %r)' % (self.name, self.spec)

class VariantDef(Node):
	def __init__(self, name=None, body=None):
		self.name = make_name(name)
		self.body = body

	def __repr__(self):
		return 'VariantDef(%r, %r)' % (self.name, self.body)

class NamespaceDef(Node):
	def __init__(self, name, body=None):
		self.name = make_name(name)
		self.body = body

	def __repr__(self):
		return 'NamespaceDef(%r, %r)' % (self.name, self.body)

class ConstraintDef(Node):
	def __init__(self, left, right):
		self.left = left
		self.right = right

	def __repr__(self):
		return 'ConstraintDef(%r, %r)' % (self.left, self.right)

class FieldDef(Node):
	def __init__(self, names, field_type):
		self.names = [make_name(name) for name in names]
		self.field_type = field_type

	def __repr__(self):
		return 'FieldDef(%r, %r)' % (self.names, self.field_type)

