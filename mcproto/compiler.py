import collections
import re

from .parser import parse
from .ast import *

__all__ = ['MCProtoNamespace', 'MCProtoStruct', 'MCProtoField']

class MCProtoBaseNamespace(collections.abc.MutableMapping):
	def __init__(self):
		super().__init__()
		self.namespace = collections.OrderedDict()

	def __setitem__(self, key, value):
		self.namespace[key] = value

	def __getitem__(self, key):
		return self.namespace[key]

	def __delitem__(self, key):
		del self.namespace[key]

	def __iter__(self):
		return iter(self.namespace)

	def __len__(self):
		return len(self.namespace)

class MCProtoNamespace(MCProtoBaseNamespace):
	def __init__(self, parent=None, name=None):
		super().__init__()
		self.parent = parent
		self.name = name

	def build_constraint(self, node):
		raise ValueError('constraint in namespace? at %s' % node.pos)

	def build_field(self, name, field_type, pos=None):
		raise ValueError('field in namespace? at %s' % pos)

	def _find_struct(self, name):
		while not isinstance(self, MCProtoStruct):
			if self.parent is None:
				return (None, name)

			if not self.name:
				assert False, 'anonomous namespace? %s'

			name = '%s.%s' % (self.name, name)
			self = self.parent

		return (self, name)

	def build_branch(self, name, struct, pos=None):
		if not name:
			raise ValueError('unnamed branch in namespace? at %s' \
					  % pos)

		parent, name = self._find_struct(name)

		if parent is None:
			raise ValueError('cannot find parent struct %s' % pos)

		parent.named_branch(name, struct, pos)

	def lookup(self, name, include_parents=True):
		path = name.split('.')
		while parent is not None:
			val = self
			for key in path:
				if key not in val:
					break
				val = val[key]
			else:
				return val
			if not include_parents:
				break
			self = self.parent
		raise KeyError(name)

	__repr__ = object.__repr__

class MCProtoField:
	def __init__(self, field_type):
		self.field_type = field_type

class MCProtoStruct(MCProtoNamespace):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields = collections.OrderedDict()
		self.constraints = collections.OrderedDict()
		self.order = []

		#inherit fields from parent
		base, _ = self.parent._find_struct('')
		if base:
			self.fields.update(base.fields)
			self.constraints.update(base.constraints)

	def build_field(self, name, field_type, pos=None):
		if name in self.fields:
			raise ValueError('duplicate %r at %s' % (name, pos))
		self.fields[name] = MCProtoField(field_type)
		self.order.append(('field', name))

	def build_constraint(self, node):
		# TODO
		# verify this was consistent
		print('constrain', node)

	def build_branch(self, name, struct, pos=None):
		# create a branch
		self.order.append(('branch', name))

		# verify this is consistent
		print('branch', name)

class MCProtoProxyStruct(MCProtoStruct):
	def __setitem__(self, key, value):
		self.parent[key] = value

	def __getitem__(self, key):
		return self.parent[key]

	def __delitem__(self, key):
		del self.parent[key]

	def __iter__(self):
		return iter(self.parent)

	def __len__(self):
		return len(self.parent)

class MCProtoCompiler:
	def __init__(self):
		self.namespace = MCProtoNamespace()

	def compile(self, name, src=None):
		self.build_namespace(parse(name, src))

	def build_namespace(self,
			    body,
			    parent=None,
			    name=None,
			    factory=MCProtoNamespace):
		if parent is None:
			dest = self.namespace
		else:
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
				factory = MCProtoStruct

				if not child.name:
					name = None
					factory = MCProtoProxyStruct

				ns = self.build_namespace(child.body,
							  dest,
							  name,
							  factory)

				if name:
					dest[name] = ns

				dest.build_branch(name,
						  ns,
						  pos=child.pos)
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
		if isinstance(spec, TypeSpec):
			# alias type
			return self.type_with_parameters(spec, parent)
		else:
			# struct type
			return self.build_namespace(spec,
						    parent,
						    factory=MCProtoStruct)

	def type_with_parameters(self, spec, parent):
		#TODO construct type
		print(spec)
		pass

# this should be the last line
def compile(name, src=None):
	compiler = MCProtoCompiler()
	compiler.compile(name, src)
	return compiler.namespace

