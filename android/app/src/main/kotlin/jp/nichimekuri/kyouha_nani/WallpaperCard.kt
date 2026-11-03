package jp.nichimekuri.kyouha_nani

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Shader
import android.graphics.Typeface
import android.os.Build
import android.text.Layout
import android.text.StaticLayout
import android.text.TextPaint
import org.json.JSONObject

/**
 * A plain lock-screen image with the day's text, used when that year's wallpaper (a replaced or
 * moved day) could not be downloaded. Showing the bundled first-year image would show another topic.
 */
object WallpaperCard {
    private const val WIDTH = 1080
    private const val HEIGHT = 2400
    private const val CARD_LEFT = 82f
    private const val CARD_RIGHT = WIDTH - 82f
    private const val CARD_TOP = 675f
    private const val PAD = 50f

    // Same colors as tools/compose_wallpapers.py VISUAL_COLORS.
    private val visualColors = mapOf(
        "nature" to Color.rgb(78, 120, 85), "water" to Color.rgb(47, 119, 132),
        "travel" to Color.rgb(50, 109, 122), "history" to Color.rgb(120, 92, 73),
        "people" to Color.rgb(183, 101, 86), "peace" to Color.rgb(71, 121, 94),
        "sports" to Color.rgb(77, 133, 93), "science" to Color.rgb(76, 102, 132),
        "space" to Color.rgb(81, 88, 141), "culture" to Color.rgb(145, 105, 75),
        "food" to Color.rgb(166, 111, 62), "health" to Color.rgb(73, 130, 115),
        "technology" to Color.rgb(60, 104, 115), "work" to Color.rgb(104, 98, 79),
        "seasonal" to Color.rgb(100, 122, 84),
    )

    fun render(entry: JSONObject): Bitmap {
        val bitmap = Bitmap.createBitmap(WIDTH, HEIGHT, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        val color = visualColors[entry.optString("visual")] ?: Color.rgb(39, 96, 82)
        canvas.drawRect(0f, 0f, WIDTH.toFloat(), HEIGHT.toFloat(), Paint().apply {
            shader = LinearGradient(
                0f, 0f, 0f, HEIGHT.toFloat(), lighten(color, .72f), lighten(color, .34f), Shader.TileMode.CLAMP,
            )
        })

        val width = (CARD_RIGHT - CARD_LEFT - 2 * PAD).toInt()
        val (month, day) = entry.getString("date").split("-").map { it.toInt() }
        val blocks = listOf(
            layout("${month}月${day}日 ・ ${entry.optString("kind")}", 34f, Color.rgb(65, 90, 82), false, width),
            layout(entry.optString("title"), 68f, Color.rgb(25, 50, 43), true, width),
            layout(entry.optString("summary"), 42f, Color.rgb(32, 51, 45), false, width),
            layout("今日の仕事メモ", 32f, Color.rgb(25, 74, 62), true, width),
            layout(entry.optString("work_tip"), 38f, Color.rgb(32, 51, 45), false, width),
        )
        val gaps = listOf(16f, 22f, 30f, 10f)
        val height = 2 * PAD + blocks.sumOf { it.height } + gaps.sum()
        canvas.drawRoundRect(
            RectF(CARD_LEFT, CARD_TOP, CARD_RIGHT, CARD_TOP + height), 36f, 36f,
            Paint(Paint.ANTI_ALIAS_FLAG).apply { this.color = Color.argb(240, 248, 247, 242) },
        )
        var y = CARD_TOP + PAD
        blocks.forEachIndexed { index, block ->
            canvas.save()
            canvas.translate(CARD_LEFT + PAD, y)
            block.draw(canvas)
            canvas.restore()
            y += block.height + gaps.getOrElse(index) { 0f }
        }
        return bitmap
    }

    private fun layout(text: String, size: Float, color: Int, bold: Boolean, width: Int): StaticLayout {
        val paint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
            textSize = size
            this.color = color
            typeface = if (bold) Typeface.DEFAULT_BOLD else Typeface.DEFAULT
        }
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            StaticLayout.Builder.obtain(text, 0, text.length, paint, width)
                .setLineSpacing(0f, 1.25f)
                .build()
        } else {
            @Suppress("DEPRECATION")
            StaticLayout(text, paint, width, Layout.Alignment.ALIGN_NORMAL, 1.25f, 0f, false)
        }
    }

    private fun lighten(color: Int, amount: Float): Int = Color.rgb(
        (Color.red(color) + (255 - Color.red(color)) * amount).toInt(),
        (Color.green(color) + (255 - Color.green(color)) * amount).toInt(),
        (Color.blue(color) + (255 - Color.blue(color)) * amount).toInt(),
    )
}
