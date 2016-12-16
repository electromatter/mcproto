import collections
import re

from .parser import parse
from .ast import *
from .types import *

__all__ = ['MCProtoNamespace', 'MCProtoStruct', 'MCProtoField',
		'MCProtoCompiler']

class MCProtoScopeView:
	def __init__(self, namespace, include_parents=True):
		self.namespace = namespace
		self.include_parents = include_parents

	def __contains__(self, key):
		try:
			self[key]
		except Exception:
			return False
		return True

	def __getitem__(self, key):
		return self.namespace.lookup(key, self.include_parents)

class MCProtoBaseNamespace(collections.abc.MutableMapping):
	def __init__(self):
		super().__init__()
		self.namespace = collections.OrderedDict()

	def __setitem__(self, key, value):
		if not key:
			raise KeyError(key)

		if not isinstance(key, str):
			raise TypeError('key must be str')

		path = key.split('.')
		if len(path) > 1:
			self, key = self._lookup(path, False)
			self[key] = value
			return

		self.namespace[key] = value

	def __getitem__(self, key):
		if not key:
			raise KeyError(key)

		if not isinstance(key, str):
			raise TypeError('key must be str')

		path = key.split('.')
		if len(path) > 1:
			self, key = self._lookup(path, False)
			return self[key]

		return self.namespace[key]

	def __delitem__(self, key):
		if not key:
			raise KeyError(key)

		if not isinstance(key, str):
			raise TypeError('key must be str')

		path = key.split('.')
		if len(path) > 1:
			self, key = self._lookup(path, False)
			del self[key]
			return

		del self.namespace[key]

	def __iter__(self):
		return iter(self.namespace)

	def __len__(self):
		return len(self.namespace)

	def scope(self, include_parents=True):
		return MCProtoScopeView(self, include_parents)

	def lookup(self, key, include_parents=True):
		path = key.split('.')
		self, key = self._lookup(path, include_parents)
		return self[key]

	def _lookup(self, path, include_parents):
		while True:
			val = self
			for key in path:
				try:
					cont = val
					val = val[key]
				except Exception:
					break
			else:
				# return actual container and key
				return cont, path[-1]

			# if we cannot continue, raise KeyError
			if not include_parents or self.parent is None:
				raise KeyError('.'.join(path))

			# retry on parent scope
			self = self.parent


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

		parent.build_branch(name, struct, pos)

class MCProtoField:
	def __init__(self, field_type):
		self.field_type = field_type

class MCProtoStruct(MCProtoNamespace):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields = collections.OrderedDict()
		self.constraints = collections.OrderedDict()
		self.branches = collections.OrderedDict()
		self.order = []

		#inherit fields from parent
		base, _ = self.parent._find_struct('')
		if base:
			self.fields.update(base.fields)
			self.constraints.update(base.constraints)

	def build_field(self, name, field_type, pos=None):
		if name in self.fields:
			raise ValueError('duplicate %r at %s' % (name, pos))
		self.fields[name] = field = MCProtoField(field_type)
		self.order.append(('field', name, field))

	def build_constraint(self, node):
		# verify the constraint is consistent
		# and add it to the constraint list

		if not isinstance(node.left, Identifier) \
		   or not isinstance(node.right, Value):
			raise ValueError('expected ident = value at %s' \
					  % node.pos)

		name = str(node.left)
		val = node.right.value

		if self.constraints.get(name, val) != val:
			raise ValueError('inconsistent constarint at %s' \
					 % node.pos)

		# TODO: Typecheck constraint

		self.constraints[name] = val
		self.order.append(('test', name, val))

	def build_branch(self, name, struct, pos=None):
		if name in self.branches:
			raise ValueError('duplicate branch %r at %s' \
					  % (name, pos))

		# create a branch
		self.order.append(('branch', name, struct))
		self.branches[name] = struct

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

	def _find_struct(self, *args, **kwargs):
		raise NotImplementedError()

	def build_branch(self, *args, **kwargs):
		raise NotImplementedError()

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
			return build_type(spec, parent)
		else:
			# struct type
			return self.build_namespace(spec,
						    parent,
						    factory=MCProtoStruct)

# this should be the last line
def compile(name, src=None):
	compiler = MCProtoCompiler()
	compiler.compile(name, src)
	return compiler.namespace

