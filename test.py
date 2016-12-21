#!/usr/bin/env python3

import mcproto

# generate types
# generate parser
# generate generators

class MCProtoPythonGenerator(mcproto.types.MCProtoVisitor):
	def __init__(self):
		self.seen = set()

	def visit_struct(self, obj, path):
		super().visit_struct(obj, path)
		print(path, obj)

def main():
	import sys

	if len(sys.argv) <= 1:
		src = 'src/handshake.mcproto'
	else:
		src = sys.argv[1]

	code = mcproto.compiler.compile(src)

	MCProtoPythonGenerator().visit(code)

	return code

if __name__ == '__main__':
	main()

