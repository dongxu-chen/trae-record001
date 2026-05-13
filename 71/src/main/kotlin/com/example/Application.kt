package com.example

import com.example.alerter.ConsoleAlertChannel
import com.example.alerter.WeatherAlerter
import com.example.aggregator.WeatherAggregator
import com.example.cache.CacheManager
import com.example.client.OpenMeteoProvider
import com.example.client.SevenTimerProvider
import com.example.client.WeatherProvider
import com.example.metrics.MetricsRecorder
import com.example.routes.metricsRoutes
import com.example.routes.weatherRoutes
import io.ktor.client.*
import io.ktor.client.engine.cio.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.serialization.kotlinx.json.*
import io.ktor.server.application.*
import io.ktor.server.plugins.contentnegotiation.*
import kotlinx.serialization.json.Json

fun Application.module() {
    val config = environment.config
    val openMeteoUrl = config.propertyOrNull("weather.api.openMeteoUrl")?.getString()
        ?: "https://api.open-meteo.com"
    val sevenTimerUrl = config.propertyOrNull("weather.api.sevenTimerUrl")?.getString()
        ?: "https://www.7timer.info"
    val cacheTtl = config.propertyOrNull("weather.cache.ttlSeconds")?.getString()?.toLong()
        ?: 600L
    val cacheMaxEntries = config.propertyOrNull("weather.cache.maxEntries")?.getString()?.toInt()
        ?: 1000
    val highTempThreshold = config.propertyOrNull("weather.alert.highTempThreshold")?.getString()?.toDouble()
        ?: 35.0
    val alertCooldown = config.propertyOrNull("weather.alert.cooldownSeconds")?.getString()?.toLong()
        ?: 300L

    val httpClient = HttpClient(CIO) {
        engine {
            maxConnectionsCount = 100
            endpoint {
                maxConnectionsPerRoute = 50
                connectTimeout = 5000
                requestTimeout = 10000
                socketTimeout = 10000
            }
        }
        install(ContentNegotiation) {
            json(Json {
                prettyPrint = true
                isLenient = true
            })
        }
    }

    val providers: List<WeatherProvider> = listOf(
        OpenMeteoProvider(httpClient, openMeteoUrl),
        SevenTimerProvider(httpClient, sevenTimerUrl)
    )

    val metricsRecorder = MetricsRecorder()
    val aggregator = WeatherAggregator(providers)
    val cacheManager = CacheManager(cacheTtl, cacheMaxEntries)

    val alertChannels = listOf(ConsoleAlertChannel())
    val alerter = WeatherAlerter(
        channels = alertChannels,
        metricsRecorder = metricsRecorder,
        highTempThreshold = highTempThreshold,
        cooldownSeconds = alertCooldown
    )

    install(ContentNegotiation) {
        json(Json {
            prettyPrint = true
            isLenient = true
        })
    }

    weatherRoutes(aggregator, cacheManager, alerter, metricsRecorder)
    metricsRoutes(metricsRecorder)
}

fun main(args: Array<String>) {
    io.ktor.server.netty.EngineMain.main(args)
}
