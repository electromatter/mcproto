#!/usr/bin/env python3

import mcproto

def indent(block, n=1):
	if not block:
		block = ''

	if isinstance(block, list):
		block = '\n'.join(block)

	return '\n'.join(
		'\t' * n + line if line else line
		for line in block.split('\n')
	)

class PyFrame:
	def __init__(self, parent=None, path=None):
		self.name = None
		self.qualname = None
		self.path = path or tuple()
		self.body = []

		if self.path:
			assert parent is not None
			assert len(path) == len(parent.path) + 1
			assert path[:len(parent.path)] == parent.path
			self.name = path[-1]

			# assume if we reached the frame from a field
			# it must be an array, so append _item
			if self.name.startswith('^'):
				self.name = self.name[1:] + '_item'

	def emit(self):
		body = '\n\n'.join(self.body)

		# empty namespace must have pass
		if not body:
			body = 'pass'

		# if we are the root, do not indent
		if not self.name:
			return body

		# indent lines that have stuff
		body = indent(body)

		return 'class %s:\n%s' % (self.name, body)

	def append(self, item):
		if item is None:
			return
		self.body.append(item)

def make_constants(constraints):
	return '\n'.join('%s=%r' % item for item in constraints.items())

def make_ctr(fields):
	args = ('self',) + tuple(name for name in fields)
	args = ', '.join(args)

	if not fields:
		assigns = 'pass'
	else:
		assigns = '\n\t'.join('self.{name} = {name}'.format(name=name) for name in fields)

	return """def __init__({args}):
	{assigns}""".format(args=args, assigns=assigns)

def make_repr(name, fields):
	formats = ', '.join('%s=%%r' % name for name in fields)
	names = ', '.join('self.%s' % name for name in fields)

	return """def __repr__(self):
	return '{name}({formats})' % ({names})""".format(name=name, formats=formats, names=names)

def encode_array(length, val_type, val):
	val_encoder = encode_field(val_type, '_item')
	if length is None:
		return """if {val} not is None:
	for _item in {val}:
{val_encoder}""".format(val=val, val_encoder=indent(val_encoder, 2))
	elif isinstance(length, int):
		return """if len({val}) != {length}:
	raise ValueError('expceted {length} items on {val}')
for _item in {val}:
{val_encoder}""".format(length=length, val=val, val_encoder=indent(val_encoder))
	else:
		return """{length}(len({val}))
for _item in {val}:
{val_encoder}""".format(length=length, val=val, val_encoder=indent(val_encoder))

def encode_bool_optional(val_type, val):
	val_encoder = encode_field(val_type, val)

	val_encoder = indent(val_encoder)

	return """if {val} is None:
	mcprotolib.dump_bool(False, f)
else:
	mcprotolib.dump_bool(True, f)
{val_encoder}""".format(val=val, val_encoder=val_encoder)

def encode_field(field_type, val):
	if hasattr(field_type, 'length'):
		if isinstance(field_type.length, int):
			if field_type.length < 0:
				length = None
			else:
				length = field_type.length
		else:
			if not isinstance(field_type.length, mcproto.types.MCProtoIntType):
				raise ValueError('expceted int type for array length got %r' % field_type.length.__class__)
			length = 'mcprotolib.dump_%s' % field_type.length.name

	if not isinstance(field_type, mcproto.types.MCProtoBuiltinType):
		return '%s.dump(f)' % val
	elif isinstance(field_type, mcproto.types.MCProtoSimpleType):
		return 'mcprotolib.dump_%s(%s, f)' % (field_type.name, val)
	elif isinstance(field_type, mcproto.types.MCProtoBoolOptionalType):
		return encode_bool_optional(field_type.elem, val)
	elif isinstance(field_type, mcproto.types.MCProtoArrayType):
		return encode_array(length, field_type.elem, val)
	elif isinstance(field_type, mcproto.types.MCProtoStringType):
		return 'mcprotolib.dump_bytes(%s, %r, %s, f)' % (length, field_type.encoding, val)
	elif isinstance(field_type, mcproto.types.MCProtoBytesType):
		return 'mcprotolib.dump_bytes(%s, %s, f)' % (length, val)
	elif isinstance(field_type, mcproto.types.MCProtoUUIDType):
		return 'mcprotolib.dump_uuid(%r, %s, f)' % (field_type.encoding, val)
	else:
		raise TypeError('unknown field type %r' % field_type.__class__)

def make_encode(struct):
	body = []

	for name, field in struct.fields.items():
		val = 'self.%s' % name

		# pick the correct encoder
		body.append(encode_field(field.field_type, val))

	if not body:
		body = '\tpass'
	else:
		body = indent(body)

	return 'def dump(self, f):\n%s' % body

def make_decode(struct, terminal=False):
	return None

class PyGenerator(mcproto.gen.MCProtoGenerator):
	def __init__(self):
		super().__init__(self)
		self.qualname = []
		self.stack = [PyFrame()]

	def enter(self, path):
		if self.stack[-1].path == path:
			frame = self.stack[-1]
		else:
			frame = PyFrame(self.stack[-1], path)
			self.qualname.append(frame.name)
			frame.qualname = '.'.join(self.qualname)
		self.stack.append(frame)
		return self

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		frame = self.stack.pop()
		if frame is self.stack[-1]:
			return
		self.qualname.pop()
		self.stack[-1].append(frame.emit())

	def build(self, struct, path):
		frame = self.stack[-1]
		qualname = struct.qualname = frame.qualname
		unconstrained = [field for field in struct.fields if field not in struct.constraints]

		if not struct.branches or None in struct.branches:
			frame.append(make_constants(struct.constraints))
			frame.append(make_ctr(unconstrained))
			frame.append(make_repr(qualname, unconstrained))
			frame.append(make_encode(struct))
		else:
			frame.append(make_decode(struct))

	def emit(self):
		return self.stack[-1].emit()

def main():
	import sys

	if len(sys.argv) <= 1:
		src = 'src/handshake.mcproto'
	else:
		src = sys.argv[1]

	code = mcproto.compiler.compile(src)
	gen = PyGenerator()
	gen.visit(code)
	print(gen.emit())

	return code

if __name__ == '__main__':
	main()

