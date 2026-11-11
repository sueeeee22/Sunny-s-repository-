package com.playoffticker

object PlayoffRepository {
    @Volatile private var cached: List<SeriesRow> = emptyList()

    @Volatile
    var lastUpdatedMillis: Long = 0L
        private set

    fun current(): List<SeriesRow> = cached

    @Synchronized
    fun refreshBlocking(): List<SeriesRow> {
        val rows = try {
            EspnApi.fetchPlayoffSeries()
        } catch (e: Exception) {
            return cached
        }
        cached = rows
        lastUpdatedMillis = System.currentTimeMillis()
        return rows
    }
}
