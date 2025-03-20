from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from os import getenv
from dotenv import load_dotenv
from .db_base import Base, engine  # 从 db_base.py 导入 Base 和 engine

# 加载环境变量
load_dotenv()

# Pydantic models (用于API请求和响应)
class NutritionInfo(BaseModel):
    calories: float
    protein: float
    carbs: float
    fat: float

class FoodInfo(BaseModel):
    name: str
    category: str
    weight: str
    overallNutrition: str
    otherNutrients: Dict

class HealthAdvice(BaseModel):
    nutritionAnalysis: str
    suitableGroups: str
    consumptionTips: str
    precautions: str

class FoodRecordBase(BaseModel):
    food_name: str
    calories: float
    protein: float
    carbs: float
    fat: float

class FoodRecordCreate(FoodRecordBase):
    image_url: str

class FoodRecordResponse(FoodRecordBase):
    id: int
    image_url: str
    created_at: datetime

    class Config:
        from_attributes = True

class ExerciseRecordBase(BaseModel):
    type: str
    duration: int
    calories: float

class ExerciseRecordCreate(ExerciseRecordBase):
    pass

class ExerciseRecordResponse(ExerciseRecordBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# SQLAlchemy models (用于数据库)
class MealType(enum.Enum):
    BREAKFAST = "早餐"
    LUNCH = "午餐" 
    DINNER = "晚餐"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    openid = Column(String, unique=True, index=True)
    nickname = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    ai_api_calls = Column(Integer, default=0)
    max_ai_api_calls = Column(Integer, default=3)  # 每个用户默认100次调用限制
    last_api_reset = Column(DateTime, default=datetime.utcnow)  # 上次重置时间

    # 关系
    achievements = relationship("Achievement", back_populates="user")
    food_records = relationship("FoodRecord", back_populates="user")
    exercise_records = relationship("ExerciseRecord", back_populates="user")
    goals = relationship("UserGoal", back_populates="user")

class FoodRecord(Base):
    __tablename__ = "food_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))  # 添加用户外键
    food_name = Column(String)
    meal_type = Column(Enum(MealType))
    calories = Column(Float, default=0)
    protein = Column(Float, default=0)
    carbs = Column(Float, default=0)
    fat = Column(Float, default=0)
    image_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    user = relationship("User", back_populates="food_records")

class ExerciseRecord(Base):
    __tablename__ = "exercise_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))  # 添加用户外键
    type = Column(String)
    duration = Column(Integer)  # 分钟
    calories = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    user = relationship("User", back_populates="exercise_records")

class IntensityLevel(enum.Enum):
    LOW = "低强度"
    MEDIUM = "中等强度"
    HIGH = "高强度"
    VERY_HIGH = "极高强度"
    OTHER = "其他"

class ExerciseMET(Base):
    __tablename__ = "exercise_mets"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, index=True)  # 运动代码，如 WALK_SLOW
    name = Column(String(50), nullable=False)  # 运动名称
    intensity = Column(Enum(IntensityLevel), nullable=False)  # 强度级别
    met_min = Column(Float, nullable=False)  # MET最小值
    met_max = Column(Float, nullable=False)  # MET最大值
    description = Column(String(200))  # 描述（可选）

class Achievement(Base):
    __tablename__ = 'achievements'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    type = Column(String(50))  # 成就类型
    name = Column(String(100))  # 成就名称
    description = Column(String(255))  # 成就描述
    icon = Column(String(50))  # 成就图标
    progress = Column(Integer, default=0)  # 当前进度
    target = Column(Integer)  # 目标值
    achieved = Column(Boolean, default=False)  # 是否已获得
    achieved_at = Column(DateTime)  # 获得时间
    created_at = Column(DateTime, default=func.now())
    
    # 关联关系
    user = relationship("User", back_populates="achievements")

class UserGoal(Base):
    __tablename__ = 'user_goals'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # 营养目标
    calories = Column(Float, default=0.0)
    protein = Column(Float, default=0.0)
    carbs = Column(Float, default=0.0)
    fat = Column(Float, default=0.0)
    
    # 运动目标
    exercise_frequency = Column(Integer, default=0)
    exercise_duration = Column(Integer, default=0)
    exercise_calories = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关联关系
    user = relationship("User", back_populates="goals")

# 数据库初始化
def init_db():
    if getenv("RESET_DATABASE", "false").lower() == "true":
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine) 