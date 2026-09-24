from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from database import sessionlocal, engine
from typing import Annotated
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from model import Users
from passlib.context import CryptContext
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from datetime import timedelta, datetime, timezone

router = APIRouter()

SECRET_KEY = "6bac8f543182a9822c4d3e138a8d73b0a0e0b00b2a1d163c5b219c4991f0a1bc"
ALGORITHM = 'HS256'

def open_database():
    db = sessionlocal()
    try:
        yield db
    finally:
        db.close()

by_crypt = CryptContext(schemes=['bcrypt'], deprecated='auto')
oth_bearar = OAuth2PasswordBearer(tokenUrl='/User_Login')
db_dependency = Annotated[Session, Depends(open_database)]


# -------------------- JWT Token Create -------------------- #
def create_access_token(username: str, id: int, role: str, expire: timedelta):
    encode = {'sub': username, 'id': id, 'role': role}
    expire_date = datetime.now(timezone.utc) + expire
    encode.update({'exp': expire_date})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


# -------------------- Token Decode -------------------- #
def token_decode(token: Annotated[str, Depends(oth_bearar)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        user_id: int = payload.get('id')
        role: str = payload.get('role')

        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        return {"username": username, "id": user_id, "role": role}

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


# -------------------- Schemas -------------------- #
class UserRequest(BaseModel):
    firstname: str = Field(..., min_length=3, max_length=30)
    lastname: str = Field(..., min_length=3, max_length=30)
    email: str
    password: str = Field(..., min_length=8, max_length=30)
    role: str = Field(..., min_length=3, max_length=30)
    is_active: bool = True


# -------------------- Signup -------------------- #
@router.post('/create_user')
def user_registration(db: db_dependency, new_user: UserRequest):
    # একই ইমেইলে আগে থেকেই ইউজার আছে কি না চেক
    existing = db.query(Users).filter(Users.email == new_user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_data = Users(
        firstname=new_user.firstname,
        lastname=new_user.lastname,
        email=new_user.email.lower().strip(),
        password=by_crypt.hash(new_user.password),
        role=new_user.role,
        is_active=new_user.is_active
    )

    db.add(user_data)
    db.commit()
    db.refresh(user_data)

    return JSONResponse(
        status_code=201,
        content={"message": "User created successfully"}
    )


# -------------------- Login Matching -------------------- #
def user_login_matching(email: str, password: str, db: Session):
    user = db.query(Users).filter(Users.email == email.lower().strip()).first()
    if user is None:
        return None
    if not user.is_active:
        return None
    if not by_crypt.verify(password, user.password):
        return None
    return user


# -------------------- Login -------------------- #
@router.post('/User_Login')
def user_login(db: db_dependency, from_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user_authentication = user_login_matching(from_data.username, from_data.password, db)

    if not user_authentication:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token(
        username=user_authentication.email,
        id=user_authentication.id,
        role=user_authentication.role,
        expire=timedelta(minutes=30)
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_authentication.id,
            "firstname": user_authentication.firstname,
            "role": user_authentication.role
        }
    }


user_dependency = Annotated[dict, Depends(token_decode)]


# -------------------- Update User -------------------- #
class UpdateUser(BaseModel):
    firstname: str = Field(None, min_length=3, max_length=30)
    lastname: str = Field(None, min_length=3, max_length=30)
    email: str = None


@router.put('/edituser')
def update_user(user: user_dependency, db: db_dependency, update_user: UpdateUser):
    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    db_user = db.query(Users).filter(Users.id == user.get('id')).first()
    if not db_user:
        raise HTTPException(status_code=404, detail='User not found')

    update_data = update_user.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.commit()
    return JSONResponse(status_code=200, content={'message': 'User updated successfully'})


# -------------------- Update Password -------------------- #
class UpdatePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=30)


@router.put('/passwordchange')
def update_password(user: user_dependency, db: db_dependency, update_password: UpdatePassword):
    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    db_user = db.query(Users).filter(Users.id == user.get('id')).first()
    if not db_user:
        raise HTTPException(status_code=404, detail='User not found')

    if not by_crypt.verify(update_password.current_password, db_user.password):
        raise HTTPException(status_code=401, detail='Wrong Password')

    db_user.password = by_crypt.hash(update_password.new_password)
    db.add(db_user)
    db.commit()
    return JSONResponse(status_code=200, content={'message': 'Password updated successfully'})