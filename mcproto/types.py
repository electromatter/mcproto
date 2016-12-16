"""
This file contains the compiler intrinsics for the builtin types.

=== Simple Types ===

Integral types:
 - bool
 - varint
 - varlong
 - ubyte, byte
 - ushort, short
 - uint, int
 - ulong, long
 - unsigned, signed

Floating-point types:
 - float, double

Fixed-point types:
 - position (3-vector)
 - angle

Structured types:
 - metadata, nbt

=== Parameterized Types ===

String types:
 - bytes, string, uuid

Array types:
 - array
 - bool_optional

=== Special Types ===

Enum types:
 - enum
 - flag

"""

from .ast import *

__all__ = ['MCProtoBaseType', 'build_type']

integral = {'bool', 'varint', 'varlong', 'ubyte', 'byte',
	    'ushort', 'short', 'uint', 'int', 'ulong', 'long'}

simple = integral \
	 | {'float', 'double', 'position', 'angle', 'metadata', 'angle'}

class MCProtoBaseType:
	pass

def build_type(spec, parent):
	pass

