import io
import zlib

from .fields import VARINT

__all__ = ['Framer']

def read_mem(f, size):
	if size < 0:
		raise ValueError('negitive size?')

	# for efficiency, try to read a slice of a memoryview
	if hasattr(f, 'getbuffer'):
		buf = memoryview(f.getbuffer())[f.tell():][:size]
		if len(buf) < size:
			raise EOFError
		f.seek(size, 1)
		return buf

	# fallback to using read otherwise
	buf = f.read(size)
	if len(buf) < size:
		raise EOFError
	return buf

class Framer:
	def __init__(self, threshold=None, max_frame=None, length=VARINT):
		self.threshold = threshold
		self.max_frame = max_frame
		self.length = length
		return

	def load_m(self, f):
		size = self.length.load(f)

		# size starts counting from here
		off = f.tell()

		if self.max_frame is not None and size > self.max_frame:
			raise ValueError('exceeds maximum size')

		# compression disabled
		if self.threshold is None or self.threshold < 0:
			return read_mem(f, size)

		expcet_size = self.length.load(f)

		# bail early since decompress is expensive
		if self.max_frame is not None and size > self.max_frame:
			raise ValueError('exceeds maximum size')

		# size includes the size of expect_size
		size -= off - f.tell()

		if size < 0 or expect_size < 0:
			raise ValueError('malformed frame: negative size?')

		# uncompressed frame
		if expect_size == 0:
			return read_mem(f, size - 1)

		# compressed frame
		frame = zlib.decompress(readmem(f, size))
		if len(frame) != inner_size:
			raise ValueError('frame size does not match expected')

		return frame

	def load(self, f):
		packet_id, mem = self.load_m(f)
		if not isinstance(mem, bytes):
			return bytes(mem)
		return mem

	def dump(self, f, frame):
		# compression disabled
		if self.threshold is None or self.threshold < 0:
			# length prefix + frame
			self.length.dump(f, len(frame))
			f.write(frame)
			return

		# uncompressed frame
		if len(frame) < self.threshold:
			# length prefix + b'\x00' + frame
			VARINT.dump(f, 1 + len(frame))
			f.write(b'\x00')
			f.write(frame)
			return

		# compressed frame
		inner = zlib.compress(frame)
		size = self.length.size(len(frame)) + len(inner)
		self.length.dump(f, size)
		self.length.dump(f, len(frame))
		f.write(inner)
		return

	def loads(self, raw):
		f = io.BytesIO(raw)
		return self.load(f)

	def dumps(self, frame):
		f = io.BytesIO()
		self.dump(f, frame)
		return bytes(f.getbuffer())

