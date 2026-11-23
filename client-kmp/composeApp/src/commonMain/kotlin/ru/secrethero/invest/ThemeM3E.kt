package ru.secrethero.invest

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = Color(0xFF006A60),
    onPrimary = Color.White,
    secondary = Color(0xFF4A635F),
    background = Color(0xFFFBFDFC),
    surface = Color.White,
    error = Color(0xFFBA1A1A),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF4DDBCB),
    onPrimary = Color(0xFF003733),
    secondary = Color(0xFFB1CCC7),
    background = Color(0xFF0E1513),
    surface = Color(0xFF16201E),
    error = Color(0xFFFFB4AB),
)

@Composable
fun AppThemeM3E(
    darkTheme: Boolean = false,
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        content = content,
    )
}
