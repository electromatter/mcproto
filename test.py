#!/usr/bin/env python3

import mcproto

# generate types
# generate parser
# generate generators

def main():
	import sys

	if len(sys.argv) <= 1:
		src = 'src/handshake.mcproto'
	else:
		src = sys.argv[1]

	code = mcproto.compiler.compile(src)

	for path, obj in mcproto.types.walk(code):
		if isinstance(obj, mcproto.MCProtoBuiltinType):
			continue
		print(path, obj)

	return code

if __name__ == '__main__':
	main()

