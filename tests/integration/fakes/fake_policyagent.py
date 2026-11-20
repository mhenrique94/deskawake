#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

PA_NAME = "org.kde.Solid.PowerManagement"
PA_PATH = "/org/kde/Solid/PowerManagement/PolicyAgent"
PA_IFACE = "org.kde.Solid.PowerManagement.PolicyAgent"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"



def _plain(value):
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


class JsonlLog:
    def __init__(self, path):
        self._file = open(path, "a", encoding="utf-8") if path else None

    def write(self, **entry):
        if self._file is None:
            return
        self._file.write(json.dumps(_plain(entry), ensure_ascii=False) + "\n")
        self._file.flush()

    def close(self):
        if self._file is not None:
            self._file.close()
            self._file = None


class PolicyAgent(dbus.service.Object):
    def __init__(self, bus, log, *, debounce_ms, fail, no_active, no_has):
        super().__init__(bus, PA_PATH)
        self.log = log
        self.debounce_ms = debounce_ms
        self.fail = fail
        self.no_active = no_active
        self.no_has = no_has
        self.next_cookie = 500
        self.inhibitions = {}

    def _unknown(self, name):
        return dbus.exceptions.DBusException("método/propriedade ausente", name=name)

    @dbus.service.method(PA_IFACE, in_signature="uss", out_signature="u")
    def AddInhibition(self, inhibition_type, who, why):
        cookie = self.next_cookie
        self.next_cookie += 1
        inhibition_type = int(inhibition_type)
        self.inhibitions[cookie] = {
            "type": inhibition_type,
            "who": str(who),
            "why": str(why),
            "active": False,
        }
        self.log.write(
            backend="policyagent",
            method="AddInhibition",
            args=[inhibition_type, str(who), str(why)],
            cookie=cookie,
        )
        if not self.fail:
            GLib.timeout_add(self.debounce_ms, self._activate, cookie)
        return dbus.UInt32(cookie)

    def _activate(self, cookie):
        inhibition = self.inhibitions.get(cookie)
        if inhibition is not None:
            inhibition["active"] = True
            self.log.write(
                backend="policyagent",
                event="inhibition_active",
                cookie=cookie,
            )
        return False

    @dbus.service.method(PA_IFACE, in_signature="u", out_signature="")
    def ReleaseInhibition(self, cookie):
        cookie = int(cookie)
        self.inhibitions.pop(cookie, None)
        self.log.write(
            backend="policyagent", method="ReleaseInhibition", args=[cookie]
        )

    @dbus.service.method(PA_IFACE, in_signature="u", out_signature="b")
    def HasInhibition(self, inhibition_type):
        inhibition_type = int(inhibition_type)
        if self.no_has:
            raise self._unknown("org.freedesktop.DBus.Error.UnknownMethod")
        active = any(
            inhibition["active"] and (inhibition["type"] & inhibition_type)
            for inhibition in self.inhibitions.values()
        )
        self.log.write(
            backend="policyagent",
            method="HasInhibition",
            args=[inhibition_type],
            active=active,
        )
        return dbus.Boolean(active)

    @dbus.service.method(PROPERTIES_IFACE, in_signature="ss", out_signature="v")
    def Get(self, interface, prop):
        if interface != PA_IFACE or prop != "ActiveInhibitions":
            raise self._unknown("org.freedesktop.DBus.Error.UnknownProperty")
        if self.no_active:
            raise self._unknown("org.freedesktop.DBus.Error.UnknownProperty")
        entries = [
            (
                "idle",
                inhibition["who"],
                inhibition["why"],
                "block",
                dbus.UInt32(3),
            )
            for inhibition in self.inhibitions.values()
            if inhibition["active"]
        ]
        self.log.write(
            backend="policyagent",
            method="Get",
            args=[interface, prop],
            count=len(entries),
        )
        return dbus.Array([dbus.Struct(entry, signature="ssssu") for entry in entries], signature="(ssssu)")

    @dbus.service.method(PROPERTIES_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != PA_IFACE:
            raise self._unknown("org.freedesktop.DBus.Error.UnknownInterface")
        return dbus.Dictionary(
            {"ActiveInhibitions": self.Get(interface, "ActiveInhibitions")},
            signature="sv",
        )


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--log")
    parser.add_argument("--debounce-ms", type=int, default=5000)
    parser.add_argument("--fail", action="store_true")
    parser.add_argument("--no-active-inhibitions", action="store_true")
    parser.add_argument("--no-has-inhibition", action="store_true")
    args = parser.parse_args(argv)

    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    bus.set_exit_on_disconnect(False)
    log = JsonlLog(args.log)
    log.write(event="started", pid=os.getpid())

    if bus.request_name(PA_NAME, dbus.bus.NAME_FLAG_DO_NOT_QUEUE) not in (
        dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER,
        dbus.bus.REQUEST_NAME_REPLY_ALREADY_OWNER,
    ):
        log.write(event="name_busy", name=PA_NAME)
        return 2

    PolicyAgent(
        bus,
        log,
        debounce_ms=args.debounce_ms,
        fail=args.fail,
        no_active=args.no_active_inhibitions,
        no_has=args.no_has_inhibition,
    )

    loop = GLib.MainLoop()

    def on_disconnected(*_args):
        log.write(event="bus_disconnected")
        GLib.idle_add(loop.quit)

    bus.add_signal_receiver(
        on_disconnected,
        signal_name="Disconnected",
        dbus_interface=dbus.LOCAL_IFACE,
        path=dbus.LOCAL_PATH,
    )

    try:
        loop.run()
    finally:
        log.write(event="stopped", pid=os.getpid())
        log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
