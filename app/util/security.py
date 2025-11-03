import hashlib
import hmac

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


CERT_HASH_SECRET = "test"


def hash_certificate(user_id: int, course_id: int) -> str:
    msg = f"{user_id}:{course_id}".encode()
    return hmac.new(CERT_HASH_SECRET.encode(), msg, hashlib.sha256).hexdigest()


def verify_certificate(user_id: int, course_id: int, sig: str) -> bool:
    expected = hash_certificate(user_id, course_id)
    return hmac.compare_digest(expected, sig)
