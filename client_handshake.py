import socket
from typing import Tuple


class ClientHandshake:
	def __init__(self, private_key: int, server_address: str, server_port: int):
		self.private_key = private_key
		self.server_address = server_address
		self.server_port = server_port

	def get_encryption_given_G(self, G: bytes) -> Tuple[bytes, bytes]:
		# Connect to the server
		with socket.create_connection((self.server_address, self.server_port)) as conn:
			# Send public key Qclient to server
			Qclient = G
			conn.sendall(Qclient)

			# Receive public key Qserver from server
			Qserver_bytes = conn.recv(64)

			# Receive nonce from server
			nonce = conn.recv(32)

			# Receive encrypted signature from server
			size = len("LlsServerHello:") + 64
			encrypted_signature = conn.recv(size)
			return encrypted_signature, nonce
