"""订单 / 设备查询 Agent 测试。"""
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from app.agents import lookup_agent
from app.agents.lookup_agent import LookupAgent


def _write_temp_csv(tmp_path: Path, name: str, df: pd.DataFrame) -> Path:
    path = tmp_path / name
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def test_lookup_order(monkeypatch, tmp_path):
    orders = pd.DataFrame([{
        "order_id": "ORD-2026-00123",
        "product": "破壁榨汁机",
        "category": "生活电器",
        "price": 599,
        "quantity": 1,
        "order_date": "2026-03-12",
        "region": "华东",
        "channel": "天猫旗舰店",
        "status": "已完成",
    }])
    orders_path = _write_temp_csv(tmp_path, "orders.csv", orders)
    monkeypatch.setattr(
        lookup_agent,
        "settings",
        SimpleNamespace(orders_csv=orders_path, devices_csv=tmp_path / "devices.csv"),
    )

    result = LookupAgent().handle("查询订单 ORD-2026-00123 到哪了")
    assert result.type == "text"
    assert "ORD-2026-00123" in result.text
    assert "破壁榨汁机" in result.text


def test_lookup_device(monkeypatch, tmp_path):
    devices = pd.DataFrame([{
        "device_id": "DEV-1001",
        "device_type": "智能门锁",
        "status": "在线",
        "fault_code": "E01",
        "fault_desc": "连接超时",
        "region": "华南",
        "report_date": "2026-02-01",
    }])
    devices_path = _write_temp_csv(tmp_path, "devices.csv", devices)
    monkeypatch.setattr(
        lookup_agent,
        "settings",
        SimpleNamespace(orders_csv=tmp_path / "orders.csv", devices_csv=devices_path),
    )

    result = LookupAgent().handle("设备 DEV-1001 现在是什么状态？")
    assert result.type == "text"
    assert "DEV-1001" in result.text
    assert "在线" in result.text


def test_lookup_missing_id(monkeypatch, tmp_path):
    orders = pd.DataFrame([{
        "order_id": "ORD-2026-00123",
        "product": "破壁榨汁机",
        "category": "生活电器",
        "price": 599,
        "quantity": 1,
        "order_date": "2026-03-12",
        "region": "华东",
        "channel": "天猫旗舰店",
        "status": "已完成",
    }])
    orders_path = _write_temp_csv(tmp_path, "orders.csv", orders)
    monkeypatch.setattr(
        lookup_agent,
        "settings",
        SimpleNamespace(orders_csv=orders_path, devices_csv=tmp_path / "devices.csv"),
    )

    result = LookupAgent().handle("查询订单 ORD-2026-99999")
    assert result.type == "text"
    assert "没有找到" in result.text