from .types import *

class MCProtoGenerator(MCProtoVisitor):
	def __init__(self, doc):
		self.doc = doc

	def visit_namespace(self, ns, path):
		with self.doc.enter(path):
			super().visit_namespace(ns, path)

	def visit_struct(self, struct, path):
		with self.doc.enter(path):
			super().visit_struct(struct, path)
			self.doc.build(struct, path)

