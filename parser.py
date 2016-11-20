import ast
import collections
import io
import re

__all__ = ['Array', 'Constant', 'Field', 'Branch', 'Fork', 'Parser', 'parse']

INTEGER_TYPES = 'vVbBhHiIlL?'
STRING_TYPES = 's'

NUMBER = re.compile(r'\s+|(-|)(0b[0-1]+|0o[0-7]+|0x[0-9a-fA-F]+|[0-9]+)')
STRING = re.compile(r'[\'"]|\\.|[^\'"\\]+')
STRING_START = re.compile(r'\s+|[\'"]')
ARRAY = re.compile(r'\s+|\*|[a-zA-Z]|[1-9][0-9]*')
SIMPLE_TYPE = re.compile(r'\s+|[a-zA-Z?(]')
CONST_START = re.compile(r'\s+|[0-9\'"(]')
FORK_END = re.compile(r'\s+|[)|]')

Array = collections.namedtuple('Array', 'type length elem')
Constant = collections.namedtuple('Constant', 'type value')
Field = collections.namedtuple('Field', 'type')
Branch = collections.namedtuple('Branch', 'value fields')
Fork = collections.namedtuple('Fork', 'type branches')

class Parser:
	def __init__(self, src):
		self.src = src
		self.off = 0
		self.line = 1
		self.line_start = 0

	def match(self, pattern):
		while True:
			match = pattern.match(self.src, self.off)
			if not match:
				return None
			self.off = match.end(0)
			token = match.group(0)
			if '\n' in token:
				self.line += token.count('\n')
				self.line_start = self.off - (len(token) - token.rfind('\n'))
			if not token.isspace():
				return match

	def peek(self, pattern):
		match = self.match(pattern)
		if not match:
			return None
		self.off = match.start(0)
		return match

	def expect(self, s):
		if self.src[self.off:self.off + len(s)] != s:
			raise SyntaxError('expected %r line %r col %r' % ((s,) + self.pos))
		self.off += len(s)

	@property
	def col(self):
		return self.off - self.line_start + 1

	@property
	def pos(self):
		return (self.line, self.col)

	def string(self):
		match = self.match(STRING_START)

		if not match or match.group(0) not in '\'"':
			return None

		val = match.group(0)

		while True:
			match = self.match(STRING)

			if not match:
				raise SyntaxError('broken string literal? line %r col %r' % self.pos)

			val += match.group(0)

			if match.group(0) == val[0]:
				break

		return ast.literal_eval(val)

	def number(self):
		match = self.match(NUMBER)

		if not match:
			return None

		return ast.literal_eval(match.group(0))

	def array(self):
		match = self.match(ARRAY)

		if not match:
			raise SyntaxError('expected length type at line %r col %r' % self.pos)

		token = match.group(0)

		_type = self.type()

		if _type is None:
			raise SyntaxError('expected element type at line %r col %r' % self.pos)

		if token == '*':
			return Array('A', None, _type)
		elif token in INTEGER_TYPES:
			return Array('A', token, _type)
		elif token[0] in '123456789':
			return Array('A', int(token), _type)
		else:
			raise SyntaxError('unknown length type at line %r col %r' % self.pos)

	def type(self):
		match = self.match(SIMPLE_TYPE)

		if not match:
			return None

		token = match.group(0)

		if token == '(':
			result = self.compound()
			end = self.match(FORK_END)
			if not end or end.group(0) != ')':
				raise SyntaxError('unmatched ( at line %r col %r' % self.pos)
			return result
		elif token == 'A':
			return self.array()
		else:
			return token

	def field(self):
		field_type = self.type()

		if not isinstance(field_type, str):
			return field_type

		head = self.peek(CONST_START)
		if field_type in STRING_TYPES:
			if not head:
				pass
			elif head.group(0) == '(':
				self.expect('(')
				return self.fork(field_type)
			elif head.group(0) in '\'"':
				return Constant(field_type, self.string())
		elif field_type in INTEGER_TYPES:
			if not head:
				pass
			elif head.group(0) == '(':
				self.expect('(')
				return self.fork(field_type)
			elif head.group(0) in '0123456789':
				return Constant(field_type, self.number())

		return Field(field_type)

	def compound(self):
		fields = []
		while True:
			field = self.field()
			if field is None:
				break
			fields.append(field)

		if not fields:
			return None

		return fields

	def fork(self, type):
		branches = []

		has_default = False

		while True:
			if type in STRING_TYPES:
				val = self.string()
			elif type in INTEGER_TYPES:
				val = self.number()
			else:
				val = None

			if val is None:
				if has_default:
					raise SyntaxError('ambiguous grammar; multiple defaults at line %r col %r' % self.pos)
				has_default = True

			fields = self.compound() or []
			branches.append(Branch(val, fields))

			match = self.match(FORK_END)
			if not match:
				raise SyntaxError('expected | or ) at line %r col %r' % self.pos)

			if match.group(0) != '|':
				break

		if len(branches) == 1 and has_default:
			return branches[0].fields

		return Fork(type, branches)

	def parse(self):
		fields = []

		while True:
			field = self.field()

			if field is None:
				break

			fields.append(field)

		if self.off != len(self.src):
			raise SyntaxError('unexpected token at line %r col %r' % self.pos)

		return fields

def parse(src):
	return Parser(src).parse()

