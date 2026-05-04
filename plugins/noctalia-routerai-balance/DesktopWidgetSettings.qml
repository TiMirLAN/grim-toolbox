import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Widgets
import qs.Services.System

Item {
  id: root

  property var pluginApi: null
  property ShellScreen screen
  property string widgetId: ""
  property int instanceIndex: -1

  readonly property var settings: pluginApi?.widgetSettings || ({})

  property string apiKey: settings.apiKey || ""
  property int updateInterval: settings.updateInterval || 300000

  width: 300
  height: 150

  ColumnLayout {
    anchors.fill: parent
    anchors.margins: Style.marginM
    spacing: Style.marginM

    NText {
      text: pluginApi?.tr("settings.title") || "RouterAI Balance Settings"
      color: Color.mOnSurface
      pointSize: Style.fontSizeM
      font.weight: Font.Bold
    }

    NText {
      text: pluginApi?.tr("settings.apiKey") || "API Key:"
      color: Color.mOnSurface
      pointSize: Style.fontSizeS
    }

    NTextField {
      id: apiKeyInput
      Layout.fillWidth: true
      text: root.apiKey
      placeholderText: pluginApi?.tr("settings.apiKeyPlaceholder") || "Введите API ключ"
      echoMode: TextInput.Password
      onTextChanged: {
        root.apiKey = text
      }
    }

    NText {
      text: pluginApi?.tr("settings.updateInterval") || "Update Interval:"
      color: Color.mOnSurface
      pointSize: Style.fontSizeS
    }

    RowLayout {
      Layout.fillWidth: true

      NTextField {
        id: intervalInput
        Layout.fillWidth: true
        text: (root.updateInterval / 1000).toString()
        validator: IntValidator { bottom: 10; top: 3600 }
        onTextChanged: {
          var seconds = parseInt(text)
          if (!isNaN(seconds) && seconds >= 10) {
            root.updateInterval = seconds * 1000
          }
        }
      }

      NText {
        text: "sec"
        color: Color.mOnSurfaceVariant
        pointSize: Style.fontSizeS
      }
    }

    Item {
      Layout.fillHeight: true
    }

    RowLayout {
      Layout.fillWidth: true

      Item {
        Layout.fillWidth: true
      }

      NButton {
        text: pluginApi?.tr("settings.save") || "Save"
        onClicked: {
          saveSettings()
          ToastService.showNotice(pluginApi?.tr("settings.saved") || "Settings saved")
        }
      }
    }
  }

  function saveSettings() {
    if (root.pluginApi && root.pluginApi.setWidgetSettings) {
      root.pluginApi.setWidgetSettings({
        apiKey: root.apiKey,
        updateInterval: root.updateInterval
      })
    }
  }

  Component.onCompleted: {
    Logger.i("RouterAI-Balance", "DesktopWidgetSettings loaded")
  }
}