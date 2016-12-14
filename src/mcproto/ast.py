import ast

__all__ = ['Node', 'Identifier',
		'Value', 'Number', 'String',
		'Body', 'TypeSpec',
		'TypeDef', 'VariantDef', 'NamespaceDef',
		'ConstraintDef', 'FieldDef']

class Node:
	_fields = ()

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
	_fields = ('children', )

	def __init__(self, children):
		self.children = children

	def __repr__(self):
		return 'Body(%r)' % self.children

class TypeSpec(Node):
	_fields = ('args', )

	def __init__(self, args):
		self.args = args

	def __repr__(self):
		return 'TypeSpec(%r)' % self.args

class TypeDef(Node):
	_fields = ('name', 'spec')

	def __init__(self, name, spec=None):
		self.name = name
		self.spec = spec

	def __repr__(self):
		return 'TypeDef(%r, %r)' % (self.name, self.spec)

class VariantDef(Node):
	_fields = ('name', 'body')

	def __init__(self, name=None, body=None):
		self.name = name
		self.body = body

	def __repr__(self):
		return 'VariantDef(%r, %r)' % (self.name, self.body)

class NamespaceDef(Node):
	_fields = ('name', 'body')

	def __init__(self, name, body=None):
		self.name = name
		self.body = body

	def __repr__(self):
		return 'NamespaceDef(%r, %r)' % (self.name, self.body)

class ConstraintDef(Node):
	_fields = ('left', 'right')

	def __init__(self, left, right):
		self.left = left
		self.right = right

	def __repr__(self):
		return 'ConstraintDef(%r, %r)' % (self.left, self.right)

class FieldDef(Node):
	_fields = ('names', 'field_type')

	def __init__(self, names, field_type):
		self.names = names
		self.field_type = field_type

	def __repr__(self):
		return 'FieldDef(%r, %r)' % (self.names, self.field_type)

