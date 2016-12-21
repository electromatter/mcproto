"""
This file contains the compiler intrinsics for the builtin types.

=== Simple Types ===

Integral types:
 - bool
 - varint
 - varlong
 - ubyte, byte
 - ushort, short
 - uint, int
 - ulong, long

Floating-point types:
 - float, double

Fixed-point types:
 - position (3-vector)
 - angle

Structured types:
 - metadata, nbt

=== Parameterized Types ===

Integral types:
 - signed, unsigned

String types:
 - bytes, string, uuid

Array types:
 - array
 - bool_optional

=== Special Types ===

Enum types:
 - enum
 - flag

"""

import collections

from .ast import *

builtin_types = {}

class MCProtoBaseType:
	_types = ()

	def __call__(self, spec, factory):
		if len(spec.args) > 1:
			raise ValueError('type %r expected no arguments at %s' % (str(spec.args[0]), spec.pos))
		return self

from .namespace import *

__all__ = ['MCProtoBaseType', 'MCProtoStruct', 'MCProtoVariant',
	   'MCProtoBuiltinType', 'MCProtoParamType',
	   'MCProtoSimpleType', 'MCProtoIntType', 'MCProtoBaseStringType',
	   'MCProtoStringType', 'MCProtoBytesType', 'MCProtoUUIDType',
	   'MCProtoBaseArrayType', 'MCProtoArrayType',
	   'MCProtoBoolOptionalType', 'MCProtoTypeFactory',
	   'MCProtoVisitor']

def register_type(name):
	def func(cls):
		builtin_types[name] = cls(name)
		return cls
	return func

class MCProtoBuiltinType(MCProtoBaseType):
	def __init__(self, name):
		self.name = name

class MCProtoParamType(MCProtoBuiltinType):
	_POOL = {}

	# memorize the result to reduce reuse the constructed types
	def parameterize(self, *args):
		key = (self.__class__, args)

		cached = self._POOL.get(key, None)
		if cached is None:
			cached = key[0](self.name, *key[1])
			self._POOL[key] = cached
		return cached

@register_type('float')
@register_type('double')
@register_type('position')
@register_type('angle')
@register_type('slot')
@register_type('metadata')
@register_type('nbt')
class MCProtoSimpleType(MCProtoBuiltinType):
	pass

@register_type('bool')
@register_type('varint')
@register_type('varlong')
@register_type('ubyte')
@register_type('byte')
@register_type('ushort')
@register_type('short')
@register_type('uint')
@register_type('int')
@register_type('ulong')
@register_type('long')
class MCProtoIntType(MCProtoSimpleType):
	pass

# string types
class MCProtoBaseStringType(MCProtoParamType):
	_types = ('length',)

	def __init__(self, name, length=None):
		super().__init__(name)
		self.length = length

@register_type('string')
class MCProtoStringType(MCProtoBaseStringType):
	ENCODINGS = {'utf8', 'utf16'}
	DEFAULT_ENCODING = 'utf8'
	DEFAULT_LENGTH = 'varint'

	def __init__(self, name, length=None, encoding=None):
		super().__init__(name, length or self.DEFAULT_LENGTH)
		self.encoding = encoding or self.DEFAULT_ENCODING

	def __call__(self, spec, factory):
		if len(spec.args) > 3:
			raise ValueError('too many arguments: "string <length> <encoding>" at %s' % spec.pos)

		# default to DEFAULT_LENGTH
		length = spec.args[1] if len(spec.args) > 1 else self.length
		if isinstance(length, Number):
			# constant length
			length = int(length)
		else:
			# int type length
			length = factory(length)
			if not isinstance(length, MCProtoIntType):
				raise ValueError('expected int type for <length> at %s' % spec.pos)

		encoding = str(spec.args[2]) if len(spec.args) > 2 else self.encoding
		if encoding not in self.ENCODINGS:
			raise ValueError('unknown encoding %s at %s' % (encoding, spec.pos))

		return self.parameterize(length, encoding)

@register_type('bytes')
class MCProtoBytesType(MCProtoBaseStringType):
	DEFAULT_LENGTH = 'varint'

	def __init__(self, name, length=None):
		super().__init__(name, length or self.DEFAULT_LENGTH)

	def __call__(self, spec, factory):
		if len(spec.args) > 2:
			raise ValueError('too many arguments: "bytes <length>" at %s' % spec.pos)

		# default to DEFAULT_LENGTH
		length = spec.args[1] if len(spec.args) > 1 else self.length
		if isinstance(length, Number):
			# constant length
			length = int(length)
		else:
			if isinstance(length, Identifier) and str(length) == 'eof':
				length = -1
			else:
				# int type length
				length = factory(length)
				if not isinstance(length, MCProtoIntType):
					raise ValueError('expected int type for <length> at %s' % spec.pos)

		return self.parameterize(length)

@register_type('uuid')
class MCProtoUUIDType(MCProtoParamType):
	ENCODINGS = {'rfc', 'hex', 'bin'}
	DEFAULT_ENCODING = 'bin'

	def __init__(self, name, encoding=None):
		super().__init__(name)
		self.encoding = encoding or self.DEFAULT_ENCODING

	def __call__(self, spec, factory):
		if len(spec.args) > 2:
			raise ValueError('too many arguments: "uuid <encoding>" at %s' % spec.pos)

		encoding = str(spec.args[1]) if len(spec.args) > 1 else self.encoding
		if encoding not in self.ENCODINGS:
			raise ValueError('unknown encoding %s at %s' % (encoding, spec.pos))

		return self.parameterize(encoding)

# arrays
class MCProtoBaseArrayType(MCProtoParamType):
	_types = ('length', 'elem')

	def __init__(self, name, length=None, elem=None):
		super().__init__(name)
		self.length = length
		self.elem = elem

@register_type('array')
class MCProtoArrayType(MCProtoBaseArrayType):
	def __call__(self, spec, factory):
		if len(spec.args) != 3:
			raise ValueError('expected "array <length> <elem>" at %s' % spec.pos)

		if isinstance(spec.args[1], Number):
			length = int(spec.args[1])
		else:
			length = factory(spec.args[1])

		if not isinstance(length, int) and not isinstance(length, MCProtoIntType):
			raise ValueError('expected int type for <length> at %s' % spec.pos)

		elem = factory(spec.args[2])

		return self.parameterize(length, elem)

@register_type('bool_optional')
class MCProtoBoolOptionalType(MCProtoBaseArrayType):
	def __call__(self, spec, factory):
		if len(spec.args) != 2:
			raise ValueError('expected "bool_optional <elem>" at %s' % spec.pos)

		length = factory('bool')
		elem = factory(spec.args[1])

		return self.parameterize(length, elem)

class MCProtoTypeFactory:
	def __init__(self, compiler):
		self.compiler = compiler
		self.parent = None

	def _build_type(self, spec):
		if not spec.args:
			raise ValueError('no arguments for type? at %s' % spec.pos)

		name = str(spec.args[0])

		type_val = builtin_types.get(name, None)

		if type_val is None:
			type_val = self.parent.get(name, None)

		if type_val is None:
			raise ValueError('unknown type %r at %s' % (name, spec.pos))

		return type_val(spec, self)

	def _build_struct(self, spec):
		return self.compiler.build_namespace(spec,
						     self.parent,
						     factory=MCProtoStruct)

	def __call__(self, spec, parent=None):
		if parent is not None:
			self.parent = parent

		if isinstance(spec, str):
			return self._build_type(TypeSpec([Identifier(spec)]))
		elif isinstance(spec, Identifier):
			return self._build_type(TypeSpec([spec], **spec.pos_dict))
		elif isinstance(spec, TypeSpec):
			return self._build_type(spec)
		else:
			return self._build_struct(spec)

def walk(obj, path=(), seen=None):
	"""
	All types that derive from MCProtoBaseType define a property cls._types
	is a tuple that defines the names of the children links in this tree.

	Link names that start with:
	 - '^' intrpreted as field namespace, a dict is expected
	 - '**' intrpreted as a namespace, a dict is expected
	 - '*' intrpreted as a list, an iterable is expected
	 - othewise, it is intrpreted as a single link

	This function yields (path, type) for the first instance of each
	MCProtoBaseType in a given tree.

	Path is a tuple of identifiers of the path followed to reach the first
	usage of a particular type. If an identifier in path starts with ^,
	it was anonymously defined and first used with a field of the name that
	follows the ^.
	"""

	if obj is None:
		return

	# use a set to only yield the first
	if seen is None:
		seen = set()
	try:
		if obj in seen:
			return
	except TypeError:
		pass

	# nodes in our tree have types attribute
	for child_name in getattr(obj, '_types', ()):
		if child_name.startswith('^'):
			ns = getattr(obj, child_name[1:], None)

			if not ns:
				continue

			for name, child in ns.items():
				name = '^%s' % name
				for _type in walk(child, path + (name,), seen):
					yield _type
		elif child_name.startswith('**'):
			ns = getattr(obj, child_name[2:], None)

			if not ns:
				continue

			for name, child in ns.items():
				for _type in walk(child, path + (name,), seen):
					yield _type
		elif child_name.startswith('*'):
			ns = getattr(obj, child_name[1:], None)

			if not ns:
				continue

			for child in ns:
				for _type in walk(child, path, seen):
					yield _type
		else:
			child = getattr(obj, child_name, None)
			for _type in walk(child, path, seen):
				yield _type

	if isinstance(obj, MCProtoBaseType):
		yield path, obj
		seen.add(obj)

class MCProtoVisitor:
	'see walk()'

	def visit(self, obj, path=()):
		if isinstance(obj, MCProtoStruct):
			return self.visit_struct(obj, path)
		elif isinstance(obj, MCProtoNamespace):
			return self.visit_namespace(obj, path)
		elif isinstance(obj, MCProtoBuiltinType):
			return self.visit_builtin(obj, path)
		else:
			return

	def visit_namespace(self, obj, path=()):
		for name, child in obj.namespace.items():
			self.visit(child, path + (name,))

	def visit_struct(self, obj, path=()):
		self.visit_namespace(obj, path)

		for name, field in obj.fields.items():
			self.visit(field.field_type, path + ('^' + name,))

	def visit_builtin(self, obj, path):
		for linkname in getattr(obj, '_types', ()):
			assert linkname[0] not in '^*', 'namespace in builtin type?'

			child = getattr(obj, linkname, None)

			if child is None:
				continue

			self.visit(child, path)

