package ru.secrethero.invest

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ProviderHealthDto(
    @SerialName("provider_id") val providerId: String,
    val title: String,
    val mode: String,
    val configured: Boolean,
    val connected: Boolean,
    @SerialName("latency_ms") val latencyMs: Double? = null,
    val message: String,
)

@Serializable
data class PositionDto(
    val broker: String = "tinvest",
    val figi: String = "",
    val ticker: String,
    val name: String,
    val type: String,
    val quantity: Double,
    val lot: Int = 1,
    @SerialName("current_price") val currentPrice: Double,
    @SerialName("lot_price") val lotPrice: Double,
    @SerialName("total_value") val totalValue: Double,
    @SerialName("pnl_pct") val pnlPct: Double = 0.0,
    @SerialName("is_exit_candidate") val isExitCandidate: Boolean = false,
    @SerialName("exit_target_pnl") val exitTargetPnl: Double? = null,
)

@Serializable
data class SnapshotDto(
    @SerialName("iis_account_id") val iisAccountId: String = "",
    @SerialName("total_iis_value") val totalIisValue: Double = 0.0,
    @SerialName("external_brokers_value") val externalBrokersValue: Double = 0.0,
    @SerialName("rub_balance") val rubBalance: Double = 0.0,
    @SerialName("margin_debt") val marginDebt: Double = 0.0,
    @SerialName("tmon_available") val tmonAvailable: Double = 0.0,
    val positions: List<PositionDto> = emptyList(),
    @SerialName("providers_health") val providersHealth: List<ProviderHealthDto> = emptyList(),
)

@Serializable
data class RebalanceOrderDto(
    val ticker: String,
    val name: String,
    @SerialName("asset_class") val assetClass: String,
    @SerialName("lots_to_buy") val lotsToBuy: Int,
    @SerialName("shares_count") val sharesCount: Int,
    @SerialName("lot_price") val lotPrice: Double,
    @SerialName("total_cost") val totalCost: Double,
    @SerialName("current_share_pct") val currentSharePct: Double,
    @SerialName("target_share_pct") val targetSharePct: Double,
)

@Serializable
data class RebalancePlanDto(
    val snapshot: SnapshotDto,
    @SerialName("deposit_amount") val depositAmount: Double,
    @SerialName("margin_debt_covered") val marginDebtCovered: Double,
    @SerialName("remaining_margin_debt") val remainingMarginDebt: Double,
    val orders: List<RebalanceOrderDto>,
    @SerialName("unspent_cash") val unspentCash: Double,
    val summary: String,
)
