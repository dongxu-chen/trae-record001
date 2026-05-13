package com.example.client

import com.example.model.RawWeatherData
import com.example.model.WeatherCondition
import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.request.*
import kotlinx.serialization.Serializable
import org.slf4j.LoggerFactory

@Serializable
private data class OpenMeteoResponse(
    val latitude: Double,
    val longitude: Double,
    val current_weather: OpenMeteoCurrentWeather? = null
)

@Serializable
private data class OpenMeteoCurrentWeather(
    val temperature: Double,
    val windspeed: Double,
    val winddirection: Double,
    val weathercode: Int,
    val time: String
)

class OpenMeteoProvider(
    private val httpClient: HttpClient,
    private val baseUrl: String = "https://api.open-meteo.com"
) : WeatherProvider {
    override val name: String = "open-meteo"
    override val priority: Int = 1

    private val logger = LoggerFactory.getLogger(javaClass)

    override suspend fun fetchWeather(latitude: Double, longitude: Double): Result<RawWeatherData> {
        return try {
            val url = "$baseUrl/v1/forecast"
            val response = httpClient.get(url) {
                parameter("latitude", latitude)
                parameter("longitude", longitude)
                parameter("current_weather", "true")
            }.body<OpenMeteoResponse>()

            val current = response.current_weather
                ?: return Result.failure(RuntimeException("No current weather data from Open-Meteo"))

            Result.success(
                RawWeatherData(
                    source = name,
                    latitude = response.latitude,
                    longitude = response.longitude,
                    temperature = current.temperature,
                    windSpeed = current.windspeed,
                    windDirection = current.winddirection,
                    condition = mapWeatherCode(current.weathercode)
                )
            )
        } catch (e: Exception) {
            logger.error("Failed to fetch from Open-Meteo: ${e.message}", e)
            Result.failure(e)
        }
    }

    private fun mapWeatherCode(code: Int): WeatherCondition {
        return when (code) {
            0 -> WeatherCondition.SUNNY
            1, 2 -> WeatherCondition.PARTLY_CLOUDY
            3 -> WeatherCondition.CLOUDY
            in 45..48 -> WeatherCondition.FOGGY
            in 51..67 -> WeatherCondition.RAINY
            in 71..77 -> WeatherCondition.SNOWY
            in 80..82 -> WeatherCondition.RAINY
            in 85..86 -> WeatherCondition.SNOWY
            in 95..99 -> WeatherCondition.STORMY
            else -> WeatherCondition.UNKNOWN
        }
    }
}
