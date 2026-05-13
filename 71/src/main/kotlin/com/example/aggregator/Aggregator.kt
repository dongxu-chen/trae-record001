package com.example.aggregator

import com.example.client.WeatherProvider
import com.example.model.AggregatedWeather
import com.example.model.RawWeatherData
import com.example.model.WeatherCondition
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import org.slf4j.LoggerFactory

class WeatherAggregator(
    private val providers: List<WeatherProvider>
) {
    private val logger = LoggerFactory.getLogger(javaClass)

    suspend fun getAggregatedWeather(latitude: Double, longitude: Double): AggregatedWeather {
        val rawData = fetchFromAllProviders(latitude, longitude)

        if (rawData.isEmpty()) {
            throw RuntimeException("No weather data available from any provider")
        }

        return aggregate(rawData)
    }

    private suspend fun fetchFromAllProviders(lat: Double, lon: Double): List<RawWeatherData> =
        coroutineScope {
            providers
                .sortedBy { it.priority }
                .map { provider ->
                    async {
                        val result = provider.fetchWeather(lat, lon)
                        result.getOrNull()
                    }
                }
                .awaitAll()
                .filterNotNull()
        }

    private fun aggregate(data: List<RawWeatherData>): AggregatedWeather {
        if (data.size == 1) {
            val single = data.first()
            return AggregatedWeather(
                latitude = single.latitude,
                longitude = single.longitude,
                temperature = single.temperature,
                temperatureSources = mapOf(single.source to single.temperature),
                humidity = single.humidity,
                windSpeed = single.windSpeed,
                windSpeedSources = mapOf(single.source to single.windSpeed),
                condition = single.condition,
                conditionSources = mapOf(single.source to single.condition),
                precipitation = single.precipitation,
                sources = listOf(single.source)
            )
        }

        val tempSources = data.associate { it.source to it.temperature }
        val windSources = data.associate { it.source to it.windSpeed }
        val condSources = data.associate { it.source to it.condition }

        val votedTemp = voteNumeric(data.map { it.temperature }, data.map { it.source }, providers)
        val votedWind = voteNumeric(data.map { it.windSpeed }, data.map { it.source }, providers)
        val votedCondition = voteCondition(data.map { it.condition to it.source }, providers)

        val humidityValues = data.mapNotNull { it.humidity }
        val avgHumidity = if (humidityValues.isNotEmpty()) humidityValues.average() else null

        val precipValues = data.mapNotNull { it.precipitation }
        val avgPrecip = if (precipValues.isNotEmpty()) precipValues.average() else null

        return AggregatedWeather(
            latitude = data.first().latitude,
            longitude = data.first().longitude,
            temperature = votedTemp,
            temperatureSources = tempSources,
            humidity = avgHumidity,
            windSpeed = votedWind,
            windSpeedSources = windSources,
            condition = votedCondition,
            conditionSources = condSources,
            precipitation = avgPrecip,
            sources = data.map { it.source }
        )
    }

    private fun voteNumeric(
        values: List<Double>,
        sources: List<String>,
        allProviders: List<WeatherProvider>
    ): Double {
        if (values.isEmpty()) return 0.0
        if (values.size == 1) return values.first()

        val weightedSum = values.zip(sources).sumOf { (value, source) ->
            val weight = allProviders.find { it.name == source }?.priority ?: 1
            value * weight.toDouble()
        }

        val totalWeight = sources.sumOf { source ->
            allProviders.find { it.name == source }?.priority ?: 1
        }.toDouble()

        return weightedSum / totalWeight
    }

    private fun voteCondition(
        conditions: List<Pair<WeatherCondition, String>>,
        allProviders: List<WeatherProvider>
    ): WeatherCondition {
        if (conditions.isEmpty()) return WeatherCondition.UNKNOWN
        if (conditions.size == 1) return conditions.first().first

        val votes = mutableMapOf<WeatherCondition, Int>()

        for ((condition, source) in conditions) {
            val weight = allProviders.find { it.name == source }?.priority ?: 1
            votes[condition] = (votes[condition] ?: 0) + weight
        }

        val sortedVotes = votes.entries.sortedByDescending { it.value }

        val maxVotes = sortedVotes.first().value
        val tieCandidates = sortedVotes.takeWhile { it.value == maxVotes }.map { it.key }

        if (tieCandidates.size == 1) {
            return tieCandidates.first()
        }

        for ((condition, source) in conditions.sortedBy { (_, source) ->
            allProviders.find { it.name == source }?.priority ?: Int.MAX_VALUE
        }) {
            if (tieCandidates.contains(condition)) {
                return condition
            }
        }

        return conditions.first().first
    }
}
