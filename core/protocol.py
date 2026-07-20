# core/protocol.py
import json
from .constants import ENCODING

def build_message(msg_type: str, **kwargs) -> dict:
    """
    Construye el diccionario base de un mensaje garantizando el campo obligatorio 'type'.
    """
    message = {"type": msg_type}
    message.update(kwargs)
    return message

def encode_udp_message(message_dict: dict) -> bytes:
    """
    Convierte un diccionario en un JSON (string) y luego en bytes para enviarlo por UDP.
    """
    # separators=(',', ':') elimina los espacios en blanco innecesarios
    json_str = json.dumps(message_dict, separators=(',', ':'))
    return json_str.encode(ENCODING)

def encode_tcp_message(message_dict: dict) -> bytes:
    """
    Convierte un diccionario en un JSON, agrega el salto de línea obligatorio,
    y lo convierte en bytes para enviarlo por TCP.
    """
    json_str = json.dumps(message_dict, separators=(',', ':'))
    # Agregamos \n al final para el framing de TCP
    payload = json_str + "\n"
    return payload.encode(ENCODING)

def decode_message(message_bytes: bytes) -> dict:
    """
    Convierte los bytes recibidos de la red en un diccionario de Python.
    Sirve tanto para UDP como para TCP (después de haber cortado por \n).
    """
    # .strip() elimina saltos de línea y espacios en los extremos
    json_str = message_bytes.decode(ENCODING).strip()
    return json.loads(json_str)