"""Tests for number.py availability support."""

from custom_components.s7plc.number import S7Number


def test_number_respects_availability_address(mock_coordinator):
    topic = "number:DB13,R208"
    availability_topic = "availability:DB30,X234.5"
    mock_coordinator.data = {
        topic: 80.0,
        availability_topic: True,
    }

    entity = S7Number(
        mock_coordinator,
        "Setpoint",
        "number-setpoint",
        {
            "identifiers": {("s7plc", "test-device")},
            "name": "Test Device",
            "manufacturer": "Siemens",
        },
        topic,
        "DB13,R208",
        "DB13,R208",
        1.0,
        500.0,
        0.1,
        availability_topic=availability_topic,
        availability_address="DB30,X234.5",
        availability_invert=False,
    )

    assert entity.available is True
    assert entity.extra_state_attributes["s7_availability_address"] == "DB30,X234.5"

    mock_coordinator.data[availability_topic] = False
    assert entity.available is False
