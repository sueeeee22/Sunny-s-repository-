package com.playoffticker

import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

object EspnApi {

    private const val NBA_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    private const val NHL_URL = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard"

    fun fetchPlayoffSeries(): List<SeriesRow> {
        val nba = runCatching { fetchAndParse("NBA", NBA_URL) }.getOrDefault(emptyList())
        val nhl = runCatching { fetchAndParse("NHL", NHL_URL) }.getOrDefault(emptyList())
        return (nba + nhl).sortedWith(
            compareByDescending<SeriesRow> { it.liveStatus != null }
                .thenBy { it.league }
                .thenBy { it.matchup }
        )
    }

    private fun fetchAndParse(league: String, baseUrl: String): List<SeriesRow> {
        val now = System.currentTimeMillis()
        val day = 24L * 60 * 60 * 1000
        val fmt = SimpleDateFormat("yyyyMMdd", Locale.US).apply { timeZone = TimeZone.getTimeZone("UTC") }
        val from = fmt.format(Date(now - 21 * day))
        val to = fmt.format(Date(now + 10 * day))
        val url = "$baseUrl?dates=$from-$to&limit=300"

        val root = httpGetJson(url)
        val events = root.optJSONArray("events") ?: JSONArray()

        val grouped = mutableMapOf<String, MutableList<JSONObject>>()
        for (i in 0 until events.length()) {
            val ev = events.getJSONObject(i)
            val seasonType = ev.optJSONObject("season")?.optInt("type") ?: 0
            if (seasonType != 3) continue // 3 == postseason
            val comp = ev.optJSONArray("competitions")?.optJSONObject(0) ?: continue
            val competitors = comp.optJSONArray("competitors") ?: continue
            if (competitors.length() < 2) continue
            val ids = listOf(
                competitors.getJSONObject(0).optString("id"),
                competitors.getJSONObject(1).optString("id")
            ).sorted()
            val key = ids.joinToString("-")
            grouped.getOrPut(key) { mutableListOf() }.add(ev)
        }

        return grouped.values.mapNotNull { runCatching { buildRow(league, it) }.getOrNull() }
    }

    private fun buildRow(league: String, events: List<JSONObject>): SeriesRow? {
        val parser = SimpleDateFormat("yyyy-MM-dd'T'HH:mm'Z'", Locale.US).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }
        val sorted = events.sortedByDescending {
            runCatching { parser.parse(it.optString("date"))?.time ?: 0L }.getOrDefault(0L)
        }
        val newest = sorted.first()
        val newestComp = newest.getJSONArray("competitions").getJSONObject(0)
        val competitors = newestComp.getJSONArray("competitors")

        val homeC = (0 until competitors.length()).map { competitors.getJSONObject(it) }
            .firstOrNull { it.optString("homeAway") == "home" } ?: competitors.getJSONObject(0)
        val awayC = (0 until competitors.length()).map { competitors.getJSONObject(it) }
            .firstOrNull { it.optString("homeAway") == "away" } ?: competitors.getJSONObject(1)
        val homeAbbr = teamLabel(homeC)
        val awayAbbr = teamLabel(awayC)
        val matchup = "$awayAbbr @ $homeAbbr"

        // series score from ESPN if present; otherwise tally completed games
        val seriesObj = newestComp.opt("series").let { v ->
            when (v) {
                is JSONArray -> v.optJSONObject(0)
                is JSONObject -> v
                else -> null
            }
        }
        var espnSummary = ""
        var homeWins = -1
        var awayWins = -1
        if (seriesObj != null) {
            espnSummary = seriesObj.optString("summary").trim()
            val sc = seriesObj.optJSONArray("competitors")
            if (sc != null) {
                for (i in 0 until sc.length()) {
                    val s = sc.getJSONObject(i)
                    val id = s.optString("id").ifEmpty { s.optJSONObject("team")?.optString("id") ?: "" }
                    val wins = s.optInt("wins", -1)
                    when (id) {
                        homeC.optString("id") -> homeWins = wins
                        awayC.optString("id") -> awayWins = wins
                    }
                }
            }
        }
        if (homeWins < 0 || awayWins < 0) {
            var hw = 0; var aw = 0
            for (ev in sorted) {
                val c = ev.getJSONArray("competitions").getJSONObject(0)
                val st = c.optJSONObject("status")?.optJSONObject("type")?.optString("state") ?: ""
                if (st != "post") continue
                val comps = c.getJSONArray("competitors")
                var winnerId: String? = null
                for (i in 0 until comps.length()) {
                    val co = comps.getJSONObject(i)
                    if (co.optBoolean("winner", false)) winnerId = co.optString("id")
                }
                when (winnerId) {
                    homeC.optString("id") -> hw++
                    awayC.optString("id") -> aw++
                }
            }
            if (homeWins < 0) homeWins = hw
            if (awayWins < 0) awayWins = aw
        }

        // Best-of-7 in both NBA and NHL playoffs: 4 wins clinches the series.
        // Drop completed series so the ticker only shows what's still being played.
        if (homeWins >= 4 || awayWins >= 4) return null

        val seriesScore = when {
            espnSummary.isNotBlank() -> espnSummary
            homeWins == awayWins -> "Tied $homeWins-$awayWins"
            homeWins > awayWins -> "$homeAbbr leads $homeWins-$awayWins"
            else -> "$awayAbbr leads $awayWins-$homeWins"
        }

        // last completed game
        val last = sorted.firstOrNull {
            it.getJSONArray("competitions").getJSONObject(0)
                .optJSONObject("status")?.optJSONObject("type")?.optString("state") == "post"
        }
        val lastGame = last?.let { formatPostGame(it) } ?: "No completed games yet"

        // live game (in progress)
        val live = sorted.firstOrNull {
            it.getJSONArray("competitions").getJSONObject(0)
                .optJSONObject("status")?.optJSONObject("type")?.optString("state") == "in"
        }
        val liveStr = live?.let { formatLiveGame(it) }

        return SeriesRow(
            league = league,
            matchup = matchup,
            seriesScore = seriesScore,
            lastGame = lastGame,
            liveStatus = liveStr
        )
    }

    private fun teamLabel(competitor: JSONObject): String {
        val team = competitor.optJSONObject("team") ?: return "?"
        return team.optString("abbreviation").ifBlank {
            team.optString("shortDisplayName").ifBlank { team.optString("displayName") }
        }
    }

    private fun formatPostGame(ev: JSONObject): String {
        val c = ev.getJSONArray("competitions").getJSONObject(0)
        val comps = c.getJSONArray("competitors")
        var home: JSONObject? = null
        var away: JSONObject? = null
        for (i in 0 until comps.length()) {
            val co = comps.getJSONObject(i)
            if (co.optString("homeAway") == "home") home = co else away = co
        }
        if (home == null || away == null) return ""
        val date = formatDate(ev.optString("date"))
        return "Last: ${teamLabel(away!!)} ${away!!.optString("score")} - ${home!!.optString("score")} ${teamLabel(home!!)}  ·  $date"
    }

    private fun formatLiveGame(ev: JSONObject): String {
        val c = ev.getJSONArray("competitions").getJSONObject(0)
        val comps = c.getJSONArray("competitors")
        var home: JSONObject? = null
        var away: JSONObject? = null
        for (i in 0 until comps.length()) {
            val co = comps.getJSONObject(i)
            if (co.optString("homeAway") == "home") home = co else away = co
        }
        if (home == null || away == null) return "LIVE"
        val status = c.optJSONObject("status")?.optJSONObject("type")?.optString("shortDetail") ?: "LIVE"
        return "● LIVE  ${teamLabel(away!!)} ${away!!.optString("score")} - ${home!!.optString("score")} ${teamLabel(home!!)}  ·  $status"
    }

    private fun formatDate(iso: String): String {
        if (iso.isBlank()) return ""
        return try {
            val parser = SimpleDateFormat("yyyy-MM-dd'T'HH:mm'Z'", Locale.US).apply {
                timeZone = TimeZone.getTimeZone("UTC")
            }
            val out = SimpleDateFormat("MMM d", Locale.getDefault())
            out.format(parser.parse(iso) ?: return iso.take(10))
        } catch (e: Exception) {
            iso.take(10)
        }
    }

    private fun httpGetJson(url: String): JSONObject {
        val conn = (URL(url).openConnection() as HttpURLConnection).apply {
            connectTimeout = 8000
            readTimeout = 8000
            requestMethod = "GET"
            setRequestProperty("Accept", "application/json")
            setRequestProperty("User-Agent", "PlayoffTickerWidget/1.0")
        }
        return conn.inputStream.use {
            JSONObject(it.bufferedReader().readText())
        }
    }
}
