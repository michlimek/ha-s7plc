from __future__ import annotations

import asyncio

from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.s7plc.const import (
    CONF_ADDRESS,
    CONF_CLIMATE_CONTROL_MODE,
    CONF_CLIMATES,
    CONF_COVERS,
    CONF_DEVICE_GROUP,
    CONF_NUMBERS,
    CONF_POSITION_STATE_ADDRESS,
    CONF_SENSORS,
    CONTROL_MODE_DIRECT,
    DOMAIN,
)
from custom_components.s7plc.entity_editor import (
    WS_IMPORT,
    WS_SAVE,
    async_setup_entity_editor,
    entity_options_revision,
    merge_import_payload,
    options_to_editor_rows,
    validate_editor_rows,
    websocket_import_editor,
    websocket_save_editor,
)


def _entry(options=None) -> ConfigEntry:
    return ConfigEntry(
        data={"host": "192.0.2.10", "name": "PLC"},
        options=options or {},
        entry_id="plc-1",
        title="PLC",
        domain=DOMAIN,
    )


def test_options_to_editor_rows_distinguishes_shared_option_types():
    rows = options_to_editor_rows(
        {
            CONF_COVERS: [
                {"open_command_address": "DB1,X0.0"},
                {CONF_POSITION_STATE_ADDRESS: "DB1,B2"},
            ],
            CONF_CLIMATES: [
                {
                    CONF_CLIMATE_CONTROL_MODE: CONTROL_MODE_DIRECT,
                    "current_temperature_address": "DB1,REAL4",
                },
                {
                    CONF_CLIMATE_CONTROL_MODE: "setpoint",
                    "current_temperature_address": "DB1,REAL8",
                },
            ],
        }
    )

    assert [row["prefix"] for row in rows] == ["cv", "cvp", "cl_d", "cl_s"]


def test_validate_editor_rows_reuses_form_validation_and_device_groups():
    entry = _entry()
    normalized, errors = validate_editor_rows(
        entry,
        [
            {
                "prefix": "s",
                "data": {
                    CONF_ADDRESS: " DB1,W0 ",
                    "name": "Temperature",
                    CONF_DEVICE_GROUP: "Boiler room",
                },
            }
        ],
    )

    assert errors == []
    assert normalized is not None
    assert normalized[CONF_SENSORS] == [
        {
            CONF_ADDRESS: "DB1,W0",
            "name": "Temperature",
            CONF_DEVICE_GROUP: "Boiler room",
        }
    ]


def test_validate_editor_rows_reports_duplicate_addresses():
    entry = _entry()
    normalized, errors = validate_editor_rows(
        entry,
        [
            {"prefix": "s", "data": {CONF_ADDRESS: "DB1,W0"}},
            {"prefix": "s", "data": {CONF_ADDRESS: "db1,w0"}},
        ],
    )

    assert normalized is None
    assert errors == [{"row": 1, "field": "base", "code": "duplicate_entry"}]


def test_merge_import_payload_adds_without_replacing_existing_entities():
    entry = _entry(
        {
            CONF_SENSORS: [{CONF_ADDRESS: "DB1,W0", "name": "Existing"}],
        }
    )

    rows, errors, stats = merge_import_payload(
        entry,
        {
            CONF_NUMBERS: [
                {
                    CONF_ADDRESS: "DB13,R208",
                    "command_address": "DB13,R208",
                    "name": "Pressure setpoint",
                    "device_group": "Wentylacja suszarki",
                    "availability_address": "DB30,X234.5",
                }
            ]
        },
    )

    assert errors == []
    assert stats == {"added": 1, "skipped": 0}
    assert rows is not None
    assert any(
        row["prefix"] == "s" and row["data"][CONF_ADDRESS] == "DB1,W0"
        for row in rows
    )
    imported = next(row for row in rows if row["prefix"] == "nm")
    assert imported["data"][CONF_ADDRESS] == "DB13,R208"
    assert imported["data"]["device_group"] == "Wentylacja suszarki"
    assert imported["data"]["availability_address"] == "DB30,X234.5"


def test_merge_import_payload_skips_existing_duplicate_without_changing_it():
    entry = _entry(
        {
            CONF_NUMBERS: [
                {
                    CONF_ADDRESS: "DB13,R208",
                    "command_address": "DB13,R208",
                    "name": "Existing name",
                }
            ]
        }
    )

    rows, errors, stats = merge_import_payload(
        entry,
        {
            CONF_NUMBERS: [
                {
                    CONF_ADDRESS: "db13,r208",
                    "command_address": "DB13,R208",
                    "name": "Imported replacement",
                },
                {
                    CONF_ADDRESS: "DB13,R212",
                    "command_address": "DB13,R212",
                    "name": "New item",
                },
            ]
        },
    )

    assert errors == []
    assert stats == {"added": 1, "skipped": 1}
    assert rows is not None
    number_rows = [row for row in rows if row["prefix"] == "nm"]
    assert [row["data"][CONF_ADDRESS] for row in number_rows] == [
        "DB13,R208",
        "DB13,R212",
    ]
    assert number_rows[0]["data"]["name"] == "Existing name"


def test_websocket_import_prepares_rows_without_mutating_entry():
    entry = _entry({CONF_SENSORS: [{CONF_ADDRESS: "DB1,W0"}]})
    hass = HomeAssistant()
    hass.config_entries._entries.append(entry)
    connection = ActiveConnection()
    revision = entity_options_revision(entry.options)

    websocket_import_editor(
        hass,
        connection,
        {
            "id": 6,
            "type": WS_IMPORT,
            "entry_id": entry.entry_id,
            "revision": revision,
            "payload": {
                CONF_NUMBERS: [
                    {
                        CONF_ADDRESS: "DB13,R208",
                        "command_address": "DB13,R208",
                    }
                ]
            },
        },
    )

    result = connection.results[0][1]
    assert result["imported"] is True
    assert result["added"] == 1
    assert result["skipped"] == 0
    assert entry.options == {CONF_SENSORS: [{CONF_ADDRESS: "DB1,W0"}]}
    assert any(row["prefix"] == "nm" for row in result["rows"])


def test_websocket_save_rejects_stale_revision():
    entry = _entry({CONF_SENSORS: [{CONF_ADDRESS: "DB1,W0"}]})
    hass = HomeAssistant()
    hass.config_entries._entries.append(entry)
    connection = ActiveConnection()

    asyncio.run(
        websocket_save_editor(
            hass,
            connection,
            {
                "id": 7,
                "type": WS_SAVE,
                "entry_id": entry.entry_id,
                "revision": "old",
                "rows": [],
            },
        )
    )

    assert connection.errors[0][1] == "stale_config"
    assert entry.options[CONF_SENSORS] == [{CONF_ADDRESS: "DB1,W0"}]


def test_websocket_save_updates_all_rows_atomically():
    entry = _entry({CONF_SENSORS: [{CONF_ADDRESS: "DB1,W0"}]})
    hass = HomeAssistant()
    hass.config_entries._entries.append(entry)
    connection = ActiveConnection()
    revision = entity_options_revision(entry.options)

    asyncio.run(
        websocket_save_editor(
            hass,
            connection,
            {
                "id": 8,
                "type": WS_SAVE,
                "entry_id": entry.entry_id,
                "revision": revision,
                "rows": [
                    {
                        "prefix": "s",
                        "data": {CONF_ADDRESS: "DB1,W2", "name": "Pressure"},
                    }
                ],
            },
        )
    )

    result = connection.results[0][1]
    assert result["saved"] is True
    assert result["changed"] is True
    assert entry.options[CONF_SENSORS] == [
        {CONF_ADDRESS: "DB1,W2", "name": "Pressure"}
    ]


def test_editor_setup_registers_panel_static_asset_and_commands_once():
    hass = HomeAssistant()

    asyncio.run(async_setup_entity_editor(hass))
    asyncio.run(async_setup_entity_editor(hass))

    assert len(hass.http.static_paths) == 1
    assert len(hass.data["_test_ws_commands"]) == 4
    assert len(hass.data["_test_panels"]) == 1
