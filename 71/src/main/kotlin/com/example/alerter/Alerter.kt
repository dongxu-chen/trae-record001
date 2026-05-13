package com.example.alerter

import com.example.metrics.MetricsRecorder
import com.example.model.AggregatedWeather
import com.example.model.WeatherCondition
import kotlinx.serialization.Serializable
import org.slf4j.LoggerFactory
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit

@Serializable
data class Alert(
    val id: String,
    val type: AlertType,
    val latitude: Double,
    val longitude: Double,
    val temperature: Double,
    val condition: WeatherCondition,
    val message: String,
    val timestamp: Long
)

enum class AlertType {
    HIGH_TEMPERATURE,
    HEAVY_RAIN,
    STORM
}

interface AlertChannel {
    suspend fun send(alert: Alert)
}

class ConsoleAlertChannel : AlertChannel {
    private val logger = LoggerFactory.getLogger(javaClass)

    override suspend fun send(alert: Alert) {
        logger.warn(
            "[ALERT] ${alert.type} at (${alert.latitude}, ${alert.longitude}): " +
            "${alert.message} (temp=${alert.temperature}°C, condition=${alert.condition})"
        )
    }
}

class WeatherAlerter(
    private val channels: List<AlertChannel>,
    private val metricsRecorder: MetricsRecorder,
    private val highTempThreshold: Double = 35.0,
    private val heavyRainConditions: Set<WeatherCondition> = setOf(
        WeatherCondition.RAINY,
        WeatherCondition.STORMY
    ),
    private val cooldownSeconds: Long = 300
) {
    private val logger = LoggerFactory.getLogger(javaClass)
    private val lastAlertTime = ConcurrentHashMap<String, Long>()

    suspend fun checkAndAlert(weather: AggregatedWeather) {
        val locationKey = "${weather.latitude.format(2)}:${weather.longitude.format(2)}"
        val now = System.currentTimeMillis()
        val cooldownMillis = TimeUnit.SECONDS.toMillis(cooldownSeconds)

        val lastTime = lastAlertTime[locationKey]
        if (lastTime != null && now - lastTime < cooldownMillis) {
            return
        }

        val alerts = mutableListOf<Alert>()

        if (weather.temperature >= highTempThreshold) {
            alerts.add(
                Alert(
                    id = "high-temp-$locationKey-$now",
                    type = AlertType.HIGH_TEMPERATURE,
                    latitude = weather.latitude,
                    longitude = weather.longitude,
                    temperature = weather.temperature,
                    condition = weather.condition,
                    message = "High temperature alert: ${weather.temperature}°C exceeds threshold of ${highTempThreshold}°C",
                    timestamp = now
                )
            )
        }

        if (heavyRainConditions.contains(weather.condition)) {
            alerts.add(
                Alert(
                    id = "heavy-rain-$locationKey-$now",
                    type = if (weather.condition == WeatherCondition.STORMY) AlertType.STORM else AlertType.HEAVY_RAIN,
                    latitude = weather.latitude,
                    longitude = weather.longitude,
                    temperature = weather.temperature,
                    condition = weather.condition,
                    message = "Severe weather alert: ${weather.condition} detected",
                    timestamp = now
                )
            )
        }

        if (alerts.isNotEmpty()) {
            for (alert in alerts) {
                for (channel in channels) {
                    try {
                        channel.send(alert)
                    } catch (e: Exception) {
                        logger.error("Failed to send alert via channel: ${e.message}", e)
                    }
                }
                metricsRecorder.recordAlertFired()
            }
            lastAlertTime[locationKey] = now
        }
    }

    private fun Double.format(decimals: Int): String = String.format("%.${decimals}f", this)
}
