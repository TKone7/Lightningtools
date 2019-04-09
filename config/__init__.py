import os

macaroon_path = "config/readonly.macaroon"
cert_path = "config/tls.cert"
grpc_max_length = 32 * 1024 * 1024

lnd_grpc_server = os.getenv("LNDASH_LND_SERVER", "192.168.0.200:10009")
