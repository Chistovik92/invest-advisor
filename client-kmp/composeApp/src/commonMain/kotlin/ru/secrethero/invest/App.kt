package ru.secrethero.invest

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

private fun fmt(value: Double): String = "%,.2f".format(value).replace(',', ' ')

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun App(client: ApiClient) {
    var snapshot by remember { mutableStateOf<SnapshotDto?>(null) }
    var plan by remember { mutableStateOf<RebalancePlanDto?>(null) }
    var error by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        try {
            snapshot = client.fetchSnapshot()
            plan = client.fetchRecommendations(15000.0)
        } catch (e: Exception) {
            error = e.message ?: "Ошибка подключения"
        }
    }

    AppThemeM3E(darkTheme = false) {
        Scaffold(
            topBar = {
                TopAppBar(
                    title = { Text("InvestAdvisor — Мультиброкерный ребаланс") },
                    colors = TopAppBarDefaults.topAppBarColors(
                        containerColor = MaterialTheme.colorScheme.primary,
                        titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    ),
                )
            },
        ) { padding ->
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                when {
                    error != null -> Text("Ошибка: $error", color = MaterialTheme.colorScheme.error)
                    snapshot == null -> {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            CircularProgressIndicator()
                            Spacer(Modifier.width(12.dp))
                            Text("Загрузка портфеля…")
                        }
                    }
                    else -> {
                        val s = snapshot!!
                        SummaryCard(s)
                        ProviderHealthCard(s)
                        plan?.let { OrdersCard(it) }
                    }
                }
            }
        }
    }
}

@Composable
private fun SummaryCard(s: SnapshotDto) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Сводка по портфелю", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            MetricRow("ИИС:", "${fmt(s.totalIisValue)} ₽")
            MetricRow("Внешние брокеры:", "${fmt(s.externalBrokersValue)} ₽")
            MetricRow("Свободные рубли:", "${fmt(s.rubBalance)} ₽")
            MetricRow("Маржинальный долг:", "${fmt(s.marginDebt)} ₽")
            MetricRow("Подушка TMON:", "${fmt(s.tmonAvailable)} ₽")
        }
    }
}

@Composable
private fun ProviderHealthCard(s: SnapshotDto) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Статус платформ (${s.providersHealth.size})", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            s.providersHealth.forEach { h ->
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(h.title, style = MaterialTheme.typography.bodyMedium)
                    Text(
                        if (h.connected) "✓" else if (h.configured) "✗" else "—",
                        color = when {
                            h.connected -> MaterialTheme.colorScheme.primary
                            h.configured -> MaterialTheme.colorScheme.error
                            else -> MaterialTheme.colorScheme.outline
                        },
                        fontWeight = FontWeight.Bold,
                    )
                }
                HorizontalDivider()
            }
        }
    }
}

@Composable
private fun OrdersCard(p: RebalancePlanDto) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("План покупок на ${fmt(p.depositAmount)} ₽", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            if (p.marginDebtCovered > 0) {
                Text("Погашение маржи: ${fmt(p.marginDebtCovered)} ₽", color = MaterialTheme.colorScheme.error)
            }
            p.orders.forEach { o ->
                Column(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text("${o.name} (${o.ticker})", fontWeight = FontWeight.SemiBold)
                        Text("${fmt(o.totalCost)} ₽")
                    }
                    Text(
                        "${o.lotsToBuy} лот. (${o.sharesCount} шт.) — цель ${"%.1f".format(o.targetSharePct)}%",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.outline,
                    )
                }
                HorizontalDivider()
            }
            Spacer(Modifier.height(4.dp))
            Text("Остаток кэша: ${fmt(p.unspentCash)} ₽", fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun MetricRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = MaterialTheme.colorScheme.outline)
        Text(value, fontWeight = FontWeight.SemiBold)
    }
}
