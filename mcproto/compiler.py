import collections
import collections.abc
import re

from .parser import parse
from .ast import *
from .types import *
from .namespace import *

__all__ = ['MCProtoCompiler']

class MCProtoCompiler:
	def __init__(self):
		self.namespace = MCProtoNamespace()
		self.type_factory = MCProtoTypeFactory(self)

	def _globals(self, *args, **kwargs):
		return self.namespace

	def compile(self, name, src=None):
		self.build_namespace(parse(name, src), factory=self._globals)

	def build_namespace(self,
			    body,
			    parent=None,
			    name=None,
			    factory=MCProtoNamespace):
		dest = factory(parent=parent, name=name)

		if not body:
			return dest

		for child in body:
			if hasattr(child, 'name') and child.name:
				name = str(child.name)
				if name in dest:
					raise ValueError('duplicate %r at %s' \
							  % (name, child.pos))

			if isinstance(child, NamespaceDef):
				dest[name] = self.build_namespace(child.body,
								  dest,
								  name)
			elif isinstance(child, TypeDef):
				dest[name] = self.build_type(child.spec, dest)
			elif isinstance(child, VariantDef):
				if child.name:
					factory = MCProtoVariant
				else:
					name = None
					factory = MCProtoProxyVariant

				ns = self.build_namespace(child.body,
							  dest,
							  name,
							  factory)

				if child.name:
					dest[name] = ns

				ns.base._build_variant(ns, child.pos)
			elif isinstance(child, FieldDef):
				field_type = self.build_type(child.field_type,
							     dest)
				for name in child.names:
					dest.build_field(str(name),
							 field_type,
							 pos=name.pos)
			elif isinstance(child, ConstraintDef):
				dest.build_constraint(child)
			else:
				raise TypeError('expected body at %s' \
							% child.pos)

		return dest

	def build_type(self, spec, parent):
		return self.type_factory(spec, parent)

# this should be the last line
def compile(name, src=None):
	compiler = MCProtoCompiler()
	compiler.compile(name, src)
	return compiler.namespace

