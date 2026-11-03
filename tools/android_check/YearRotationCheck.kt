import jp.nichimekuri.kyouha_nani.YearRotation
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import kotlin.system.exitProcess

// Parity check: android YearRotation vs tools/build_year.py output, years 2025-2034.
fun canonical(value: Any?): Any? = when (value) {
    is JSONObject -> value.keys().asSequence().toList().sorted().associateWith { canonical(value.get(it)) }
    is JSONArray -> (0 until value.length()).map { canonical(value.get(it)) }
    else -> value
}

fun rows(file: File): Map<String, Any?> {
    val payload = JSONObject(file.readText())
    val list = payload.getJSONArray("entries")
    val out = (0 until list.length()).associate { list.getJSONObject(it).getString("date") to canonical(list.getJSONObject(it)) }.toMutableMap()
    payload.optJSONObject("leap_day")?.let { out[it.getString("date")] = canonical(it) }
    return out
}

fun main(args: Array<String>) {
    val data = File(args[0], "assets/data")
    val py = File(args[1])
    var failures = 0
    fun check(ok: Boolean, message: String) { if (!ok) { failures++; if (failures < 20) println("FAIL $message") } }
    check((2024..2031).map { YearRotation.slotFor(it) } == listOf(1, 1, 1, 1, 2, 3, 4, 1), "slotFor")
    val rotation = YearRotation.load { name -> File(data, name).takeIf { it.isFile }?.readText() }
    val base = rows(File(data, "calendar.json"))
    for (year in 2025..2034) {
        val expected = rows(File(py, "$year.json"))
        val actual = rotation.resolve(year)
        check(expected.keys.sorted() == actual.keys.sorted(), "$year dates")
        var changed = 0
        for ((key, day) in actual) {
            check(expected[key] == canonical(day.entry), "$year $key entry")
            check((expected[key] != base[key]) == day.changed, "$year $key changed flag")
            if (day.changed) changed++
        }
        println("$year: ${actual.size} days, $changed differ from the first year")
    }
    // A missing slot file keeps the first-year data.
    val noSlots = YearRotation.load { name -> if (name == "calendar.json") File(data, name).readText() else null }
    check(noSlots.resolve(2028).values.none { it.changed }, "missing files fall back to base")
    println(if (failures == 0) "ALL OK" else "$failures failures")
    exitProcess(if (failures == 0) 0 else 1)
}
