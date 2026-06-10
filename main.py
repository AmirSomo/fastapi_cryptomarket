import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
import jwt
from datetime import datetime, timedelta
import random
import uuid
import os

# Cryptography and Security
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Sample Cryptocurrencies
class Cryptocurrency(BaseModel):
    id: str
    name: str
    symbol: str
    current_price: float
    market_cap: float

# User Model
class User(BaseModel):
    username: str
    email: str
    hashed_password: str
    balance: float
    owned_tokens: dict

# Transaction Model
class Transaction(BaseModel):
    id: str
    user_id: str
    crypto_symbol: str
    amount: float
    price: float
    transaction_type: str  # 'buy' or 'sell'
    timestamp: datetime

# Token Model
class Token(BaseModel):
    access_token: str
    token_type: str

class CryptoAPI:
    def __init__(self):
        self.users = {}
        self.transactions = []
        self.cryptocurrencies = {
            'RNDM': Cryptocurrency(
                id='rndm', 
                name='RandomCoin', 
                symbol='RNDM', 
                current_price=1.0, 
                market_cap=1000000
            ),
            'FLUX': Cryptocurrency(
                id='flux', 
                name='FluxCoin', 
                symbol='FLUX', 
                current_price=5.0, 
                market_cap=5000000
            )
        }
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

    def create_access_token(self, data: dict):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def register_user(self, username: str, email: str, password: str):
        if username in self.users:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        hashed_password = self._hash_password(password)
        user = User(
            username=username, 
            email=email, 
            hashed_password=hashed_password,
            balance=1000.0,  # Initial balance
            owned_tokens={}
        )
        self.users[username] = user
        return user

    def _hash_password(self, password: str):
        # In a real implementation, use proper password hashing
        return password + "_hashed"

    def login_user(self, username: str, password: str):
        user = self.users.get(username)
        if not user or user.hashed_password != self._hash_password(password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        access_token = self.create_access_token(data={"sub": username})
        return Token(access_token=access_token, token_type="bearer")

    def buy_crypto(self, username: str, symbol: str, amount: float):
        user = self.users.get(username)
        crypto = self.cryptocurrencies.get(symbol)
        
        if not user or not crypto:
            raise HTTPException(status_code=404, detail="User or Cryptocurrency not found")
        
        total_cost = crypto.current_price * amount
        if user.balance < total_cost:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
        # Dynamic price change
        crypto.current_price *= 1.02  # Price increases by 2% on buy
        
        user.balance -= total_cost
        user.owned_tokens[symbol] = user.owned_tokens.get(symbol, 0) + amount
        
        transaction = Transaction(
            id=str(uuid.uuid4()),
            user_id=username,
            crypto_symbol=symbol,
            amount=amount,
            price=crypto.current_price,
            transaction_type='buy',
            timestamp=datetime.now()
        )
        self.transactions.append(transaction)
        
        return transaction

    def sell_crypto(self, username: str, symbol: str, amount: float):
        user = self.users.get(username)
        crypto = self.cryptocurrencies.get(symbol)
        
        if not user or not crypto:
            raise HTTPException(status_code=404, detail="User or Cryptocurrency not found")
        
        if user.owned_tokens.get(symbol, 0) < amount:
            raise HTTPException(status_code=400, detail="Insufficient token balance")
        
        # Dynamic price change
        crypto.current_price *= 0.98  # Price decreases by 2% on sell
        
        total_revenue = crypto.current_price * amount
        user.balance += total_revenue
        user.owned_tokens[symbol] -= amount
        
        transaction = Transaction(
            id=str(uuid.uuid4()),
            user_id=username,
            crypto_symbol=symbol,
            amount=amount,
            price=crypto.current_price,
            transaction_type='sell',
            timestamp=datetime.now()
        )
        self.transactions.append(transaction)
        
        return transaction

# FastAPI Application
app = FastAPI()
crypto_api = CryptoAPI()

@app.post("/register")
def register(username: str, email: str, password: str):
    return crypto_api.register_user(username, email, password)

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    return crypto_api.login_user(form_data.username, form_data.password)

@app.get("/cryptocurrencies")
def list_cryptocurrencies():
    return list(crypto_api.cryptocurrencies.values())

@app.post("/buy")
def buy_crypto(username: str, symbol: str, amount: float):
    return crypto_api.buy_crypto(username, symbol, amount)

@app.post("/sell")
def sell_crypto(username: str, symbol: str, amount: float):
    return crypto_api.sell_crypto(username, symbol, amount)

@app.get("/transactions")
def get_transactions(username: str):
    return [t for t in crypto_api.transactions if t.user_id == username]

if __name__ == "__main__":
    import os
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
