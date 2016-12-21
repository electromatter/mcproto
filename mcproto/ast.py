import ast

__all__ = ['Node', 'Identifier',
		'Value', 'Number', 'String',
		'TypeSpec', 'TypeDef',
		'VariantDef', 'NamespaceDef', 'ConstraintDef', 'FieldDef']

class Node:
	_fields = ()

	def __init__(self, **kwargs):
		self._srcname = kwargs.get('_srcname', None)
		self.lineno = kwargs.get('lineno', None)
		self.col_offset = kwargs.get('col_offset', None)

	@property
	def pos_dict(self):
		return {'_srcname': self._srcname, \
			'lineno': self.lineno, \
			'col_offset': self.col_offset}

	@property
	def pos(self):
		return '%s:%r col %r' % (self._srcname, \
					 self.lineno, \
					 self.col_offset)

class Identifier(Node):
	def __init__(self, name=None, **kwargs):
		super().__init__(**kwargs)
		self.name = name

	def __repr__(self):
		return 'Identififer(%r)' % self.name

	def __str__(self):
		return self.name

class Value(Node):
	_type=None

	def __init__(self, value=None, token=None, **kwargs):
		super().__init__(**kwargs)

		if token is not None and value is None:
			value = ast.literal_eval(token)

			if self._type and not isinstance(value, self._type):
				raise ValueError('token wrong type?')

		self.value = value
		self.token = token

class Number(Value):
	_type=int

	def __init__(self, *args, **kwargs):
		super().__init__(*args, _type=int, **kwargs)

	def __repr__(self):
		return 'Number(%r)' % self.value

	def __int__(self):
		return self.value

class String(Value):
	_type=str

	def __init__(self, *args, **kwargs):
		super().__init__(*args, _type=str, **kwargs)

	def __repr__(self):
		return 'String(%r)' % self.value

	def __str__(self):
		return self.value

class TypeSpec(Node):
	_fields = ('args', )

	def __init__(self, args=None, **kwargs):
		super().__init__(**kwargs)
		self.args = args

	def __repr__(self):
		return 'TypeSpec(%r)' % self.args

class TypeDef(Node):
	_fields = ('name', 'spec')

	def __init__(self, name=None, spec=None, **kwargs):
		super().__init__(**kwargs)
		self.name = name
		self.spec = spec

	def __repr__(self):
		return 'TypeDef(%r, %r)' % (self.name, self.spec)

class VariantDef(Node):
	_fields = ('name', 'body')

	def __init__(self, name=None, body=None, **kwargs):
		super().__init__(**kwargs)
		self.name = name
		self.body = body

	def __repr__(self):
		return 'VariantDef(%r, %r)' % (self.name, self.body)

class NamespaceDef(Node):
	_fields = ('name', 'body')

	def __init__(self, name=None, body=None, **kwargs):
		super().__init__(**kwargs)
		self.name = name
		self.body = body

	def __repr__(self):
		return 'NamespaceDef(%r, %r)' % (self.name, self.body)

class ConstraintDef(Node):
	_fields = ('left', 'right')

	def __init__(self, left=None, right=None, **kwargs):
		super().__init__(**kwargs)
		self.left = left
		self.right = right

	def __repr__(self):
		return 'ConstraintDef(%r, %r)' % (self.left, self.right)

class FieldDef(Node):
	_fields = ('names', 'field_type')

	def __init__(self, names=None, field_type=None, **kwargs):
		super().__init__(**kwargs)
		self.names = names
		self.field_type = field_type

	def __repr__(self):
		return 'FieldDef(%r, %r)' % (self.names, self.field_type)

