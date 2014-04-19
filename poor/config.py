# -*- coding: utf-8 -*-

# Copyright (C) 2014 Osmo Salomaa
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Attribute dictionary of configuration values."""

import copy
import json
import os
import poor
import sys

__all__ = ("ConfigurationStore",)

DEFAULTS = {
    "auto_center": False,
    "center": [24.941, 60.169],
    "download_timeout": 10,
    "geocoder": "mapquest_nominatim",
    "gps_update_interval": 3,
    "tilesource": "mapquest_open",
    "zoom": 15,
}


class AttrDict(dict):

    """Dictionary with attribute access to keys."""

    def __init__(self, *args, **kwargs):
        """Initialize an :class:`AttrDict` instance."""
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self


class ConfigurationStore(AttrDict):

    """Attribute dictionary of configuration values."""

    def __init__(self):
        """Initialize a :class:`Configuration` instance."""
        AttrDict.__init__(self, copy.deepcopy(DEFAULTS))

    def _coerce(self, value, ref):
        """Coerce type of `value` to match `ref`."""
        if isinstance(value, list):
            return [self._coerce(x, ref[0]) for x in value]
        return type(ref)(value)

    def _comment_unmodified(self, root=None, defaults=None):
        """Return values with those at default commented out."""
        root = (self if root is None else root)
        defaults = (DEFAULTS if defaults is None else defaults)
        out = {}
        for name, value in root.items():
            if isinstance(value, dict):
                value = self._comment_unmodified(value,
                                                 defaults.setdefault(name, {}))

            else:
                if name in defaults:
                    if value == defaults[name]:
                        name = "# {}".format(name)
            out[name] = copy.deepcopy(value)
        return out

    def get_default(self, option):
        """
        Get the default value of `option`.

        For nested keys, `option` can be a dotted string,
        e.g. 'router.mycoolrouter.type'.
        """
        defaults = DEFAULTS
        for section in option.split(".")[:-1]:
            defaults = defaults[section]
        name = option.split(".")[-1]
        return copy.deepcopy(defaults[name])

    def read(self, path=None):
        """Read values of options from JSON file at `path`."""
        if path is None:
            path = os.path.join(poor.CONFIG_HOME_DIR, "poor-maps.json")
        if not os.path.isfile(path): return
        try:
            with open(path, "r", encoding="utf_8") as f:
                self._update(json.load(f))
        except Exception as error:
            return print("Failed to read file {}: {}"
                         .format(repr(path), str(error)),
                         file=sys.stderr)

    def _register(self, values, root=None, defaults=None):
        """Add entries for `values` if missing."""
        root = (self if root is None else root)
        defaults = (DEFAULTS if defaults is None else defaults)
        for name, value in values.items():
            if isinstance(value, dict):
                self._register(values[name],
                               root.setdefault(name, AttrDict()),
                               defaults.setdefault(name, {}))

            else:
                root.setdefault(name, copy.deepcopy(value))
                defaults.setdefault(name, copy.deepcopy(value))

    def register_router(self, name, values):
        """
        Add configuration `values` for router `name` if missing.

        e.g. calling ``register_router("foo", {"type": "car"})`` will make type
        available as ``poor.conf.router.foo.type``.
        """
        self._register({"router": {name: values}}, self)

    def set(self, option, value):
        """
        Set the value of `option`.

        For nested keys, `option` can be a dotted string,
        e.g. 'router.mycoolrouter.type'.
        """
        root = self
        for section in option.split(".")[:-1]:
            if not section in root:
                # Create missing hierarchies.
                root[section] = AttrDict()
            root = root[section]
        name = option.split(".")[-1]
        root[name] = copy.deepcopy(value)

    def _update(self, values, root=None, defaults=None, path=()):
        """Load values of options after validation."""
        root = (self if root is None else root)
        defaults = (DEFAULTS if defaults is None else defaults)
        for name, value in values.items():
            # Ignore options commented out.
            if name.startswith("#"): continue
            if isinstance(value, dict):
                self._update(value,
                             root.setdefault(name, AttrDict()),
                             defaults.setdefault(name, {}),
                             (path + (name,)))

            else:
                try:
                    if name in defaults:
                        # Be liberal, but careful in what to accept.
                        value = self._coerce(value, defaults[name])
                    root[name] = copy.deepcopy(value)
                except Exception as error:
                    full_name = ".".join(path + (name,))
                    print("Discarding bad option-value pair ({}, {}): {}"
                          .format(repr(full_name), repr(value), str(error)),
                          file=sys.stderr)

    def write(self, path=None):
        """Write values of options to JSON file at `path`."""
        if path is None:
            path = os.path.join(poor.CONFIG_HOME_DIR, "poor-maps.json")
        directory = os.path.dirname(path)
        directory = poor.util.makedirs(directory)
        if directory is None: return
        out = self._comment_unmodified()
        try:
            with open(path, "w", encoding="utf_8") as f:
                json.dump(out, f, ensure_ascii=False, indent=4, sort_keys=True)
        except Exception as error:
            print("Failed to write file {}: {}"
                  .format(repr(path), str(error)),
                  file=sys.stderr)
