import collections
import re

from .parser import parse
from .ast import *

__all__ = ['compile']

SIMPLE_IDENT = re.compile('^[a-zA-Z_][0-9a-zA-Z_.]*$')
def is_simple_ident(value):
	return not not SIMPLE_IDENT.match(value)

def name_join(*args):
	return '.'.join(filter(None, args))

class MCPBase:
	def __init__(self, root, parent, forward=True):
		self.name = None
		self.qualname = None
		self.root = root
		self.parent = parent
		self.forward = forward

	def set_name(self, name):
		if not name:
			return

		assert self.name is None, 'namespace already defined?'

		if not is_simple_ident(name):
			raise TypeError('%r not an identifier?' % name)

		self.name = name

		if self.parent is not None:
			self.parent.register(self)

	def resolve_forward_references(self):
		if not self.forward:
			return
		self.forward = False

		#TODO

class MCPType(MCPBase):
	def visit(self, node):
		if not isinstance(node, TypeDef):
			raise TypeError('expected type def at %s' % node.pos)

		print(node.name)

class MCPNamespace(MCPBase):
	def __init__(self, root=None, parent=None):
		if root is None:
			root = self
		super().__init__(root, parent)
		self.children = collections.OrderedDict()

	def visit(self, node):
		if isinstance(node, NamespaceDef):
			self.visit_def(node)
		elif isinstance(node, Body):
			self.visit_body(node)
		else:
			raise TypeError('expected namespace def at %s' % node.pos)

	def register(self, child):
		if child.name in self.children:
			raise ValueError('duplicate names %s' % child.name)
		self.children[child.name] = child
		child.qualname = name_join(self.qualname, child.name)

	def visit_def(self, node):
		self.set_name(str(node.name))
		self.visit_body(node.body)

	def visit_body(self, node):
		if not node:
			return

		assert self.forward, 'namespace already resolved?'

		for child in node.body:
			self.visit_child(child)

		self.resolve_forward_references()

	def visit_child(self, node):
		if isinstance(node, NamespaceDef):
			child = MCPNamespace(self.root, self)
		elif isinstance(node, TypeDef):
			child = MCPType(self.root, self)
		else:
			raise TypeError('expected namespace or type at %s' % self.pos)
		child.visit(node)

def _compile(name, src=None, **kwargs):
	src = parse(name, src)

	root = MCPNamespace()
	root.visit(src)

	print(root.children)

	return root

# this should be the last line
compile = _compile

