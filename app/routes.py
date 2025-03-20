from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Body, Request
from sqlalchemy.orm import Session
from typing import List, Dict
from datetime import datetime, timedelta
from .database import get_db
from .models import (
    User, FoodRecord, ExerciseRecord, ExerciseMET, 
    MealType, Achievement, UserGoal,
    # Pydantic models
    FoodRecordResponse, ExerciseRecordResponse,
    FoodRecordCreate, ExerciseRecordCreate
)
from .utils import (
    analyze_food_image_openai, 
    parse_food_info,
    get_wx_session,
    create_token,
    verify_token,
    get_current_user_id
)
from .logger import api_logger
import base64
from flask import jsonify
from sqlalchemy import func

router = APIRouter()

# 删除内存存储变量，因为我们使用数据库
# food_records: List[FoodRecord] = []
# exercise_records: List[ExerciseRecord] = []

@router.post("/analyze-food")
async def analyze_food(request: Request, data: Dict = Body(...), db: Session = Depends(get_db)):
    try:
        api_logger.info(f"收到食物分析请求: {request.client.host}")
        # 获取用户信息
        try:
            # 临时禁用用户验证，用于测试
            # user_id = get_current_user_id(request)
            # user = db.query(User).filter(User.id == user_id).first()
            # if not user:
            #     return {
            #         "success": False,
            #         "error": "用户不存在"
            #     }
            
            # 使用测试用户
            user = db.query(User).first()
            if not user:
                # 如果没有用户，创建一个测试用户
                user = User(
                    openid="test_user",
                    ai_api_calls=0,
                    max_ai_api_calls=100
                )
                db.add(user)
                db.commit()
                db.refresh(user)

        except HTTPException:
            # 如果用户认证失败，使用测试用户
            user = db.query(User).first()
            if not user:
                return {
                    "success": False,
                    "error": "系统错误"
                }

        # 检查用户API调用次数
        if user.ai_api_calls >= user.max_ai_api_calls:
            return {
                "success": False,
                "error": "已达到AI分析次数限制",
                "remaining_calls": 0
            }

        # 获取图片数据
        image_data = data.get('image')
        if not image_data:
            return {
                "success": False,
                "error": "未提供图片数据"
            }

        try:
            # 处理base64数据
            if ',' in image_data:  # 如果包含data URI scheme
                image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)
            api_logger.info(f"成功解码图片数据，大小: {len(image_bytes)} bytes")

            # 调用API分析图片
            result = await analyze_food_image_openai(image_bytes)
            if not result:
                return {
                    "success": False,
                    "error": "食物分析失败"
                }

            # 更新用户API调用次数
            try:
                user.ai_api_calls += 1
                db.commit()
                api_logger.info(f"用户 {user.id} API调用次数更新为: {user.ai_api_calls}")
            except Exception as e:
                api_logger.error(f"更新API调用次数失败: {str(e)}")
                db.rollback()

            # 解析结果
            parsed_result = parse_food_info(result)

            return {
                "success": True,
                "data": {
                    "raw_result": result,
                    "parsed_result": parsed_result
                },
                "remaining_calls": user.max_ai_api_calls - user.ai_api_calls
            }

        except Exception as e:
            api_logger.error(f"处理图片数据失败: {str(e)}")
            return {
                "success": False,
                "error": "图片处理失败"
            }

    except Exception as e:
        api_logger.error(f"处理请求失败: {str(e)}")
        return {
            "success": False,
            "error": "服务器内部错误"
        }
@router.get("/food-records")
async def get_food_records(request: Request, db: Session = Depends(get_db)):
    try:
        # 获取用户ID
        user_id = get_current_user_id(request)
        
        today = datetime.utcnow().date()
        # 获取该用户的所有食物记录
        records = db.query(FoodRecord).filter(FoodRecord.user_id == user_id).filter(
            func.date(FoodRecord.created_at) == today
        ).all()
        
        # 返回记录
        return {
            "success": True,
            "data": [
                {
                    "id": record.id,
                    "user_id": record.user_id,
                    "food_name": record.food_name,
                    "meal_type_value": record.meal_type if record.meal_type else None,
                    "meal_type": record.meal_type.value if record.meal_type else None,
                    "calories": record.calories,
                    "protein": record.protein,
                    "carbs": record.carbs,
                    "fat": record.fat,
                    "image_url": record.image_url,
                    "created_at": record.created_at.isoformat()
                }
                for record in records
            ]
        }
    except Exception as e:
        api_logger.exception(f"获取食物记录失败: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/food-records")
async def create_food_record(request: Request, data: dict, db: Session = Depends(get_db)):
    try:
        user_id = get_current_user_id(request)
        if not user_id:
            api_logger.error("更新目标失败：未找到用户ID")
            return {"success": False, "error": "未找到用户ID"}
        
        # 创建新记录
        db_record = FoodRecord(
            food_name=data.get("food_name", ""),
            meal_type=MealType[data.get("meal_type", "BREAKFAST")],
            calories=float(data.get("calories", 0)),
            protein=float(data.get("protein", 0)),
            carbs=float(data.get("carbs", 0)),
            fat=float(data.get("fat", 0)),
            user_id=user_id,
            image_url=data.get("image_url")
        )
        
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        
        return {
            "success": True,
            "data": {
                "id": db_record.id,
                "food_name": db_record.food_name,
                "meal_type": db_record.meal_type.value,
                "calories": db_record.calories,
                "protein": db_record.protein,
                "carbs": db_record.carbs,
                "fat": db_record.fat,
                "image_url": db_record.image_url,
                "created_at": db_record.created_at.isoformat()
            }
        }
    except Exception as e:
        print(f"Error in create_food_record: {str(e)}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/today-stats")
async def get_today_stats(db: Session = Depends(get_db)):
    try:
        today = datetime.utcnow().date()
        
        # 获取今日食物记录
        food_records = db.query(FoodRecord).filter(
            FoodRecord.created_at >= today
        ).all()
        
        # 获取今日运动记录
        exercise_records = db.query(ExerciseRecord).filter(
            ExerciseRecord.created_at >= today
        ).all()
        
        # 计算总计
        total_calories = sum(r.calories or 0 for r in food_records)
        total_protein = sum(r.protein or 0 for r in food_records)
        total_carbs = sum(r.carbs or 0 for r in food_records)
        total_fat = sum(r.fat or 0 for r in food_records)
        
        # 减去运动消耗
        exercise_calories = sum(r.calories or 0 for r in exercise_records)
        
        return {
            "success": True,
            "data": {
                "calories": total_calories - exercise_calories,
                "protein": total_protein,
                "carbs": total_carbs,
                "fat": total_fat
            }
        }
    except Exception as e:
        print(f"Error in get_today_stats: {str(e)}")
        return {
            "success": False,
            "data": {
                "calories": 0,
                "protein": 0,
                "carbs": 0,
                "fat": 0
            }
        }

@router.get("/recent-activities")
async def get_recent_activities(db: Session = Depends(get_db)):
    try:
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        food_records = db.query(FoodRecord).filter(
            FoodRecord.created_at >= seven_days_ago
        ).all()
        
        exercise_records = db.query(ExerciseRecord).filter(
            ExerciseRecord.created_at >= seven_days_ago
        ).all()
        
        activities = []
        
        for record in food_records:
            activities.append({
                "type": "food",
                "name": record.food_name,
                "calories": record.calories or 0,
                "createdAt": record.created_at.isoformat()
            })
            
        for record in exercise_records:
            activities.append({
                "type": "exercise",
                "name": record.type,
                "calories": -(record.calories or 0),  # 负值表示消耗
                "createdAt": record.created_at.isoformat()
            })
            
        activities.sort(key=lambda x: x["createdAt"], reverse=True)
        
        return {
            "success": True,
            "data": activities
        }
    except Exception as e:
        print(f"Error in get_recent_activities: {str(e)}")
        return {
            "success": False,
            "data": []
        }

@router.get("/exercise-records")
async def get_exercise_records(request: Request, db: Session = Depends(get_db)):
    # 获取用户ID
    user_id = get_current_user_id(request)
        
    try:
        records = db.query(ExerciseRecord).filter(ExerciseRecord.user_id == user_id).order_by(
            ExerciseRecord.created_at.desc()
        ).all()
        
        formatted_records = [{
            "id": r.id,
            "type": r.type,
            "duration": r.duration,
            "calories": r.calories,
            "createdAt": r.created_at.isoformat()
        } for r in records]
        
        return {
            "success": True,
            "data": formatted_records
        }
    except Exception as e:
        api_logger.error(f"获取运动记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/exercise-records")
async def add_exercise_record(request: Request, data: dict, db: Session = Depends(get_db)):
    try:
        user_id = get_current_user_id(request)
        if not user_id:
            api_logger.error("更新目标失败：未找到用户ID")
            return {"success": False, "error": "未找到用户ID"}
        
        exercise = ExerciseRecord(
            type=data["type"],
            duration=data["duration"],
            calories=data["calories"],
            user_id=user_id
        )
        db.add(exercise)
        db.commit()
        db.refresh(exercise)
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/exercise-mets")
async def get_exercise_mets(db: Session = Depends(get_db)):
    try:
        mets = db.query(ExerciseMET).order_by(ExerciseMET.name).all()
        return {
            "success": True,
            "data": [{
                "code": met.code,
                "name": met.name,
                "met_min": met.met_min,
                "met_max": met.met_max,
                "description": met.description
            } for met in mets]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/today-meals")
async def get_today_meals(db: Session = Depends(get_db)):
    try:
        today = datetime.utcnow().date()
        meals = db.query(FoodRecord).filter(
            FoodRecord.created_at >= today
        ).order_by(FoodRecord.created_at.desc()).all()
        
        return {
            "success": True,
            "data": {
                "breakfast": next((m for m in meals if m.meal_type == MealType.BREAKFAST), None),
                "lunch": next((m for m in meals if m.meal_type == MealType.LUNCH), None),
                "dinner": next((m for m in meals if m.meal_type == MealType.DINNER), None)
            }
        }
    except Exception as e:
        print(f"Error in get_today_meals: {str(e)}")
        return {
            "success": False,
            "data": {
                "breakfast": None,
                "lunch": None,
                "dinner": None
            }
        }

@router.get("/daily-nutrition")
async def get_daily_nutrition(db: Session = Depends(get_db)):
    try:
        # 获取今天的日期
        today = datetime.utcnow().date()
        
        # 获取今日饮食记录
        food_records = db.query(FoodRecord).filter(
            func.date(FoodRecord.created_at) == today
        ).all()
        
        print(f"获取今日饮食记录: {len(food_records)}")
        # 获取今日运动记录
        exercise_records = db.query(ExerciseRecord).filter(
            func.date(ExerciseRecord.created_at) == today
        ).all()
        
        print(f"获取今日运动记录: {len(exercise_records)}")
        # 计算总营养摄入
        total_calories = sum(record.calories or 0 for record in food_records)
        total_protein = sum(record.protein or 0 for record in food_records)
        total_carbs = sum(record.carbs or 0 for record in food_records)
        total_fat = sum(record.fat or 0 for record in food_records)
        
        # 计算运动消耗
        exercise_calories = sum(record.calories or 0 for record in exercise_records)
        
        # 计算净摄入（摄入 - 消耗）
        net_calories = total_calories - exercise_calories
        
        return {
            'success': True,
            'data': {
                'calories': net_calories,
                'protein': total_protein,
                'carbs': total_carbs,
                'fat': total_fat,
                'exercise_calories': exercise_calories
            }
        }
    except Exception as e:
        print(f"获取每日营养数据失败: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

@router.get("/achievements")
async def get_achievements(db: Session = Depends(get_db)):
    try:
        # 获取用户的所有成就
        achievements = db.query(Achievement).all()
        
        # 计算连续打卡天数
        streak = calculate_streak(db)
        
        return {
            "success": True,
            "data": {
                "achievements": [
                    {
                        "id": ach.id,
                        "type": ach.type,
                        "name": ach.name,
                        "description": ach.description,
                        "icon": ach.icon,
                        "progress": ach.progress,
                        "target": ach.target,
                        "achieved": ach.achieved,
                        "achieved_at": ach.achieved_at
                    } for ach in achievements
                ],
                "streak": streak
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def calculate_streak(db: Session):
    # 获取用户的所有记录，按日期排序
    records = db.query(FoodRecord).order_by(FoodRecord.created_at.desc()).all()
    
    if not records:
        return 0
        
    streak = 1
    last_date = records[0].created_at.date()
    
    for record in records[1:]:
        current_date = record.created_at.date()
        if (last_date - current_date).days == 1:
            streak += 1
            last_date = current_date
        else:
            break
            
    return streak

@router.get("/food-stats")
async def get_food_stats(db: Session = Depends(get_db)):
    try:
        # 获取所有食物记录
        records = db.query(FoodRecord).all()
        
        if not records:
            return {
                "success": True,
                "data": {
                    "totalRecords": 0,
                    "daysCount": 0,
                    "avgCalories": 0,
                    "avgProtein": 0,
                    "avgCarbs": 0,
                    "avgFat": 0
                }
            }

        # 计算统计数据
        total_records = len(records)
        
        # 计算不同日期的数量
        unique_dates = len(set(record.created_at.date() for record in records))
        
        # 计算平均值
        total_calories = sum(record.calories for record in records)
        total_protein = sum(record.protein for record in records)
        total_carbs = sum(record.carbs for record in records)
        total_fat = sum(record.fat for record in records)
        
        return {
            "success": True,
            "data": {
                "totalRecords": total_records,
                "daysCount": unique_dates,
                "avgCalories": round(total_calories / total_records, 1),
                "avgProtein": round(total_protein / total_records, 1),
                "avgCarbs": round(total_carbs / total_records, 1),
                "avgFat": round(total_fat / total_records, 1)
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/exercise-stats")
async def get_exercise_stats(db: Session = Depends(get_db)):
    try:
        # 获取所有运动记录
        records = db.query(ExerciseRecord).all()
        
        if not records:
            return {
                "success": True,
                "data": {
                    "totalRecords": 0,
                    "daysCount": 0,
                    "totalDuration": 0,
                    "avgCalories": 0,
                    "totalCalories": 0
                }
            }

        # 计算统计数据
        total_records = len(records)
        
        # 计算不同日期的数量
        unique_dates = len(set(record.created_at.date() for record in records))
        
        # 计算总时长和卡路里
        total_duration = sum(record.duration for record in records)
        total_calories = sum(record.calories for record in records)
        
        return {
            "success": True,
            "data": {
                "totalRecords": total_records,
                "daysCount": unique_dates,
                "totalDuration": total_duration,
                "avgCalories": round(total_calories / total_records, 1),
                "totalCalories": total_calories
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/users")
async def create_user(user_data: dict, db: Session = Depends(get_db)):
    try:
        user = User(
            nickname=user_data.get("nickname"),
            avatar_url=user_data.get("avatar_url")
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"success": True, "data": {"id": user.id}}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}

@router.get("/users/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}
        return {
            "success": True,
            "data": {
                "id": user.id,
                "nickname": user.nickname,
                "avatar_url": user.avatar_url
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/user-goals")
async def get_user_goals(request: Request, db: Session = Depends(get_db)):
    try:
        # 获取用户ID
        user_id = get_current_user_id(request)
        if not user_id:
            api_logger.warning("未找到用户ID，返回默认值")
            return {
                "success": True,
                "data": {
                    "nutritionGoals": {
                        "calories": 2000,
                        "protein": 60,
                        "carbs": 250,
                        "fat": 70
                    },
                    "exerciseGoals": {
                        "frequency": 3,
                        "duration": 30,
                        "calories": 300
                    }
                }
            }
        
        # 查询用户目标
        user_goal = db.query(UserGoal).filter(UserGoal.user_id == user_id).first()
        
        # 如果没有找到，返回默认值
        if not user_goal:
            return {
                "success": True,
                "data": {
                    "nutritionGoals": {
                        "calories": 2000,
                        "protein": 60,
                        "carbs": 250,
                        "fat": 70
                    },
                    "exerciseGoals": {
                        "frequency": 3,
                        "duration": 30,
                        "calories": 300
                    }
                }
            }
        
        # 返回用户目标
        return {
            "success": True,
            "data": {
                "nutritionGoals": {
                    "calories": user_goal.calories,
                    "protein": user_goal.protein,
                    "carbs": user_goal.carbs,
                    "fat": user_goal.fat
                },
                "exerciseGoals": {
                    "frequency": user_goal.exercise_frequency,
                    "duration": user_goal.exercise_duration,
                    "calories": user_goal.exercise_calories
                }
            }
        }
    except Exception as e:
        api_logger.error(f"获取用户目标失败: {str(e)}")
        return {"success": False, "error": f"获取用户目标失败: {str(e)}"}

@router.post("/user-goals")
async def update_user_goals(request: Request, data: dict, db: Session = Depends(get_db)):
    try:
        # 获取用户ID
        user_id = get_current_user_id(request)
        if not user_id:
            api_logger.error("更新目标失败：未找到用户ID")
            return {"success": False, "error": "未找到用户ID"}
        
        # 获取请求数据
        nutrition_goals = data.get("nutritionGoals", {})
        exercise_goals = data.get("exerciseGoals", {})
        
        if not nutrition_goals or not exercise_goals:
            api_logger.error("更新目标失败：请求数据不完整")
            return {"success": False, "error": "请求数据不完整"}
        
        # 查询用户目标
        user_goal = db.query(UserGoal).filter(UserGoal.user_id == user_id).first()
        
        try:
            # 如果没有找到，创建新的
            if not user_goal:
                user_goal = UserGoal(user_id=user_id)
                db.add(user_goal)
            
            # 更新营养目标
            user_goal.calories = float(nutrition_goals.get("calories", 0))
            user_goal.protein = float(nutrition_goals.get("protein", 0))
            user_goal.carbs = float(nutrition_goals.get("carbs", 0))
            user_goal.fat = float(nutrition_goals.get("fat", 0))
            
            # 更新运动目标
            user_goal.exercise_frequency = int(exercise_goals.get("frequency", 0))
            user_goal.exercise_duration = int(exercise_goals.get("duration", 0))
            user_goal.exercise_calories = float(exercise_goals.get("calories", 0))
            
            # 保存更改
            db.commit()
            
            api_logger.info(f"用户 {user_id} 目标更新成功")
            return {"success": True, "message": "目标更新成功"}
            
        except (ValueError, TypeError) as e:
            db.rollback()
            api_logger.error(f"数据转换失败: {str(e)}")
            return {"success": False, "error": "数据格式错误"}
            
    except Exception as e:
        db.rollback()
        api_logger.error(f"更新用户目标失败: {str(e)}")
        return {"success": False, "error": "更新用户目标失败"}

@router.post("/login")
async def login(data: dict, db: Session = Depends(get_db)):
    print("开始登陆...")
    try:
        code = data.get("code")
        if not code:
            api_logger.error("登录请求缺少code参数")
            return {"success": False, "error": "Missing code"}

        api_logger.info(f"开始处理登录请求，code: {code}")
        
        # 从微信服务器获取session信息
        wx_session = await get_wx_session(code)
        if not wx_session:
            api_logger.error("获取微信session失败")
            return {"success": False, "error": "Failed to get session from WeChat"}

        openid = wx_session["openid"]
        session_key = wx_session["session_key"]

        api_logger.info(f"登录请求:openid: {openid}")
        api_logger.info(f"登录请求:session_key: {session_key}")
        # 查找或创建用户
        user = db.query(User).filter(User.openid == openid).first()
        new_user_created = False
        if not user:
            user = User(openid=openid)
            db.add(user)
            db.commit()
            db.refresh(user)
            new_user_created = True
            api_logger.info(f"新用户创建成功，ID: {user.id}")
        

        api_logger.info(f"查找或创建用户成功:user: {user.nickname}")
        # 如果是新用户，为其创建默认的用户目标
        if new_user_created:
            try:
                user_goal = UserGoal(
                    user_id=user.id,
                    # 默认营养目标
                    calories=2000.0,
                    protein=60.0,
                    carbs=250.0,
                    fat=70.0,
                    # 默认运动目标
                    exercise_frequency=3,
                    exercise_duration=30,
                    exercise_calories=300.0
                )
                db.add(user_goal)
                db.commit()
                api_logger.info(f"为用户 {user.id} 创建了默认目标设置")
            except Exception as e:
                api_logger.error(f"创建默认用户目标失败: {str(e)}")
                # 继续执行，不中断登录流程
        # 生成token
        token = create_token(user.id, session_key)

        return {
            "success": True,
            "data": {
                "token": token,
                "userId": user.id
            }
        }
    except Exception as e:
        api_logger.exception(f"登录失败: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/validate-token")
async def validate_token(request: Request):
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return {"success": False}
        
        token = auth_header.split(" ")[1]
        payload = verify_token(token)
        if not payload:
            return {"success": False}
            
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/health-check")
async def health_check():
    return {"status": "ok"}

# 添加获取用户API使用情况的接口
@router.get("/user/ai-api-status")
async def get_ai_api_status(db: Session = Depends(get_db)):
    try:
        # 使用测试用户
        user = db.query(User).first()
        if not user:
            return {
                "data": {
                    "success": False,
                    "error": "用户不存在"
                }
            }
        
        return {
            "success": True,
            "data": {
                "success": True,
                "used_calls": user.ai_api_calls,
                "max_calls": user.max_ai_api_calls,
                "remaining_calls": user.max_ai_api_calls - user.ai_api_calls
            }
        }
    except Exception as e:
        api_logger.error(f"获取API使用状态失败: {str(e)}")
        return {
            "data": {
                "success": False,
                "error": "获取API使用状态失败"
            }
        }
# 处理根路径请求
@router.get("/")
def read_root():
    return {"message": "Hello, World!"}

# 处理健康检查请求
@router.get("/__engine/1/ping")
def health_check():
    return {"status": "ok"}