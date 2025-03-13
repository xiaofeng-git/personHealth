from sqlalchemy.orm import Session
from .db_base import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_test_data(db: Session):
    from .models import User, FoodRecord, ExerciseRecord  # 避免循环导入
    try:
        # 检查是否已有数据
        existing_records = db.query(FoodRecord).first()
        if existing_records:
            print("数据库中已有记录，跳过初始化测试数据")
            return
            
        # 检查是否已有测试用户
        test_user = db.query(User).filter(User.openid == "test_user").first()
        if not test_user:
            # 创建测试用户
            test_user = User(
                openid="test_user",
                ai_api_calls=0,
                max_ai_api_calls=100
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            print("测试用户创建成功")
        else:
            print("测试用户已存在")
    except Exception as e:
        print(f"初始化测试用户失败: {str(e)}")
        db.rollback()

def reset_test_user_calls(db: Session):
    try:
        test_user = db.query(User).filter(User.openid == "test_user").first()
        if test_user:
            test_user.ai_api_calls = 0
            db.commit()
            print("测试用户调用次数已重置")
    except Exception as e:
        print(f"重置调用次数失败: {str(e)}")
        db.rollback() 