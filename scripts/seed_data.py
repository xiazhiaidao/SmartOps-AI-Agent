"""生成示例数据：订单 CSV + 设备故障 CSV + 知识库文档，并自动完成 RAG 入库。

用法：python scripts/seed_data.py
"""
import random
import shutil
import sys
from pathlib import Path

# Windows 控制台默认 GBK，强制 UTF-8 避免中文/符号打印报错
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import settings  # noqa: E402
from app.knowledge import get_knowledge_base  # noqa: E402

random.seed(42)

ORDERS_CSV = [
    ("智能家居", "智能门锁 X9"),
    ("智能家居", "智能摄像头 C6"),
    ("智能家居", "智能音箱 M1"),
    ("生活电器", "破壁榨汁机"),
    ("生活电器", "空气净化器 P3"),
    ("生活电器", "扫地机器人 R8"),
    ("数码配件", "无线充电板"),
    ("数码配件", "蓝牙耳机 Pro"),
    ("服饰", "轻薄羽绒服"),
    ("服饰", "运动跑鞋"),
]
CATEGORY_PRICE = {
    "智能家居": (299, 1299),
    "生活电器": (199, 2699),
    "数码配件": (99, 599),
    "服饰": (129, 899),
}
STATUS = ["已完成", "已完成", "已完成", "已完成", "已完成", "已完成", "待发货", "待发货", "退款中", "售后中", "售后中"]
REGIONS = ["华东", "华南", "华北", "华中", "西南", "西北", "东北"]
CHANNELS = ["天猫旗舰店", "京东自营", "抖音小店", "官网商城"]

FAULT_CODES = {
    "E01": "连接超时",
    "E02": "传感器异常",
    "E03": "电池电量低",
    "E04": "固件升级失败",
    "E05": "电机过载保护",
}
DEVICE_TYPES = ["智能插座", "扫地机器人", "空气净化器", "智能门锁", "智能摄像头"]
DEVICE_STATUS = ["在线", "离线", "待维修", "维修中"]


def gen_orders(n: int = 300) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        category, product = random.choice(ORDERS_CSV)
        lo, hi = CATEGORY_PRICE[category]
        price = random.randint(lo, hi)
        quantity = random.choices([1, 1, 1, 2, 3], weights=[50, 25, 15, 7, 3])[0]
        month = random.randint(1, 7)
        day = random.randint(1, 28)
        rows.append({
            "order_id": f"ORD-2026-{i:05d}",
            "product": product,
            "category": category,
            "price": price,
            "quantity": quantity,
            "status": random.choice(STATUS),
            "order_date": f"2026-{month:02d}-{day:02d}",
            "region": random.choice(REGIONS),
            "channel": random.choice(CHANNELS),
        })
    df = pd.DataFrame(rows)
    df.to_csv(settings.orders_csv, index=False, encoding="utf-8-sig")
    return df


def gen_devices(n: int = 90) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        device_type = random.choice(DEVICE_TYPES)
        fault_code = random.choices(list(FAULT_CODES), weights=[35, 25, 15, 10, 15])[0]
        month = random.randint(1, 7)
        day = random.randint(1, 28)
        rows.append({
            "device_id": f"DEV-{1000 + i}",
            "device_type": device_type,
            "status": random.choices(DEVICE_STATUS, weights=[60, 20, 15, 5])[0],
            "fault_code": fault_code,
            "fault_desc": FAULT_CODES[fault_code],
            "region": random.choice(REGIONS),
            "report_date": f"2026-{month:02d}-{day:02d}",
        })
    df = pd.DataFrame(rows)
    df.to_csv(settings.devices_csv, index=False, encoding="utf-8-sig")
    return df


KNOWLEDGE_DOCS = {
    "售后政策.txt": """SmartOps 电商售后政策（2026 版）

一、七天无理由退换
1. 用户自签收之日起 7 天内，商品未拆封、不影响二次销售，可申请无理由退货。
2. 退货需保留商品外包装及全部配件、赠品，运费由买家承担（质量问题除外）。

二、质量问题退换
1. 商品自签收之日起 15 天内出现非人为质量问题（如无法开机、运行异响、功能缺失），可免费换新。
2. 换新流程：联系在线客服 → 提交故障视频/照片 → 审核通过后寄回 → 3 个工作日内发出新品。

三、保修政策
1. 智能家居类商品整机保修 1 年，核心部件（电机、主板）保修 2 年。
2. 生活电器类商品整机保修 2 年。
3. 数码配件类商品保修 6 个月。
4. 保修期内非人为故障，维修免费；人为损坏（进水、摔落、私自拆机）不在保修范围。

四、维修时效
1. 保修期内收到返修件后 7 个工作日内完成维修并寄回。
2. 维修超过 15 天仍未完成，可申请换新或退款。

五、退款时效
1. 审核通过后，退款将在 1-3 个工作日内原路退回。""",
    "破壁榨汁机说明书.txt": """破壁榨汁机使用说明（型号 JS-2026）

一、装箱清单
主机 1 台、玻璃搅拌杯 1 个、说明书 1 份、清洁刷 1 把。

二、首次使用
1. 拆除机身保护膜，用温水清洗搅拌杯并擦干。
2. 将主机放置在平稳干燥的台面上。
3. 空杯试运行 30 秒，确认无异常噪音。

三、基本操作
1. 放入食材，注意总量不要超过杯身「MAX」刻度线。
2. 盖上杯盖并旋转到位，听到「咔哒」声表示锁定。
3. 接入电源，按下「开始」键；可按「+/-」调节档位（1-8 档）。
4. 结束后先断电，再逆时针旋转解锁杯盖。

四、常见故障处理
1. 无法开机：检查是否接入电源、杯盖是否旋紧到位；若仍无法开机，请检查底座与杯体接触是否清洁。
2. 运转时有明显异响：多为食材过硬或过量，请切块后重新启动。
3. 漏水：检查密封圈是否安装到位或老化，必要时更换密封圈。
4. 机器自动停止：属于电机过载保护，待 10 分钟冷却后重新启动。

五、保养与清洁
1. 每次使用后，加入清水点动清洗 10 秒。
2. 严禁整机浸入水中清洗，可用湿布擦拭底座。
3. 长时间不用时，请拔掉电源并放置在干燥处。""",
    "智能门锁使用手册.txt": """智能门锁使用手册（型号 L9-Pro）

一、装箱清单
前面板、后面板、锁体、导向片、电池（4 节 5 号）、机械钥匙 2 把、安装说明书。

二、安装与初始化
1. 安装需使用随附螺丝，按照开孔图固定锁体与面板。
2. 装入 4 节电池，面板点亮即通电。
3. 首次使用按提示录入管理员指纹（最多 5 枚）。

三、开锁方式
1. 指纹开锁：将指纹手指轻触传感器，1 秒内识别成功。
2. 密码开锁：输入 6 位数字密码后按「#」确认。
3. 机械钥匙开锁：紧急情况下从下方钥匙孔插入旋转。
4. 手机远程：配合网关可远程查看开锁记录（需选购网关）。

四、电池与低电量
1. 电量低于 20% 时每次开锁会语音提示「电量不足」。
2. 电量耗尽前请尽快更换电池；完全没电可用 USB 应急供电（前面板下方接口）。

五、常见故障处理
1. 指纹识别失败：请保持手指干燥清洁，或重新录入指纹。
2. 密码无法输入：检查是否误触锁定（连续错误 5 次会锁定 3 分钟）。
3. 门锁报警声长鸣：多为电池电量过低或门未关严，请更换电池或重新关门。
4. 锁体卡死：切勿暴力拽拉，用机械钥匙开锁后联系售后。""",
}


def gen_knowledge() -> None:
    settings.knowledge_dir.mkdir(parents=True, exist_ok=True)
    for name, content in KNOWLEDGE_DOCS.items():
        (settings.knowledge_dir / name).write_text(content, encoding="utf-8")


def main() -> None:
    print("[seed] 生成订单数据...")
    orders = gen_orders()
    print(f"        订单 {len(orders)} 条 → {settings.orders_csv}")

    print("[seed] 生设备故障数据...")
    devices = gen_devices()
    print(f"        设备故障 {len(devices)} 条 → {settings.devices_csv}")

    print("[seed] 生成知识库文档...")
    gen_knowledge()

    # 清空旧向量索引，保证脚本可重复运行不产生重复块
    index_dir = Path(settings.vector_index_dir)
    if index_dir.exists():
        shutil.rmtree(index_dir)

    print("[seed] 向量化并写入知识库（首次运行会加载本地 BGE 模型，约 10-30 秒）...")
    kb = get_knowledge_base()
    result = kb.ingest_knowledge_dir(settings.knowledge_dir)
    for name, chunks in result.items():
        print(f"        {name}: {chunks} 块")

    print("[seed] 完成 ✔")


if __name__ == "__main__":
    main()
