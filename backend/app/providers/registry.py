from ..models import Plant
from .base import DataProvider, ManualReadings
from .demo import DemoDataProvider
from .iot import IoTDataProvider

_demo = None
_iot = IoTDataProvider()
_manual = ManualReadings()


def demo_provider() -> DemoDataProvider:
    global _demo
    if _demo is None:
        _demo = DemoDataProvider()
    return _demo


def provider_for(plant: Plant) -> DataProvider:
    """Основной источник растения: demo или iot."""
    return demo_provider() if plant.data_source == "demo" else _iot


def iot_provider() -> IoTDataProvider:
    return _iot


def manual_provider() -> ManualReadings:
    return _manual
