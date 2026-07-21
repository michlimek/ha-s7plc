const WS_LIST = "s7plc/entity_editor/list";
const WS_GET = "s7plc/entity_editor/get";
const WS_SAVE = "s7plc/entity_editor/save";

const COMMON_FIELDS = [
  "name",
  "device_group",
  "area",
  "scan_interval",
  "unit_of_measurement",
  "device_class",
];

const field = (key, pl, en, type = "text", options = undefined) => ({
  key,
  label: { pl, en },
  type,
  options,
});

const TYPES = {
  s: {
    label: { pl: "Sensor", en: "Sensor" },
    primary: field("address", "Adres odczytu", "Read address"),
    secondary: null,
    unit: true,
    deviceClass: true,
    defaults: {},
    advanced: [
      field("value_multiplier", "Mnożnik wartości", "Value multiplier", "number"),
      field("min_value", "Minimum", "Minimum", "number"),
      field("max_value", "Maksimum", "Maximum", "number"),
      field("scale_raw_min", "Surowe minimum", "Raw minimum", "number"),
      field("scale_raw_max", "Surowe maksimum", "Raw maximum", "number"),
      field("state_class", "Klasa stanu", "State class", "select", [
        "measurement",
        "total",
        "total_increasing",
      ]),
      field("real_precision", "Miejsca po przecinku", "Decimal places", "integer"),
      field("availability_address", "Adres dostępności", "Availability address"),
      field("availability_invert", "Odwróć dostępność", "Invert availability", "checkbox"),
    ],
  },
  bs: {
    label: { pl: "Sensor binarny", en: "Binary sensor" },
    primary: field("address", "Adres odczytu", "Read address"),
    secondary: null,
    unit: false,
    deviceClass: true,
    defaults: { invert_state: false },
    advanced: [
      field("invert_state", "Odwróć stan", "Invert state", "checkbox"),
      field("availability_address", "Adres dostępności", "Availability address"),
      field("availability_invert", "Odwróć dostępność", "Invert availability", "checkbox"),
    ],
  },
  sw: {
    label: { pl: "Przełącznik", en: "Switch" },
    primary: field("state_address", "Adres stanu", "State address"),
    secondary: field("command_address", "Adres zapisu", "Command address"),
    unit: false,
    deviceClass: false,
    defaults: { sync_state: false, pulse_command: false, pulse_duration: 0.5 },
    advanced: [
      field("sync_state", "Synchronizuj stan", "Synchronize state", "checkbox"),
      field("pulse_command", "Sterowanie impulsem", "Pulse command", "checkbox"),
      field("pulse_duration", "Długość impulsu [s]", "Pulse duration [s]", "number"),
    ],
  },
  cv: {
    label: { pl: "Roleta czasowa", en: "Timed cover" },
    primary: field("open_command_address", "Adres otwierania", "Open command address"),
    secondary: field("close_command_address", "Adres zamykania", "Close command address"),
    secondaryRequired: true,
    unit: false,
    deviceClass: true,
    defaults: { operate_time: 60, use_state_topics: false },
    advanced: [
      field("opening_state_address", "Adres stanu otwierania", "Opening state address"),
      field("closing_state_address", "Adres stanu zamykania", "Closing state address"),
      field("operate_time", "Czas ruchu [s]", "Travel time [s]", "number"),
      field("use_state_topics", "Użyj adresów stanu", "Use state addresses", "checkbox"),
    ],
  },
  cvp: {
    label: { pl: "Roleta pozycyjna", en: "Position cover" },
    primary: field("position_state_address", "Adres pozycji", "Position state address"),
    secondary: field("position_command_address", "Adres zadanej pozycji", "Position command address"),
    unit: false,
    deviceClass: true,
    defaults: { stop_pulse_duration: 0.5, invert_position: false },
    advanced: [
      field("stop_command_address", "Adres STOP", "Stop command address"),
      field("stop_pulse_duration", "Impuls STOP [s]", "Stop pulse [s]", "number"),
      field("invert_position", "Odwróć pozycję", "Invert position", "checkbox"),
    ],
  },
  bt: {
    label: { pl: "Przycisk", en: "Button" },
    primary: field("address", "Adres zapisu", "Write address"),
    secondary: null,
    unit: false,
    deviceClass: false,
    defaults: { button_pulse: 0.5 },
    advanced: [field("button_pulse", "Długość impulsu [s]", "Pulse duration [s]", "number")],
  },
  lt: {
    label: { pl: "Światło", en: "Light" },
    primary: field("state_address", "Adres stanu", "State address"),
    secondary: field("command_address", "Adres zapisu", "Command address"),
    unit: false,
    deviceClass: false,
    defaults: { sync_state: false, pulse_command: false, pulse_duration: 0.5 },
    advanced: [
      field("sync_state", "Synchronizuj stan", "Synchronize state", "checkbox"),
      field("pulse_command", "Sterowanie impulsem", "Pulse command", "checkbox"),
      field("pulse_duration", "Długość impulsu [s]", "Pulse duration [s]", "number"),
      field("brightness_state_address", "Adres jasności", "Brightness state address"),
      field("brightness_command_address", "Adres zadanej jasności", "Brightness command address"),
      field("brightness_scale", "Skala jasności", "Brightness scale", "integer"),
    ],
  },
  nm: {
    label: { pl: "Liczba", en: "Number" },
    primary: field("address", "Adres odczytu", "Read address"),
    secondary: field("command_address", "Adres zapisu", "Command address"),
    unit: true,
    deviceClass: true,
    defaults: {},
    advanced: [
      field("step", "Krok", "Step", "number"),
      field("value_multiplier", "Mnożnik wartości", "Value multiplier", "number"),
      field("min_value", "Minimum", "Minimum", "number"),
      field("max_value", "Maksimum", "Maximum", "number"),
      field("scale_raw_min", "Surowe minimum", "Raw minimum", "number"),
      field("scale_raw_max", "Surowe maksimum", "Raw maximum", "number"),
      field("real_precision", "Miejsca po przecinku", "Decimal places", "integer"),
    ],
  },
  tx: {
    label: { pl: "Tekst", en: "Text" },
    primary: field("address", "Adres odczytu", "Read address"),
    secondary: field("command_address", "Adres zapisu", "Command address"),
    unit: false,
    deviceClass: false,
    defaults: {},
    advanced: [field("pattern", "Wzorzec (regex)", "Pattern (regex)")],
  },
  cl_d: {
    label: { pl: "Klimat — wyjścia", en: "Climate — outputs" },
    primary: field("current_temperature_address", "Adres temperatury", "Temperature address"),
    secondary: field("heating_output_address", "Wyjście grzania", "Heating output"),
    unit: false,
    deviceClass: false,
    defaults: { control_mode: "direct", min_temp: 7, max_temp: 35, temp_step: 0.5 },
    advanced: [
      field("cooling_output_address", "Wyjście chłodzenia", "Cooling output"),
      field("heating_action_address", "Stan grzania", "Heating action address"),
      field("cooling_action_address", "Stan chłodzenia", "Cooling action address"),
      field("min_temp", "Minimalna temperatura", "Minimum temperature", "number"),
      field("max_temp", "Maksymalna temperatura", "Maximum temperature", "number"),
      field("temp_step", "Krok temperatury", "Temperature step", "number"),
    ],
  },
  cl_s: {
    label: { pl: "Klimat — nastawa", en: "Climate — setpoint" },
    primary: field("current_temperature_address", "Adres temperatury", "Temperature address"),
    secondary: field("target_temperature_address", "Adres nastawy", "Setpoint address"),
    secondaryRequired: true,
    unit: false,
    deviceClass: false,
    defaults: { control_mode: "setpoint", min_temp: 7, max_temp: 35, temp_step: 0.5 },
    advanced: [
      field("preset_mode_address", "Adres trybu preset", "Preset mode address"),
      field("hvac_status_address", "Adres stanu HVAC", "HVAC status address"),
      field("min_temp", "Minimalna temperatura", "Minimum temperature", "number"),
      field("max_temp", "Maksymalna temperatura", "Maximum temperature", "number"),
      field("temp_step", "Krok temperatury", "Temperature step", "number"),
    ],
  },
  wr: {
    label: { pl: "Synchronizacja encji", en: "Entity sync" },
    primary: field("address", "Adres zapisu", "Write address"),
    secondary: field("source_entity", "Encja źródłowa", "Source entity"),
    secondaryRequired: true,
    unit: false,
    deviceClass: false,
    defaults: {},
    advanced: [],
  },
};

const UI = {
  pl: {
    title: "Edytor encji S7 PLC",
    subtitle: "Edycja tabelaryczna. Zmiany trafiają do Home Assistant dopiero po użyciu przycisku Zapisz.",
    plc: "Sterownik",
    search: "Szukaj po nazwie, adresie lub urządzeniu…",
    add: "Dodaj wiersz",
    save: "Zapisz",
    discard: "Odrzuć zmiany",
    unsaved: "Niezapisane zmiany",
    saved: "Brak niezapisanych zmian",
    noEntries: "Nie znaleziono skonfigurowanych sterowników S7 PLC.",
    noRows: "Brak encji pasujących do filtra.",
    loading: "Wczytywanie…",
    selected: "zaznaczono",
    copy: "Kopiuj do Excela",
    fill: "Wypełnij w dół",
    remove: "Usuń zaznaczone",
    name: "Nazwa",
    device: "Urządzenie",
    type: "Typ",
    address1: "Adres 1",
    address2: "Adres 2",
    unit: "Jednostka",
    deviceClass: "Klasa",
    interval: "Interwał [s]",
    area: "Obszar",
    more: "Więcej",
    actions: "Akcje",
    details: "Ustawienia dodatkowe",
    close: "Gotowe",
    duplicate: "Duplikuj",
    delete: "Usuń",
    choose: "— wybierz —",
    empty: "—",
    saveOk: "Konfiguracja została zapisana. Integracja zostanie przeładowana.",
    noChanges: "Konfiguracja nie wymagała zmian.",
    copied: "Skopiowano zaznaczone wiersze do schowka.",
    pasted: "Wklejono dane z arkusza.",
    fillHint: "Zaznacz co najmniej dwa wiersze i ustaw kursor w kolumnie, którą chcesz wypełnić.",
    required: "Uzupełnij wymagane pola oznaczone na czerwono.",
    validation: "Nie udało się zapisać. Sprawdź oznaczone wiersze.",
    stale: "Konfiguracja została w międzyczasie zmieniona. Wczytaj ją ponownie, aby nie nadpisać cudzych zmian.",
    loadFailed: "Nie udało się wczytać konfiguracji.",
    saveFailed: "Nie udało się zapisać konfiguracji.",
    confirmSwitch: "Masz niezapisane zmiany. Odrzucić je i przełączyć sterownik?",
    confirmDiscard: "Odrzucić wszystkie niezapisane zmiany?",
    excelTip: "Wklejaj wiele komórek bezpośrednio do tabeli (Ctrl+V). Kolejność kolumn jest taka jak na ekranie.",
  },
  en: {
    title: "S7 PLC entity editor",
    subtitle: "Spreadsheet editing. Changes reach Home Assistant only after you press Save.",
    plc: "PLC",
    search: "Search by name, address or device…",
    add: "Add row",
    save: "Save",
    discard: "Discard changes",
    unsaved: "Unsaved changes",
    saved: "No unsaved changes",
    noEntries: "No configured S7 PLC entries were found.",
    noRows: "No entities match the filter.",
    loading: "Loading…",
    selected: "selected",
    copy: "Copy to Excel",
    fill: "Fill down",
    remove: "Remove selected",
    name: "Name",
    device: "Device",
    type: "Type",
    address1: "Address 1",
    address2: "Address 2",
    unit: "Unit",
    deviceClass: "Class",
    interval: "Interval [s]",
    area: "Area",
    more: "More",
    actions: "Actions",
    details: "Additional settings",
    close: "Done",
    duplicate: "Duplicate",
    delete: "Delete",
    choose: "— choose —",
    empty: "—",
    saveOk: "Configuration saved. The integration will reload.",
    noChanges: "The configuration did not need changes.",
    copied: "Selected rows copied to the clipboard.",
    pasted: "Spreadsheet data pasted.",
    fillHint: "Select at least two rows and focus the column you want to fill.",
    required: "Complete the required fields highlighted in red.",
    validation: "Could not save. Check the highlighted rows.",
    stale: "The configuration changed while this editor was open. Reload it to avoid overwriting newer changes.",
    loadFailed: "Could not load the configuration.",
    saveFailed: "Could not save the configuration.",
    confirmSwitch: "You have unsaved changes. Discard them and switch PLC?",
    confirmDiscard: "Discard all unsaved changes?",
    excelTip: "Paste multiple cells directly into the grid (Ctrl+V). Columns follow the on-screen order.",
  },
};

const ERROR_TEXT = {
  invalid_address: { pl: "Nieprawidłowy adres PLC", en: "Invalid PLC address" },
  duplicate_entry: { pl: "Powtórzony adres", en: "Duplicate address" },
  invalid_entity_type: { pl: "Nieprawidłowy typ encji", en: "Invalid entity type" },
  invalid_value: { pl: "Nieprawidłowa wartość", en: "Invalid value" },
  invalid_number: { pl: "Nieprawidłowa liczba", en: "Invalid number" },
  invalid_range: { pl: "Minimum jest większe od maksimum", en: "Minimum is greater than maximum" },
  min_max_required_for_real: { pl: "REAL/LREAL wymaga minimum i maksimum", en: "REAL/LREAL requires minimum and maximum" },
  scale_requires_all_four: { pl: "Skalowanie wymaga wszystkich czterech wartości", en: "Scaling requires all four values" },
  scale_raw_requires_min_max: { pl: "Skalowanie wymaga minimum i maksimum", en: "Scaling requires minimum and maximum" },
  sync_pulse_conflict: { pl: "Synchronizacja i impuls nie mogą być aktywne jednocześnie", en: "Sync and pulse cannot both be enabled" },
  sync_same_address: { pl: "Synchronizacja wymaga osobnego adresu zapisu", en: "Sync requires a separate command address" },
  state_addresses_required: { pl: "Wymagane są oba adresy stanu rolety", en: "Both cover state addresses are required" },
  text_requires_string_type: { pl: "Encja tekstowa wymaga typu STRING lub WSTRING", en: "Text requires STRING or WSTRING" },
  invalid_source_entity: { pl: "Brak encji źródłowej", en: "Source entity is missing" },
  "At least one of heating or cooling output is required": { pl: "Wymagane jest wyjście grzania lub chłodzenia", en: "A heating or cooling output is required" },
};

const escapeHtml = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

class S7PLCEntityEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._narrow = false;
    this._initialized = false;
    this._loading = true;
    this._saving = false;
    this._entries = [];
    this._entryId = "";
    this._entry = null;
    this._rows = [];
    this._revision = "";
    this._areas = [];
    this._groups = [];
    this._deviceClasses = {};
    this._selected = new Set();
    this._dirty = false;
    this._query = "";
    this._addType = "s";
    this._dialogIndex = null;
    this._serverErrors = new Map();
    this._activeField = "primary";
    this._toast = null;
    this._beforeUnload = (event) => {
      if (!this._dirty) return;
      event.preventDefault();
      event.returnValue = "";
    };
  }

  set hass(value) {
    this._hass = value;
    if (!this._initialized && value) {
      this._initialized = true;
      this._initialize();
    }
  }

  get hass() {
    return this._hass;
  }

  set narrow(value) {
    this._narrow = Boolean(value);
  }

  set route(value) {
    this._route = value;
  }

  set panel(value) {
    this._panel = value;
  }

  connectedCallback() {
    window.addEventListener("beforeunload", this._beforeUnload);
    this._render();
  }

  disconnectedCallback() {
    window.removeEventListener("beforeunload", this._beforeUnload);
  }

  get _lang() {
    return this._hass?.language?.toLowerCase().startsWith("pl") ? "pl" : "en";
  }

  get _t() {
    return UI[this._lang];
  }

  _label(value) {
    return value?.[this._lang] ?? "";
  }

  async _callWS(message) {
    const response = await this._hass.connection.sendMessagePromise(message);
    return response?.result ?? response;
  }

  async _initialize() {
    this._loading = true;
    this._render();
    try {
      const result = await this._callWS({ type: WS_LIST });
      this._entries = result.entries ?? [];
      if (this._entries.length) {
        this._entryId = this._entries[0].entry_id;
        await this._loadEntry(this._entryId, false);
      }
    } catch (error) {
      this._showToast(this._t.loadFailed, "error");
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _loadEntry(entryId, rerender = true) {
    this._loading = true;
    if (rerender) this._render();
    try {
      const result = await this._callWS({ type: WS_GET, entry_id: entryId });
      this._entryId = entryId;
      this._entry = result.entry;
      this._revision = result.revision;
      this._areas = result.areas ?? [];
      this._groups = result.device_groups ?? [];
      this._deviceClasses = result.device_classes ?? {};
      this._rows = (result.rows ?? []).map((row) => ({
        prefix: row.prefix,
        data: { ...row.data },
      }));
      this._selected.clear();
      this._serverErrors.clear();
      this._dirty = false;
      this._dialogIndex = null;
    } catch (error) {
      this._showToast(this._t.loadFailed, "error");
    } finally {
      this._loading = false;
      if (rerender) this._render();
    }
  }

  _newRow(prefix = this._addType) {
    const definition = TYPES[prefix] ?? TYPES.s;
    return {
      prefix,
      data: { ...definition.defaults, [definition.primary.key]: "" },
    };
  }

  _visibleRows() {
    const needle = this._query.trim().toLocaleLowerCase();
    return this._rows
      .map((row, index) => ({ row, index }))
      .filter(({ row }) => {
        if (!needle) return true;
        const haystack = [
          this._label(TYPES[row.prefix]?.label),
          ...Object.values(row.data),
        ]
          .join(" ")
          .toLocaleLowerCase();
        return haystack.includes(needle);
      });
  }

  _markDirty() {
    this._dirty = true;
    this._serverErrors.clear();
    const indicator = this.shadowRoot.querySelector(".dirty-indicator");
    if (indicator) {
      indicator.textContent = this._t.unsaved;
      indicator.classList.add("is-dirty");
    }
    const save = this.shadowRoot.querySelector('[data-action="save"]');
    const discard = this.shadowRoot.querySelector('[data-action="discard"]');
    if (save) save.disabled = false;
    if (discard) discard.disabled = false;
  }

  _definition(row) {
    return TYPES[row.prefix] ?? TYPES.s;
  }

  _requiredMissing(row, logicalField) {
    const definition = this._definition(row);
    const spec = logicalField === "primary" ? definition.primary : definition.secondary;
    if (!spec) return false;
    const required = logicalField === "primary" || definition.secondaryRequired;
    return required && !String(row.data[spec.key] ?? "").trim();
  }

  _clientErrors() {
    const errors = [];
    this._rows.forEach((row, index) => {
      if (this._requiredMissing(row, "primary")) errors.push({ row: index, field: "primary" });
      if (this._requiredMissing(row, "secondary")) errors.push({ row: index, field: "secondary" });
      if (
        row.prefix === "cl_d" &&
        !String(row.data.heating_output_address ?? "").trim() &&
        !String(row.data.cooling_output_address ?? "").trim()
      ) {
        errors.push({ row: index, field: "secondary" });
      }
    });
    return errors;
  }

  _valueFromElement(element) {
    if (element.type === "checkbox") return element.checked;
    if (element.dataset.valueType === "number" || element.dataset.valueType === "integer") {
      if (element.value === "") return undefined;
      const parsed = Number(element.value.replace?.(",", ".") ?? element.value);
      if (!Number.isFinite(parsed)) return element.value;
      return element.dataset.valueType === "integer" ? Math.trunc(parsed) : parsed;
    }
    return element.value;
  }

  _writeElementValue(element) {
    const index = Number(element.dataset.index);
    const key = element.dataset.key;
    const row = this._rows[index];
    if (!row || !key) return;
    const value = this._valueFromElement(element);
    if (value === undefined || value === "") delete row.data[key];
    else row.data[key] = value;
    if (element.dataset.copyField === "primary" || element.dataset.copyField === "secondary") {
      element.classList.toggle("invalid", this._requiredMissing(row, element.dataset.copyField));
    }
    this._markDirty();
  }

  _switchRowType(index, prefix) {
    const row = this._rows[index];
    if (!row || !TYPES[prefix]) return;
    const oldDefinition = this._definition(row);
    const newDefinition = TYPES[prefix];
    const oldPrimary = row.data[oldDefinition.primary.key];
    const oldSecondary = oldDefinition.secondary ? row.data[oldDefinition.secondary.key] : undefined;
    const data = { ...newDefinition.defaults };
    COMMON_FIELDS.forEach((key) => {
      if (row.data[key] !== undefined) data[key] = row.data[key];
    });
    if (oldPrimary !== undefined) data[newDefinition.primary.key] = oldPrimary;
    else data[newDefinition.primary.key] = "";
    if (newDefinition.secondary && oldSecondary !== undefined) {
      data[newDefinition.secondary.key] = oldSecondary;
    }
    this._rows[index] = { prefix, data };
    this._markDirty();
    this._render();
  }

  _logicalValue(row, logical) {
    const definition = this._definition(row);
    if (logical === "prefix") return row.prefix;
    if (logical === "primary") return row.data[definition.primary.key] ?? "";
    if (logical === "secondary") return definition.secondary ? row.data[definition.secondary.key] ?? "" : "";
    return row.data[logical] ?? "";
  }

  _setLogicalValue(row, logical, rawValue) {
    if (logical === "prefix") {
      const match = Object.entries(TYPES).find(
        ([prefix, definition]) =>
          prefix.toLowerCase() === String(rawValue).trim().toLowerCase() ||
          this._label(definition.label).toLowerCase() === String(rawValue).trim().toLowerCase(),
      );
      return match?.[0] ?? row.prefix;
    }
    const definition = this._definition(row);
    let key = logical;
    if (logical === "primary") key = definition.primary.key;
    if (logical === "secondary") {
      if (!definition.secondary) return;
      key = definition.secondary.key;
    }
    let value = String(rawValue).trim();
    if (logical === "area") {
      const area = this._areas.find(
        (candidate) => candidate.label.toLowerCase() === value.toLowerCase() || candidate.value === value,
      );
      value = area?.value ?? value;
    }
    if (logical === "scan_interval" && value !== "") {
      const parsed = Number(value.replace(",", "."));
      if (Number.isFinite(parsed)) value = parsed;
    }
    if (value === "") delete row.data[key];
    else row.data[key] = value;
  }

  async _pasteGrid(event) {
    const target = event.target.closest("[data-copy-field]");
    if (!target) return;
    const text = event.clipboardData?.getData("text/plain") ?? "";
    if (!text.includes("\t") && !text.includes("\n") && !text.includes("\r")) return;
    event.preventDefault();

    const columns = [
      "prefix",
      "device_group",
      "name",
      "primary",
      "secondary",
      "unit_of_measurement",
      "device_class",
      "scan_interval",
      "area",
    ];
    const startColumn = Math.max(0, columns.indexOf(target.dataset.copyField));
    const startRow = Number(target.dataset.index);
    const matrix = text
      .replace(/\r/g, "")
      .split("\n")
      .filter((line, index, all) => !(index === all.length - 1 && line === ""))
      .map((line) => line.split("\t"));

    matrix.forEach((cells, rowOffset) => {
      const index = startRow + rowOffset;
      while (this._rows.length <= index) {
        this._rows.push(this._newRow(this._rows[startRow]?.prefix ?? this._addType));
      }
      let row = this._rows[index];
      cells.forEach((cell, columnOffset) => {
        const logical = columns[startColumn + columnOffset];
        if (!logical) return;
        if (logical === "prefix") {
          const nextPrefix = this._setLogicalValue(row, logical, cell);
          if (nextPrefix !== row.prefix) {
            const oldPrimary = this._logicalValue(row, "primary");
            const oldSecondary = this._logicalValue(row, "secondary");
            row = this._newRow(nextPrefix);
            this._setLogicalValue(row, "primary", oldPrimary);
            this._setLogicalValue(row, "secondary", oldSecondary);
            this._rows[index] = row;
          }
        } else {
          this._setLogicalValue(row, logical, cell);
        }
      });
    });

    this._markDirty();
    this._render();
    this._showToast(this._t.pasted, "success");
  }

  async _copySelected() {
    const indices = [...this._selected].sort((a, b) => a - b);
    if (!indices.length) return;
    const columns = [
      "prefix",
      "device_group",
      "name",
      "primary",
      "secondary",
      "unit_of_measurement",
      "device_class",
      "scan_interval",
      "area",
    ];
    const lines = indices.map((index) => {
      const row = this._rows[index];
      return columns
        .map((logical) => {
          let value = this._logicalValue(row, logical);
          if (logical === "prefix") value = this._label(TYPES[row.prefix].label);
          if (logical === "area") {
            value = this._areas.find((area) => area.value === value)?.label ?? value;
          }
          return String(value ?? "").replaceAll("\t", " ").replaceAll("\n", " ");
        })
        .join("\t");
    });
    await navigator.clipboard.writeText(lines.join("\n"));
    this._showToast(this._t.copied, "success");
  }

  _fillDown() {
    const indices = [...this._selected].sort((a, b) => a - b);
    if (indices.length < 2) {
      this._showToast(this._t.fillHint, "warning");
      return;
    }
    const source = this._logicalValue(this._rows[indices[0]], this._activeField);
    indices.slice(1).forEach((index) => {
      this._setLogicalValue(this._rows[index], this._activeField, source);
    });
    this._markDirty();
    this._render();
  }

  async _save() {
    const clientErrors = this._clientErrors();
    if (clientErrors.length) {
      this._showToast(this._t.required, "error");
      this._render();
      const first = clientErrors[0];
      this.shadowRoot
        .querySelector(`[data-index="${first.row}"][data-copy-field="${first.field}"]`)
        ?.focus();
      return;
    }

    this._saving = true;
    this._serverErrors.clear();
    this._render();
    try {
      const result = await this._callWS({
        type: WS_SAVE,
        entry_id: this._entryId,
        revision: this._revision,
        rows: this._rows.map((row) => ({ prefix: row.prefix, data: row.data })),
      });
      if (!result.saved) {
        (result.errors ?? []).forEach((error) => this._serverErrors.set(error.row, error.code));
        this._showToast(this._t.validation, "error");
        return;
      }
      this._revision = result.revision;
      if (result.rows) {
        this._rows = result.rows.map((row) => ({ prefix: row.prefix, data: { ...row.data } }));
      }
      this._dirty = false;
      this._selected.clear();
      this._showToast(result.changed ? this._t.saveOk : this._t.noChanges, "success");
    } catch (error) {
      const code = error?.code ?? error?.error?.code;
      this._showToast(code === "stale_config" ? this._t.stale : this._t.saveFailed, "error");
    } finally {
      this._saving = false;
      this._render();
    }
  }

  _showToast(message, kind = "info") {
    this._toast = { message, kind };
    const existing = this.shadowRoot.querySelector(".toast");
    if (existing) {
      existing.className = `toast ${kind}`;
      existing.textContent = message;
    } else {
      this._render();
    }
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => {
      this._toast = null;
      this.shadowRoot.querySelector(".toast")?.remove();
    }, 5500);
  }

  _errorText(code) {
    return ERROR_TEXT[code]?.[this._lang] ?? code;
  }

  _typeOptions(selected) {
    return Object.entries(TYPES)
      .map(
        ([prefix, definition]) =>
          `<option value="${prefix}" ${prefix === selected ? "selected" : ""}>${escapeHtml(this._label(definition.label))}</option>`,
      )
      .join("");
  }

  _areaOptions(selected) {
    return [
      `<option value="">${escapeHtml(this._t.empty)}</option>`,
      ...this._areas.map(
        (area) =>
          `<option value="${escapeHtml(area.value)}" ${area.value === selected ? "selected" : ""}>${escapeHtml(area.label)}</option>`,
      ),
    ].join("");
  }

  _deviceClassOptions(prefix, selected) {
    const values = [...(this._deviceClasses[prefix] ?? [])];
    if (selected && !values.includes(selected)) values.push(selected);
    return [
      `<option value="">${escapeHtml(this._t.empty)}</option>`,
      ...values.map(
        (value) =>
          `<option value="${escapeHtml(value)}" ${value === selected ? "selected" : ""}>${escapeHtml(value.replaceAll("_", " "))}</option>`,
      ),
    ].join("");
  }

  _input(index, key, value, logical, options = {}) {
    const classes = ["cell-input"];
    if (options.invalid) classes.push("invalid");
    const attributes = `data-index="${index}" data-key="${escapeHtml(key)}" data-copy-field="${logical}"`;
    if (options.type === "select") {
      return `<select class="${classes.join(" ")}" ${attributes}>${options.html}</select>`;
    }
    return `<input class="${classes.join(" ")}" ${attributes} ${options.type ? `data-value-type="${options.type}" type="number" step="any"` : "type=\"text\""} value="${escapeHtml(value)}" placeholder="${escapeHtml(options.placeholder ?? "")}" ${options.list ? `list="${options.list}"` : ""}>`;
  }

  _renderRow(row, index) {
    const definition = this._definition(row);
    const data = row.data;
    const error = this._serverErrors.get(index);
    const selected = this._selected.has(index);
    const primaryValue = data[definition.primary.key] ?? "";
    const secondaryValue = definition.secondary ? data[definition.secondary.key] ?? "" : "";
    const unit = definition.unit
      ? this._input(index, "unit_of_measurement", data.unit_of_measurement ?? "", "unit_of_measurement")
      : `<span class="not-applicable">—</span>`;
    const deviceClass = definition.deviceClass
      ? this._input(index, "device_class", data.device_class ?? "", "device_class", {
          type: "select",
          html: this._deviceClassOptions(row.prefix, data.device_class ?? ""),
        })
      : `<span class="not-applicable">—</span>`;

    return `
      <tr class="${error ? "row-error" : ""}" data-row="${index}" title="${error ? escapeHtml(this._errorText(error)) : ""}">
        <td class="check"><input type="checkbox" data-action="select-row" data-index="${index}" ${selected ? "checked" : ""}></td>
        <td class="row-number">${index + 1}</td>
        <td class="type-cell">
          <select class="cell-input" data-action="row-type" data-index="${index}" data-copy-field="prefix">${this._typeOptions(row.prefix)}</select>
          ${error ? `<span class="row-error-text">${escapeHtml(this._errorText(error))}</span>` : ""}
        </td>
        <td>${this._input(index, "device_group", data.device_group ?? "", "device_group", { list: "device-group-list" })}</td>
        <td>${this._input(index, "name", data.name ?? "", "name")}</td>
        <td>${this._input(index, definition.primary.key, primaryValue, "primary", {
          invalid: this._requiredMissing(row, "primary"),
          placeholder: this._label(definition.primary.label),
        })}</td>
        <td>${definition.secondary
          ? this._input(index, definition.secondary.key, secondaryValue, "secondary", {
              invalid: this._requiredMissing(row, "secondary") || (row.prefix === "cl_d" && !secondaryValue && !data.cooling_output_address),
              placeholder: this._label(definition.secondary.label),
              list: row.prefix === "wr" ? "entity-id-list" : undefined,
            })
          : `<span class="not-applicable">—</span>`}</td>
        <td>${unit}</td>
        <td>${deviceClass}</td>
        <td>${this._input(index, "scan_interval", data.scan_interval ?? "", "scan_interval", { type: "number" })}</td>
        <td><select class="cell-input" data-index="${index}" data-key="area" data-copy-field="area">${this._areaOptions(data.area ?? "")}</select></td>
        <td class="center"><button class="icon-button" data-action="advanced" data-index="${index}" title="${escapeHtml(this._t.details)}">${definition.advanced.length ? "⚙" : "…"}</button></td>
        <td class="row-actions">
          <button class="icon-button" data-action="duplicate" data-index="${index}" title="${escapeHtml(this._t.duplicate)}">⧉</button>
          <button class="icon-button danger" data-action="delete" data-index="${index}" title="${escapeHtml(this._t.delete)}">×</button>
        </td>
      </tr>`;
  }

  _advancedInput(index, spec, value) {
    const label = escapeHtml(this._label(spec.label));
    if (spec.type === "checkbox") {
      return `<label class="advanced-checkbox"><input type="checkbox" data-index="${index}" data-key="${spec.key}" ${value ? "checked" : ""}> <span>${label}</span></label>`;
    }
    if (spec.type === "select") {
      const options = [
        `<option value="">${escapeHtml(this._t.empty)}</option>`,
        ...(spec.options ?? []).map(
          (option) => `<option value="${escapeHtml(option)}" ${option === value ? "selected" : ""}>${escapeHtml(option)}</option>`,
        ),
      ].join("");
      return `<label><span>${label}</span><select data-index="${index}" data-key="${spec.key}">${options}</select></label>`;
    }
    const numeric = spec.type === "number" || spec.type === "integer";
    return `<label><span>${label}</span><input data-index="${index}" data-key="${spec.key}" ${numeric ? `type="number" step="any" data-value-type="${spec.type}"` : "type=\"text\""} value="${escapeHtml(value ?? "")}"></label>`;
  }

  _renderDialog() {
    if (this._dialogIndex === null || !this._rows[this._dialogIndex]) return "";
    const index = this._dialogIndex;
    const row = this._rows[index];
    const definition = this._definition(row);
    const fields = definition.advanced
      .map((spec) => this._advancedInput(index, spec, row.data[spec.key]))
      .join("");
    return `
      <div class="dialog-backdrop" data-action="close-dialog-backdrop">
        <section class="dialog" role="dialog" aria-modal="true">
          <header>
            <div>
              <h2>${escapeHtml(this._t.details)}</h2>
              <p>${escapeHtml(this._label(definition.label))} · ${escapeHtml(row.data.name || `#${index + 1}`)}</p>
            </div>
            <button class="icon-button" data-action="close-dialog">×</button>
          </header>
          <div class="advanced-grid">
            ${fields || `<p class="empty-dialog">${escapeHtml(this._t.noRows)}</p>`}
          </div>
          <footer><button class="primary" data-action="close-dialog">${escapeHtml(this._t.close)}</button></footer>
        </section>
      </div>`;
  }

  _styles() {
    return `
      :host { display: block; min-height: 100vh; color: var(--primary-text-color); background: var(--primary-background-color); font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif); }
      * { box-sizing: border-box; }
      button, input, select { font: inherit; color: inherit; }
      button { cursor: pointer; }
      button:disabled { cursor: default; opacity: .45; }
      .page { padding: 20px; max-width: 1900px; margin: 0 auto; }
      .page-header { display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; margin-bottom: 16px; }
      h1 { font-size: 28px; line-height: 1.2; margin: 0 0 6px; }
      .subtitle { margin: 0; color: var(--secondary-text-color); }
      .header-actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; justify-content: flex-end; }
      .dirty-indicator { font-size: 13px; color: var(--secondary-text-color); white-space: nowrap; }
      .dirty-indicator.is-dirty { color: var(--warning-color, #f59e0b); font-weight: 600; }
      .card { background: var(--card-background-color); border-radius: var(--ha-card-border-radius, 12px); box-shadow: var(--ha-card-box-shadow, 0 2px 6px rgba(0,0,0,.15)); overflow: hidden; }
      .toolbar { display: grid; grid-template-columns: minmax(210px, 1fr) minmax(240px, 1.6fr) auto auto; gap: 10px; padding: 14px; border-bottom: 1px solid var(--divider-color); align-items: end; }
      .toolbar-group { display: flex; gap: 8px; align-items: end; }
      .toolbar label { display: grid; gap: 5px; font-size: 12px; color: var(--secondary-text-color); }
      .toolbar input, .toolbar select, .advanced-grid input, .advanced-grid select { height: 40px; border: 1px solid var(--divider-color); background: var(--card-background-color); border-radius: 7px; padding: 0 10px; min-width: 0; }
      .toolbar .search { width: 100%; }
      .selection-bar { display: flex; min-height: 48px; align-items: center; gap: 8px; padding: 8px 14px; background: color-mix(in srgb, var(--primary-color) 8%, var(--card-background-color)); border-bottom: 1px solid var(--divider-color); }
      .selection-bar .spacer { flex: 1; }
      .hint { font-size: 12px; color: var(--secondary-text-color); }
      .primary, .secondary, .danger-button, .small-button { min-height: 38px; padding: 0 14px; border-radius: 7px; border: 1px solid transparent; font-weight: 500; }
      .primary { color: var(--text-primary-color, white); background: var(--primary-color); }
      .secondary, .small-button { background: transparent; color: var(--primary-color); border-color: var(--primary-color); }
      .danger-button { color: var(--error-color); background: transparent; border-color: var(--error-color); }
      .table-wrap { overflow: auto; max-height: calc(100vh - 275px); min-height: 260px; }
      table { border-collapse: separate; border-spacing: 0; width: max-content; min-width: 100%; }
      th { position: sticky; top: 0; z-index: 2; text-align: left; font-size: 12px; color: var(--secondary-text-color); font-weight: 600; background: var(--card-background-color); border-bottom: 1px solid var(--divider-color); padding: 9px 7px; white-space: nowrap; }
      td { padding: 5px 4px; border-bottom: 1px solid var(--divider-color); background: var(--card-background-color); vertical-align: top; }
      tbody tr:hover td { background: color-mix(in srgb, var(--primary-color) 4%, var(--card-background-color)); }
      tr.row-error td { background: color-mix(in srgb, var(--error-color) 7%, var(--card-background-color)); }
      .check, .row-number, .center { text-align: center; }
      .check { width: 34px; vertical-align: middle; }
      .row-number { width: 42px; color: var(--secondary-text-color); padding-top: 14px; }
      .type-cell { min-width: 170px; }
      .cell-input { height: 36px; border: 1px solid transparent; background: transparent; border-radius: 5px; padding: 0 7px; min-width: 118px; width: 100%; }
      .cell-input:hover { border-color: var(--divider-color); background: var(--card-background-color); }
      .cell-input:focus { outline: none; border-color: var(--primary-color); box-shadow: 0 0 0 1px var(--primary-color); background: var(--card-background-color); }
      .cell-input.invalid { border-color: var(--error-color); background: color-mix(in srgb, var(--error-color) 8%, var(--card-background-color)); }
      td:nth-child(4), td:nth-child(5) { min-width: 170px; }
      td:nth-child(6), td:nth-child(7) { min-width: 190px; }
      td:nth-child(8), td:nth-child(9) { min-width: 130px; }
      td:nth-child(10) { min-width: 105px; }
      td:nth-child(11) { min-width: 150px; }
      .not-applicable { display: block; color: var(--disabled-text-color); text-align: center; padding-top: 10px; }
      .row-actions { white-space: nowrap; }
      .icon-button { width: 34px; height: 34px; border: 0; border-radius: 50%; background: transparent; font-size: 20px; line-height: 1; }
      .icon-button:hover { background: var(--secondary-background-color); }
      .icon-button.danger { color: var(--error-color); }
      .row-error-text { display: block; color: var(--error-color); font-size: 11px; line-height: 1.25; padding: 3px 7px 0; max-width: 210px; }
      .empty-state { padding: 50px 20px; text-align: center; color: var(--secondary-text-color); }
      .dialog-backdrop { position: fixed; inset: 0; z-index: 20; display: grid; place-items: center; background: rgba(0,0,0,.45); padding: 18px; }
      .dialog { width: min(760px, 100%); max-height: min(760px, 92vh); overflow: auto; background: var(--card-background-color); border-radius: 14px; box-shadow: 0 18px 50px rgba(0,0,0,.35); }
      .dialog header { position: sticky; top: 0; z-index: 1; display: flex; justify-content: space-between; align-items: flex-start; padding: 18px 20px; background: var(--card-background-color); border-bottom: 1px solid var(--divider-color); }
      .dialog h2 { margin: 0 0 4px; font-size: 21px; }
      .dialog p { margin: 0; color: var(--secondary-text-color); }
      .advanced-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; padding: 20px; }
      .advanced-grid label:not(.advanced-checkbox) { display: grid; gap: 6px; color: var(--secondary-text-color); font-size: 13px; }
      .advanced-checkbox { min-height: 42px; display: flex; align-items: center; gap: 9px; }
      .advanced-checkbox input { width: 18px; height: 18px; }
      .dialog footer { display: flex; justify-content: flex-end; padding: 14px 20px; border-top: 1px solid var(--divider-color); }
      .empty-dialog { grid-column: 1 / -1; color: var(--secondary-text-color); text-align: center; }
      .toast { position: fixed; right: 20px; bottom: 20px; z-index: 30; max-width: 520px; padding: 13px 16px; color: white; background: #374151; border-radius: 8px; box-shadow: 0 8px 28px rgba(0,0,0,.3); }
      .toast.success { background: #18794e; }
      .toast.error { background: var(--error-color, #b91c1c); }
      .toast.warning { background: #9a6700; }
      @media (max-width: 900px) {
        .page { padding: 10px; }
        .page-header { display: block; }
        .header-actions { justify-content: flex-start; margin-top: 12px; }
        .toolbar { grid-template-columns: 1fr; }
        .toolbar-group { flex-wrap: wrap; }
        .selection-bar { overflow-x: auto; }
        .hint { display: none; }
        .table-wrap { max-height: calc(100vh - 390px); }
        .advanced-grid { grid-template-columns: 1fr; }
      }
    `;
  }

  _render() {
    if (!this.shadowRoot) return;
    const visible = this._visibleRows();
    const entries = this._entries
      .map(
        (entry) =>
          `<option value="${escapeHtml(entry.entry_id)}" ${entry.entry_id === this._entryId ? "selected" : ""}>${escapeHtml(entry.title)}${entry.host ? ` · ${escapeHtml(entry.host)}` : ""} (${entry.entity_count})</option>`,
      )
      .join("");
    const allVisibleSelected = visible.length > 0 && visible.every(({ index }) => this._selected.has(index));
    const rows = visible.map(({ row, index }) => this._renderRow(row, index)).join("");

    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <main class="page">
        <div class="page-header">
          <div>
            <h1>${escapeHtml(this._t.title)}</h1>
            <p class="subtitle">${escapeHtml(this._t.subtitle)}</p>
          </div>
          <div class="header-actions">
            <span class="dirty-indicator ${this._dirty ? "is-dirty" : ""}">${escapeHtml(this._dirty ? this._t.unsaved : this._t.saved)}</span>
            <button class="secondary" data-action="discard" ${!this._dirty || this._saving ? "disabled" : ""}>${escapeHtml(this._t.discard)}</button>
            <button class="primary" data-action="save" ${!this._dirty || this._saving ? "disabled" : ""}>${escapeHtml(this._saving ? this._t.loading : this._t.save)}</button>
          </div>
        </div>

        <section class="card">
          <div class="toolbar">
            <label>${escapeHtml(this._t.plc)}
              <select data-action="entry" ${this._loading ? "disabled" : ""}>${entries}</select>
            </label>
            <input class="search" data-action="search" type="search" value="${escapeHtml(this._query)}" placeholder="${escapeHtml(this._t.search)}">
            <div class="toolbar-group">
              <select data-action="add-type">${this._typeOptions(this._addType)}</select>
              <button class="primary" data-action="add" ${!this._entryId ? "disabled" : ""}>+ ${escapeHtml(this._t.add)}</button>
            </div>
          </div>

          <div class="selection-bar">
            <strong>${this._selected.size} ${escapeHtml(this._t.selected)}</strong>
            <button class="small-button" data-action="copy" ${!this._selected.size ? "disabled" : ""}>${escapeHtml(this._t.copy)}</button>
            <button class="small-button" data-action="fill" ${this._selected.size < 2 ? "disabled" : ""}>${escapeHtml(this._t.fill)}</button>
            <button class="danger-button" data-action="bulk-delete" ${!this._selected.size ? "disabled" : ""}>${escapeHtml(this._t.remove)}</button>
            <span class="spacer"></span>
            <span class="hint">${escapeHtml(this._t.excelTip)}</span>
          </div>

          ${this._loading
            ? `<div class="empty-state">${escapeHtml(this._t.loading)}</div>`
            : !this._entries.length
              ? `<div class="empty-state">${escapeHtml(this._t.noEntries)}</div>`
              : `<div class="table-wrap">
                  <table>
                    <thead><tr>
                      <th class="check"><input type="checkbox" data-action="select-all" ${allVisibleSelected ? "checked" : ""}></th>
                      <th>#</th><th>${escapeHtml(this._t.type)}</th><th>${escapeHtml(this._t.device)}</th><th>${escapeHtml(this._t.name)}</th>
                      <th>${escapeHtml(this._t.address1)}</th><th>${escapeHtml(this._t.address2)}</th><th>${escapeHtml(this._t.unit)}</th>
                      <th>${escapeHtml(this._t.deviceClass)}</th><th>${escapeHtml(this._t.interval)}</th><th>${escapeHtml(this._t.area)}</th>
                      <th>${escapeHtml(this._t.more)}</th><th>${escapeHtml(this._t.actions)}</th>
                    </tr></thead>
                    <tbody>${rows || `<tr><td colspan="13"><div class="empty-state">${escapeHtml(this._t.noRows)}</div></td></tr>`}</tbody>
                  </table>
                </div>`}
        </section>
      </main>

      <datalist id="device-group-list">${this._groups.map((group) => `<option value="${escapeHtml(group)}"></option>`).join("")}</datalist>
      <datalist id="entity-id-list">${Object.keys(this._hass?.states ?? {}).map((entityId) => `<option value="${escapeHtml(entityId)}"></option>`).join("")}</datalist>
      ${this._renderDialog()}
      ${this._toast ? `<div class="toast ${escapeHtml(this._toast.kind)}">${escapeHtml(this._toast.message)}</div>` : ""}
    `;
    this._bindEvents();
  }

  _bindEvents() {
    if (this._eventsBound) return;
    this._eventsBound = true;
    const root = this.shadowRoot;
    root.addEventListener("input", (event) => {
      const target = event.target;
      if (target.dataset.action === "search") {
        this._query = target.value;
        this._render();
        this.shadowRoot.querySelector('[data-action="search"]')?.focus();
        return;
      }
      if (target.dataset.key) this._writeElementValue(target);
    });
    root.addEventListener("change", async (event) => {
      const target = event.target;
      const action = target.dataset.action;
      if (action === "entry") {
        if (this._dirty && !window.confirm(this._t.confirmSwitch)) {
          target.value = this._entryId;
          return;
        }
        await this._loadEntry(target.value);
      } else if (action === "add-type") {
        this._addType = target.value;
      } else if (action === "row-type") {
        this._switchRowType(Number(target.dataset.index), target.value);
      } else if (action === "select-row") {
        const index = Number(target.dataset.index);
        if (target.checked) this._selected.add(index);
        else this._selected.delete(index);
        this._render();
      } else if (action === "select-all") {
        this._visibleRows().forEach(({ index }) => {
          if (target.checked) this._selected.add(index);
          else this._selected.delete(index);
        });
        this._render();
      } else if (target.dataset.key) {
        this._writeElementValue(target);
      }
    });
    root.addEventListener("focusin", (event) => {
      if (event.target.dataset.copyField) this._activeField = event.target.dataset.copyField;
    });
    root.addEventListener("paste", (event) => this._pasteGrid(event));
    root.addEventListener("click", async (event) => {
      const target = event.target.closest("[data-action]");
      if (!target) return;
      const action = target.dataset.action;
      const index = Number(target.dataset.index);
      if (action === "add") {
        this._rows.push(this._newRow());
        this._markDirty();
        this._render();
        this.shadowRoot.querySelector(`[data-index="${this._rows.length - 1}"][data-copy-field="primary"]`)?.focus();
      } else if (action === "duplicate") {
        const copy = JSON.parse(JSON.stringify(this._rows[index]));
        this._rows.splice(index + 1, 0, copy);
        this._markDirty();
        this._render();
      } else if (action === "delete") {
        this._rows.splice(index, 1);
        this._selected = new Set([...this._selected].filter((item) => item !== index).map((item) => (item > index ? item - 1 : item)));
        this._markDirty();
        this._render();
      } else if (action === "bulk-delete") {
        this._rows = this._rows.filter((_, rowIndex) => !this._selected.has(rowIndex));
        this._selected.clear();
        this._markDirty();
        this._render();
      } else if (action === "copy") {
        await this._copySelected();
      } else if (action === "fill") {
        this._fillDown();
      } else if (action === "advanced") {
        this._dialogIndex = index;
        this._render();
      } else if (action === "close-dialog") {
        this._dialogIndex = null;
        this._render();
      } else if (action === "close-dialog-backdrop" && event.target === target) {
        this._dialogIndex = null;
        this._render();
      } else if (action === "save") {
        await this._save();
      } else if (action === "discard") {
        if (window.confirm(this._t.confirmDiscard)) await this._loadEntry(this._entryId);
      }
    });
  }
}

if (!customElements.get("s7plc-entity-editor")) {
  customElements.define("s7plc-entity-editor", S7PLCEntityEditor);
}
