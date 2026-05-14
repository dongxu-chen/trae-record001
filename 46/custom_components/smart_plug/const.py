from homeassistant.const import (
    POWER_WATT,
    ENERGY_KILO_WATT_HOUR,
    ELECTRIC_POTENTIAL_VOLT,
    ELECTRIC_CURRENT_AMPERE,
)

DOMAIN = "smart_plug"

CONF_DEFAULT_POWER = "default_power"
CONF_VOLTAGE = "voltage"
CONF_CURRENT = "current"
CONF_POWER = "power"
CONF_ENERGY = "energy"
CONF_POLL_INTERVAL = "poll_interval"
CONF_AUTOMATION = "automation"
CONF_MAX_POWER = "max_power"

DEFAULT_POLL_INTERVAL = 60
DEFAULT_VOLTAGE = 220.0
DEFAULT_CURRENT = 0.0
DEFAULT_POWER = 100.0
DEFAULT_ENERGY = 0.0

ATTR_POWER = "power"
ATTR_ENERGY = "energy"
ATTR_VOLTAGE = "voltage"
ATTR_CURRENT = "current"

DEVICE_CLASS_POWER = "power"
DEVICE_CLASS_ENERGY = "energy"
DEVICE_CLASS_VOLTAGE = "voltage"
DEVICE_CLASS_CURRENT = "current"

STATE_CLASS_MEASUREMENT = "measurement"
STATE_CLASS_TOTAL_INCREASING = "total_increasing"

ICON_POWER = "mdi:flash"
ICON_ENERGY = "mdi:lightning-bolt"
ICON_VOLTAGE = "mdi:current-ac"
ICON_CURRENT = "mdi:current-dc"
