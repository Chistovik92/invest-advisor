package ru.secrethero.invest

import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Window
import androidx.compose.ui.window.application
import androidx.compose.ui.window.rememberWindowState
import io.ktor.client.engine.cio.CIO

fun main() = application {
    Window(
        onCloseRequest = ::exitApplication,
        title = "InvestAdvisor",
        state = rememberWindowState(width = 480.dp, height = 820.dp),
    ) {
        App(client = ApiClient(CIO.create()))
    }
}
