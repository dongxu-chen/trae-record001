package com.example.client

import com.example.model.RawWeatherData

interface WeatherProvider {
    val name: String
    val priority: Int

    suspend fun fetchWeather(latitude: Double, longitude: Double): Result<RawWeatherData>
}
