import collections
import collections.abc

from .ast import *
from .types import MCProtoBaseType

__all__ = ['MCProtoNamespace', 'MCProtoField', 'MCProtoStruct',
	   'MCProtoVariant', 'MCProtoProxyVariant']

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
	_types = ('**namespace', )

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

class MCProtoField:
	_types = ('field_type',)

	def __init__(self, field_type):
		self.field_type = field_type

class MCProtoStruct(MCProtoNamespace, MCProtoBaseType):
	_types = ('^fields', '**namespace')

	def __hash__(self):
		#dirty hack to get memorization to work
		return id(self)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields = collections.OrderedDict()
		self.constraints = collections.OrderedDict()
		self.branches = collections.OrderedDict()
		self.order = []

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

		self.constraints[name] = val
		self.order.append(('test', name, val))

	def _build_variant(self, struct, pos=None):
		if struct.path in self.branches:
			raise ValueError('duplicate branch %r at %s' \
						  % (struct.path, pos))

		# create a branch
		self.order.append(('branch', struct.path, struct))
		self.branches[struct.path] = struct

class MCProtoVariant(MCProtoStruct):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		# find base
		parent = self.parent
		path = self.name
		while not isinstance(parent, MCProtoStruct):
			assert parent is not None
			if path is None or parent.name is None:
				raise ValueError('anon branch inside a namespace?')
			path = '%s.%s' % (parent.name, path)
			parent = parent.parent

		# set self.base and self.path
		self.path = path
		self.base = parent

		# inherit fields and constraints from base
		self.fields.update(self.base.fields)
		self.constraints.update(self.base.constraints)

class MCProtoProxyVariant(MCProtoVariant):
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

