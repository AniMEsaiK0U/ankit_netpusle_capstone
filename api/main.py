import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel, Field


ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 30
DEMO_USERNAME = os.getenv("DEMO_USERNAME")
JWT_SECRET = os.getenv("JWT_SECRET")
demo_password = os.getenv("DEMO_PASSWORD")

if not DEMO_USERNAME or not demo_password or not JWT_SECRET:
    raise RuntimeError(
        "Set DEMO_USERNAME, DEMO_PASSWORD, and JWT_SECRET before starting the API."
    )
if len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must contain at least 32 characters.")

password_hash = PasswordHash.recommended()
demo_user = {
    "username": DEMO_USERNAME,
    "password_hash": password_hash.hash(demo_password),
}
del demo_password

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
app = FastAPI(title="NetPulse Devices API", version="1.0.0")


class DeviceBase(BaseModel):
    name: str = Field(min_length=1)
    device_type: str = Field(min_length=1)
    status: str = Field(min_length=1)
    location: str = Field(min_length=1)


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    device_type: str | None = Field(default=None, min_length=1)
    status: str | None = Field(default=None, min_length=1)
    location: str | None = Field(default=None, min_length=1)


class Device(DeviceBase):
    id: int


class Token(BaseModel):
    access_token: str
    token_type: str


devices: dict[int, dict] = {
    1: {
        "id": 1,
        "name": "North Campus Gateway",
        "device_type": "gateway",
        "status": "online",
        "location": "North Campus",
    },
    2: {
        "id": 2,
        "name": "Research Lab Sensor",
        "device_type": "sensor",
        "status": "online",
        "location": "Research Lab",
    },
}


def authenticate(username: str, password: str) -> bool:
    return username == demo_user["username"] and password_hash.verify(
        password, demo_user["password_hash"]
    )


def create_access_token(subject: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    return jwt.encode(
        {"sub": subject, "exp": expires},
        JWT_SECRET,
        algorithm=ALGORITHM,
    )


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username != demo_user["username"]:
            raise credentials_error
    except InvalidTokenError:
        raise credentials_error from None
    return username


def get_device_or_404(device_id: int) -> dict:
    device = devices.get(device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@app.get("/")
def home() -> dict[str, str]:
    return {"message": "NetPulse Devices API is running"}


@app.post("/auth/token", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends()) -> Token:
    if not authenticate(form.username, form.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(
        access_token=create_access_token(form.username),
        token_type="bearer",
    )


@app.get("/devices", response_model=list[Device])
def list_devices() -> list[dict]:
    return list(devices.values())


@app.get("/devices/{device_id}", response_model=Device)
def get_device(device_id: int) -> dict:
    return get_device_or_404(device_id)


@app.post("/devices", response_model=Device, status_code=status.HTTP_201_CREATED)
def create_device(
    device: DeviceCreate,
    current_user: str = Depends(get_current_user),
) -> dict:
    device_id = max(devices, default=0) + 1
    record = {"id": device_id, **device.model_dump()}
    devices[device_id] = record
    return record


@app.put("/devices/{device_id}", response_model=Device)
def replace_device(
    device_id: int,
    device: DeviceCreate,
    current_user: str = Depends(get_current_user),
) -> dict:
    get_device_or_404(device_id)
    record = {"id": device_id, **device.model_dump()}
    devices[device_id] = record
    return record


@app.patch("/devices/{device_id}", response_model=Device)
def update_device(
    device_id: int,
    patch: DeviceUpdate,
    current_user: str = Depends(get_current_user),
) -> dict:
    device = get_device_or_404(device_id)
    device.update(patch.model_dump(exclude_unset=True, exclude_none=True))
    return device


@app.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: int,
    current_user: str = Depends(get_current_user),
) -> Response:
    get_device_or_404(device_id)
    del devices[device_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)