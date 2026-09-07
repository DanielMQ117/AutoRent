"""Utilidades criptográficas para seguridad, hashing y verificación de contraseñas."""

import bcrypt
from src.core.exceptions import AuthenticationError


def hash_password(password: str) -> str:
    """Genera un hash seguro con salt usando el algoritmo bcrypt.
    
    Args:
        password: La contraseña en texto plano.
        
    Returns:
        Cadena de caracteres con el hash bcrypt listo para persistir.
    """
    if not password:
        raise ValueError("La contraseña no puede estar vacía.")
    
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña en texto plano coincide con su hash almacenado.
    
    Args:
        plain_password: La contraseña proporcionada por el usuario.
        hashed_password: El hash almacenado previamente en la base de datos.
        
    Returns:
        True si coincide, False en caso contrario.
    """
    if not plain_password or not hashed_password:
        return False

    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception as e:
        raise AuthenticationError(
            message=f"Error durante la verificación de contraseña: {e}",
            code="SECURITY_VERIFY_ERROR",
        ) from e
