#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

from fake_common import JsonlLog
from dbus_contract import (
    BACKEND_IFACES,
    BACKEND_NAMES,
    BACKEND_PATHS,
    GSM_IDLE_FLAG,
    POLICYAGENT_CHANGE_SCREEN_SETTINGS,
    POLICYAGENT_IFACE,
    POLICYAGENT_NAME,
    POLICYAGENT_PATH,
)

FDO_NAME = BACKEND_NAMES["fdo"]
FDO_PATH = BACKEND_PATHS["fdo"]
FDO_IFACE = BACKEND_IFACES["fdo"]

MATE_NAME = BACKEND_NAMES["mate"]
MATE_PATH = BACKEND_PATHS["mate"]
MATE_IFACE = BACKEND_IFACES["mate"]
MATE_SINCE = "2026-01-01 00:00:00"

GSM_NAME = BACKEND_NAMES["gsm"]
GSM_PATH = BACKEND_PATHS["gsm"]
GSM_IFACE = BACKEND_IFACES["gsm"]

PA_NAME = POLICYAGENT_NAME
PA_PATH = POLICYAGENT_PATH
PA_IFACE = POLICYAGENT_IFACE


class State:
    def __init__(self, bus, log, *, kde=False, gsm=False):
        self.bus = bus
        self.log = log
        self.kde = kde
        self.gsm_enabled = gsm
        self.next_cookie = 100
        self.fdo = {}
        self.mate = {}
        self.gsm = {}
        self.mate_proxy = {}
        self.policy_cookies = {}

    def cookie(self):
        value = self.next_cookie
        self.next_cookie += 1
        return value

    def add_gsm(self, who, why, flags):
        cookie = self.cookie()
        self.gsm[cookie] = int(flags)
        return cookie

    def remove_gsm(self, cookie):
        return self.gsm.pop(int(cookie), None)


class FdoObject(dbus.service.Object):
    def __init__(self, bus, state):
        super().__init__(bus, FDO_PATH)
        self.state = state

    @dbus.service.method(FDO_IFACE, in_signature="ss", out_signature="u")
    def Inhibit(self, who, why):
        cookie = self.state.cookie()
        self.state.fdo[cookie] = (str(who), str(why))
        self.state.log.write(
            backend="fdo", method="Inhibit", args=[str(who), str(why)], cookie=cookie
        )
        if self.state.kde:
            self._add_policy_inhibition(cookie, str(who), str(why))
        return dbus.UInt32(cookie)

    @dbus.service.method(FDO_IFACE, in_signature="u", out_signature="")
    def UnInhibit(self, cookie):
        cookie = int(cookie)
        self.state.fdo.pop(cookie, None)
        self.state.log.write(backend="fdo", method="UnInhibit", args=[cookie])
        policy_cookie = self.state.policy_cookies.pop(cookie, None)
        if policy_cookie is not None:
            self._release_policy_inhibition(policy_cookie)

    def _add_policy_inhibition(self, cookie, who, why):
        try:
            proxy = self.state.bus.get_object(PA_NAME, PA_PATH)
            interface = dbus.Interface(proxy, PA_IFACE)
            policy_cookie = int(
                interface.AddInhibition(
                    dbus.UInt32(POLICYAGENT_CHANGE_SCREEN_SETTINGS), who, why
                )
            )
        except Exception as exc:
            self.state.log.write(
                backend="policyagent",
                event="error",
                method="AddInhibition",
                error=str(exc),
            )
            return
        self.state.policy_cookies[cookie] = policy_cookie
        self.state.log.write(
            backend="policyagent",
            method="AddInhibition",
            args=[POLICYAGENT_CHANGE_SCREEN_SETTINGS, who, why],
            cookie=policy_cookie,
        )

    def _release_policy_inhibition(self, policy_cookie):
        try:
            proxy = self.state.bus.get_object(PA_NAME, PA_PATH)
            interface = dbus.Interface(proxy, PA_IFACE)
            interface.ReleaseInhibition(dbus.UInt32(policy_cookie))
        except Exception as exc:
            self.state.log.write(
                backend="policyagent",
                event="error",
                method="ReleaseInhibition",
                error=str(exc),
            )
            return
        self.state.log.write(
            backend="policyagent",
            method="ReleaseInhibition",
            args=[policy_cookie],
        )


class MateObject(dbus.service.Object):
    def __init__(self, bus, state):
        super().__init__(bus, MATE_PATH)
        self.state = state

    @dbus.service.method(MATE_IFACE, in_signature="ss", out_signature="u")
    def Inhibit(self, who, why):
        cookie = self.state.cookie()
        self.state.mate[cookie] = (str(who), str(why))
        self.state.log.write(
            backend="mate", method="Inhibit", args=[str(who), str(why)], cookie=cookie
        )
        if self.state.gsm_enabled:
            gsm_cookie = self.state.add_gsm(str(who), str(why), GSM_IDLE_FLAG)
            self.state.mate_proxy[cookie] = gsm_cookie
            self.state.log.write(
                backend="gsm",
                method="Inhibit",
                args=[str(who), 0, str(why), GSM_IDLE_FLAG],
                cookie=gsm_cookie,
                proxy="mate",
            )
        return dbus.UInt32(cookie)

    @dbus.service.method(MATE_IFACE, in_signature="u", out_signature="")
    def UnInhibit(self, cookie):
        cookie = int(cookie)
        self.state.mate.pop(cookie, None)
        self.state.log.write(backend="mate", method="UnInhibit", args=[cookie])
        gsm_cookie = self.state.mate_proxy.pop(cookie, None)
        if gsm_cookie is not None:
            self.state.remove_gsm(gsm_cookie)
            self.state.log.write(
                backend="gsm",
                method="Uninhibit",
                args=[gsm_cookie],
                proxy="mate",
            )

    @dbus.service.method(MATE_IFACE, in_signature="", out_signature="as")
    def GetInhibitors(self):
        items = [
            f'Application="{who}"; Since="{MATE_SINCE}"; Reason="{why}";'
            for who, why in self.state.mate.values()
        ]
        self.state.log.write(
            backend="mate", method="GetInhibitors", args=[], cookie=None
        )
        return dbus.Array(items, signature="s")


class GsmObject(dbus.service.Object):
    def __init__(self, bus, state):
        super().__init__(bus, GSM_PATH)
        self.state = state

    @dbus.service.method(GSM_IFACE, in_signature="susu", out_signature="u")
    def Inhibit(self, who, xid, why, flags):
        cookie = self.state.add_gsm(str(who), str(why), int(flags))
        self.state.log.write(
            backend="gsm",
            method="Inhibit",
            args=[str(who), int(xid), str(why), int(flags)],
            cookie=cookie,
        )
        return dbus.UInt32(cookie)

    @dbus.service.method(GSM_IFACE, in_signature="u", out_signature="")
    def Uninhibit(self, cookie):
        self.state.remove_gsm(int(cookie))
        self.state.log.write(backend="gsm", method="Uninhibit", args=[int(cookie)])

    @dbus.service.method(GSM_IFACE, in_signature="u", out_signature="b")
    def IsInhibited(self, flags):
        flags = int(flags)
        active = any(value & flags for value in self.state.gsm.values())
        self.state.log.write(
            backend="gsm", method="IsInhibited", args=[flags], active=active
        )
        return dbus.Boolean(active)

    @dbus.service.method(GSM_IFACE, in_signature="", out_signature="")
    def DropMate(self):
        self.state.bus.release_name(MATE_NAME)
        self.state.log.write(event="mate_name_dropped")

    @dbus.service.method(GSM_IFACE, in_signature="", out_signature="")
    def RestoreMate(self):
        reply = self.state.bus.request_name(
            MATE_NAME, dbus.bus.NAME_FLAG_DO_NOT_QUEUE
        )
        if reply not in (
            dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER,
            dbus.bus.REQUEST_NAME_REPLY_ALREADY_OWNER,
        ):
            raise dbus.DBusException("não foi possível restaurar o MATE")
        self.state.log.write(event="mate_name_restored")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--fdo", action="store_true")
    parser.add_argument("--mate", action="store_true")
    parser.add_argument("--gsm", action="store_true")
    parser.add_argument("--kde", action="store_true")
    parser.add_argument("--log")
    args = parser.parse_args(argv)

    if not any((args.fdo, args.mate, args.gsm)):
        parser.error("pelo menos um backend é obrigatório")

    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    bus.set_exit_on_disconnect(False)
    log = JsonlLog(args.log)
    log.write(event="started", pid=os.getpid())
    state = State(bus, log, kde=args.kde, gsm=args.gsm)

    specs = []
    if args.fdo:
        specs.append((FDO_NAME, FdoObject))
    if args.mate:
        specs.append((MATE_NAME, MateObject))
    if args.gsm:
        specs.append((GSM_NAME, GsmObject))

    objects = []
    for name, factory in specs:
        reply = bus.request_name(name, dbus.bus.NAME_FLAG_DO_NOT_QUEUE)
        if reply not in (
            dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER,
            dbus.bus.REQUEST_NAME_REPLY_ALREADY_OWNER,
        ):
            log.write(event="name_busy", name=name)
            return 2
        objects.append(factory(bus, state))

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
