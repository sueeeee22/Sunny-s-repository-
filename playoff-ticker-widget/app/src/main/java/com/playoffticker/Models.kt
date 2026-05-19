package com.playoffticker

data class SeriesRow(
    val league: String,
    val matchup: String,
    val seriesScore: String,
    val lastGame: String,
    val liveStatus: String?
)
