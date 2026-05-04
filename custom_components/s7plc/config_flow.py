from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers import selector

from .address import get_numeric_limits, parse_tag
from .const import (
    CONF_ADDRESS,
    CONF_AREA,
    CONF_AVAILABILITY_ADDRESS,
    CONF_AVAILABILITY_INVERT,
    CONF_BACKOFF_INITIAL,
    CONF_BACKOFF_MAX,
    CONF_BINARY_SENSORS,
    CONF_BRIGHTNESS_COMMAND_ADDRESS,
    CONF_BRIGHTNESS_SCALE,
    CONF_BRIGHTNESS_STATE_ADDRESS,
    CONF_BUTTON_PULSE,
    CONF_BUTTONS,
    CONF_CLIMATE_CONTROL_MODE,
    CONF_CLIMATES,
    CONF_CLOSE_COMMAND_ADDRESS,
    CONF_CLOSING_STATE_ADDRESS,
    CONF_COMMAND_ADDRESS,
    CONF_CONNECTION_TYPE,
    CONF_COOLING_ACTION_ADDRESS,
    CONF_COOLING_OUTPUT_ADDRESS,
    CONF_COVERS,
    CONF_CURRENT_TEMPERATURE_ADDRESS,
    CONF_DEVICE_CLASS,
    CONF_ENABLE_METRICS,
    CONF_ENABLE_WRITE_BATCHING,
    CONF_ENTITY_SYNC,
    CONF_HEATING_ACTION_ADDRESS,
    CONF_HEATING_OUTPUT_ADDRESS,
    CONF_HVAC_STATUS_ADDRESS,
    CONF_INVERT_POSITION,
    CONF_INVERT_STATE,
    CONF_LIGHTS,
    CONF_LOCAL_TSAP,
    CONF_MAX_RETRIES,
    CONF_MAX_TEMP,
    CONF_MAX_VALUE,
    CONF_MIN_TEMP,
    CONF_MIN_VALUE,
    CONF_NUMBERS,
    CONF_OP_TIMEOUT,
    CONF_OPEN_COMMAND_ADDRESS,
    CONF_OPENING_STATE_ADDRESS,
    CONF_OPERATE_TIME,
    CONF_OPTIMIZE_READ,
    CONF_PATTERN,
    CONF_POSITION_COMMAND_ADDRESS,
    CONF_POSITION_STATE_ADDRESS,
    CONF_PRESET_MODE_ADDRESS,
    CONF_PULSE_COMMAND,
    CONF_PULSE_DURATION,
    CONF_PYS7_CONNECTION_TYPE,
    CONF_RACK,
    CONF_REAL_PRECISION,
    CONF_REMOTE_TSAP,
    CONF_SCALE_RAW_MAX,
    CONF_SCALE_RAW_MIN,
    CONF_SCAN_INTERVAL,
    CONF_SENSORS,
    CONF_SLOT,
    CONF_SOURCE_ENTITY,
    CONF_STATE_ADDRESS,
    CONF_STATE_CLASS,
    CONF_STEP,
    CONF_STOP_COMMAND_ADDRESS,
    CONF_STOP_PULSE_DURATION,
    CONF_SWITCHES,
    CONF_SYNC_STATE,
    CONF_TARGET_TEMPERATURE_ADDRESS,
    CONF_TEMP_STEP,
    CONF_TEXTS,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_USE_STATE_TOPICS,
    CONF_VALUE_MULTIPLIER,
    CONNECTION_TYPE_RACK_SLOT,
    CONNECTION_TYPE_TSAP,
    CONTROL_MODE_DIRECT,
    CONTROL_MODE_SETPOINT,
    DEFAULT_BACKOFF_INITIAL,
    DEFAULT_BACKOFF_MAX,
    DEFAULT_BRIGHTNESS_SCALE,
    DEFAULT_ENABLE_METRICS,
    DEFAULT_ENABLE_WRITE_BATCHING,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DEFAULT_OP_TIMEOUT,
    DEFAULT_OPERATE_TIME,
    DEFAULT_OPTIMIZE_READ,
    DEFAULT_PORT,
    DEFAULT_PULSE_DURATION,
    DEFAULT_PYS7_CONNECTION_TYPE,
    DEFAULT_RACK,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLOT,
    DEFAULT_TEMP_STEP,
    DEFAULT_USE_STATE_TOPICS,
    DOMAIN,
    OPTION_KEYS,
)
from .helpers import parse_pulse_duration

_LOGGER = logging.getLogger(__name__)

NONE_OPTION = selector.SelectOptionDict(value="__none__", label="No device class")
ADD_ENTITY_STEP_IDS: tuple[str, ...] = (
    "sensors",
    "binary_sensors",
    "switches",
    "covers_traditional",
    "covers_position",
    "buttons",
    "lights",
    "numbers",
    "texts",
    "climates_direct",
    "climates_setpoint",
    "entity_sync",
)


def _num_sel(*, min: float | None = None, max: float | None = None, step: float | str | None = None):
    cfg: dict[str, Any] = {"mode": selector.NumberSelectorMode.BOX}
    if min is not None:
        cfg["min"] = min
    if max is not None:
        cfg["max"] = max
    if step is not None:
        cfg["step"] = step
    return selector.NumberSelector(selector.NumberSelectorConfig(**cfg))


scan_interval_selector = _num_sel(min=0.1, max=3600, step=0.1)
real_precision_selector = _num_sel(min=0, max=6, step=1)
operate_time_selector = _num_sel(min=0, max=3600, step=1)
value_multiplier_selector = _num_sel(min=-1000, max=1000, step=0.05)
scale_value_selector = _num_sel(step=0.001)
pulse_duration_selector = _num_sel(min=0.1, max=60, step=0.1)
number_value_selector = _num_sel(step=0.01)
positive_number_selector = _num_sel(min=0, step=0.01)

state_class_selector = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=[
            selector.SelectOptionDict(value="none", label="none"),
            selector.SelectOptionDict(value="measurement", label="measurement"),
            selector.SelectOptionDict(value="total", label="total"),
            selector.SelectOptionDict(value="total_increasing", label="total_increasing"),
        ],
        mode=selector.SelectSelectorMode.DROPDOWN,
    )
)


def _device_selector_by_type(entity_type: str) -> selector.SelectSelector:
    enum_map = {
        CONF_BINARY_SENSORS: BinarySensorDeviceClass,
        CONF_SENSORS: SensorDeviceClass,
        CONF_NUMBERS: NumberDeviceClass,
        CONF_COVERS: CoverDeviceClass,
    }
    enum_cls = enum_map[entity_type]
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[NONE_OPTION]
            + [
                selector.SelectOptionDict(
                    value=dc.value,
                    label=dc.value.replace("_", " ").title(),
                )
                for dc in enum_cls
            ],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _strip_none_option(value: Any) -> Any:
    return None if value in (None, "", "__none__", "none") else value


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        value = value.replace(",", ".")
    return float(value)


def _to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(float(str(value).replace(",", ".")))


def _copy_optional(src: dict[str, Any], dst: dict[str, Any], key: str, cast: Callable[[Any], Any] | None = None) -> None:
    if key not in src:
        return
    value = src.get(key)
    if value in (None, "", "__none__", "none"):
        return
    dst[key] = cast(value) if cast else value


def _connection_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    connection_type = defaults.get(CONF_CONNECTION_TYPE, CONNECTION_TYPE_RACK_SLOT)
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "S7 PLC")): str,
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Optional(CONF_PORT, default=int(defaults.get(CONF_PORT, DEFAULT_PORT))): int,
            vol.Optional(CONF_CONNECTION_TYPE, default=connection_type): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=CONNECTION_TYPE_RACK_SLOT, label="Rack / Slot"),
                        selector.SelectOptionDict(value=CONNECTION_TYPE_TSAP, label="TSAP"),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_RACK, default=int(defaults.get(CONF_RACK, DEFAULT_RACK))): int,
            vol.Optional(CONF_SLOT, default=int(defaults.get(CONF_SLOT, DEFAULT_SLOT))): int,
            vol.Optional(CONF_LOCAL_TSAP, default=defaults.get(CONF_LOCAL_TSAP, "01.00")): str,
            vol.Optional(CONF_REMOTE_TSAP, default=defaults.get(CONF_REMOTE_TSAP, "01.01")): str,
            vol.Optional(CONF_PYS7_CONNECTION_TYPE, default=defaults.get(CONF_PYS7_CONNECTION_TYPE, DEFAULT_PYS7_CONNECTION_TYPE)): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value="pg", label="PG"),
                        selector.SelectOptionDict(value="op", label="OP"),
                        selector.SelectOptionDict(value="s7basic", label="S7 Basic"),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_SCAN_INTERVAL, default=float(defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))): scan_interval_selector,
            vol.Optional(CONF_OP_TIMEOUT, default=float(defaults.get(CONF_OP_TIMEOUT, DEFAULT_OP_TIMEOUT))): _num_sel(min=0.1, max=120, step=0.1),
            vol.Optional(CONF_MAX_RETRIES, default=int(defaults.get(CONF_MAX_RETRIES, DEFAULT_MAX_RETRIES))): _num_sel(min=0, max=20, step=1),
            vol.Optional(CONF_BACKOFF_INITIAL, default=float(defaults.get(CONF_BACKOFF_INITIAL, DEFAULT_BACKOFF_INITIAL))): _num_sel(min=0.1, max=60, step=0.1),
            vol.Optional(CONF_BACKOFF_MAX, default=float(defaults.get(CONF_BACKOFF_MAX, DEFAULT_BACKOFF_MAX))): _num_sel(min=0.1, max=120, step=0.1),
            vol.Optional(CONF_OPTIMIZE_READ, default=bool(defaults.get(CONF_OPTIMIZE_READ, DEFAULT_OPTIMIZE_READ))): selector.BooleanSelector(),
            vol.Optional(CONF_ENABLE_WRITE_BATCHING, default=bool(defaults.get(CONF_ENABLE_WRITE_BATCHING, DEFAULT_ENABLE_WRITE_BATCHING))): selector.BooleanSelector(),
            vol.Optional(CONF_ENABLE_METRICS, default=bool(defaults.get(CONF_ENABLE_METRICS, DEFAULT_ENABLE_METRICS))): selector.BooleanSelector(),
        }
    )


def _normalize_connection_input(user_input: dict[str, Any]) -> dict[str, Any]:
    data = dict(user_input)
    data[CONF_PORT] = int(data.get(CONF_PORT, DEFAULT_PORT))
    data[CONF_SCAN_INTERVAL] = float(data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
    data[CONF_OP_TIMEOUT] = float(data.get(CONF_OP_TIMEOUT, DEFAULT_OP_TIMEOUT))
    data[CONF_MAX_RETRIES] = int(data.get(CONF_MAX_RETRIES, DEFAULT_MAX_RETRIES))
    data[CONF_BACKOFF_INITIAL] = float(data.get(CONF_BACKOFF_INITIAL, DEFAULT_BACKOFF_INITIAL))
    data[CONF_BACKOFF_MAX] = float(data.get(CONF_BACKOFF_MAX, DEFAULT_BACKOFF_MAX))
    data[CONF_CONNECTION_TYPE] = data.get(CONF_CONNECTION_TYPE, CONNECTION_TYPE_RACK_SLOT)
    if data[CONF_CONNECTION_TYPE] == CONNECTION_TYPE_TSAP:
        data.pop(CONF_RACK, None)
        data.pop(CONF_SLOT, None)
        data[CONF_LOCAL_TSAP] = data.get(CONF_LOCAL_TSAP, "01.00")
        data[CONF_REMOTE_TSAP] = data.get(CONF_REMOTE_TSAP, "01.01")
    else:
        data.pop(CONF_LOCAL_TSAP, None)
        data.pop(CONF_REMOTE_TSAP, None)
        data[CONF_RACK] = int(data.get(CONF_RACK, DEFAULT_RACK))
        data[CONF_SLOT] = int(data.get(CONF_SLOT, DEFAULT_SLOT))
    return data


def _generate_unique_id(data: dict[str, Any]) -> str:
    host = data.get(CONF_HOST)
    if data.get(CONF_CONNECTION_TYPE) == CONNECTION_TYPE_TSAP:
        return f"{host}-tsap-{data.get(CONF_LOCAL_TSAP)}-{data.get(CONF_REMOTE_TSAP)}"
    return f"{host}-{data.get(CONF_RACK, DEFAULT_RACK)}-{data.get(CONF_SLOT, DEFAULT_SLOT)}"


@dataclass(frozen=True)
class EntityTypeInfo:
    option_key: str
    prefix: str
    add_step_id: str
    edit_step_id: str
    build_add_schema: Callable[[Any], vol.Schema]
    build_edit_schema: Callable[[Any, dict[str, Any]], vol.Schema]
    item_builder_name: str


class S7PLCConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return S7PLCOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _normalize_connection_input(user_input)
            await self.async_set_unique_id(_generate_unique_id(data))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=data.get(CONF_NAME, "S7 PLC"), data=data, options={key: [] for key in OPTION_KEYS})
        return self.async_show_form(step_id="user", data_schema=_connection_schema(), errors=errors)


class S7PLCOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry
        self._options: dict[str, list[dict[str, Any]]] = {key: list(config_entry.options.get(key, [])) for key in OPTION_KEYS}
        # Backward compatibility with older key.
        if "writers" in getattr(config_entry, "options", {}):
            self._options[CONF_ENTITY_SYNC] = list(config_entry.options.get("writers", []))
        self._action: str | None = None
        self._edit_target: tuple[str, int] | None = None
        self._last_add_input: dict[str, Any] | None = None

    def _get_area_selector(self):
        try:
            from homeassistant.helpers import area_registry as ar

            area_reg = ar.async_get(self.hass)
            options = [selector.SelectOptionDict(value="__none__", label="No area")]
            for area in sorted(area_reg.async_list_areas(), key=lambda a: a.name):
                options.append(selector.SelectOptionDict(value=area.id, label=area.name))
            return selector.SelectSelector(selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.DROPDOWN))
        except Exception:
            return selector.TextSelector()

    def _optional_field(self, key: str, item: dict[str, Any], sel):
        value = item.get(key)
        if value in (None, "", "__none__"):
            return vol.Optional(key), sel
        return vol.Optional(key, default=value), sel

    def _sanitize_address(self, value: Any) -> str | None:
        return _clean_text(value)

    def _normalized_address(self, value: Any) -> str | None:
        value = self._sanitize_address(value)
        return value.upper() if value else None

    def _has_duplicate(self, option_key: str, address: Any, *, keys: tuple[str, ...] = (CONF_ADDRESS,), skip_idx: int | None = None) -> bool:
        normalized = self._normalized_address(address)
        if not normalized:
            return False
        for idx, item in enumerate(self._options.get(option_key, [])):
            if skip_idx is not None and idx == skip_idx:
                continue
            for key in keys:
                if self._normalized_address(item.get(key)) == normalized:
                    return True
        return False

    def _finish(self):
        return self.async_create_entry(title="", data=self._options)

    def _with_suggested_values(self, schema: vol.Schema) -> vol.Schema:
        if not self._last_add_input:
            return schema
        suggested = {k: v for k, v in self._last_add_input.items() if k != "add_another"}
        self._last_add_input = None
        return self.add_suggested_values_to_schema(schema, suggested)

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        return self.async_show_menu(
            step_id="init",
            menu_options=["connection", "add", "edit", "remove", "import", "export"],
        )

    async def async_step_connection(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        data = dict(getattr(self.config_entry, "data", {}))
        if user_input is not None:
            new_data = _normalize_connection_input(user_input)
            try:
                self.hass.config_entries.async_update_entry(self.config_entry, data=new_data, title=new_data.get(CONF_NAME, "S7 PLC"))
            except Exception:
                # The test stubs and some older HA versions expose a minimal API; keep the flow usable.
                self.config_entry.data = new_data
                self.config_entry.title = new_data.get(CONF_NAME, "S7 PLC")
            return self._finish()
        return self.async_show_form(step_id="connection", data_schema=_connection_schema(data), errors=errors)

    async def async_step_add(self, user_input: dict[str, Any] | None = None):
        if user_input and user_input.get("item_type"):
            step = user_input["item_type"]
            return await getattr(self, f"async_step_{step}")()
        return self.async_show_menu(step_id="add", menu_options=list(ADD_ENTITY_STEP_IDS))

    async def async_step_edit(self, user_input: dict[str, Any] | None = None):
        choices: list[str] = []
        for prefix, info in ENTITY_TYPE_REGISTRY.items():
            for idx, item in enumerate(self._options.get(info.option_key, [])):
                label = item.get(CONF_NAME) or item.get(CONF_ADDRESS) or item.get(CONF_STATE_ADDRESS) or item.get(CONF_CURRENT_TEMPERATURE_ADDRESS) or f"{info.option_key} {idx+1}"
                choices.append(f"{prefix}:{idx}:{label}")
        if user_input and user_input.get("item"):
            prefix, idx, *_ = str(user_input["item"]).split(":", 2)
            self._edit_target = (prefix, int(idx))
            return await getattr(self, f"async_step_{ENTITY_TYPE_REGISTRY[prefix].edit_step_id}")()
        return self.async_show_form(
            step_id="edit",
            data_schema=vol.Schema({vol.Required("item"): selector.SelectSelector(selector.SelectSelectorConfig(options=choices, mode=selector.SelectSelectorMode.DROPDOWN))}),
        )

    async def async_step_remove(self, user_input: dict[str, Any] | None = None):
        choices: list[str] = []
        for prefix, info in ENTITY_TYPE_REGISTRY.items():
            for idx, item in enumerate(self._options.get(info.option_key, [])):
                label = item.get(CONF_NAME) or item.get(CONF_ADDRESS) or item.get(CONF_STATE_ADDRESS) or item.get(CONF_CURRENT_TEMPERATURE_ADDRESS) or f"{info.option_key} {idx+1}"
                choices.append(f"{prefix}:{idx}:{label}")
        if user_input and user_input.get("item"):
            prefix, idx, *_ = str(user_input["item"]).split(":", 2)
            info = ENTITY_TYPE_REGISTRY[prefix]
            del self._options[info.option_key][int(idx)]
            return self._finish()
        return self.async_show_form(
            step_id="remove",
            data_schema=vol.Schema({vol.Required("item"): selector.SelectSelector(selector.SelectSelectorConfig(options=choices, mode=selector.SelectSelectorMode.DROPDOWN))}),
        )

    def _build_export_data(self) -> str:
        return json.dumps({key: self._options.get(key, []) for key in OPTION_KEYS}, indent=2, ensure_ascii=False)

    async def async_step_export(self, user_input: dict[str, Any] | None = None):
        return self.async_show_form(
            step_id="export",
            data_schema=vol.Schema({vol.Optional("export_json", default=self._build_export_data()): selector.TextSelector(selector.TextSelectorConfig(multiline=True))}),
        )

    async def async_step_import(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                payload = json.loads(user_input.get("import_json", ""))
                if not isinstance(payload, dict):
                    raise ValueError
            except Exception:
                errors["base"] = "invalid_json"
            else:
                new_options = {key: list(payload.get(key, [])) for key in OPTION_KEYS}
                if _has_any_duplicate(new_options):
                    errors["base"] = "duplicate_addresses_in_import"
                else:
                    self._options = new_options
                    return self._finish()
        return self.async_show_form(
            step_id="import",
            data_schema=vol.Schema({vol.Required("import_json"): selector.TextSelector(selector.TextSelectorConfig(multiline=True))}),
            errors=errors,
        )

    def _store_item(self, info: EntityTypeInfo, item: dict[str, Any], add_another: bool):
        if self._edit_target and self._edit_target[0] == info.prefix:
            self._options[info.option_key][self._edit_target[1]] = item
            self._edit_target = None
            return self._finish()
        self._options.setdefault(info.option_key, []).append(item)
        if add_another:
            self._last_add_input = dict(item)
            return self.async_show_form(step_id=info.add_step_id, data_schema=self._with_suggested_values(info.build_add_schema(self)), errors={})
        return self._finish()

    def _form(self, step_id: str, schema: vol.Schema, errors: dict[str, str] | None = None):
        return self.async_show_form(step_id=step_id, data_schema=schema, errors=errors or {})


# ---------------------------------------------------------------------------
# Schema builders
# ---------------------------------------------------------------------------

def _add_schema_sensor(flow) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_NAME): selector.TextSelector(),
        vol.Optional(CONF_DEVICE_CLASS): _device_selector_by_type(CONF_SENSORS),
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): selector.TextSelector(),
        vol.Optional(CONF_VALUE_MULTIPLIER): value_multiplier_selector,
        vol.Optional(CONF_MIN_VALUE): number_value_selector,
        vol.Optional(CONF_MAX_VALUE): number_value_selector,
        vol.Optional(CONF_SCALE_RAW_MIN): scale_value_selector,
        vol.Optional(CONF_SCALE_RAW_MAX): scale_value_selector,
        vol.Optional(CONF_STATE_CLASS): state_class_selector,
        vol.Optional(CONF_REAL_PRECISION): real_precision_selector,
        vol.Optional(CONF_SCAN_INTERVAL): scan_interval_selector,
        vol.Optional(CONF_AVAILABILITY_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_AVAILABILITY_INVERT, default=False): selector.BooleanSelector(),
        vol.Optional(CONF_AREA): flow._get_area_selector(),
        vol.Optional("add_another", default=False): selector.BooleanSelector(),
    })


def _add_schema_binary_sensor(flow) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_NAME): selector.TextSelector(),
        vol.Optional(CONF_DEVICE_CLASS): _device_selector_by_type(CONF_BINARY_SENSORS),
        vol.Optional(CONF_INVERT_STATE, default=False): selector.BooleanSelector(),
        vol.Optional(CONF_SCAN_INTERVAL): scan_interval_selector,
        vol.Optional(CONF_AVAILABILITY_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_AVAILABILITY_INVERT, default=False): selector.BooleanSelector(),
        vol.Optional(CONF_AREA): flow._get_area_selector(),
        vol.Optional("add_another", default=False): selector.BooleanSelector(),
    })


def _add_schema_switch(flow) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_STATE_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_COMMAND_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_NAME): selector.TextSelector(),
        vol.Optional(CONF_SYNC_STATE, default=False): selector.BooleanSelector(),
        vol.Optional(CONF_PULSE_COMMAND, default=False): selector.BooleanSelector(),
        vol.Optional(CONF_PULSE_DURATION, default=DEFAULT_PULSE_DURATION): pulse_duration_selector,
        vol.Optional(CONF_SCAN_INTERVAL): scan_interval_selector,
        vol.Optional(CONF_AREA): flow._get_area_selector(),
        vol.Optional("add_another", default=False): selector.BooleanSelector(),
    })


def _add_schema_cover(flow) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_OPEN_COMMAND_ADDRESS): selector.TextSelector(),
        vol.Required(CONF_CLOSE_COMMAND_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_OPENING_STATE_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_CLOSING_STATE_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_NAME): selector.TextSelector(),
        vol.Optional(CONF_DEVICE_CLASS): _device_selector_by_type(CONF_COVERS),
        vol.Optional(CONF_OPERATE_TIME, default=DEFAULT_OPERATE_TIME): operate_time_selector,
        vol.Optional(CONF_USE_STATE_TOPICS, default=DEFAULT_USE_STATE_TOPICS): selector.BooleanSelector(),
        vol.Optional(CONF_SCAN_INTERVAL): scan_interval_selector,
        vol.Optional(CONF_AREA): flow._get_area_selector(),
        vol.Optional("add_another", default=False): selector.BooleanSelector(),
    })


def _add_schema_cover_position(flow) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_POSITION_STATE_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_POSITION_COMMAND_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_STOP_COMMAND_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_STOP_PULSE_DURATION, default=DEFAULT_PULSE_DURATION): pulse_duration_selector,
        vol.Optional(CONF_NAME): selector.TextSelector(),
        vol.Optional(CONF_DEVICE_CLASS): _device_selector_by_type(CONF_COVERS),
        vol.Optional(CONF_INVERT_POSITION, default=False): selector.BooleanSelector(),
        vol.Optional(CONF_SCAN_INTERVAL): scan_interval_selector,
        vol.Optional(CONF_AREA): flow._get_area_selector(),
        vol.Optional("add_another", default=False): selector.BooleanSelector(),
    })


def _add_schema_button(flow) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_NAME): selector.TextSelector(),
        vol.Optional(CONF_BUTTON_PULSE, default=DEFAULT_PULSE_DURATION): pulse_duration_selector,
        vol.Optional(CONF_AREA): flow._get_area_selector(),
        vol.Optional("add_another", default=False): selector.BooleanSelector(),
    })


def _add_schema_light(flow) -> vol.Schema:
    brightness_scale_sel = _num_sel(min=1, max=65535, step=1)
    return vol.Schema({
        vol.Required(CONF_STATE_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_COMMAND_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_NAME): selector.TextSelector(),
        vol.Optional(CONF_SYNC_STATE, default=False): selector.BooleanSelector(),
        vol.Optional(CONF_PULSE_COMMAND, default=False): selector.BooleanSelector(),
        vol.Optional(CONF_PULSE_DURATION, default=DEFAULT_PULSE_DURATION): pulse_duration_selector,
        vol.Optional(CONF_BRIGHTNESS_STATE_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_BRIGHTNESS_COMMAND_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_BRIGHTNESS_SCALE, default=DEFAULT_BRIGHTNESS_SCALE): brightness_scale_sel,
        vol.Optional(CONF_SCAN_INTERVAL): scan_interval_selector,
        vol.Optional(CONF_AREA): flow._get_area_selector(),
        vol.Optional("add_another", default=False): selector.BooleanSelector(),
    })


def _add_schema_number(flow) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_COMMAND_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_NAME): selector.TextSelector(),
        vol.Optional(CONF_DEVICE_CLASS): _device_selector_by_type(CONF_NUMBERS),
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): selector.TextSelector(),
        vol.Optional(CONF_STEP): positive_number_selector,
        vol.Optional(CONF_VALUE_MULTIPLIER): value_multiplier_selector,
        vol.Optional(CONF_MIN_VALUE): number_value_selector,
        vol.Optional(CONF_MAX_VALUE): number_value_selector,
        vol.Optional(CONF_SCALE_RAW_MIN): scale_value_selector,
        vol.Optional(CONF_SCALE_RAW_MAX): scale_value_selector,
        vol.Optional(CONF_REAL_PRECISION): real_precision_selector,
        vol.Optional(CONF_SCAN_INTERVAL): scan_interval_selector,
        vol.Optional(CONF_AREA): flow._get_area_selector(),
        vol.Optional("add_another", default=False): selector.BooleanSelector(),
    })


def _add_schema_text(flow) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_COMMAND_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_NAME): selector.TextSelector(),
        vol.Optional(CONF_PATTERN): selector.TextSelector(),
        vol.Optional(CONF_SCAN_INTERVAL): scan_interval_selector,
        vol.Optional(CONF_AREA): flow._get_area_selector(),
        vol.Optional("add_another", default=False): selector.BooleanSelector(),
    })


def _temp_selector():
    return _num_sel(min=-50, max=100, step=0.1)


def _add_schema_climate_direct(flow) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_CURRENT_TEMPERATURE_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_HEATING_OUTPUT_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_COOLING_OUTPUT_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_HEATING_ACTION_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_COOLING_ACTION_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): _temp_selector(),
        vol.Optional(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): _temp_selector(),
        vol.Optional(CONF_TEMP_STEP, default=DEFAULT_TEMP_STEP): _num_sel(min=0.1, max=10, step=0.1),
        vol.Optional(CONF_NAME): selector.TextSelector(),
        vol.Optional(CONF_SCAN_INTERVAL): scan_interval_selector,
        vol.Optional(CONF_AREA): flow._get_area_selector(),
        vol.Optional("add_another", default=False): selector.BooleanSelector(),
    })


def _add_schema_climate_setpoint(flow) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_CURRENT_TEMPERATURE_ADDRESS): selector.TextSelector(),
        vol.Required(CONF_TARGET_TEMPERATURE_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_PRESET_MODE_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_HVAC_STATUS_ADDRESS): selector.TextSelector(),
        vol.Optional(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): _temp_selector(),
        vol.Optional(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): _temp_selector(),
        vol.Optional(CONF_TEMP_STEP, default=DEFAULT_TEMP_STEP): _num_sel(min=0.1, max=10, step=0.1),
        vol.Optional(CONF_NAME): selector.TextSelector(),
        vol.Optional(CONF_SCAN_INTERVAL): scan_interval_selector,
        vol.Optional(CONF_AREA): flow._get_area_selector(),
        vol.Optional("add_another", default=False): selector.BooleanSelector(),
    })


def _add_schema_writer(flow) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_ADDRESS): selector.TextSelector(),
        vol.Required(CONF_SOURCE_ENTITY): selector.EntitySelector(),
        vol.Optional(CONF_NAME): selector.TextSelector(),
        vol.Optional(CONF_AREA): flow._get_area_selector(),
        vol.Optional("add_another", default=False): selector.BooleanSelector(),
    })


def _edit_schema_from_add(add_schema_builder, flow, item: dict[str, Any]) -> vol.Schema:
    # Build an edit schema by copying the add schema defaults where possible.
    schema = {}
    for key, value in add_schema_builder(flow).schema.items():
        if getattr(key, "schema", None) == "add_another":
            continue
        raw_key = getattr(key, "schema", key)
        default = item.get(raw_key, None)
        if isinstance(key, vol.Required):
            marker = vol.Required(raw_key, default=default if default is not None else "")
        else:
            marker = vol.Optional(raw_key, default=default) if default not in (None, "") else vol.Optional(raw_key)
        schema[marker] = value
    return vol.Schema(schema)


def _edit_schema_sensor(flow, item: dict[str, Any]) -> vol.Schema:
    return _edit_schema_from_add(_add_schema_sensor, flow, item)


def _edit_schema_binary_sensor(flow, item: dict[str, Any]) -> vol.Schema:
    return _edit_schema_from_add(_add_schema_binary_sensor, flow, item)


def _edit_schema_switch(flow, item: dict[str, Any]) -> vol.Schema:
    return _edit_schema_from_add(_add_schema_switch, flow, item)


def _edit_schema_cover(flow, item: dict[str, Any]) -> vol.Schema:
    return _edit_schema_from_add(_add_schema_cover, flow, item)


def _edit_schema_cover_position(flow, item: dict[str, Any]) -> vol.Schema:
    return _edit_schema_from_add(_add_schema_cover_position, flow, item)


def _edit_schema_button(flow, item: dict[str, Any]) -> vol.Schema:
    return _edit_schema_from_add(_add_schema_button, flow, item)


def _edit_schema_light(flow, item: dict[str, Any]) -> vol.Schema:
    return _edit_schema_from_add(_add_schema_light, flow, item)


def _edit_schema_number(flow, item: dict[str, Any]) -> vol.Schema:
    return _edit_schema_from_add(_add_schema_number, flow, item)


def _edit_schema_text(flow, item: dict[str, Any]) -> vol.Schema:
    return _edit_schema_from_add(_add_schema_text, flow, item)


def _edit_schema_climate_direct(flow, item: dict[str, Any]) -> vol.Schema:
    return _edit_schema_from_add(_add_schema_climate_direct, flow, item)


def _edit_schema_climate_setpoint(flow, item: dict[str, Any]) -> vol.Schema:
    return _edit_schema_from_add(_add_schema_climate_setpoint, flow, item)


def _edit_schema_writer(flow, item: dict[str, Any]) -> vol.Schema:
    return _edit_schema_from_add(_add_schema_writer, flow, item)


# ---------------------------------------------------------------------------
# Item builders
# ---------------------------------------------------------------------------

def _base_address_item(user_input: dict[str, Any]) -> dict[str, Any]:
    item = {CONF_ADDRESS: _clean_text(user_input.get(CONF_ADDRESS))}
    _copy_optional(user_input, item, CONF_NAME, _clean_text)
    _copy_optional(user_input, item, CONF_AREA, _clean_text)
    _copy_optional(user_input, item, CONF_SCAN_INTERVAL, _to_float)
    return item


def _build_sensor_item(user_input: dict[str, Any]) -> dict[str, Any]:
    item = _base_address_item(user_input)
    _copy_optional(user_input, item, CONF_DEVICE_CLASS, _strip_none_option)
    _copy_optional(user_input, item, CONF_UNIT_OF_MEASUREMENT, _clean_text)
    _copy_optional(user_input, item, CONF_VALUE_MULTIPLIER, _to_float)
    _copy_optional(user_input, item, CONF_MIN_VALUE, _to_float)
    _copy_optional(user_input, item, CONF_MAX_VALUE, _to_float)
    _copy_optional(user_input, item, CONF_SCALE_RAW_MIN, _to_float)
    _copy_optional(user_input, item, CONF_SCALE_RAW_MAX, _to_float)
    _copy_optional(user_input, item, CONF_STATE_CLASS, _strip_none_option)
    _copy_optional(user_input, item, CONF_REAL_PRECISION, _to_int)
    _copy_optional(user_input, item, CONF_AVAILABILITY_ADDRESS, _clean_text)
    if user_input.get(CONF_AVAILABILITY_INVERT):
        item[CONF_AVAILABILITY_INVERT] = True
    return item


def _build_binary_sensor_item(user_input: dict[str, Any]) -> dict[str, Any]:
    item = _base_address_item(user_input)
    _copy_optional(user_input, item, CONF_DEVICE_CLASS, _strip_none_option)
    if user_input.get(CONF_INVERT_STATE):
        item[CONF_INVERT_STATE] = True
    _copy_optional(user_input, item, CONF_AVAILABILITY_ADDRESS, _clean_text)
    if user_input.get(CONF_AVAILABILITY_INVERT):
        item[CONF_AVAILABILITY_INVERT] = True
    return item


def _state_command_item(user_input: dict[str, Any]) -> dict[str, Any]:
    item = {CONF_STATE_ADDRESS: _clean_text(user_input.get(CONF_STATE_ADDRESS))}
    _copy_optional(user_input, item, CONF_COMMAND_ADDRESS, _clean_text)
    _copy_optional(user_input, item, CONF_NAME, _clean_text)
    _copy_optional(user_input, item, CONF_AREA, _clean_text)
    _copy_optional(user_input, item, CONF_SCAN_INTERVAL, _to_float)
    if user_input.get(CONF_SYNC_STATE):
        item[CONF_SYNC_STATE] = True
    if user_input.get(CONF_PULSE_COMMAND):
        item[CONF_PULSE_COMMAND] = True
    if user_input.get(CONF_PULSE_DURATION) not in (None, ""):
        item[CONF_PULSE_DURATION] = parse_pulse_duration(user_input.get(CONF_PULSE_DURATION))
    return item


def _build_switch_item(user_input: dict[str, Any]) -> dict[str, Any]:
    return _state_command_item(user_input)


def _build_light_item(user_input: dict[str, Any]) -> dict[str, Any]:
    item = _state_command_item(user_input)
    _copy_optional(user_input, item, CONF_BRIGHTNESS_STATE_ADDRESS, _clean_text)
    _copy_optional(user_input, item, CONF_BRIGHTNESS_COMMAND_ADDRESS, _clean_text)
    _copy_optional(user_input, item, CONF_BRIGHTNESS_SCALE, _to_int)
    return item


def _build_cover_item(user_input: dict[str, Any]) -> dict[str, Any]:
    item = {
        CONF_OPEN_COMMAND_ADDRESS: _clean_text(user_input.get(CONF_OPEN_COMMAND_ADDRESS)),
        CONF_CLOSE_COMMAND_ADDRESS: _clean_text(user_input.get(CONF_CLOSE_COMMAND_ADDRESS)),
    }
    for key in (CONF_OPENING_STATE_ADDRESS, CONF_CLOSING_STATE_ADDRESS, CONF_NAME, CONF_AREA):
        _copy_optional(user_input, item, key, _clean_text)
    _copy_optional(user_input, item, CONF_DEVICE_CLASS, _strip_none_option)
    _copy_optional(user_input, item, CONF_OPERATE_TIME, _to_float)
    if user_input.get(CONF_USE_STATE_TOPICS):
        item[CONF_USE_STATE_TOPICS] = True
    _copy_optional(user_input, item, CONF_SCAN_INTERVAL, _to_float)
    return item


def _build_cover_position_item(user_input: dict[str, Any]) -> dict[str, Any]:
    item = {CONF_POSITION_STATE_ADDRESS: _clean_text(user_input.get(CONF_POSITION_STATE_ADDRESS))}
    for key in (CONF_POSITION_COMMAND_ADDRESS, CONF_STOP_COMMAND_ADDRESS, CONF_NAME, CONF_AREA):
        _copy_optional(user_input, item, key, _clean_text)
    _copy_optional(user_input, item, CONF_DEVICE_CLASS, _strip_none_option)
    _copy_optional(user_input, item, CONF_STOP_PULSE_DURATION, _to_float)
    if user_input.get(CONF_INVERT_POSITION):
        item[CONF_INVERT_POSITION] = True
    _copy_optional(user_input, item, CONF_SCAN_INTERVAL, _to_float)
    return item


def _build_button_item(user_input: dict[str, Any]) -> dict[str, Any]:
    item = _base_address_item(user_input)
    _copy_optional(user_input, item, CONF_BUTTON_PULSE, _to_float)
    return item


def _build_number_item(user_input: dict[str, Any]) -> dict[str, Any]:
    item = _base_address_item(user_input)
    _copy_optional(user_input, item, CONF_COMMAND_ADDRESS, _clean_text)
    _copy_optional(user_input, item, CONF_DEVICE_CLASS, _strip_none_option)
    _copy_optional(user_input, item, CONF_UNIT_OF_MEASUREMENT, _clean_text)
    _copy_optional(user_input, item, CONF_STEP, _to_float)
    _copy_optional(user_input, item, CONF_VALUE_MULTIPLIER, _to_float)
    _copy_optional(user_input, item, CONF_SCALE_RAW_MIN, _to_float)
    _copy_optional(user_input, item, CONF_SCALE_RAW_MAX, _to_float)
    _copy_optional(user_input, item, CONF_REAL_PRECISION, _to_int)
    min_value = _to_float(user_input.get(CONF_MIN_VALUE)) if user_input.get(CONF_MIN_VALUE) not in (None, "") else None
    max_value = _to_float(user_input.get(CONF_MAX_VALUE)) if user_input.get(CONF_MAX_VALUE) not in (None, "") else None
    try:
        limits = get_numeric_limits(parse_tag(item[CONF_ADDRESS]).data_type)
    except Exception:
        limits = None
    if limits:
        lo, hi = limits
        if min_value is not None:
            min_value = max(lo, min(hi, min_value))
        if max_value is not None:
            max_value = max(lo, min(hi, max_value))
    if min_value is not None:
        item[CONF_MIN_VALUE] = min_value
    if max_value is not None:
        item[CONF_MAX_VALUE] = max_value
    return item


def _build_text_item(user_input: dict[str, Any]) -> dict[str, Any]:
    item = _base_address_item(user_input)
    _copy_optional(user_input, item, CONF_COMMAND_ADDRESS, _clean_text)
    _copy_optional(user_input, item, CONF_PATTERN, _clean_text)
    return item


def _build_climate_direct_item(user_input: dict[str, Any]) -> dict[str, Any]:
    item = {CONF_CLIMATE_CONTROL_MODE: CONTROL_MODE_DIRECT, CONF_CURRENT_TEMPERATURE_ADDRESS: _clean_text(user_input.get(CONF_CURRENT_TEMPERATURE_ADDRESS))}
    for key in (CONF_HEATING_OUTPUT_ADDRESS, CONF_COOLING_OUTPUT_ADDRESS, CONF_HEATING_ACTION_ADDRESS, CONF_COOLING_ACTION_ADDRESS, CONF_NAME, CONF_AREA):
        _copy_optional(user_input, item, key, _clean_text)
    for key in (CONF_MIN_TEMP, CONF_MAX_TEMP, CONF_TEMP_STEP, CONF_SCAN_INTERVAL):
        _copy_optional(user_input, item, key, _to_float)
    return item


def _build_climate_setpoint_item(user_input: dict[str, Any]) -> dict[str, Any]:
    item = {CONF_CLIMATE_CONTROL_MODE: CONTROL_MODE_SETPOINT, CONF_CURRENT_TEMPERATURE_ADDRESS: _clean_text(user_input.get(CONF_CURRENT_TEMPERATURE_ADDRESS)), CONF_TARGET_TEMPERATURE_ADDRESS: _clean_text(user_input.get(CONF_TARGET_TEMPERATURE_ADDRESS))}
    for key in (CONF_PRESET_MODE_ADDRESS, CONF_HVAC_STATUS_ADDRESS, CONF_NAME, CONF_AREA):
        _copy_optional(user_input, item, key, _clean_text)
    for key in (CONF_MIN_TEMP, CONF_MAX_TEMP, CONF_TEMP_STEP, CONF_SCAN_INTERVAL):
        _copy_optional(user_input, item, key, _to_float)
    return item


def _build_writer_item(user_input: dict[str, Any]) -> dict[str, Any]:
    item = _base_address_item(user_input)
    _copy_optional(user_input, item, CONF_SOURCE_ENTITY, _clean_text)
    return item


def _validate_sync_pulse(flow: S7PLCOptionsFlow, info: EntityTypeInfo, user_input: dict[str, Any], item: dict[str, Any], schema: vol.Schema):
    if info.option_key not in (CONF_SWITCHES, CONF_LIGHTS):
        return None
    if item.get(CONF_SYNC_STATE) and item.get(CONF_PULSE_COMMAND):
        return flow._form(info.add_step_id, schema, {"base": "sync_pulse_conflict"})
    if item.get(CONF_SYNC_STATE):
        state_address = flow._normalized_address(item.get(CONF_STATE_ADDRESS))
        command_address = flow._normalized_address(item.get(CONF_COMMAND_ADDRESS) or item.get(CONF_STATE_ADDRESS))
        if not item.get(CONF_COMMAND_ADDRESS) or state_address == command_address:
            return flow._form(info.add_step_id, schema, {"base": "sync_same_address"})
    return None


def _address_for_duplicate(item: dict[str, Any]) -> Any:
    return item.get(CONF_ADDRESS) or item.get(CONF_STATE_ADDRESS) or item.get(CONF_OPEN_COMMAND_ADDRESS) or item.get(CONF_POSITION_STATE_ADDRESS) or item.get(CONF_CURRENT_TEMPERATURE_ADDRESS)


def _has_any_duplicate(options: dict[str, list[dict[str, Any]]]) -> bool:
    for option_key, items in options.items():
        seen: set[str] = set()
        keys = (CONF_ADDRESS, CONF_STATE_ADDRESS, CONF_OPEN_COMMAND_ADDRESS, CONF_POSITION_STATE_ADDRESS, CONF_CURRENT_TEMPERATURE_ADDRESS)
        for item in items:
            for key in keys:
                value = item.get(key)
                if not value:
                    continue
                norm = str(value).strip().upper()
                if norm in seen:
                    return True
                seen.add(norm)
    return False


def _make_add_step(info: EntityTypeInfo):
    async def _step(self: S7PLCOptionsFlow, user_input: dict[str, Any] | None = None):
        schema = info.build_add_schema(self)
        if user_input is None:
            return self._form(info.add_step_id, self._with_suggested_values(schema))
        item = getattr(self, info.item_builder_name)(user_input)
        item = {k: v for k, v in item.items() if v not in (None, "", "__none__")}
        validation = _validate_sync_pulse(self, info, user_input, item, schema)
        if validation:
            return validation
        addr = _address_for_duplicate(item)
        skip = self._edit_target[1] if self._edit_target and self._edit_target[0] == info.prefix else None
        if addr and self._has_duplicate(info.option_key, addr, keys=(CONF_ADDRESS, CONF_STATE_ADDRESS, CONF_OPEN_COMMAND_ADDRESS, CONF_POSITION_STATE_ADDRESS, CONF_CURRENT_TEMPERATURE_ADDRESS), skip_idx=skip):
            return self._form(info.add_step_id, schema, {"base": "already_configured"})
        return self._store_item(info, item, bool(user_input.get("add_another")))
    return _step


def _make_edit_step(info: EntityTypeInfo):
    async def _step(self: S7PLCOptionsFlow, user_input: dict[str, Any] | None = None):
        if not self._edit_target or self._edit_target[0] != info.prefix:
            return await self.async_step_edit()
        item = self._options[info.option_key][self._edit_target[1]]
        schema = info.build_edit_schema(self, item)
        if user_input is None:
            return self._form(info.edit_step_id, schema)
        new_item = getattr(self, info.item_builder_name)(user_input)
        new_item = {k: v for k, v in new_item.items() if v not in (None, "", "__none__")}
        validation = _validate_sync_pulse(self, info, user_input, new_item, schema)
        if validation:
            return validation
        self._options[info.option_key][self._edit_target[1]] = new_item
        self._edit_target = None
        return self._finish()
    return _step


ENTITY_TYPE_REGISTRY: dict[str, EntityTypeInfo] = {
    "s": EntityTypeInfo(CONF_SENSORS, "s", "sensors", "edit_sensor", _add_schema_sensor, _edit_schema_sensor, "_build_sensor_item"),
    "bs": EntityTypeInfo(CONF_BINARY_SENSORS, "bs", "binary_sensors", "edit_binary_sensor", _add_schema_binary_sensor, _edit_schema_binary_sensor, "_build_binary_sensor_item"),
    "sw": EntityTypeInfo(CONF_SWITCHES, "sw", "switches", "edit_switch", _add_schema_switch, _edit_schema_switch, "_build_switch_item"),
    "cv": EntityTypeInfo(CONF_COVERS, "cv", "covers_traditional", "edit_cover", _add_schema_cover, _edit_schema_cover, "_build_cover_item"),
    "cvp": EntityTypeInfo(CONF_COVERS, "cvp", "covers_position", "edit_cover_position", _add_schema_cover_position, _edit_schema_cover_position, "_build_cover_position_item"),
    "bt": EntityTypeInfo(CONF_BUTTONS, "bt", "buttons", "edit_button", _add_schema_button, _edit_schema_button, "_build_button_item"),
    "lt": EntityTypeInfo(CONF_LIGHTS, "lt", "lights", "edit_light", _add_schema_light, _edit_schema_light, "_build_light_item"),
    "nm": EntityTypeInfo(CONF_NUMBERS, "nm", "numbers", "edit_number", _add_schema_number, _edit_schema_number, "_build_number_item"),
    "tx": EntityTypeInfo(CONF_TEXTS, "tx", "texts", "edit_text", _add_schema_text, _edit_schema_text, "_build_text_item"),
    "cld": EntityTypeInfo(CONF_CLIMATES, "cld", "climates_direct", "edit_climate_direct", _add_schema_climate_direct, _edit_schema_climate_direct, "_build_climate_direct_item"),
    "cls": EntityTypeInfo(CONF_CLIMATES, "cls", "climates_setpoint", "edit_climate_setpoint", _add_schema_climate_setpoint, _edit_schema_climate_setpoint, "_build_climate_setpoint_item"),
    "wr": EntityTypeInfo(CONF_ENTITY_SYNC, "wr", "entity_sync", "edit_writer", _add_schema_writer, _edit_schema_writer, "_build_writer_item"),
}

for _prefix, _info in ENTITY_TYPE_REGISTRY.items():
    setattr(S7PLCOptionsFlow, f"async_step_{_info.add_step_id}", _make_add_step(_info))
    setattr(S7PLCOptionsFlow, f"async_step_{_info.edit_step_id}", _make_edit_step(_info))
    setattr(S7PLCOptionsFlow, _info.item_builder_name, staticmethod(globals()[_info.item_builder_name]))
