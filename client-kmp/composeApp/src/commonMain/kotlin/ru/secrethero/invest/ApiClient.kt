package ru.secrethero.invest

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.engine.HttpClientEngine
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.request.get
import io.ktor.client.request.parameter
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json

class ApiClient(
    engine: HttpClientEngine,
    private val baseUrl: String = "http://127.0.0.1:8085",
) {
    private val client = HttpClient(engine) {
        install(ContentNegotiation) {
            json(Json { ignoreUnknownKeys = true })
        }
    }

    suspend fun fetchSnapshot(): SnapshotDto =
        client.get("$baseUrl/api/portfolio").body()

    suspend fun fetchRecommendations(deposit: Double = 15000.0): RebalancePlanDto =
        client.get("$baseUrl/api/recommend") {
            parameter("deposit", deposit)
        }.body()
}
