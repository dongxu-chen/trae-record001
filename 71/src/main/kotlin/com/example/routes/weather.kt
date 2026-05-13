package com.example.routes

import com.example.alerter.WeatherAlerter
import com.example.aggregator.WeatherAggregator
import com.example.cache.CacheManager
import com.example.metrics.MetricsRecorder
import com.example.model.AggregatedWeather
import io.ktor.http.*
import io.ktor.server.application.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import io.ktor.server.routing.get
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

fun Application.weatherRoutes(
    aggregator: WeatherAggregator,
    cacheManager: CacheManager,
    alerter: WeatherAlerter,
    metricsRecorder: MetricsRecorder
) {
    routing {
        route("/api/weather") {
            get("/current") {
                metricsRecorder.recordRequest()

                val latParam = call.request.queryParameters["lat"]
                val lonParam = call.request.queryParameters["lon"]

                val validationErrors = mutableListOf<String>()

                if (latParam.isNullOrBlank()) {
                    validationErrors.add("lat parameter is required")
                }

                if (lonParam.isNullOrBlank()) {
                    validationErrors.add("lon parameter is required")
                }

                val latitude = if (latParam != null) {
                    val parsed = latParam.toDoubleOrNull()
                    if (parsed == null) {
                        validationErrors.add("lat must be a valid number")
                    } else if (parsed < -90.0 || parsed > 90.0) {
                        validationErrors.add("lat must be between -90 and 90")
                    }
                    parsed
                } else {
                    null
                }

                val longitude = if (lonParam != null) {
                    val parsed = lonParam.toDoubleOrNull()
                    if (parsed == null) {
                        validationErrors.add("lon must be a valid number")
                    } else if (parsed < -180.0 || parsed > 180.0) {
                        validationErrors.add("lon must be between -180 and 180")
                    }
                    parsed
                } else {
                    null
                }

                if (validationErrors.isNotEmpty()) {
                    call.respondText(
                        "Validation errors: ${validationErrors.joinToString(", ")}",
                        status = HttpStatusCode.BadRequest
                    )
                    return@get
                }

                latitude!!
                longitude!!

                val cacheKey = "weather:${latitude.format(4)}:${longitude.format(4)}"
                val cached = cacheManager.get(cacheKey)

                if (cached != null) {
                    metricsRecorder.recordCacheHit()
                    call.response.header("X-Cache", "HIT")
                    call.respondText(cached, ContentType.Application.Json)
                    return@get
                }

                metricsRecorder.recordCacheMiss()

                val weather = try {
                    aggregator.getAggregatedWeather(latitude, longitude)
                } catch (e: Exception) {
                    call.respondText(
                        "Failed to fetch weather data: ${e.message}",
                        status = HttpStatusCode.ServiceUnavailable
                    )
                    return@get
                }

                for (source in weather.sources) {
                    metricsRecorder.recordProviderSuccess(source)
                }

                val json = Json.encodeToString(AggregatedWeather.serializer(), weather)
                cacheManager.put(cacheKey, json)

                alerter.checkAndAlert(weather)

                call.response.header("X-Cache", "MISS")
                call.respond(weather)
            }
        }
    }
}

private fun Double.format(decimals: Int): String {
    return String.format("%.${decimals}f", this)
}
