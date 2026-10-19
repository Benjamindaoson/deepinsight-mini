"""OS-bound Windows secrets and environment-keyed Linux authenticated encryption."""
import ctypes
import os


def protect(raw, decrypt=False, platform=None):
    if (platform or os.name) != 'nt':
        from cryptography.fernet import Fernet, InvalidToken
        try:
            key = os.environ.get('MINI_VAULT_KEY', '').encode('ascii')
            cipher = Fernet(key)
            return cipher.decrypt(raw) if decrypt else cipher.encrypt(raw)
        except (ValueError, InvalidToken, UnicodeError):
            raise ValueError('The encrypted provider store requires its configured server master key. No plaintext key was saved.') from None
    class Blob(ctypes.Structure):
        _fields_ = [('size', ctypes.c_ulong), ('data', ctypes.POINTER(ctypes.c_char))]
    buffer = ctypes.create_string_buffer(raw)
    source = Blob(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    output = Blob()
    function = ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise ValueError('The encrypted secret store could not be opened for this OS account.')
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        ctypes.windll.kernel32.LocalFree(output.data)
