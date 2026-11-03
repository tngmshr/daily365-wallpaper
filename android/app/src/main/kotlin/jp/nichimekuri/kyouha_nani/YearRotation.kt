package jp.nichimekuri.kyouha_nani

import org.json.JSONObject

/**
 * Resolves the content of one calendar year: 2nd-4th year replacements and solar terms whose date
 * moves by year. Same rules as tools/build_year.py (which renders Pages' wallpapers/YYYY/) and
 * lib/year_calendar.dart (the in-app page). Keep the three in step.
 *
 * Pure Kotlin + org.json so it can be checked on a plain JVM against the Python output.
 */
class YearRotation(
    calendarJson: String,
    private val slots: Map<Int, String?>,
    solarTermsJson: String?,
) {
    /** [changed] is true when the entry differs from the bundled first-year entry for that date. */
    data class Day(val entry: JSONObject, val changed: Boolean)

    private val base = LinkedHashMap<String, JSONObject>()
    private val solarTerms: JSONObject? = solarTermsJson?.let { parseOrNull(it) }
    private val years = HashMap<Int, Map<String, Day>>()

    init {
        val payload = JSONObject(calendarJson)
        val entries = payload.getJSONArray("entries")
        for (index in 0 until entries.length()) {
            val row = entries.getJSONObject(index)
            base[row.getString("date")] = row
        }
        payload.optJSONObject("leap_day")?.let { base[it.getString("date")] = it }
    }

    fun day(year: Int, key: String): Day? = resolve(year)[key]

    @Synchronized
    fun resolve(year: Int): Map<String, Day> = years.getOrPut(year) { resolveYear(year) }

    private fun resolveYear(year: Int): Map<String, Day> {
        val rows = LinkedHashMap<String, Day>()
        for ((key, row) in base) rows[key] = Day(copy(row), changed = false)

        val slot = slotFor(year)
        if (slot != 1) {
            val overrides = slots[slot]?.let { parseOrNull(it) }
            if (overrides != null) {
                for (key in overrides.keys()) {
                    val replacement = overrides.optJSONObject(key) ?: continue
                    // A broken replacement keeps the first-year entry (Python stops before publishing).
                    if (!rows.containsKey(key) || replacement.optString("date", key) != key) continue
                    rows[key] = Day(copy(replacement).put("date", key), changed = true)
                }
            }
        }

        val dates = solarTerms?.optJSONObject(year.toString())
        if (dates != null) {
            val terms = rows.values.mapNotNull { it.entry.optString("solar_term", "").ifEmpty { null } }
            val targets = terms.mapNotNull { dates.optString(it, "").ifEmpty { null } }
            if (terms.toSet().size == terms.size && targets.toSet().size == targets.size) {
                for (term in terms) {
                    val target = dates.optString(term, "")
                    if (target.isEmpty() || !rows.containsKey(target)) continue
                    if (target == "02-29" && !isLeap(year)) continue
                    val source = rows.entries.first { it.value.entry.optString("solar_term", "") == term }.key
                    if (source == target) continue
                    for (key in listOf(source, target)) {
                        val entry = rows.getValue(key).entry
                        if (!entry.has("illustration_date")) entry.put("illustration_date", entry.getString("date"))
                    }
                    val moved = rows.getValue(source).entry
                    val other = rows.getValue(target).entry
                    rows[source] = Day(other.put("date", source), changed = true)
                    rows[target] = Day(moved.put("date", target), changed = true)
                }
            }
        }

        if (!isLeap(year)) rows.remove("02-29")
        return rows
    }

    companion object {
        const val FIRST_YEAR = 2027

        /** 2027 is year 1 of the four-year cycle; earlier years stay on the first-year data. */
        fun slotFor(year: Int): Int = if (year < FIRST_YEAR) 1 else Math.floorMod(year - FIRST_YEAR, 4) + 1

        fun isLeap(year: Int): Boolean = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)

        /** [read] returns a file under assets/data/ (e.g. "years/slot2.json"), or null when missing. */
        fun load(read: (String) -> String?): YearRotation = YearRotation(
            read("calendar.json") ?: throw IllegalStateException("calendar.json is missing"),
            (2..4).associateWith { read("years/slot$it.json") },
            read("solar_terms.json"),
        )

        private fun copy(row: JSONObject) = JSONObject(row.toString())

        private fun parseOrNull(text: String): JSONObject? = try {
            JSONObject(text)
        } catch (_: Exception) {
            null
        }
    }
}
