pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.kirigami as Kirigami
import org.kde.plasma.workspace.dbus as DBus

PlasmoidItem {
    id: root

    readonly property string serviceName: "org.local.DeskAwake"
    readonly property string objectPath: "/org/local/DeskAwake"
    readonly property string ifaceName: "org.local.DeskAwake"
    readonly property int verifyWindowMs: 6000
    readonly property int pillWidth: 124
    readonly property int pillHeight: 42

    property string state: "off"
    property string lastError: ""
    property bool callPending: false
    property bool verifying: false
    property int callToken: 0

    Layout.minimumWidth: 124
    Layout.preferredWidth: 124
    Layout.maximumWidth: 124
    Layout.minimumHeight: 42
    Layout.preferredHeight: 42
    Layout.maximumHeight: 42

    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    toolTipMainText: "DeskAwake"
    toolTipSubText: root.state === "error" ? root.lastError : ""
    toolTipTextFormat: Text.PlainText

    DBus.SignalWatcher {
        id: signalWatcher
        busType: DBus.BusType.Session
        service: root.serviceName
        path: root.objectPath
        iface: root.ifaceName

        function dbusStateChanged(state) {
            const value = String(state)
            root.applyState(value)
            if (value === "error") {
                root.requestLastError()
            }
        }
    }

    DBus.DBusServiceWatcher {
        id: daemonWatcher
        busType: DBus.BusType.Session
        watchedService: root.serviceName

        onRegisteredChanged: {
            if (registered) {
                root.syncFromDaemon()
            } else {
                root.invalidateCalls()
                root.applyState("off")
                root.lastError = ""
            }
        }
    }

    Timer {
        id: verifyTimer
        interval: root.verifyWindowMs
        repeat: false
        running: root.verifying
        onTriggered: root.stopVerification()
    }

    // O containment do desktop reserva uma célula maior que a pílula; manter a pílula
    // em 124×42 centralizada preserva a forma aprovada independentemente da célula.
    PlasmaCore.ToolTipArea {
        id: pillToolTip
        anchors.centerIn: parent
        width: root.pillWidth
        height: root.pillHeight
        mainText: "DeskAwake"
        subText: root.state === "error" ? root.lastError : ""
        textFormat: Text.PlainText
        active: root.state === "error"
        location: Plasmoid.location

        Rectangle {
            id: pill
            anchors.fill: parent
            radius: 12
            border.width: 1
            color: Qt.rgba(
                Kirigami.Theme.backgroundColor.r,
                Kirigami.Theme.backgroundColor.g,
                Kirigami.Theme.backgroundColor.b,
                0.88
            )
            border.color: Qt.rgba(
                Kirigami.Theme.textColor.r,
                Kirigami.Theme.textColor.g,
                Kirigami.Theme.textColor.b,
                pillToolTip.containsMouse ? 0.28 : 0.18
            )

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 1
                anchors.rightMargin: 1
                spacing: 4

                Item {
                    id: symbolSlot
                    Layout.minimumWidth: 22
                    Layout.preferredWidth: 22
                    Layout.maximumWidth: 22
                    Layout.minimumHeight: 22
                    Layout.preferredHeight: 22
                    Layout.maximumHeight: 22
                    Layout.alignment: Qt.AlignVCenter

                    Kirigami.Icon {
                        anchors.centerIn: parent
                        width: 22
                        height: 22
                        source: Qt.resolvedUrl("assets/deskawake.svg")
                        isMask: true
                        color: Kirigami.Theme.textColor
                        visible: !(root.callPending || root.verifying)
                    }

                    Kirigami.Icon {
                        anchors.centerIn: parent
                        width: 22
                        height: 22
                        source: Qt.resolvedUrl("assets/spinner.svg")
                        isMask: true
                        color: Kirigami.Theme.textColor
                        visible: root.callPending || root.verifying
                        transformOrigin: Item.Center

                        RotationAnimator on rotation {
                            from: 0
                            to: 360
                            duration: 960
                            easing.type: Easing.Linear
                            loops: Animation.Infinite
                            running: root.callPending || root.verifying
                        }
                    }
                }

                Text {
                    id: nameLabel
                    text: "DeskAwake"
                    font.family: Kirigami.Theme.defaultFont.family
                    font.pixelSize: 10
                    font.weight: Font.DemiBold
                    // No Noto Sans, o peso semibold resolve para Bold e mede 58,1 px; o
                    // tracking mínimo mantém o nome completo dentro do slot de 58 px.
                    font.letterSpacing: -0.05
                    elide: Text.ElideRight
                    Layout.minimumWidth: 58
                    Layout.preferredWidth: 58
                    Layout.maximumWidth: 58
                    Layout.alignment: Qt.AlignVCenter
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                Item {
                    id: toggleSlot
                    Layout.minimumWidth: 32
                    Layout.preferredWidth: 32
                    Layout.maximumWidth: 32
                    Layout.minimumHeight: 18
                    Layout.preferredHeight: 18
                    Layout.maximumHeight: 18
                    Layout.alignment: Qt.AlignVCenter
                    opacity: root.callPending ? 0.6 : 1

                    Rectangle {
                        id: toggleTrack
                        anchors.fill: parent
                        radius: 9
                        color: (root.state === "on" || root.verifying)
                            ? "#80D9A4"
                            : root.state === "error"
                                ? "#E47F7F"
                                : "#929DA5"
                    }

                    Rectangle {
                        id: toggleKnob
                        width: 14
                        height: 14
                        radius: 7
                        y: 2
                        x: root.state === "on" ? 17 : 1
                        color: Kirigami.Theme.backgroundColor
                    }

                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.LeftButton
                        enabled: !root.callPending
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.requestActive(root.state !== "on")
                    }
                }
            }
        }
    }

    Plasmoid.contextualActions: [
        PlasmaCore.Action {
            text: root.state === "on" ? "Desativar" : "Ativar"
            enabled: !root.callPending
            onTriggered: root.requestActive(root.state !== "on")
        },
        PlasmaCore.Action {
            text: "Sair"
            enabled: !root.callPending
            onTriggered: root.quitDaemon()
        }
    ]

    function syncFromDaemon() {
        if (!daemonWatcher.registered) {
            root.applyState("off")
            return
        }

        root.callToken += 1
        const token = root.callToken

        DBus.SessionBus.asyncCall({
            service: root.serviceName,
            path: root.objectPath,
            iface: root.ifaceName,
            member: "GetState"
        }, function (reply) {
            if (token !== root.callToken) {
                return
            }
            const current = String(reply.value)
            root.applyState(current)
            if (current === "error") {
                root.requestLastError()
            }
        }, function (error) {
            if (token !== root.callToken) {
                return
            }
            console.warn("DeskAwake: falha ao consultar o estado:", error.message)
        })
    }

    function applyState(newState) {
        // O motor JS entrega o argumento do sinal como objeto String; normalizar permite
        // as comparações estritas com os tokens públicos do contrato.
        const value = String(newState)
        if (value !== "on" && value !== "off" && value !== "error") {
            return
        }
        if (value !== "error") {
            root.lastError = ""
        }
        root.state = value
        if (value !== "on") {
            root.stopVerification()
        }
    }

    function requestLastError() {
        if (!daemonWatcher.registered) {
            return
        }

        const token = root.callToken

        DBus.SessionBus.asyncCall({
            service: root.serviceName,
            path: root.objectPath,
            iface: root.ifaceName,
            member: "GetLastError"
        }, function (reply) {
            if (token !== root.callToken) {
                return
            }
            root.lastError = String(reply.value)
        }, function (error) {
            console.warn("DeskAwake: falha ao consultar o último erro:", error.message)
        })
    }

    function requestActive(active) {
        if (root.callPending) {
            return
        }

        root.callToken += 1
        const token = root.callToken
        root.callPending = true
        root.stopVerification()

        DBus.SessionBus.asyncCall({
            service: root.serviceName,
            path: root.objectPath,
            iface: root.ifaceName,
            member: "SetActive",
            signature: "(b)",
            arguments: [new DBus.bool(active)]
        }, function (reply) {
            if (token !== root.callToken) {
                return
            }
            root.callPending = false
            const newState = String(reply.value)
            root.applyState(newState)
            if (active && newState === "on") {
                root.startVerification()
            }
            if (newState === "error") {
                root.requestLastError()
            }
        }, function (error) {
            if (token !== root.callToken) {
                return
            }
            root.callPending = false
            console.warn("DeskAwake: falha ao alterar o estado:", error.message)
            if (daemonWatcher.registered) {
                root.syncFromDaemon()
            } else {
                root.applyState("off")
            }
        })
    }

    function startVerification() {
        root.verifying = true
        verifyTimer.restart()
    }

    function stopVerification() {
        root.verifying = false
        verifyTimer.stop()
    }

    function invalidateCalls() {
        root.callToken += 1
        root.callPending = false
        root.verifying = false
        verifyTimer.stop()
    }

    function quitDaemon() {
        if (!daemonWatcher.registered || root.callPending) {
            return
        }

        root.stopVerification()
        root.callToken += 1
        const token = root.callToken
        root.callPending = true

        DBus.SessionBus.asyncCall({
            service: root.serviceName,
            path: root.objectPath,
            iface: root.ifaceName,
            member: "SetActive",
            signature: "(b)",
            arguments: [new DBus.bool(false)]
        }, function (reply) {
            if (token !== root.callToken) {
                return
            }
            root.callPending = false
            root.applyState(String(reply.value))
            sendQuit()
        }, function (error) {
            if (token !== root.callToken) {
                return
            }
            root.callPending = false
            console.warn("DeskAwake: falha ao desativar antes de sair:", error.message)
            sendQuit()
        })

        function sendQuit() {
            if (!daemonWatcher.registered) {
                return
            }
            DBus.SessionBus.asyncCall({
                service: root.serviceName,
                path: root.objectPath,
                iface: root.ifaceName,
                member: "Quit"
            }, function () {
            }, function (error) {
                console.warn("DeskAwake: falha ao encerrar o daemon:", error.message)
            })
        }
    }

    Component.onCompleted: {
        if (daemonWatcher.registered) {
            root.syncFromDaemon()
        } else {
            root.applyState("off")
        }
    }
}
