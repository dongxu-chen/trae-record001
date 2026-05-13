package com.example.client

import com.example.model.RawWeatherData
import com.example.model.WeatherCondition
import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.request.*
import kotlinx.serialization.Serializable
import org.slf4j.LoggerFactory

@Serializable
private data class SevenTimerResponse(
    val dataseries: List<SevenTimerDataPoint> = emptyList()
)

@Serializable
private data class SevenTimerDataPoint(
    val timepoint: Int,
    val temp2m: Int,
    val wind10m: Wind10m? = null,
    val weather: String
)

@Serializable
private data class Wind10m(
    val direction: String,
    val speed: Int
)

class SevenTimerProvider(
    private val httpClient: HttpClient,
    private val baseUrl: String = "https://www.7timer.info"
) : WeatherProvider {
    override val name: String = "7timer"
    override val priority: Int = 2

    private val logger = LoggerFactory.getLogger(javaClass)

    override suspend fun fetchWeather(latitude: Double, longitude: Double): Result<RawWeatherData> {
        return try {
            val lonStr = longitude.coerceIn(-180.0, 180.0).let {
                if (it < 0) (it + 360) else it
            }.toString()
            val latStr = latitude.toString()

            val url = "$baseUrl/bin/astro.php"
            val response = httpClient.get(url) {
                parameter("lon", lonStr)
                parameter("lat", latStr)
                parameter("product", "civil")
                parameter("output", "json")
            }.body<SevenTimerResponse>()

            val currentPoint = response.dataseries.firstOrNull()
                ?: return Result.failure(RuntimeException("No data from 7Timer"))

            val wind = currentPoint.wind10m
            Result.success(
                RawWeatherData(
                    source = name,
                    latitude = latitude,
                    longitude = longitude,
                    temperature = currentPoint.temp2m.toDouble(),
                    windSpeed = (wind?.speed ?: 1) * 3.6,
                    windDirection = mapWindDirection(wind?.direction ?: "N"),
                    condition = mapWeather(currentPoint.weather)
                )
            )
        } catch (e: Exception) {
            logger.error("Failed to fetch from 7Timer: ${e.message}", e)
            Result.failure(e)
        }
    }

    private fun mapWeather(weather: String): WeatherCondition {
        return when {
            weather.contains("clear", ignoreCase = true) -> WeatherCondition.SUNNY
            weather.contains("pcloudy", ignoreCase = true) -> WeatherCondition.PARTLY_CLOUDY
            weather.contains("cloudy", ignoreCase = true) -> WeatherCondition.CLOUDY
            weather.contains("rain", ignoreCase = true) -> WeatherCondition.RAINY
            weather.contains("ts", ignoreCase = true) -> WeatherCondition.STORMY
            weather.contains("snow", ignoreCase = true) -> WeatherCondition.SNOWY
            weather.contains("fog", ignoreCase = true) -> WeatherCondition.FOGGY
            else -> WeatherCondition.UNKNOWN
        }
    }

    private fun mapWindDirection(direction: String): Double {
        return when (direction.uppercase()) {
            "N" -> 0.0
            "NE" -> 45.0
            "E" -> 90.0
            "SE" -> 135.0
            "S" -> 180.0
            "SW" -> 225.0
            "W" -> 270.0
            "NW" -> 315.0
            else -> 0.0
        }
    }
}
