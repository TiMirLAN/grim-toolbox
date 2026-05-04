import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Widgets

Item {
  id: root

  property var pluginApi: null
  property ShellScreen screen
  property string widgetId: ""
  property int instanceIndex: -1

  property string apiKey: pluginApi?.pluginSettings?.apiKey || ""
  property int updateInterval: pluginApi?.pluginSettings?.updateInterval || 300000

  property string balanceText: "—"
  property bool isLoading: false
  property bool hasError: false
  property string lastUpdated: ""

  width: 200
  height: 100

  Rectangle {
    id: background
    anchors.fill: parent
    color: Style.desktopWidgetBackground
    radius: Style.radiusM
    border.color: Style.desktopWidgetBorder
    border.width: 1
  }

  ColumnLayout {
    id: content
    anchors.fill: parent
    anchors.margins: Style.marginM
    spacing: Style.marginS

    RowLayout {
      Layout.fillWidth: true

      NText {
        text: "RouterAI"
        color: Color.mOnSurface
        pointSize: Style.fontSizeM
        font.weight: Font.Bold
      }

      Item {
        Layout.fillWidth: true
      }

      NIconButton {
        icon: "refresh"
        width: 24
        height: 24
        onClicked: refreshBalance()
      }
    }

    Item {
      Layout.fillHeight: true
    }

    RowLayout {
      Layout.fillWidth: true

      NIcon {
        icon: "wallet"
        color: root.hasError ? Color.mError : Color.mPrimary
        pointSize: Style.fontSizeL
      }

      NText {
        text: root.balanceText
        color: root.hasError ? Color.mError : Color.mOnSurface
        pointSize: Style.fontSizeL
        font.weight: Font.Bold
      }
    }

    NText {
      text: root.lastUpdated
      color: Color.mOnSurfaceVariant
      pointSize: Style.fontSizeXS
      visible: root.lastUpdated !== ""
    }
  }

  DraggableMouseArea {
    anchors.fill: parent
    targetItem: root
  }

  Timer {
    id: refreshTimer
    interval: root.updateInterval
    repeat: true
    onTriggered: {
      refreshBalance()
    }
  }

  function refreshBalance() {
    if (!root.apiKey || root.apiKey === "") {
      root.hasError = true
      root.balanceText = pluginApi?.tr("label.noKey") || "No key"
      return
    }

    root.isLoading = true
    root.hasError = false

    var xhr = new XMLHttpRequest()
    xhr.open("GET", "https://routerai.ru/api/v1/key", true)
    xhr.setRequestHeader("Authorization", "Bearer " + root.apiKey)

    xhr.onreadystatechange = function() {
      if (xhr.readyState === XMLHttpRequest.DONE) {
        root.isLoading = false
        var now = new Date()
        root.lastUpdated = now.toLocaleTimeString("ru-RU", { hour: '2-digit', minute: '2-digit' })

        if (xhr.status === 200) {
          try {
            var response = JSON.parse(xhr.responseText)
            if (response.balance !== undefined) {
              root.balanceText = formatBalance(response.balance)
              root.hasError = false
            } else if (response.data && response.data.balance !== undefined) {
              root.balanceText = formatBalance(response.data.balance)
              root.hasError = false
            } else {
              root.hasError = true
              root.balanceText = "—"
            }
          } catch (e) {
            root.hasError = true
            root.balanceText = "—"
          }
        } else if (xhr.status === 401) {
          root.hasError = true
          root.balanceText = pluginApi?.tr("label.error") || "Error"
        } else {
          root.hasError = true
          root.balanceText = "—"
        }
      }
    }

    xhr.onerror = function() {
      root.isLoading = false
      root.hasError = true
      root.balanceText = "—"
    }

    xhr.send()
  }

  function formatBalance(balance) {
    var num = parseFloat(balance)
    if (isNaN(num)) {
      return balance
    }
    return num.toLocaleString("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: 2 }) + " ₽"
  }

  Component.onCompleted: {
    if (root.apiKey) {
      refreshBalance()
      refreshTimer.start()
    } else {
      root.balanceText = pluginApi?.tr("label.noKey") || "No key"
      root.lastUpdated = ""
    }
    Logger.i("RouterAI-Balance", "DesktopWidget loaded")
  }

  Component.onDestruction: {
    refreshTimer.stop()
  }
}