package ru.secrethero.invest

import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals

class RebalanceModelTest {

    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun `snapshot dto parses 18 providers health`() {
        val raw = """
            {
              "iis_account_id": "IIS-MAIN",
              "total_iis_value": 259000.0,
              "external_brokers_value": 12500.0,
              "rub_balance": -2848.31,
              "margin_debt": 2848.31,
              "tmon_available": 150000.0,
              "positions": [
                {"ticker": "SBER", "name": "Сбербанк", "type": "share", "quantity": 10.0,
                 "current_price": 290.0, "lot_price": 290.0, "total_value": 2900.0, "pnl_pct": 5.0}
              ],
              "providers_health": [
                {"provider_id": "tinvest", "title": "Т-Инвестиции", "mode": "api",
                 "configured": true, "connected": true, "latency_ms": 45.0, "message": "ok"}
              ]
            }
        """.trimIndent()

        val snapshot = json.decodeFromString<SnapshotDto>(raw)
        assertEquals(259000.0, snapshot.totalIisValue)
        assertEquals(2848.31, snapshot.marginDebt)
        assertEquals("SBER", snapshot.positions.first().ticker)
        assertEquals("tinvest", snapshot.providersHealth.first().providerId)
    }

    @Test
    fun `rebalance plan dto parses orders`() {
        val raw = """
            {
              "snapshot": {},
              "deposit_amount": 15000.0,
              "margin_debt_covered": 2848.31,
              "remaining_margin_debt": 0.0,
              "orders": [
                {"ticker": "SU26236RMFS8", "name": "ОФЗ 26236", "asset_class": "Облигации баланса",
                 "lots_to_buy": 8, "shares_count": 8, "lot_price": 750.0, "total_cost": 6000.0,
                 "current_share_pct": 0.0, "target_share_pct": 10.0}
              ],
              "unspent_cash": 6151.69,
              "summary": "Подобрано 1 позиций."
            }
        """.trimIndent()

        val plan = json.decodeFromString<RebalancePlanDto>(raw)
        assertEquals(2848.31, plan.marginDebtCovered)
        assertEquals(8, plan.orders.first().lotsToBuy)
        assertEquals(6151.69, plan.unspentCash)
    }
}
