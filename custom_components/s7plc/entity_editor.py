"""Spreadsheet-style entity editor for the S7 PLC integration."""

from __future__ import annotations

from collections.abc import Iterable
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components import panel_custom, websocket_api
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.sensor import SensorDeviceClass

try:
    from homeassistant.components.http import StaticPathConfig
except ImportError:  # pragma: no cover - compatibility with older HA releases
    StaticPathConfig = None  # type: ignore[assignment,misc]

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar

from .config_flow import ENTITY_TYPE_REGISTRY, S7PLCOptionsFlow
from .const import (
    CONF_CLIMATE_CONTROL_MODE,
    CONF_CLIMATES,
    CONF_COVERS,
    CONF_DEVICE_GROUP,
    CONF_POSITION_STATE_ADDRESS,
    CONTROL_MODE_DIRECT,
    DOMAIN,
    OPTION_KEYS,
)

PANEL_URL_PATH = "s7plc-editor"
PANEL_COMPONENT_NAME = "s7plc-entity-editor"
PANEL_STATIC_URL = "/s7plc_static/entity-editor.js"
PANEL_ASSET_VERSION = "1"

WS_LIST = "s7plc/entity_editor/list"
WS_GET = "s7plc/entity_editor/get"
WS_SAVE = "s7plc/entity_editor/save"

_EDITOR_SETUP_MARKER = "_entity_editor_registered"

_OPTION_PREFIXES: dict[str, str] = {
    "sensors": "s",
    "binary_sensors": "bs",
    "switches": "sw",
    "buttons": "bt",
    "lights": "lt",
    "numbers": "nm",
    "texts": "tx",
    "entity_sync": "wr",
}

_DEVICE_CLASS_ENUMS = {
    "s": SensorDeviceClass,
    "bs": BinarySensorDeviceClass,
    "nm": NumberDeviceClass,
    "cv": CoverDeviceClass,
    "cvp": CoverDeviceClass,
}


def _entry_for_editor(hass: HomeAssistant, entry_id: str) -> ConfigEntry | None:
    """Return an S7 PLC entry or None when the id is invalid."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or getattr(entry, "domain", DOMAIN) != DOMAIN:
        return None
    return entry


def _prefix_for_item(option_key: str, item: dict[str, Any]) -> str:
    """Return the editor row prefix for an options item."""
    if option_key == CONF_COVERS:
        return "cvp" if CONF_POSITION_STATE_ADDRESS in item else "cv"
    if option_key == CONF_CLIMATES:
        return (
            "cl_d"
            if item.get(CONF_CLIMATE_CONTROL_MODE) == CONTROL_MODE_DIRECT
            else "cl_s"
        )
    return _OPTION_PREFIXES[option_key]


def options_to_editor_rows(options: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert config-entry options to the row representation used by the panel."""
    rows: list[dict[str, Any]] = []
    for option_key in OPTION_KEYS:
        for item in options.get(option_key, []):
            if not isinstance(item, dict):
                continue
            rows.append(
                {
                    "prefix": _prefix_for_item(option_key, item),
                    "data": dict(item),
                }
            )
    return rows


def entity_options_revision(options: dict[str, Any]) -> str:
    """Return a stable revision of all editable options."""
    editable = {key: options.get(key, []) for key in OPTION_KEYS}
    payload = json.dumps(
        editable,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _empty_options() -> dict[str, list[dict[str, Any]]]:
    return {key: [] for key in OPTION_KEYS}


def validate_editor_rows(
    entry: ConfigEntry,
    rows: Iterable[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]] | None, list[dict[str, Any]]]:
    """Validate and normalize editor rows with the existing form builders."""
    flow = S7PLCOptionsFlow(entry)
    flow._options = _empty_options()  # noqa: SLF001 - shared canonical validation
    errors: list[dict[str, Any]] = []

    for row_index, row in enumerate(rows):
        prefix = row.get("prefix")
        data = row.get("data")
        info = ENTITY_TYPE_REGISTRY.get(prefix)

        if info is None or not isinstance(data, dict):
            errors.append(
                {
                    "row": row_index,
                    "field": "prefix",
                    "code": "invalid_entity_type",
                }
            )
            continue

        try:
            builder = getattr(flow, info.item_builder_name)
            item, item_errors = builder(dict(data), skip_idx=None)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            item = None
            item_errors = {"base": "invalid_value"}

        if item is None or item_errors:
            errors.append(
                {
                    "row": row_index,
                    "field": "base",
                    "code": item_errors.get("base", "invalid_value"),
                }
            )
            continue

        flow._copy_optional_fields(item, data, CONF_DEVICE_GROUP)  # noqa: SLF001
        flow._options[info.option_key].append(item)  # noqa: SLF001

    if errors:
        return None, errors
    return flow._options, []  # noqa: SLF001


def _device_groups(rows: Iterable[dict[str, Any]]) -> list[str]:
    groups: dict[str, str] = {}
    for row in rows:
        data = row.get("data", {})
        group = str(data.get(CONF_DEVICE_GROUP, "")).strip()
        if group:
            groups.setdefault(group.casefold(), group)
    return sorted(groups.values(), key=str.casefold)


def _area_options(hass: HomeAssistant) -> list[dict[str, str]]:
    registry = ar.async_get(hass)
    return [
        {"value": area.id, "label": area.name}
        for area in sorted(registry.async_list_areas(), key=lambda item: item.name)
    ]


def _device_class_options() -> dict[str, list[str]]:
    return {
        prefix: sorted(item.value for item in enum_class)
        for prefix, enum_class in _DEVICE_CLASS_ENUMS.items()
    }


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): WS_LIST})
@callback
def websocket_list_editors(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """List S7 PLC config entries available to the editor."""
    entries = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        entries.append(
            {
                "entry_id": entry.entry_id,
                "title": entry.title,
                "host": entry.data.get(CONF_HOST, ""),
                "entity_count": sum(
                    len(entry.options.get(key, [])) for key in OPTION_KEYS
                ),
            }
        )
    entries.sort(key=lambda item: item["title"].casefold())
    connection.send_result(msg["id"], {"entries": entries})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_GET,
        vol.Required("entry_id"): str,
    }
)
@callback
def websocket_get_editor(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return one PLC configuration for editing."""
    entry = _entry_for_editor(hass, msg["entry_id"])
    if entry is None:
        connection.send_error(msg["id"], "entry_not_found", "S7 PLC not found")
        return

    rows = options_to_editor_rows(entry.options)
    connection.send_result(
        msg["id"],
        {
            "entry": {
                "entry_id": entry.entry_id,
                "title": entry.title,
                "name": entry.data.get(CONF_NAME, entry.title),
                "host": entry.data.get(CONF_HOST, ""),
            },
            "rows": rows,
            "areas": _area_options(hass),
            "device_groups": _device_groups(rows),
            "device_classes": _device_class_options(),
            "revision": entity_options_revision(entry.options),
        },
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_SAVE,
        vol.Required("entry_id"): str,
        vol.Required("revision"): str,
        vol.Required("rows"): vol.All(
            [
                {
                    vol.Required("prefix"): str,
                    vol.Required("data"): dict,
                }
            ],
            vol.Length(max=10000),
        ),
    }
)
@websocket_api.async_response
async def websocket_save_editor(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Validate and atomically save all rows for one PLC."""
    entry = _entry_for_editor(hass, msg["entry_id"])
    if entry is None:
        connection.send_error(msg["id"], "entry_not_found", "S7 PLC not found")
        return

    current_revision = entity_options_revision(entry.options)
    if msg["revision"] != current_revision:
        connection.send_error(
            msg["id"],
            "stale_config",
            "The S7 PLC configuration changed while the editor was open",
        )
        return

    normalized, errors = validate_editor_rows(entry, msg["rows"])
    if normalized is None:
        connection.send_result(
            msg["id"],
            {"saved": False, "errors": errors, "revision": current_revision},
        )
        return

    old_editable = {key: entry.options.get(key, []) for key in OPTION_KEYS}
    if normalized == old_editable:
        connection.send_result(
            msg["id"],
            {
                "saved": True,
                "changed": False,
                "revision": current_revision,
                "rows": options_to_editor_rows(normalized),
            },
        )
        return

    new_options = dict(entry.options)
    new_options.update(normalized)
    update_result = hass.config_entries.async_update_entry(entry, options=new_options)
    if inspect.isawaitable(update_result):
        await update_result

    connection.send_result(
        msg["id"],
        {
            "saved": True,
            "changed": True,
            "revision": entity_options_revision(new_options),
            "rows": options_to_editor_rows(normalized),
        },
    )


async def async_setup_entity_editor(hass: HomeAssistant) -> None:
    """Register the editor asset, panel and WebSocket commands once."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(_EDITOR_SETUP_MARKER):
        return

    frontend_path = str(Path(__file__).parent / "frontend" / "entity-editor.js")
    if StaticPathConfig is not None and hasattr(
        hass.http, "async_register_static_paths"
    ):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(PANEL_STATIC_URL, frontend_path, False)]
        )
    else:  # pragma: no cover - compatibility with older HA releases
        hass.http.register_static_path(PANEL_STATIC_URL, frontend_path, False)

    websocket_api.async_register_command(hass, websocket_list_editors)
    websocket_api.async_register_command(hass, websocket_get_editor)
    websocket_api.async_register_command(hass, websocket_save_editor)

    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_COMPONENT_NAME,
        sidebar_title="S7 PLC Editor",
        sidebar_icon="mdi:table-edit",
        module_url=f"{PANEL_STATIC_URL}?v={PANEL_ASSET_VERSION}",
        require_admin=True,
        config={"domain": DOMAIN},
    )
    domain_data[_EDITOR_SETUP_MARKER] = True
