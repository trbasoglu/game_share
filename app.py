from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime, timedelta
import secrets
import os
from typing import Optional

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./gamecodes.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class GameCode(Base):
    __tablename__ = "gamecodes"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, nullable=False)
    url_token = Column(String, unique=True, nullable=False)
    is_used = Column(Boolean, default=False)
    used_by_ip = Column(String)
    used_at = Column(DateTime)
    game_name = Column(String, nullable=False)  # Add game_name column

class IPCooldown(Base):
    __tablename__ = "ip_cooldowns"
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, unique=True, nullable=False)
    last_access = Column(DateTime, nullable=False)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic models
class CodeCreate(BaseModel):
    code: str
    game_name: str  # Add game_name field

class CodeResponse(BaseModel):
    message: str
    share_url: str

# FastAPI app
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def is_ip_in_cooldown(request: Request, db: Session) -> bool:
    # Bypass IP check for localhost domain
    print(request.url.hostname)
    if request.url.hostname in ['localhost', '127.0.0.1']:
        return False
    client_ip = request.client.host
    cooldown = db.query(IPCooldown).filter(IPCooldown.ip_address == client_ip).first()
    if not cooldown:
        return False
    
    cooldown_period = timedelta(minutes=30)
    return datetime.utcnow() - cooldown.last_access < cooldown_period

def update_ip_cooldown(ip_address: str, db: Session):
    cooldown = db.query(IPCooldown).filter(IPCooldown.ip_address == ip_address).first()
    if cooldown:
        cooldown.last_access = datetime.utcnow()
    else:
        cooldown = IPCooldown(ip_address=ip_address, last_access=datetime.utcnow())
        db.add(cooldown)
    db.commit()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/create", response_class=HTMLResponse)
async def create_page(request: Request):
    return templates.TemplateResponse("create.html", {"request": request})

@app.post("/api/add_code", response_model=CodeResponse)
async def add_code(code_data: CodeCreate, request: Request, db: Session = Depends(get_db)):
    url_token = secrets.token_hex(16)
    new_code = GameCode(
        code=code_data.code,
        url_token=url_token,
        game_name=code_data.game_name  # Add game_name to new_code
    )
    db.add(new_code)
    db.commit()
    
    share_url = str(request.base_url) + f"code/{url_token}"
    return CodeResponse(
        message="Code added successfully",
        share_url=share_url
    )

@app.get("/code/{token}", response_class=HTMLResponse)
async def get_code(token: str, request: Request, db: Session = Depends(get_db)):
    if is_ip_in_cooldown(request, db):
        cooldown = db.query(IPCooldown).filter(IPCooldown.ip_address == request.client.host).first()
        remaining_time = cooldown.last_access + timedelta(minutes=30) - datetime.utcnow()
        minutes_remaining = int(remaining_time.total_seconds() / 60)
        return templates.TemplateResponse(
            "code.html",
            {
                "request": request,
                "error": f"Please wait {minutes_remaining} minutes before getting another code"
            }
        )
    
    code = db.query(GameCode).filter(GameCode.url_token == token).first()
    if not code:
        return templates.TemplateResponse(
            "code.html",
            {"request": request, "error": "Invalid or expired code"}
        )
    
    if code.is_used:
        return templates.TemplateResponse(
            "code.html",
            {"request": request, "error": "This code has already been claimed"}
        )
    
    code.is_used = True
    code.used_by_ip = request.client.host
    code.used_at = datetime.utcnow()
    update_ip_cooldown(request.client.host, db)
    db.commit()
    
    return templates.TemplateResponse("code.html", {
        "request": request, 
        "code": code.code, 
        "game_name": code.game_name  # Add game name to template
    })
