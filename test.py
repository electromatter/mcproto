#!/usr/bin/env python3

from mcproto import compiler

def main():
	import sys

	if len(sys.argv) <= 1:
		src = 'src/handshake.mcproto'
	else:
		src = sys.argv[1]

	code = compiler._compile(src)
	print('---')
	print(code)

if __name__ == '__main__':
	main()
