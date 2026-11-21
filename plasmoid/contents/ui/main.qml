pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents
import org.kde.kirigami as Kirigami
import org.kde.plasma.workspace.dbus as DBus

PlasmoidItem {
    id: root

    readonly property string serviceName: "org.local.DeskAwake"
    readonly property string objectPath: "/org/local/DeskAwake"
    readonly property string ifaceName: "org.local.DeskAwake"
    readonly property int verifyWindowMs: 6000

    Layout.minimumWidth: 168
    Layout.preferredWidth: 184
    Layout.maximumWidth: 300
    Layout.minimumHeight: 44
    Layout.preferredHeight: 48
    Layout.maximumHeight: 84

    implicitWidth: 184
    implicitHeight: 48
    switchWidth: 184
    switchHeight: 48

    // Escala contínua entre o mínimo (168×44) e o máximo (300×84).
    readonly property real s: clamp(Math.min((width - 168) / 132, (height - 44) / 40), 0, 1)

    readonly property real logoSize: 22 + 12 * s
    readonly property real namePixelSize: 10 + 4 * s
    readonly property real toggleWidth: 32 + 8 * s
    readonly property real toggleHeight: 18 + 4 * s
    readonly property real knobSize: 14 + 4 * s
    readonly property real hamburgerWidth: 14 + 2 * s
    readonly property real hamburgerHeight: 10 + 2 * s
    readonly property real pillPadding: 6 + 6 * s
    readonly property real logoGap: 6 + 22 * s
    readonly property real menuGap: 6 + 4 * s
    readonly property real pillRadius: 12 + 6 * s

    readonly property bool cornerMode: height > cornerModeHeight
    readonly property int cornerModeHeight: 74
    readonly property int cornerLineOffset: 10
    readonly property int cornerMenuTopInset: 2
    readonly property int cornerMenuRightInset: 4
    readonly property real hitTargetSize: 24
    readonly property real activeHamburgerWidth: cornerMode ? 16 : hamburgerWidth
    readonly property real activeHamburgerHeight: cornerMode ? 12 : hamburgerHeight

    property string state: "off"
    property string lastError: ""
    property bool callPending: false
    property bool verifying: false
    property int callToken: 0

    property int sampleToken: 0
    property string detectedVariant: ""
    property bool usingThemeFallback: true
    property real chipOpacity: 0.88

    readonly property color darkChipColor: "#20252B"
    readonly property color lightChipColor: "#F0F3F5"
    readonly property color darkInkColor: "#F0F3F5"
    readonly property color lightInkColor: "#20252B"

    readonly property string themeChipVariant: relativeLuminance(Kirigami.Theme.backgroundColor) >= 0.5 ? "light" : "dark"
    readonly property string chipVariant: usingThemeFallback ? themeChipVariant : detectedVariant
    readonly property color chipBaseColor: chipVariant === "light" ? lightChipColor : darkChipColor

    readonly property color surfaceColor: Qt.rgba(
        usingThemeFallback ? Kirigami.Theme.backgroundColor.r : chipBaseColor.r,
        usingThemeFallback ? Kirigami.Theme.backgroundColor.g : chipBaseColor.g,
        usingThemeFallback ? Kirigami.Theme.backgroundColor.b : chipBaseColor.b,
        chipOpacity
    )

    readonly property color inkColor: usingThemeFallback
        ? Kirigami.Theme.textColor
        : (chipVariant === "light" ? lightInkColor : darkInkColor)

    readonly property color borderColor: {
        const alpha = chipVariant === "light"
            ? (pillToolTip.containsMouse ? 0.26 : 0.16)
            : (pillToolTip.containsMouse ? 0.32 : 0.22)
        return Qt.rgba(inkColor.r, inkColor.g, inkColor.b, alpha)
    }

    readonly property var wallpaperGraphicsObject: {
        if (Plasmoid.location === PlasmaCore.Types.Panel) {
            return null
        }
        const containment = Plasmoid.containment
        if (!containment) {
            return null
        }
        return containment.wallpaperGraphicsObject ? containment.wallpaperGraphicsObject : null
    }

    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    toolTipMainText: "DeskAwake"
    toolTipSubText: root.state === "error" ? root.lastError : ""
    toolTipTextFormat: Text.PlainText

    onWidthChanged: root.scheduleWallpaperSample()
    onHeightChanged: root.scheduleWallpaperSample()
    onXChanged: root.scheduleWallpaperSample()
    onYChanged: root.scheduleWallpaperSample()
    onWallpaperGraphicsObjectChanged: root.scheduleWallpaperSample()

    Connections {
        target: Plasmoid.containment
        ignoreUnknownSignals: true

        function onWallpaperGraphicsObjectChanged() {
            root.scheduleWallpaperSample()
        }

        function onScreenChanged() {
            root.scheduleWallpaperSample()
        }
    }

    Connections {
        target: root.wallpaperGraphicsObject
        ignoreUnknownSignals: true

        function onSourceChanged() {
            root.scheduleWallpaperSample()
        }

        function onImageChanged() {
            root.scheduleWallpaperSample()
        }
    }

    Connections {
        target: Kirigami.Theme

        function onColorsChanged() {
            root.scheduleWallpaperSample()
        }
    }

    Timer {
        id: wallpaperSampleTimer
        interval: 200
        repeat: false
        onTriggered: root.sampleWallpaper()
    }

    Timer {
        id: verifyTimer
        interval: root.verifyWindowMs
        repeat: false
        running: root.verifying
        onTriggered: root.stopVerification()
    }

    Image {
        id: grabSnapshot
        visible: false
        cache: false

        property var pendingResult: null
        property int pendingToken: -1
        property real sampleX: 0
        property real sampleY: 0
        property real sampleWidth: 0
        property real sampleHeight: 0
        property real wallpaperWidth: 0

        function finishSample() {
            if (!pendingResult) {
                return
            }
            const token = pendingToken
            const luminance = root.sampleLuminance(grabSnapshot)
            pendingResult = null
            pendingToken = -1
            source = ""
            if (token === root.sampleToken) {
                root.applySample(luminance)
            }
        }

        onStatusChanged: {
            if (status === Image.Ready) {
                finishSample()
            } else if (status === Image.Error) {
                const token = pendingToken
                pendingResult = null
                pendingToken = -1
                source = ""
                if (token === root.sampleToken) {
                    root.applySample(-1)
                }
            }
        }
    }

    Canvas {
        id: luminanceSampler
        width: 32
        height: 32
        visible: false
        contextType: "2d"
    }

    PlasmaCore.ToolTipArea {
        id: pillToolTip
        anchors.fill: parent
        mainText: "DeskAwake"
        subText: root.state === "error" ? root.lastError : ""
        textFormat: Text.PlainText
        active: root.state === "error"
        location: Plasmoid.location

        Kirigami.ShadowedRectangle {
            id: pill
            anchors.fill: parent
            radius: root.pillRadius
            color: root.surfaceColor
            border.width: 1
            border.color: root.borderColor
            shadow.size: root.chipVariant === "light" ? 10 : 12
            shadow.color: root.chipVariant === "light"
                ? Qt.rgba(0, 0, 0, 0.16)
                : Qt.rgba(0, 0, 0, 0.32)
            shadow.yOffset: 2

            Behavior on radius {
                NumberAnimation { duration: 140; easing.type: Easing.InOutQuad }
            }

            Item {
                id: mainLine
                anchors.centerIn: parent
                width: Math.max(0, pill.width - 2 * root.pillPadding)
                height: Math.max(0, pill.height - 2 * root.pillPadding)

                transform: Translate {
                    y: root.cornerMode ? root.cornerLineOffset : 0

                    Behavior on y {
                        NumberAnimation { duration: 140; easing.type: Easing.InOutQuad }
                    }
                }

                RowLayout {
                    anchors.fill: parent
                    spacing: 0

                    Item {
                        id: symbolSlot
                        Layout.preferredWidth: root.logoSize
                        Layout.preferredHeight: root.logoSize
                        Layout.alignment: Qt.AlignVCenter

                        Kirigami.Icon {
                            anchors.fill: parent
                            source: Qt.resolvedUrl("assets/deskawake.svg")
                            isMask: true
                            color: root.inkColor
                            visible: !(root.callPending || root.verifying)
                        }

                        Kirigami.Icon {
                            anchors.fill: parent
                            source: Qt.resolvedUrl("assets/spinner.svg")
                            isMask: true
                            color: root.inkColor
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

                    Item {
                        Layout.preferredWidth: root.logoGap
                        Layout.preferredHeight: 1
                    }

                    Text {
                        id: nameLabel
                        text: "DeskAwake"
                        font.family: Kirigami.Theme.defaultFont.family
                        font.pixelSize: root.namePixelSize
                        font.weight: Font.DemiBold
                        color: root.inkColor
                        elide: Text.ElideRight
                        Layout.preferredWidth: implicitWidth
                        Layout.alignment: Qt.AlignVCenter
                        verticalAlignment: Text.AlignVCenter
                    }

                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                    }

                    Item {
                        id: toggleSlot
                        Layout.preferredWidth: root.toggleWidth
                        Layout.preferredHeight: root.toggleHeight
                        Layout.alignment: Qt.AlignVCenter
                        opacity: root.callPending ? 0.6 : 1

                        Rectangle {
                            id: toggleTrack
                            anchors.fill: parent
                            radius: height / 2
                            color: (root.state === "on" || root.verifying)
                                ? "#80D9A4"
                                : root.state === "error"
                                    ? "#E47F7F"
                                    : "#929DA5"

                            Behavior on color {
                                ColorAnimation { duration: 120 }
                            }
                        }

                        Rectangle {
                            id: toggleKnob
                            width: root.knobSize
                            height: root.knobSize
                            radius: width / 2
                            y: (toggleSlot.height - height) / 2
                            x: root.state === "on"
                                ? toggleSlot.width - width - (toggleSlot.height - height) / 2
                                : (toggleSlot.height - height) / 2
                            color: "#20252B"

                            Behavior on x {
                                NumberAnimation { duration: 120; easing.type: Easing.InOutQuad }
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.LeftButton
                            enabled: !root.callPending
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.requestActive(root.state !== "on")
                        }
                    }

                    Item {
                        Layout.preferredWidth: root.cornerMode ? 0 : root.menuGap
                        Layout.preferredHeight: 1
                    }

                    Item {
                        id: hamburgerSlot
                        Layout.preferredWidth: root.cornerMode ? 0 : root.hamburgerWidth
                        Layout.preferredHeight: root.hamburgerHeight
                        Layout.alignment: Qt.AlignVCenter
                    }
                }
            }

            Item {
                id: hamburgerButton
                width: root.hitTargetSize
                height: root.hitTargetSize
                z: 2

                x: root.cornerMode
                    ? pill.width - root.pillPadding - root.cornerMenuRightInset
                        - root.activeHamburgerWidth - (root.hitTargetSize - root.activeHamburgerWidth) / 2
                    : mainLine.x + hamburgerSlot.x
                        + (hamburgerSlot.width - width) / 2

                y: root.cornerMode
                    ? root.pillPadding + root.cornerMenuTopInset
                        - (root.hitTargetSize - root.activeHamburgerHeight) / 2
                    : mainLine.y + hamburgerSlot.y
                        + (hamburgerSlot.height - height) / 2

                Behavior on x {
                    NumberAnimation { duration: 140; easing.type: Easing.InOutQuad }
                }

                Behavior on y {
                    NumberAnimation { duration: 140; easing.type: Easing.InOutQuad }
                }

                Rectangle {
                    id: hamburgerHover
                    anchors.fill: parent
                    radius: 6
                    color: Qt.rgba(
                        root.inkColor.r,
                        root.inkColor.g,
                        root.inkColor.b,
                        hamburgerMouse.pressed ? 0.12 : hamburgerMouse.containsMouse ? 0.08 : 0
                    )

                    Behavior on color {
                        ColorAnimation { duration: 100 }
                    }
                }

                Item {
                    id: hamburgerGlyph
                    anchors.centerIn: parent
                    width: root.activeHamburgerWidth
                    height: root.activeHamburgerHeight

                    Behavior on width {
                        NumberAnimation { duration: 140; easing.type: Easing.InOutQuad }
                    }

                    Behavior on height {
                        NumberAnimation { duration: 140; easing.type: Easing.InOutQuad }
                    }

                    Rectangle {
                        width: parent.width
                        height: 2
                        radius: 1
                        color: root.inkColor
                    }

                    Rectangle {
                        y: (parent.height - height) / 2
                        width: parent.width
                        height: 2
                        radius: 1
                        color: root.inkColor
                    }

                    Rectangle {
                        y: parent.height - height
                        width: parent.width
                        height: 2
                        radius: 1
                        color: root.inkColor
                    }
                }

                MouseArea {
                    id: hamburgerMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton
                    preventStealing: true
                    cursorShape: Qt.PointingHandCursor
                    PlasmaComponents.ToolTip.delay: 500
                    PlasmaComponents.ToolTip.text: "Opções"
                    PlasmaComponents.ToolTip.visible: hamburgerMouse.containsMouse && !optionsMenu.opened
                    onClicked: optionsMenu.popup()
                }

                PlasmaComponents.Menu {
                    id: optionsMenu
                    parent: hamburgerButton
                    x: Math.round((parent.width - width) / 2)
                    y: parent.height + 4

                    PlasmaComponents.MenuItem {
                        text: toggleAction.text
                        enabled: toggleAction.enabled
                        onTriggered: toggleAction.trigger()
                    }

                    PlasmaComponents.MenuItem {
                        text: quitAction.text
                        enabled: quitAction.enabled
                        onTriggered: quitAction.trigger()
                    }

                    PlasmaComponents.MenuSeparator {}

                    PlasmaComponents.MenuItem {
                        text: Plasmoid.internalAction("configure").text
                        enabled: true
                        onTriggered: Plasmoid.internalAction("configure").trigger()
                    }

                    PlasmaComponents.MenuItem {
                        text: Plasmoid.internalAction("remove").text
                        enabled: true
                        onTriggered: Plasmoid.internalAction("remove").trigger()
                    }
                }
            }
        }
    }

    PlasmaCore.Action {
        id: toggleAction
        text: root.state === "on" ? "Desativar" : "Ativar"
        enabled: !root.callPending
        onTriggered: root.requestActive(root.state !== "on")
    }

    PlasmaCore.Action {
        id: quitAction
        text: "Sair"
        enabled: !root.callPending
        onTriggered: root.quitDaemon()
    }

    Plasmoid.contextualActions: [ toggleAction, quitAction ]

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

    function clamp(value, minimum, maximum) {
        return Math.max(minimum, Math.min(maximum, value))
    }

    function relativeLuminance(color) {
        return pixelLuminance(color.r, color.g, color.b)
    }

    function pixelLuminance(red, green, blue) {
        return 0.2126 * red + 0.7152 * green + 0.0722 * blue
    }

    function contrastRatio(first, second) {
        const lighter = Math.max(first, second)
        const darker = Math.min(first, second)
        return (lighter + 0.05) / (darker + 0.05)
    }

    function adjustedOpacity(variant, backgroundLuminance) {
        const base = variant === "light" ? lightChipColor : darkChipColor
        const ink = variant === "light" ? lightInkColor : darkInkColor
        const inkLuminance = relativeLuminance(ink)
        const baseLuminance = relativeLuminance(base)

        for (let step = 0; step <= 3; step += 1) {
            const opacity = Math.min(0.97, 0.88 + step * 0.03)
            const surfaceLuminance = baseLuminance * opacity + backgroundLuminance * (1 - opacity)
            if (contrastRatio(inkLuminance, surfaceLuminance) >= 4.5) {
                return opacity
            }
        }

        return -1
    }

    function resolveChip(luminance, variant) {
        let candidate = variant
        let opacity = adjustedOpacity(candidate, luminance)

        if (opacity < 0) {
            candidate = candidate === "dark" ? "light" : "dark"
            opacity = adjustedOpacity(candidate, luminance)
        }

        if (opacity < 0) {
            return { variant: themeChipVariant, opacity: 0.88, fallback: true }
        }

        return { variant: candidate, opacity: opacity, fallback: false }
    }

    function applySample(luminance) {
        if (!(luminance >= 0)) {
            detectedVariant = ""
            usingThemeFallback = true
            chipOpacity = 0.88
            return
        }

        let variant = detectedVariant !== "" ? detectedVariant : themeChipVariant
        if (luminance < 0.42) {
            variant = "dark"
        } else if (luminance > 0.58) {
            variant = "light"
        }

        const resolved = resolveChip(luminance, variant)
        detectedVariant = resolved.variant
        usingThemeFallback = resolved.fallback
        chipOpacity = resolved.opacity
    }

    // Wallpapers de vídeo/slideshow sem sinal observável mantêm a variante
    // atual até o próximo evento de geometria/tema; não há polling.
    function scheduleWallpaperSample() {
        wallpaperSampleTimer.restart()
    }

    function sampleWallpaper() {
        root.sampleToken += 1
        const token = root.sampleToken
        const wallpaperItem = wallpaperGraphicsObject
        if (!wallpaperItem
                || typeof wallpaperItem.grabToImage !== "function"
                || typeof wallpaperItem.mapToItem !== "function"
                || !(wallpaperItem.width > 0)
                || !(wallpaperItem.height > 0)) {
            applySample(-1)
            return
        }

        const origin = pill.mapToItem(wallpaperItem, 0, 0)
        grabSnapshot.sampleX = origin.x
        grabSnapshot.sampleY = origin.y
        grabSnapshot.sampleWidth = pill.width
        grabSnapshot.sampleHeight = pill.height
        grabSnapshot.wallpaperWidth = wallpaperItem.width

        const started = wallpaperItem.grabToImage(function (result) {
            if (token !== root.sampleToken) {
                return
            }
            if (!result) {
                applySample(-1)
                return
            }
            grabSnapshot.pendingToken = token
            grabSnapshot.pendingResult = result
            grabSnapshot.source = result.url
        })

        if (!started) {
            applySample(-1)
        }
    }

    function sampleLuminance(imageItem) {
        const imageWidth = imageItem.implicitWidth
        const imageHeight = imageItem.implicitHeight
        if (!(imageWidth > 0) || !(imageHeight > 0) || !(imageItem.wallpaperWidth > 0)) {
            return -1
        }

        const scale = imageWidth / imageItem.wallpaperWidth
        const margin = 8
        let sourceX = (imageItem.sampleX - margin) * scale
        let sourceY = (imageItem.sampleY - margin) * scale
        let sourceWidth = (imageItem.sampleWidth + margin * 2) * scale
        let sourceHeight = (imageItem.sampleHeight + margin * 2) * scale

        sourceX = Math.max(0, Math.min(imageWidth - 1, sourceX))
        sourceY = Math.max(0, Math.min(imageHeight - 1, sourceY))
        sourceWidth = Math.max(1, Math.min(imageWidth - sourceX, sourceWidth))
        sourceHeight = Math.max(1, Math.min(imageHeight - sourceY, sourceHeight))

        const context = luminanceSampler.getContext("2d")
        context.clearRect(0, 0, luminanceSampler.width, luminanceSampler.height)
        context.drawImage(
            imageItem,
            sourceX,
            sourceY,
            sourceWidth,
            sourceHeight,
            0,
            0,
            luminanceSampler.width,
            luminanceSampler.height
        )

        const pixels = context.getImageData(0, 0, luminanceSampler.width, luminanceSampler.height).data
        let total = 0
        let weight = 0
        for (let index = 0; index < pixels.length; index += 4) {
            const alpha = pixels[index + 3] / 255
            if (alpha <= 0) {
                continue
            }
            total += pixelLuminance(
                pixels[index] / 255,
                pixels[index + 1] / 255,
                pixels[index + 2] / 255
            ) * alpha
            weight += alpha
        }

        return weight > 0 ? total / weight : -1
    }

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
            const newState = String(reply.value)
            root.applyState(newState)
            // Sair pode retornar error; buscar o motivo antes de encerrar o daemon.
            if (newState === "error") {
                root.requestLastError()
            }
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
        root.scheduleWallpaperSample()
        if (daemonWatcher.registered) {
            root.syncFromDaemon()
        } else {
            root.applyState("off")
        }
    }
}
