from .models import ExerciseMET, IntensityLevel
from sqlalchemy.orm import Session

def init_met_data(db: Session):
    exercise_mets = [
        # 低强度活动 (MET 1-3)
        ExerciseMET(
            code="SIT",
            name="静坐",
            intensity=IntensityLevel.LOW,
            met_min=1.0,
            met_max=1.0,
            description="静坐活动，如看电视、办公"
        ),
        ExerciseMET(
            code="STAND",
            name="站立",
            intensity=IntensityLevel.LOW,
            met_min=1.3,
            met_max=1.3,
            description="站立状态"
        ),
        ExerciseMET(
            code="WALK_SLOW",
            name="慢走",
            intensity=IntensityLevel.LOW,
            met_min=2.0,
            met_max=2.0,
            description="慢走（2.7 km/h）"
        ),
        ExerciseMET(
            code="HOUSEWORK",
            name="轻度家务",
            intensity=IntensityLevel.LOW,
            met_min=2.0,
            met_max=2.5,
            description="轻松家务，如洗碗、整理"
        ),
        
        # 中等强度活动 (MET 3-6)
        ExerciseMET(
            code="WALK_FAST",
            name="快走",
            intensity=IntensityLevel.MEDIUM,
            met_min=3.5,
            met_max=3.5,
            description="快走（5.6 km/h）"
        ),
        ExerciseMET(
            code="BIKE_LEISURE",
            name="休闲骑行",
            intensity=IntensityLevel.MEDIUM,
            met_min=4.0,
            met_max=4.0,
            description="骑自行车（休闲，<16 km/h）"
        ),
        ExerciseMET(
            code="YOGA",
            name="瑜伽",
            intensity=IntensityLevel.MEDIUM,
            met_min=3.0,
            met_max=4.0,
            description="哈他瑜伽"
        ),
        ExerciseMET(
            code="DANCE",
            name="跳舞",
            intensity=IntensityLevel.MEDIUM,
            met_min=4.0,
            met_max=5.0,
            description="社交舞"
        ),
        ExerciseMET(
            code="GOLF",
            name="高尔夫",
            intensity=IntensityLevel.MEDIUM,
            met_min=4.3,
            met_max=4.3,
            description="步行，带球杆"
        ),
        ExerciseMET(
            code="SWIM_LIGHT",
            name="轻度游泳",
            intensity=IntensityLevel.MEDIUM,
            met_min=4.5,
            met_max=5.0,
            description="轻松游泳"
        ),
        
        # 高强度活动 (MET 6-9)
        ExerciseMET(
            code="JOG",
            name="慢跑",
            intensity=IntensityLevel.HIGH,
            met_min=7.0,
            met_max=7.0,
            description="慢跑（7 km/h）"
        ),
        ExerciseMET(
            code="BIKE_MEDIUM",
            name="中速骑行",
            intensity=IntensityLevel.HIGH,
            met_min=6.0,
            met_max=8.0,
            description="骑自行车（中等，16-19 km/h）"
        ),
        ExerciseMET(
            code="BASKETBALL_CASUAL",
            name="休闲篮球",
            intensity=IntensityLevel.HIGH,
            met_min=6.5,
            met_max=7.5,
            description="篮球（非比赛）"
        ),
        ExerciseMET(
            code="TENNIS_DOUBLES",
            name="网球双打",
            intensity=IntensityLevel.HIGH,
            met_min=6.0,
            met_max=7.0,
            description="网球双打"
        ),
        ExerciseMET(
            code="JUMP_ROPE_SLOW",
            name="慢速跳绳",
            intensity=IntensityLevel.HIGH,
            met_min=8.0,
            met_max=8.0,
            description="跳绳（慢速）"
        ),
        ExerciseMET(
            code="SWIM_MEDIUM",
            name="中速游泳",
            intensity=IntensityLevel.HIGH,
            met_min=7.0,
            met_max=8.0,
            description="游泳（中等强度）"
        ),
        
        # 极高强度活动 (MET >9)
        ExerciseMET(
            code="RUN",
            name="跑步",
            intensity=IntensityLevel.VERY_HIGH,
            met_min=9.8,
            met_max=9.8,
            description="跑步（9.7 km/h）"
        ),
        ExerciseMET(
            code="BIKE_FAST",
            name="快速骑行",
            intensity=IntensityLevel.VERY_HIGH,
            met_min=10.0,
            met_max=12.0,
            description="骑自行车（快速，>20 km/h）"
        ),
        ExerciseMET(
            code="JUMP_ROPE_FAST",
            name="快速跳绳",
            intensity=IntensityLevel.VERY_HIGH,
            met_min=12.0,
            met_max=12.0,
            description="跳绳（快速）"
        ),
        ExerciseMET(
            code="SOCCER_MATCH",
            name="足球比赛",
            intensity=IntensityLevel.VERY_HIGH,
            met_min=10.0,
            met_max=10.0,
            description="足球比赛"
        ),
        ExerciseMET(
            code="BASKETBALL_MATCH",
            name="篮球比赛",
            intensity=IntensityLevel.VERY_HIGH,
            met_min=8.0,
            met_max=12.0,
            description="篮球比赛"
        ),
        ExerciseMET(
            code="SWIM_INTENSE",
            name="高强度游泳",
            intensity=IntensityLevel.VERY_HIGH,
            met_min=10.0,
            met_max=11.0,
            description="游泳（高强度）"
        ),
        ExerciseMET(
            code="ROCK_CLIMBING",
            name="攀岩",
            intensity=IntensityLevel.VERY_HIGH,
            met_min=11.0,
            met_max=11.0,
            description="攀岩"
        ),
        
        # 其他活动
        ExerciseMET(
            code="WEIGHT_TRAINING",
            name="举重训练",
            intensity=IntensityLevel.OTHER,
            met_min=3.5,
            met_max=6.0,
            description="举重（中等强度）"
        ),
        ExerciseMET(
            code="AEROBICS",
            name="有氧操",
            intensity=IntensityLevel.OTHER,
            met_min=5.0,
            met_max=7.0,
            description="有氧操（中等强度）"
        ),
        ExerciseMET(
            code="SKIING",
            name="滑雪",
            intensity=IntensityLevel.OTHER,
            met_min=6.0,
            met_max=8.0,
            description="滑雪（下坡）"
        ),
        ExerciseMET(
            code="SKATING",
            name="滑冰",
            intensity=IntensityLevel.OTHER,
            met_min=7.0,
            met_max=9.0,
            description="滑冰"
        ),
        ExerciseMET(
            code="ROW_LEISURE",
            name="休闲划船",
            intensity=IntensityLevel.OTHER,
            met_min=3.0,
            met_max=6.0,
            description="划船（休闲）"
        ),
        ExerciseMET(
            code="ROW_RACE",
            name="竞技划船",
            intensity=IntensityLevel.OTHER,
            met_min=12.0,
            met_max=12.0,
            description="划船（比赛）"
        )
    ]
    
    for met in exercise_mets:
        db_met = db.query(ExerciseMET).filter(ExerciseMET.code == met.code).first()
        if not db_met:
            db.add(met)
    
    db.commit() 