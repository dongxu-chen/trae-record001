package com.example.routes

import com.example.metrics.MetricsRecorder
import io.ktor.http.*
import io.ktor.server.application.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import io.ktor.server.routing.delete
import io.ktor.server.routing.get

fun Application.metricsRoutes(metricsRecorder: MetricsRecorder) {
    routing {
        route("/api/metrics") {
            get {
                call.respond(metricsRecorder.snapshot())
            }

            delete("/reset") {
                metricsRecorder.reset()
                call.respondText("Metrics reset", status = HttpStatusCode.OK)
            }
        }
    }
}
