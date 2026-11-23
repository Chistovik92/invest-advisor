-- tools/quik_bridge.lua
-- Запускается в QUIK (Сервисы -> Lua скрипты) и синхронизирует портфель с InvestAdvisor
local BROKER_ID = "sovcom" -- или "rencredit", "uralsib", "vtb", "sber"
local SERVER_URL = "http://127.0.0.1:8085/api/quik-bridge/" .. BROKER_ID

is_run = true
function OnStop()
    is_run = false
end

function main()
    while is_run do
        local n = getNumberOf("depo_limits")
        local items = {}
        for i = 0, n - 1 do
            local row = getItem("depo_limits", i)
            if row and row.currentbal > 0 and row.limit_kind == 2 then
                table.insert(items, string.format(
                    '{"ticker":"%s","quantity":%f,"price":%f}',
                    row.sec_code, row.currentbal, row.awg_position_price
                ))
            end
        end
        local payload = "[" .. table.concat(items, ",") .. "]"
        os.execute(string.format(
            'curl -s -X POST -H "Content-Type: application/json" -d \'%s\' "%s"',
            payload, SERVER_URL
        ))
        sleep(60000) -- обновление раз в минуту
    end
end
