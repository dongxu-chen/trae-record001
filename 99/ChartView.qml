import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import QtQuick.Dialogs
import ChartEditor

ApplicationWindow {
    id: window
    visible: true
    width: 1400
    height: 900
    minimumWidth: 1100
    minimumHeight: 700
    title: "Real-time Chart Editor"

    readonly property int maxRenderPoints: 500
    readonly property int minTickCount: 3
    readonly property int maxTickCount: 6
    readonly property real tickTargetPixelSpacing: 100

    ChartModel {
        id: chartModel
        maxBufferSize: 10000
        useRollingBuffer: true
        visibleTimeRange: 30.0
        autoScrollX: true
    }

    Exporter {
        id: exporter
    }

    LiveDataGenerator {
        id: liveData
        intervalMs: 100
        
        onNewData: {
            chartModel.addPoint(timestamp, value)
        }
    }

    function toScene(x, y, minMax, plotArea) {
        let tX = (x - minMax.minX) / (minMax.maxX - minMax.minX)
        let tY = (y - minMax.minY) / (minMax.maxY - minMax.minY)
        return Qt.point(
            plotArea.x + tX * plotArea.width,
            plotArea.y + plotArea.height - tY * plotArea.height
        )
    }

    function calculateTickCount(range, targetSpacing) {
        let idealTicks = range / targetSpacing
        let tickCount = Math.round(idealTicks)
        tickCount = Math.max(minTickCount, Math.min(maxTickCount, tickCount))
        return tickCount
    }

    function niceTickValue(value, round) {
        let exponent = Math.floor(Math.log10(value))
        let fraction = value / Math.pow(10, exponent)
        let niceFraction
        if (round) {
            if (fraction < 1.5) niceFraction = 1
            else if (fraction < 3) niceFraction = 2
            else if (fraction < 7) niceFraction = 5
            else niceFraction = 10
        } else {
            if (fraction <= 1) niceFraction = 1
            else if (fraction <= 2) niceFraction = 2
            else if (fraction <= 5) niceFraction = 5
            else niceFraction = 10
        }
        return niceFraction * Math.pow(10, exponent)
    }

    function calculateAxisTicks(minVal, maxVal, tickCount) {
        let range = niceTickValue(maxVal - minVal, false)
        let tickSpacing = niceTickValue(range / (tickCount - 1), true)
        let niceMin = Math.floor(minVal / tickSpacing) * tickSpacing
        let niceMax = Math.ceil(maxVal / tickSpacing) * tickSpacing

        let ticks = []
        for (let t = niceMin; t <= niceMax + tickSpacing / 100; t += tickSpacing) {
            ticks.push(t)
        }
        return { ticks: ticks, niceMin: niceMin, niceMax: niceMax, spacing: tickSpacing }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Label { text: "Title:" }
            TextField {
                Layout.fillWidth: true
                text: chartModel.title
                onTextChanged: chartModel.title = text
            }

            Label { text: "X Label:" }
            TextField {
                Layout.preferredWidth: 100
                text: chartModel.xAxisLabel
                onTextChanged: chartModel.xAxisLabel = text
            }

            Label { text: "Y Label:" }
            TextField {
                Layout.preferredWidth: 100
                text: chartModel.yAxisLabel
                onTextChanged: chartModel.yAxisLabel = text
            }

            Label { text: "Color:" }
            ColorDialog {
                id: colorDialog
                title: "Select Line Color"
                currentColor: chartModel.lineColor
                onAccepted: chartModel.lineColor = currentColor
            }
            Button {
                text: "Pick"
                onClicked: colorDialog.open()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Label { text: "Chart Type:" }
            ComboBox {
                id: chartTypeCombo
                model: chartModel.availableChartTypes
                Layout.preferredWidth: 120
                onCurrentIndexChanged: {
                    chartModel.currentChartType = currentIndex
                }
            }

            Item { Layout.fillWidth: true }

            Label { text: "Visible Range:" }
            ComboBox {
                id: rangeCombo
                model: ["5s", "10s", "30s", "60s", "5m"]
                Layout.preferredWidth: 80
                currentIndex: 2
                onCurrentIndexChanged: {
                    let ranges = [5, 10, 30, 60, 300]
                    chartModel.visibleTimeRange = ranges[currentIndex]
                }
            }

            Label { text: "Buffer Size:" }
            ComboBox {
                id: bufferCombo
                model: ["1000", "5000", "10000", "50000"]
                Layout.preferredWidth: 100
                currentIndex: 2
                onCurrentIndexChanged: {
                    let sizes = [1000, 5000, 10000, 50000]
                    chartModel.maxBufferSize = sizes[currentIndex]
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Label { text: "Sensor:" }
            ComboBox {
                id: sensorCombo
                model: ["Temperature", "Pressure", "Humidity", "Vibration", "Custom"]
                Layout.preferredWidth: 120
                onCurrentIndexChanged: {
                    liveData.sensorType = currentIndex
                }
            }

            Label { text: "Interval:" }
            ComboBox {
                id: intervalCombo
                model: ["10ms", "50ms", "100ms", "500ms", "1000ms"]
                Layout.preferredWidth: 100
                currentIndex: 2
                onCurrentIndexChanged: {
                    let intervals = [10, 50, 100, 500, 1000]
                    liveData.intervalMs = intervals[currentIndex]
                }
            }

            Button {
                id: startStopBtn
                text: liveData.running ? "Stop" : "Start"
                icon.name: liveData.running ? "media-playback-pause" : "media-playback-start"
                onClicked: {
                    if (liveData.running) {
                        liveData.stop()
                    } else {
                        liveData.start()
                        chartModel.start()
                    }
                }
            }

            Button {
                text: "Reset"
                onClicked: {
                    chartModel.clearPoints()
                    liveData.reset()
                }
            }

            Item { Layout.fillWidth: true }

            Label {
                text: "Data Rate: " + chartModel.dataRate.toFixed(1) + " pts/s"
                color: chartModel.dataRate > 100 ? "#27ae60" : "#333"
                font.bold: chartModel.dataRate > 100
            }

            Label {
                text: "Points: " + chartModel.pointCount
            }

            Button {
                text: "Export PNG"
                onClicked: fileDialogPng.open()
            }

            Button {
                text: "Export SVG"
                onClicked: fileDialogSvg.open()
            }
        }

        FileDialog {
            id: fileDialogPng
            title: "Export as PNG"
            fileMode: FileDialog.SaveFile
            defaultSuffix: "png"
            nameFilters: ["PNG Image (*.png)"]
            onAccepted: {
                let path = selectedFile.toString()
                if (path.startsWith("file:///")) {
                    path = path.substring(8)
                } else if (path.startsWith("file://")) {
                    path = path.substring(7)
                }
                exporter.exportToPng(path, chartModel, Qt.size(1600, 900))
            }
        }

        FileDialog {
            id: fileDialogSvg
            title: "Export as SVG"
            fileMode: FileDialog.SaveFile
            defaultSuffix: "svg"
            nameFilters: ["SVG Image (*.svg)"]
            onAccepted: {
                let path = selectedFile.toString()
                if (path.startsWith("file:///")) {
                    path = path.substring(8)
                } else if (path.startsWith("file://")) {
                    path = path.substring(7)
                }
                exporter.exportToSvg(path, chartModel, Qt.size(1600, 900))
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10

            Rectangle {
                id: chartContainer
                Layout.fillWidth: true
                Layout.fillHeight: true
                border.color: "#cccccc"
                border.width: 1
                color: "white"

                property real margin: 60
                property real titleHeight: 40
                property var plotArea: Qt.rect(
                    margin,
                    titleHeight + margin,
                    width - 2 * margin,
                    height - titleHeight - 2 * margin
                )

                property var mm: chartModel.autoScrollX ? 
                    chartModel.getVisibleRange() : chartModel.getMinMax()

                property int xTickCount: calculateTickCount(plotArea.width, tickTargetPixelSpacing)
                property int yTickCount: calculateTickCount(plotArea.height, tickTargetPixelSpacing)
                property var xAxisInfo: calculateAxisTicks(mm.minX, mm.maxX, xTickCount)
                property var yAxisInfo: calculateAxisTicks(mm.minY, mm.maxY, yTickCount)

                Text {
                    id: chartTitle
                    text: chartModel.title
                    font.pointSize: 16
                    font.bold: true
                    anchors.top: parent.top
                    anchors.topMargin: 10
                    anchors.horizontalCenter: parent.horizontalCenter
                }

                Repeater {
                    id: xGridRepeater
                    model: chartContainer.xAxisInfo.ticks.length

                    property real minX: chartContainer.xAxisInfo.niceMin
                    property real maxX: chartContainer.xAxisInfo.niceMax
                    property real minY: chartContainer.yAxisInfo.niceMin
                    property real maxY: chartContainer.yAxisInfo.niceMax

                    delegate: Item {
                        property real tickValue: chartContainer.xAxisInfo.ticks[index]
                        property real t: (tickValue - minX) / (maxX - minX)

                        Line {
                            x1: chartContainer.plotArea.x + t * chartContainer.plotArea.width
                            y1: chartContainer.plotArea.y
                            x2: x1
                            y2: chartContainer.plotArea.y + chartContainer.plotArea.height
                            color: "#e0e0e0"
                        }

                        Text {
                            x: chartContainer.plotArea.x + t * chartContainer.plotArea.width - 30
                            y: chartContainer.plotArea.y + chartContainer.plotArea.height + 5
                            width: 60
                            horizontalAlignment: Text.AlignHCenter
                            text: tickValue.toFixed(Math.abs(tickValue) >= 1000 ? 0 : 
                                    (Math.abs(tickValue) >= 100 ? 1 : 
                                    (Math.abs(tickValue) >= 1 ? 1 : 2))
                            font.pointSize: 10
                        }
                    }
                }

                Repeater {
                    id: yGridRepeater
                    model: chartContainer.yAxisInfo.ticks.length

                    property real minX: chartContainer.xAxisInfo.niceMin
                    property real maxX: chartContainer.xAxisInfo.niceMax
                    property real minY: chartContainer.yAxisInfo.niceMin
                    property real maxY: chartContainer.yAxisInfo.niceMax

                    delegate: Item {
                        property real tickValue: chartContainer.yAxisInfo.ticks[index]
                        property real t: (tickValue - minY) / (maxY - minY)

                        Line {
                            x1: chartContainer.plotArea.x
                            y1: chartContainer.plotArea.y + (1 - t) * chartContainer.plotArea.height
                            x2: chartContainer.plotArea.x + chartContainer.plotArea.width
                            y2: y1
                            color: "#e0e0e0"
                        }

                        Text {
                            x: chartContainer.plotArea.x - 60
                            y: chartContainer.plotArea.y + (1 - t) * chartContainer.plotArea.height - 10
                            width: 55
                            horizontalAlignment: Text.AlignRight
                            text: tickValue.toFixed(Math.abs(tickValue) >= 1000 ? 0 : 
                                    (Math.abs(tickValue) >= 100 ? 1 : 
                                    (Math.abs(tickValue) >= 1 ? 1 : 2))
                            font.pointSize: 10
                        }
                    }
                }

                Line {
                    x1: chartContainer.plotArea.x
                    y1: chartContainer.plotArea.y + chartContainer.plotArea.height
                    x2: chartContainer.plotArea.x + chartContainer.plotArea.width
                    y2: y1
                    color: "black"
                    width: 2
                }

                Line {
                    x1: chartContainer.plotArea.x
                    y1: chartContainer.plotArea.y
                    x2: x1
                    y2: chartContainer.plotArea.y + chartContainer.plotArea.height
                    color: "black"
                    width: 2
                }

                Text {
                    text: chartModel.xAxisLabel
                    font.pointSize: 11
                    font.bold: true
                    anchors.top: chartContainer.plotArea.bottom
                    anchors.topMargin: 25
                    anchors.horizontalCenter: chartContainer.horizontalCenter
                }

                Text {
                    text: chartModel.yAxisLabel
                    font.pointSize: 11
                    font.bold: true
                    rotation: -90
                    anchors.verticalCenter: chartContainer.plotArea.verticalCenter
                    anchors.left: chartContainer.left
                    anchors.leftMargin: 5
                }

                Canvas {
                    id: lineCanvas
                    anchors.fill: parent
                    renderStrategy: Canvas.Cooperative

                    property var mm: chartContainer.mm
                    property var plotArea: chartContainer.plotArea
                    property var displayPoints: chartModel.getDownsampledPoints(maxRenderPoints)
                    property int chartType: chartModel.currentChartType

                    onPaint: {
                        let ctx = getContext("2d")
                        ctx.clearRect(0, 0, width, height)

                        let points = displayPoints
                        if (points.length < 2) return

                        ctx.save()
                        ctx.strokeStyle = chartModel.lineColor
                        ctx.lineWidth = 3
                        ctx.lineCap = "round"
                        ctx.lineJoin = "round"
                        ctx.beginPath()

                        if (chartType === 2) { // Area
                            let first = true
                            let lastY = 0
                            for (let p of points) {
                                let sp = toScene(p.x, p.y, mm, plotArea)
                                if (first) {
                                    ctx.moveTo(sp.x, plotArea.y + plotArea.height)
                                    ctx.lineTo(sp.x, sp.y)
                                    first = false
                                    lastY = sp.y
                                } else {
                                    ctx.lineTo(sp.x, sp.y)
                                    lastY = sp.y
                                }
                            }
                            let lastX = points[points.length - 1].x
                            let lastSP = toScene(lastX, points[points.length - 1].y, mm, plotArea)
                            ctx.lineTo(lastSP.x, plotArea.y + plotArea.height)
                            ctx.closePath()

                            let grad = ctx.createLinearGradient(0, plotArea.y, 0, plotArea.y + plotArea.height)
                            let color = chartModel.lineColor
                            grad.addColorStop(0, color)
                            grad.addColorStop(1, "rgba(255, 255, 255, 0.1)")
                            ctx.fillStyle = grad
                            ctx.fill()
                        } else if (chartType === 3) { // Step
                            let first = true
                            let prevX = 0, prevY = 0
                            for (let i = 0; i < points.length; i++) {
                                let p = points[i]
                                let sp = toScene(p.x, p.y, mm, plotArea)
                                if (first) {
                                    ctx.moveTo(sp.x, sp.y)
                                    first = false
                                } else {
                                    ctx.lineTo(sp.x, prevY)
                                    ctx.lineTo(sp.x, sp.y)
                                }
                                prevX = sp.x
                                prevY = sp.y
                            }
                        } else { // Line (0), Bar (1)
                            let first = true
                            for (let p of points) {
                                let sp = toScene(p.x, p.y, mm, plotArea)
                                if (first) {
                                    ctx.moveTo(sp.x, sp.y)
                                    first = false
                                } else {
                                    ctx.lineTo(sp.x, sp.y)
                                }
                            }
                        }
                        ctx.stroke()
                        ctx.restore()
                    }

                    Connections {
                        target: chartModel
                        function onDataChanged() { lineCanvas.requestPaint() }
                        function onRowsInserted() { lineCanvas.requestPaint() }
                        function onRowsRemoved() { lineCanvas.requestPaint() }
                        function onModelReset() { lineCanvas.requestPaint() }
                        function onLineColorChanged() { lineCanvas.requestPaint() }
                        function onPointCountChanged() { lineCanvas.requestPaint() }
                        function onCurrentChartTypeChanged() { lineCanvas.requestPaint() }
                    }
                }

                Repeater {
                    id: pointsRepeater
                    model: chartModel.pointCount <= 100 ? chartModel : 0

                    delegate: Rectangle {
                        id: pointRect
                        property var mm: chartContainer.mm
                        property var plotArea: chartContainer.plotArea
                        property var sp: toScene(model.x, model.y, mm, plotArea)

                        x: sp.x - 5
                        y: sp.y - 5
                        width: 10
                        height: 10
                        radius: 5
                        color: chartModel.lineColor
                        border.color: "white"
                        border.width: 2

                        ToolTip.text: "(" + model.x.toFixed(2) + ", " + model.y.toFixed(2) + ")"
                        ToolTip.delay: 100
                        ToolTip.visible: ma.containsMouse

                        MouseArea {
                            id: ma
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: {
                                if (chartModel.pointCount > 2) {
                                    chartModel.removePoint(index)
                                }
                            }
                        }
                    }
                }
            }

            ScrollView {
                Layout.preferredWidth: 280
                Layout.fillHeight: true

                Column {
                    width: parent.width - 10
                    spacing: 5

                    Label {
                        text: "Data Points (" + chartModel.pointCount + ")"
                        font.bold: true
                        font.pointSize: 12
                    }

                    Label {
                        text: "Buffer Size: " + chartModel.maxBufferSize
                        font.pointSize: 10
                        color: "#666"
                    }

                    Label {
                        text: "Visible Range: " + chartModel.visibleTimeRange + "s"
                        font.pointSize: 10
                        color: "#666"
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: "#ddd"
                    }

                    Label {
                        text: "Recent Data:"
                        font.bold: true
                        font.pointSize: 11
                    }

                    Repeater {
                        model: chartModel.pointCount <= 50 ? chartModel : 0

                        delegate: Row {
                            width: parent.width
                            spacing: 5

                            Label {
                                text: "#" + (index + 1)
                                width: 35
                                color: "#555"
                            }

                            Label {
                                text: model.x.toFixed(2) + ", " + model.y.toFixed(2)
                                width: 200
                            }
                        }
                    }

                    Label {
                        text: chartModel.pointCount > 50 ? "... (list truncated)" : ""
                        color: "#888"
                        font.pointSize: 10
                        visible: chartModel.pointCount > 50
                    }
                }
            }
        }
    }

    Component.onCompleted: {
        chartTypeCombo.currentIndex = 0
        sensorCombo.currentIndex = 0
        chartModel.addPoint(0, 25)
        chartModel.addPoint(1, 26)
        chartModel.addPoint(2, 24)
        chartModel.addPoint(3, 27)
        chartModel.addPoint(4, 25)
        chartModel.addPoint(5, 26)
        chartModel.addPoint(6, 24)
    }
}
