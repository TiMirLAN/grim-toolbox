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
  property string section: ""
  property int sectionWidgetIndex: -1
  property int sectionWidgetsCount: 0

  readonly property string screenName: screen?.name ?? ""
  readonly property string barPosition: Settings.getBarPositionForScreen(screenName)
  readonly property bool isBarVertical: barPosition === "left" || barPosition === "right"
  readonly property real capsuleHeight: Style.getCapsuleHeightForScreen(screenName)
  readonly property real barFontSize: Style.getBarFontSizeForScreen(screenName)

  property string apiKey: pluginApi?.pluginSettings?.apiKey || ""
  property int updateInterval: pluginApi?.pluginSettings?.updateInterval || 300000

  property string balanceText: "—"
  property bool isLoading: false
  property bool hasError: false
  property string errorMessage: ""

  readonly property real contentWidth: isBarVertical ? capsuleHeight : row.implicitWidth + Style.marginM * 2
  readonly property real contentHeight: isBarVertical ? row.implicitHeight + Style.marginM * 2 : capsuleHeight

  implicitWidth: contentWidth
  implicitHeight: contentHeight

  Rectangle {
    id: visualCapsule
    x: Style.pixelAlignCenter(parent.width, width)
    y: Style.pixelAlignCenter(parent.height, height)
    width: root.contentWidth
    height: root.contentHeight
    color: mouseArea.containsMouse ? Color.mHover : Style.capsuleColor
    radius: Style.radiusL
    border.color: Style.capsuleBorderColor
    border.width: Style.capsuleBorderWidth

    RowLayout {
      id: row
      anchors.centerIn: parent
      spacing: Style.marginS

      NIcon {
        icon: "wallet"
        color: root.hasError ? Color.mError : Color.mPrimary
        applyUiScale: true
      }

      NText {
        text: root.balanceText
        color: root.hasError ? Color.mError : Color.mOnSurface
        pointSize: barFontSize
        font.weight: Font.Medium
      }
    }
  }

  MouseArea {
    id: mouseArea
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor

    onClicked: {
      refreshBalance()
    }
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
      root.errorMessage = pluginApi?.tr("error.noApiKey") || "No API key"
      root.balanceText = pluginApi?.tr("label.noKey") || "No key"
      return
    }

    root.isLoading = true
    root.hasError = false
    root.errorMessage = ""

    var xhr = new XMLHttpRequest()
    xhr.open("GET", "https://routerai.ru/api/v1/key", true)
    xhr.setRequestHeader("Authorization", "Bearer " + root.apiKey)

    xhr.onreadystatechange = function() {
      if (xhr.readyState === XMLHttpRequest.DONE) {
        root.isLoading = false
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
              root.errorMessage = pluginApi?.tr("error.invalidResponse") || "Invalid response"
              root.balanceText = "—"
            }
          } catch (e) {
            root.hasError = true
            root.errorMessage = pluginApi?.tr("error.parseFailed") || "Parse failed"
            root.balanceText = "—"
          }
        } else if (xhr.status === 401) {
          root.hasError = true
          root.errorMessage = pluginApi?.tr("error.invalidKey") || "Invalid API key"
          root.balanceText = pluginApi?.tr("label.error") || "Error"
        } else {
          root.hasError = true
          root.errorMessage = pluginApi?.tr("error.http") || "HTTP " + xhr.status
          root.balanceText = "—"
        }
      }
    }

    xhr.onerror = function() {
      root.isLoading = false
      root.hasError = true
      root.errorMessage = pluginApi?.tr("error.network") || "Network error"
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
    }
    Logger.i("RouterAI-Balance", "BarWidget loaded")
  }

  Component.onDestruction: {
    refreshTimer.stop()
  }
}