#!/usr/bin/env python3

from mcproto.types import MCProtoBaseType
from mcproto import compiler

def walk_types(code, seen=None):
	if seen is None:
		seen = set()

	if isinstance(code, str):
		return

	try:
		if code in seen:
			return
	except TypeError:
		pass

	if isinstance(code, MCProtoBaseType):
		seen.add(code)
		yield code

	if hasattr(code, '_types'):
		for name in code._types:
			branch = getattr(code, name, None)

			# check if we have already seen this type 
			yield from walk_types(branch, seen)
	else:
		if hasattr(code, 'values'):
			children = code.values()
		else:
			try:
				children = iter(code)
			except TypeError:
				return

		# we got a dict or iterable
		for child in children:
			yield from walk_types(child, seen)

def main():
	import sys

	if len(sys.argv) <= 1:
		src = 'src/handshake.mcproto'
	else:
		src = sys.argv[1]

	code = compiler.compile(src)

	for obj in walk_types(code):
		print(obj.name)

	return code

if __name__ == '__main__':
	main()

