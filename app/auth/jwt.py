from datetime import datetime, timedelta
from datetime import timezone
from fastapi import HTTPException
from jose import ExpiredSignatureError, JWTError, jwt
from zoneinfo import ZoneInfo

SECRET_KEY_ACCESS_TOKEN = "super-secret"
SECRET_KEY_REFRESH_TOKEN = "super-secret1"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
ACCESS_TOKEN_EXPIRE_DAYS = 7
# ACCESS_TOKEN_EXPIRE_HOURS = 1

def create_refresh_token(data: dict, expires_delta: timedelta = None):
    Mexico_City = ZoneInfo("America/Mexico_City")
    # now = datetime().now()

    to_encode = data.copy()
    expire = datetime.now(Mexico_City) + (expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))
    print("expire__refresh", expire)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY_REFRESH_TOKEN, algorithm=ALGORITHM)

def create_access_token(data: dict, expires_delta: timedelta = None):
    Mexico_City = ZoneInfo("America/Mexico_City")
    print("timezone", Mexico_City)
    to_encode = data.copy()
    expire = datetime.now(Mexico_City) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    print("expire__access", expire)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY_ACCESS_TOKEN, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY_ACCESS_TOKEN, algorithms=[ALGORITHM])
    except JWTError as e:
        print("error verifying token",e)
        return None
    
def verify_refresh_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY_REFRESH_TOKEN, algorithms=[ALGORITHM])
    except JWTError as e:
        print("error verifying refresh token",e)
        return None