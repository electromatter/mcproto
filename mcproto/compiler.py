import collections
import re

from .parser import parse
from .ast import *

__all__ = ['compile']

# variants are types based on their containing type with extra constraints
# ambiguous variants are illegal
# namespaces are containers that map names to types/namespaces
# some builtin types

class MCProtoNamespace(collections.OrderedDict):
	def __init__(self, parent=None):
		super().__init__()
		self.parent = parent

	def build_constraint(self, node):
		raise ValueError('constraint in namespace? at %s' % node.pos)

	def build_field(self, name_node, field_type):
		raise ValueError('field in namespace? at %s' % node.pos)

	def unnamed_branch(self, struct):
		raise ValueError('unnamed branch in namespace? at %s' \
				  % node.pos)

	def named_branch(self, name):
		print(name)

	def lookup(self, name):
		print(name)

class MCProtoStruct(MCProtoNamespace):
	def build_constraint(self, node):
		print(node)

	def build_field(self, name_node, field_type):
		print(name_node, field_type)

	def unnamed_branch(self, struct):
		print(struct)

	def named_branch(self, name):
		print(name)

class MCProtoField:
	def __init__(self, field_type):
		self.field_type = field_type

class MCProtoCompiler:
	def __init__(self):
		self.namespace = MCProtoNamespace()

	def compile(self, name, src=None):
		self.build_namespace(parse(name, src))

	def build_namespace(self, body, parent=None, factory=MCProtoNamespace):
		if parent is None:
			dest = self.namespace
		else:
			dest = factory(parent=parent)

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
								  dest)
			elif isinstance(child, TypeDef):
				dest[name] = self.build_type(child.spec, dest)
			elif isinstance(child, VariantDef):
				ns = self.build_namespace(child.body,
							  dest,
							 factory=MCProtoStruct)

				if child.name:
					dest[name] = ns
					dest.named_branch(name)
				else:
					dest.unnamed_branch(ns)
			elif isinstance(child, FieldDef):
				field_type = self.build_type(child.field_type,
							     dest)
				for name in child.names:
					dest.build_field(name, field_type)
			elif isinstance(child, ConstraintDef):
				dest.build_constraint(child)
			else:
				raise TypeError('expected body at %s' \
							% child.pos)

		return dest

	def build_type(self, spec, parent):
		if isinstance(spec, TypeSpec):
			# alias type
			return self.type_with_parameters(spec, parent)
		else:
			# struct type
			return self.build_namespace(spec,
						    parent,
						    factory=MCProtoStruct)

	def type_with_parameters(self, spec, parent):
		print(spec)
		pass

# this should be the last line
def compile(name, src=None):
	compiler = MCProtoCompiler()
	compiler.compile(name, src)
	return compiler.namespace

