"""
核心工具函数：贝叶斯平均评分、密码哈希、JWT 处理等
"""
import math
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext

# 配置
SECRET_KEY = "your-secret-key-change-in-prod"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def calculate_bayesian_average(
    item_votes: int, 
    item_avg: float, 
    global_avg: float, 
    global_votes: int,
    c: float = 10.0
):
    """
    贝叶斯平均评分公式: (C * m + R * v) / (C + v)
    C: 置信度常数 (默认10，表示需要多少票才能接近真实分数)
    m: 全局平均分
    R: 物品当前平均分
    v: 物品当前票数
    """
    if item_votes == 0:
        return global_avg
    
    weighted_score = (c * global_avg) + (item_votes * item_avg)
    total_weight = c + item_votes
    
    return weighted_score / total_weight
