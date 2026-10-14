import QtQuick
import Quickshell
import Quickshell.Io

Item {
  id: root

  property var bar
  property string moduleName
  property var settings

  property string status: "out"
  property string elapsed: ""
  property string tooltip: ""
  property var palette: ({})

  readonly property string command: settings && settings.command ? String(settings.command) : "chronata"
  readonly property color statusColor: status === "in" ? (palette.blue || "#89b4fa")
    : status === "interrupted" ? (palette.yellow || "#f9e2af")
    : (palette.red || "#f38ba8")

  implicitWidth: bar ? bar.barSize : 28
  implicitHeight: column.implicitHeight + 12

  function update(raw) {
    try {
      var data = JSON.parse(raw)
      status = data.state || "out"
      elapsed = data.elapsed || ""
      tooltip = data.tooltip || ""
    } catch (error) {
      status = "out"
      tooltip = "chronata: could not read status"
    }
  }

  function readPalette(text) {
    var colors = {}
    var lines = String(text || "").split("\n")
    for (var i = 0; i < lines.length; i++) {
      var found = lines[i].match(/^\s*(\w+)\s*=\s*"(#[0-9a-fA-F]{6})"/)
      if (found) colors[found[1]] = found[2]
    }
    palette = colors
  }

  function quoted(value) {
    return "'" + String(value).replace(/'/g, "'\\''") + "'"
  }

  function refresh() {
    if (!poll.running) poll.running = true
  }

  Column {
    id: column
    anchors.centerIn: parent
    spacing: 1

    Text {
      anchors.horizontalCenter: parent.horizontalCenter
      text: root.status === "interrupted" ? "" : ""
      color: root.statusColor
      font.family: root.bar ? root.bar.fontFamily : "monospace"
      font.pixelSize: 14
    }

    Text {
      anchors.horizontalCenter: parent.horizontalCenter
      visible: root.status === "in"
      text: root.elapsed
      color: root.statusColor
      font.family: root.bar ? root.bar.fontFamily : "monospace"
      font.pixelSize: 10
    }
  }

  Process {
    id: poll
    command: [root.command, "bar"]
    stdout: StdioCollector {
      onStreamFinished: root.update(text)
    }
  }

  FileView {
    path: Quickshell.env("HOME") + "/.local/state/omarchy/current/theme/colors.toml"
    watchChanges: true
    onFileChanged: reload()
    onLoaded: root.readPalette(text())
  }

  Timer {
    interval: 10000
    running: true
    repeat: true
    triggeredOnStart: true
    onTriggered: root.refresh()
  }

  Timer {
    id: soon
    interval: 1500
    onTriggered: root.refresh()
  }

  MouseArea {
    anchors.fill: parent
    hoverEnabled: true
    acceptedButtons: Qt.LeftButton | Qt.RightButton
    cursorShape: Qt.PointingHandCursor
    onClicked: function(mouse) {
      if (!root.bar) return
      root.bar.run(root.quoted(root.command) + (mouse.button === Qt.RightButton ? " ui" : " toggle"))
      soon.restart()
    }
    onEntered: if (root.bar && root.tooltip) root.bar.showTooltip(root, root.tooltip)
    onExited: if (root.bar) root.bar.hideTooltip(root)
  }
}
