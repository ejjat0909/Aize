package app.aize.nav

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/**
 * The one navigation session the app and the foreground service share. Both live in the same process, so a
 * singleton is the whole IPC: the service writes, the UI reads.
 *
 * Only one route is active at a time. Starting a route replaces it; stopping clears it.
 */
object NavSession {
    /** What the UI and the notification show. Immutable so Compose recomposes on identity. */
    data class State(
        val active: Boolean = false,
        val alongMeters: Double = 0.0,
        val lengthMeters: Double = 0.0,
        val remainingMeters: Double = 0.0,
        val offRouteMeters: Double = 0.0,
        val arrived: Boolean = false,
        val instruction: String? = null,
        val metersToInstruction: Double = 0.0,
        val after: String? = null,
        val lastPrompt: String? = null,
        val fixes: Int = 0,
    )

    private val _state = MutableStateFlow(State())
    private val _reroute = MutableStateFlow(0)

    /** Increments when the service decides the driver has left the route; the UI performs the network call. */
    val rerouteTicks: StateFlow<Int> = _reroute

    fun requestReroute() {
        _reroute.value += 1
    }
    val state: StateFlow<State> = _state

    /** The route being navigated, or null when nothing is running. Written by the service, read by the UI. */
    @Volatile
    var route: Route? = null
        private set

    /** Heading of the last fix, for the camera. */
    @Volatile
    var bearing: Double = 0.0

    /** A prompt the service wants spoken, surfaced for tests and for the UI log. */
    @Volatile
    var lastPrompt: String? = null

    fun start(route: Route) {
        this.route = route
        _state.value = State(active = true, lengthMeters = route.path.lengthMeters, remainingMeters = route.path.lengthMeters)
    }

    fun publish(state: State) {
        _state.value = state.copy(active = this.route != null, lastPrompt = lastPrompt)
    }

    fun stop() {
        route = null
        _state.value = State()
    }
}
