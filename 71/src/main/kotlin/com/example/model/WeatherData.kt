package com.example.model

import kotlinx.serialization.Serializable

enum class WeatherCondition {
    SUNNY, CLOUDY, PARTLY_CLOUDY, RAINY, STORMY, SNOWY, FOGGY, UNKNOWN
}

@Serializable
data class RawWeatherData(
    val source: String,
    val latitude: Double,
    val longitude: Double,
    val temperature: Double,
    val humidity: Double? = null,
    val windSpeed: Double,
    val windDirection: Double,
    val condition: WeatherCondition,
    val precipitation: Double? = null,
    val timestamp: Long = System.currentTimeMillis()
)

@Serializable
data class AggregatedWeather(
    val latitude: Double,
    val longitude: Double,
    val temperature: Double,
    val temperatureSources: Map<String, Double>,
    val humidity: Double? = null,
    val windSpeed: Double,
    val windSpeedSources: Map<String, Double>,
    val condition: WeatherCondition,
    val conditionSources: Map<String, WeatherCondition>,
    val precipitation: Double? = null,
    val sources: List<String>,
    val aggregatedAt: Long = System.currentTimeMillis()
)
