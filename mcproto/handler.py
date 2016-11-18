from weakref import WeakKeyDictionary, WeakSet

__all__ = ['DuplicateHandlerError', 'NoHandlerError',
		'HandlerDict', 'BaseHandler',
		'handles']

class DuplicateHandlerError(KeyError):
	pass

class NoHandlerError(KeyError):
	pass

class HandlerDict(WeakKeyDictionary):
	def register(self, key):
		def annotate(val):
			if key in self:
				raise DuplicateHandlerError(key)
			self[key] = val
			return val
		return annotate

	def __getitem__(self, key):
		# specific values
		if key in self:
			return super().__getitem__(key)

		# we need the type of our key to get the mro
		if not isinstance(key, type):
			key = type(key)

		# check each class in the mro
		for cls in key.__mro__:
			if cls in self:
				return super().__getitem__(cls)

		# not found?
		raise NoHandlerError(key)

	def __call__(self, val, *args, **kwargs):
		return self[val](val, *args, **kwargs)

	def __repr__(self):
		return '<HandlerDict at 0x%x>' % id(self)

class _HandlerMeta(type):
	def __new__(metacls, cls_name, bases, namespace, **kwargs):
		# TODO: Should this really be the order?
		handler = namespace.get('_HANDLER', HandlerDict())

		# inherit handlers from bases
		for base_cls in bases:
			handler.update(getattr(base_cls, '_HANDLER', {}))

		# build up new handlers annotated with handles(TypeName)
		new_keys = set()
		for func in namespace:
			# ignore regular members
			if not hasattr(func, '_HANDLES'):
				continue

			for key in func._HANDLES:
				# error out on duplicates
				if key in new_keys:
					raise DuplicateHandlerError(key)

				new_keys.add(key)
				handler[key] = func

		namespace['_HANDLER'] = handler

		cls = super().__new__(metacls, cls_name, bases, namespace, **kwargs)

		return cls

def handles(val):
	def annotate(func):
		if not hasattr(func, '_HANDLES'):
			func.__handles__ = WeakSet()
		func.__handles__.add(val)
		return func
	return annotate

class BaseHandler(metaclass=_HandlerMeta):
	_HANDLER = HandlerDict()

	def __call__(self, val, *args, **kwargs):
		return self._HANDLER(val, *args, **kwargs)

