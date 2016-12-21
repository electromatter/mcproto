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

__all__ = ['MCProtoBaseType', 'MCProtoStruct',
	   'MCProtoBuiltinType', 'MCProtoParamType',
	   'MCProtoSimpleType', 'MCProtoIntType', 'MCProtoBaseStringType',
	   'MCProtoStringType', 'MCProtoBytesType', 'MCProtoUUIDType',
	   'MCProtoBaseArrayType', 'MCProtoArrayType',
	   'MCProtoBoolOptionalType', 'MCProtoTypeFactory']

def register_type(name):
	def func(cls):
		builtin_types[name] = cls(name)
		return cls
	return func

class MCProtoBuiltinType(MCProtoBaseType):
	def __init__(self, name):
		self.name = name

class MCProtoParamType(MCProtoBuiltinType):
	pass

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

@register_type('string')
class MCProtoStringType(MCProtoBaseStringType):
	INSTANCES = {}

	def __call__(self, spec, factory):
		if len(spec.args) > 3:
			raise ValueError('too many arguments: "string <length> <encoding>" at %s' % spec.pos)

		print(spec)

@register_type('bytes')
class MCProtoBytesType(MCProtoBaseStringType):
	def __call__(self, spec, factory):
		if len(spec.args) > 2:
			raise ValueError('too many arguments: "bytes <length>" at %s' % spec.pos)

		print(spec)

@register_type('uuid')
class MCProtoUUIDType(MCProtoBaseStringType):
	def __call__(self, spec, factory):
		if len(spec.args) > 2:
			raise ValueError('too many arguments: "uuid <encoding>" at %s' % spec.pos)

		print(spec)

# arrays
class MCProtoBaseArrayType(MCProtoParamType):
	_types = ('length', 'elem')

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

		result = MCProtoArrayType(self.name)
		result.length = length
		result.elem = factory(spec.args[2])

		return result

@register_type('bool_optional')
class MCProtoBoolOptionalType(MCProtoBaseArrayType):
	def __call__(self, spec, factory):
		if len(spec.args) != 2:
			raise ValueError('expected "bool_optional <elem>" at %s' % spec.pos)

		result = MCProtoBoolOptionalType(self.name)
		result.length = factory('bool')
		result.elem = factory(spec.args[1])

		return result

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
			type_val = parent.get(name, None)

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

		if isinstance(spec, TypeSpec):
			self._build_type(spec)
		else:
			self._build_struct(spec)

