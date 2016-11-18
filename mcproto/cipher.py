import os

from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.PublicKey import RSA

__all__ = ['AESCipher', 'RSACipher']

class AESCipher:
	def __init__(self, secret=None, iv=None):
		if isinstance(secret, Cipher):
			iv = (secret.in_iv, secret.out_iv)
			secret = secret.secret

		if secret is None:
			secret = os.urandom(16)

		if not isinstance(secret, bytes) or len(secret) != 16:
			raise TypeError('secret must be bytes[16]')

		if iv is None:
			iv = (secret, secret)

		self._secret = secret
		self._in_iv = bytearray(iv[0])
		self._out_iv = bytearray(iv[1])
		self.in_cipher = AES.new(secret, AES.MODE_CFB, self.in_iv)
		self.out_cipher = AES.new(secret, AES.MODE_CFB, self.out_iv)

	@property
	def secret(self):
		return bytes(self._secret)

	@property
	def in_iv(self):
		return bytes(self._in_iv)

	@property
	def out_iv(self):
		return bytes(self._out_iv)

	def encrypt(self, raw):
		raw = self.out_cipher.encrypt(raw)
		if len(raw) > 16:
			self._out_iv[:] = raw[-16:]
		else:
			self._out_iv[:-len(raw)] = self._out_iv[len(raw):]
			self._out_iv[-len(raw):] = raw
		return raw

	def decrypt(self, raw):
		if len(raw) > 16:
			self._in_iv[:] = raw[-16:]
		else:
			self._in_iv[:-len(raw)] = self._in_iv[len(raw):]
			self._in_iv[-len(raw):] = raw
		return self.in_cipher.decrypt(raw)

	def encrypt_inplace(self, raw):
		raw[:] = self.encrypt(raw)

	def decrypt_inplace(self, raw):
		raw[:] = self.decrypt(raw)

class RSACipher:
	def __init__(self, bits=1024, key=None):
		if key is None:
			self.rsa = RSA.generate(bits)
		else:
			self.rsa = RSA.importKey(key)

		self.cipher = PKCS1_v1_5.new(self.rsa)

		self._pubkey = self.rsa.publickey().exportKey(format='DER', pkcs=1)

	@property
	def pubkey(self):
		return self._pubkey

	def encrypt(self, raw):
		return self.cipher.encrypt(raw)

	def decrypt(self, raw):
		return self.cipher.decrypt(raw, raw)

