package app.aize.nav

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.os.Build
import android.speech.tts.TextToSpeech
import android.util.Log
import java.util.Locale

/**
 * Turn-by-turn speech through the platform TTS engine.
 *
 * The audio attributes matter as much as the words: `USAGE_ASSISTANCE_NAVIGATION_SERVICE` in the navigation
 * usage family means a music app ducks instead of pausing, and `USAGE_ASSISTANCE_NAVIGATION_GUIDANCE` on the
 * request keeps the prompts out of the media stream. Anything spoken is spoken in the current language and
 * queue-flushed so a stale instruction can never talk over the current one.
 */
class Voice(private val ctx: Context) : TextToSpeech.OnInitListener {
    private var tts: TextToSpeech? = null
    private var ready = false
    private var focus: AudioFocusRequest? = null

    fun start() {
        if (tts != null) return
        tts = TextToSpeech(ctx.applicationContext, this)
    }

    override fun onInit(status: Int) {
        if (status != TextToSpeech.SUCCESS) {
            Log.w("AizeVoice", "TTS init failed: $status")
            return
        }
        val engine = tts ?: return
        engine.setLanguage(Locale.getDefault())
        engine.setAudioAttributes(
            AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ASSISTANCE_NAVIGATION_GUIDANCE)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                .build(),
        )
        ready = true
        Log.i("AizeVoice", "ready, language ${engine.voice?.locale}")
    }

    /** Speaks one prompt, interrupting anything already queued: the newest instruction is the true one. */
    fun say(text: String) {
        if (!ready) {
            Log.i("AizeVoice", "not ready, dropped: $text")
            return
        }
        val engine = tts ?: return
        requestFocus()
        val r = engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "aize-nav")
        Log.i("AizeVoice", "speak rc=$r text=$text")
    }

    fun stop() {
        tts?.stop()
        abandonFocus()
        tts?.shutdown()
        tts = null
        ready = false
    }

    private fun requestFocus() {
        val am = ctx.getSystemService(Context.AUDIO_SERVICE) as? AudioManager ?: return
        val attrs = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_ASSISTANCE_NAVIGATION_GUIDANCE)
            .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
            .build()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val req = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
                .setAudioAttributes(attrs)
                .setWillPauseWhenDucked(false)
                .build()
            focus = req
            am.requestAudioFocus(req)
        } else {
            @Suppress("DEPRECATION")
            am.requestAudioFocus(null, AudioManager.STREAM_MUSIC, AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
        }
    }

    private fun abandonFocus() {
        val am = ctx.getSystemService(Context.AUDIO_SERVICE) as? AudioManager ?: return
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) focus?.let { am.abandonAudioFocusRequest(it) }
        focus = null
    }
}
