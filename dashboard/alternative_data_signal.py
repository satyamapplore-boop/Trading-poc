import aiohttp
import asyncio
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from config import cfg

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────

WHALE_THRESHOLD_USD   = 500_000   # $500K minimum per user spec
NEWS_ARTICLE_LIMIT    = 10
ECONOMIC_EVENT_WINDOW_HOURS = 24

# Credible sources accepted for news (matched against CryptoPanic domain field)
CREDIBLE_SOURCE_DOMAINS = {
    "coindesk.com", "coindesk",
    "cointelegraph.com", "cointelegraph",
    "reuters.com", "reuters",
    "bloomberg.com", "bloomberg",
    "theblock.co", "theblock", "the-block",
}

CREDIBLE_SOURCE_LABELS = {
    "coindesk.com": "CoinDesk", "coindesk": "CoinDesk",
    "cointelegraph.com": "CoinTelegraph", "cointelegraph": "CoinTelegraph",
    "reuters.com": "Reuters", "reuters": "Reuters",
    "bloomberg.com": "Bloomberg", "bloomberg": "Bloomberg",
    "theblock.co": "The Block", "theblock": "The Block", "the-block": "The Block",
}

# Fallback keyword lists (used when Claude is unavailable)
BULLISH_KEYWORDS = ["buy", "bullish", "long", "surge", "adoption", "etf", "halving",
                    "institutional", "support", "rally", "breakout", "accumulation",
                    "inflow", "growth", "record", "upgrade", "partnership"]
BEARISH_KEYWORDS = ["sell", "bearish", "short", "dump", "crash", "sec", "lawsuit",
                    "hack", "liquidated", "rejection", "breakdown", "ban", "fraud",
                    "outflow", "regulatory", "inflation", "fear", "scam"]

# Signal weights — must sum to 1.0
WEIGHTS = {
    "price":    0.50,   # Binance technical / price signal
    "news":     0.20,   # Claude-classified credible-source headlines
    "whale":    0.15,   # Whale Alert BTC movements
    "economic": 0.15,   # Macro calendar
}


class AlternativeDataAggregator:
    def __init__(self):
        self.whale_key       = cfg.whale_alert_key
        self.cryptopanic_key = cfg.cryptopanic_key
        self.anthropic_key   = cfg.anthropic_key
        self._last_result    = None

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────────────

    async def get_signal(self) -> dict:
        """Fetch all data sources concurrently and return a unified signal dict."""
        try:
            news_task, whale_task, eco_task = await asyncio.gather(
                self._fetch_news_sentiment(),
                self._fetch_whale_activity(),
                self._fetch_economic_events(),
                return_exceptions=True,
            )

            news     = news_task  if not isinstance(news_task,  Exception) else {"score": 0.5, "headlines": [], "classified": [], "feed": []}
            whale    = whale_task if not isinstance(whale_task, Exception) else {"score": 0.5, "transfers": [], "feed": []}
            economic = eco_task   if not isinstance(eco_task,   Exception) else {"score": 0.5, "macro_events": []}

            # Weighted alt score (excluding price — combined later)
            alt_score = (
                news["score"]     * (WEIGHTS["news"]     / (1 - WEIGHTS["price"])) +
                whale["score"]    * (WEIGHTS["whale"]    / (1 - WEIGHTS["price"])) +
                economic["score"] * (WEIGHTS["economic"] / (1 - WEIGHTS["price"]))
            )

            final_signal, final_confidence = self._score_to_signal(alt_score)
            reasoning = self._build_reasoning(news, whale, economic, final_signal, final_confidence)

            result = {
                "alt_signal":     final_signal,
                "alt_confidence": round(final_confidence, 3),
                "news_score":     news["score"],
                "whale_score":    whale["score"],
                "economic_score": economic["score"],
                "reasoning":      reasoning,
                # Live feed data for dashboard display
                "whale_feed":     whale.get("feed", [])[:5],
                "news_feed":      news.get("feed", [])[:5],
                "raw": {"news": news, "whale": whale, "economic": economic},
            }
            self._last_result = result
            return result

        except Exception as e:
            return {
                "alt_signal": "HOLD", "alt_confidence": 0.5,
                "news_score": 0.5, "whale_score": 0.5, "economic_score": 0.5,
                "reasoning": f"Aggregator error: {e}",
                "whale_feed": [], "news_feed": [], "raw": {},
            }

    def combine_with_price_signal(self, price_signal: str, price_confidence: float) -> dict:
        """Merge technical price signal with latest alternative data."""
        if self._last_result is None:
            return {
                "signal": price_signal,
                "confidence": price_confidence,
                "reasoning": "Alternative data not yet loaded — using price signal only.",
                "whale_feed": [],
                "news_feed": [],
            }

        price_score = self._signal_to_score(price_signal, price_confidence)
        alt = self._last_result

        final_score = (
            price_score           * WEIGHTS["price"] +
            alt["news_score"]     * WEIGHTS["news"] +
            alt["whale_score"]    * WEIGHTS["whale"] +
            alt["economic_score"] * WEIGHTS["economic"]
        )
        final_signal, final_confidence = self._score_to_signal(final_score)

        return {
            "signal":     final_signal,
            "confidence": round(final_confidence, 3),
            "reasoning":  alt["reasoning"],
            "whale_feed": alt.get("whale_feed", []),
            "news_feed":  alt.get("news_feed", []),
            "breakdown": {
                "price":      {"signal": price_signal, "confidence": price_confidence},
                "alt_signal": alt["alt_signal"],
                "weights":    WEIGHTS,
            },
        }

    # ─────────────────────────────────────────────────────────────────────────
    # WHALE ALERT  — BTC movements ≥ $500K, exchange direction classification
    # ─────────────────────────────────────────────────────────────────────────

    async def _fetch_whale_activity(self) -> dict:
        transfers = []
        source_name = "Blockchain.com"

        # ── Primary: Whale Alert free API ────────────────────────────────────
        if self.whale_key:
            try:
                url = (
                    f"https://api.whale-alert.io/v1/transactions"
                    f"?api_key={self.whale_key}"
                    f"&min_value={WHALE_THRESHOLD_USD}"
                    f"&currency=btc"
                    f"&limit=10"
                )
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            for tx in data.get("transactions", []):
                                if tx.get("symbol", "").upper() != "BTC":
                                    continue
                                from_type = tx.get("from", {}).get("owner_type", "")
                                to_type   = tx.get("to",   {}).get("owner_type", "")
                                from_name = tx.get("from", {}).get("owner", "Unknown Wallet")
                                to_name   = tx.get("to",   {}).get("owner", "Unknown Wallet")

                                # exchange → private wallet  =  accumulation  →  BULLISH
                                # private wallet → exchange  =  selling pressure → BEARISH
                                if from_type == "exchange" and to_type != "exchange":
                                    direction = "bullish"
                                    label     = f"{from_name} → Private Wallet"
                                elif to_type == "exchange" and from_type != "exchange":
                                    direction = "bearish"
                                    label     = f"Private Wallet → {to_name}"
                                else:
                                    direction = "neutral"
                                    label     = f"{from_name} → {to_name}"

                                amount_usd = round(tx.get("amount_usd", 0), 0)
                                if amount_usd < WHALE_THRESHOLD_USD:
                                    continue

                                transfers.append({
                                    "currency":   "BTC",
                                    "amount":     round(tx.get("amount", 0), 4),
                                    "amount_usd": amount_usd,
                                    "direction":  direction,
                                    "label":      label,
                                    "hash":       (tx.get("hash", "") or "")[:12] + "...",
                                    "source":     "Whale Alert",
                                    "time":       datetime.fromtimestamp(
                                        tx.get("timestamp", 0), tz=timezone.utc
                                    ).strftime("%H:%M UTC") if tx.get("timestamp") else "—",
                                })
                            if transfers:
                                source_name = "Whale Alert"
            except Exception:
                pass

        # ── Fallback: Blockchain.com large mempool txs ────────────────────────
        if not transfers:
            try:
                url = "https://blockchain.info/unconfirmed-transactions?format=json"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                        data = await resp.json()
                for tx in data.get("txs", []):
                    total_sat  = sum(o.get("value", 0) for o in tx.get("out", []))
                    btc_value  = total_sat / 100_000_000
                    usd_approx = btc_value * 85_000  # approximate
                    if usd_approx >= WHALE_THRESHOLD_USD:
                        transfers.append({
                            "currency":   "BTC",
                            "amount":     round(btc_value, 4),
                            "amount_usd": round(usd_approx, 0),
                            "direction":  "neutral",
                            "label":      "Unknown → Unknown (mempool)",
                            "hash":       (tx.get("hash", "") or "")[:12] + "...",
                            "source":     "Blockchain.com",
                            "time":       datetime.now(timezone.utc).strftime("%H:%M UTC"),
                        })
            except Exception:
                pass

        if not transfers:
            transfers = [{
                "currency": "BTC", "amount": 0, "amount_usd": 0,
                "direction": "neutral", "label": "No large movements detected",
                "hash": "—", "source": "—", "time": "—",
            }]

        # Score: bullish vol vs bearish vol
        bull = sum(t["amount"] for t in transfers if t["direction"] == "bullish")
        bear = sum(t["amount"] for t in transfers if t["direction"] == "bearish")
        total = bull + bear or 1
        score = 0.5 + (bull / total - bear / total) * 0.35
        score = max(0.0, min(1.0, score))

        # Build display feed (last 5 BTC-only, sorted by USD value)
        btc_txs = [t for t in transfers if t["currency"] == "BTC"]
        btc_txs.sort(key=lambda x: x["amount_usd"], reverse=True)
        feed = btc_txs[:5]

        return {
            "score": round(score, 3),
            "transfers": transfers[:10],
            "feed": feed,
            "source": source_name,
            "net_signal": "bullish" if score > 0.55 else "bearish" if score < 0.45 else "neutral",
        }

    # ─────────────────────────────────────────────────────────────────────────
    # CRYPTOPANIC NEWS  —  BTC-only, credible sources, Claude classification
    # ─────────────────────────────────────────────────────────────────────────

    async def _fetch_news_sentiment(self) -> dict:
        headlines = []

        # ── Primary: CryptoPanic free API, BTC filter ─────────────────────────
        if self.cryptopanic_key:
            try:
                url = (
                    f"https://cryptopanic.com/api/free/v1/posts/"
                    f"?auth_token={self.cryptopanic_key}"
                    f"&currencies=BTC"
                    f"&public=true"
                    f"&filter=hot"
                )
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            for item in data.get("results", []):
                                # Filter to credible sources only
                                source = item.get("source", {})
                                domain = (source.get("domain") or source.get("slug") or "").lower()
                                title  = (source.get("title") or "").lower()
                                # match against known credible domains
                                matched = next(
                                    (d for d in CREDIBLE_SOURCE_DOMAINS
                                     if d in domain or d in title.replace(" ", "")),
                                    None
                                )
                                if not matched:
                                    continue
                                source_label = CREDIBLE_SOURCE_LABELS.get(matched, source.get("title", "Unknown"))
                                headlines.append({
                                    "title":  item.get("title", "").strip(),
                                    "url":    item.get("url", ""),
                                    "date":   item.get("published_at", ""),
                                    "source": source_label,
                                    "domain": domain,
                                })
            except Exception:
                pass

        # ── Fallback: RSS from CoinDesk + CoinTelegraph ───────────────────────
        if not headlines:
            rss_feeds = {
                "CoinTelegraph": "https://cointelegraph.com/rss",
                "CoinDesk":      "https://www.coindesk.com/arc/outboundfeeds/rss/",
            }
            async with aiohttp.ClientSession() as session:
                for src_name, url in rss_feeds.items():
                    try:
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                            content = await resp.text()
                        root  = ET.fromstring(content)
                        items = root.findall(".//item")[:5]
                        for item in items:
                            t_el = item.find("title")
                            l_el = item.find("link")
                            title = t_el.text.strip() if t_el is not None and t_el.text else ""
                            link  = l_el.text.strip() if l_el is not None and l_el.text else ""
                            if title:
                                headlines.append({
                                    "title": title, "url": link,
                                    "date": "", "source": src_name,
                                })
                    except Exception:
                        continue

        if not headlines:
            headlines = [{"title": "BTC consolidates near key support as market awaits next catalyst",
                          "url": "", "date": "", "source": "System"}]

        # Classify with Claude (or fallback to keywords)
        top = headlines[:NEWS_ARTICLE_LIMIT]
        classified = await self._classify_headlines_claude(top)

        # Build score
        scores = []
        for c in classified:
            if c["sentiment"] == "bullish":
                scores.append(0.5 + c["confidence"] * 0.5)
            elif c["sentiment"] == "bearish":
                scores.append(0.5 - c["confidence"] * 0.5)
            else:
                scores.append(0.5)
        avg_score = sum(scores) / len(scores) if scores else 0.5

        # Build feed (last 5, with classification merged in)
        feed = []
        for i, h in enumerate(top[:5]):
            cls = next((c for c in classified if c["index"] == i + 1), {"sentiment": "neutral", "confidence": 0.5})
            feed.append({
                "title":      h["title"],
                "source":     h["source"],
                "sentiment":  cls["sentiment"],
                "confidence": round(cls["confidence"], 2),
            })

        return {
            "score":      round(avg_score, 3),
            "headlines":  top,
            "classified": classified,
            "feed":       feed,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # CLAUDE  — headline sentiment classification
    # ─────────────────────────────────────────────────────────────────────────

    async def _classify_headlines_claude(self, headlines: list) -> list:
        """Send headlines to Claude in one call; fall back to keyword matching."""
        if not self.anthropic_key or not headlines:
            return self._classify_headlines_local(headlines)

        try:
            import anthropic as _anthropic

            numbered = "\n".join(
                f"{i+1}. {h['title']} ({h.get('source','')})"
                for i, h in enumerate(headlines)
            )
            prompt = (
                "You are a professional Bitcoin market analyst.\n"
                "For each headline below, decide whether it is BULLISH or BEARISH "
                "for Bitcoin price over the next 24 hours, and provide a confidence "
                "score between 0.0 (very uncertain) and 1.0 (very certain).\n\n"
                f"Headlines:\n{numbered}\n\n"
                "Respond with a valid JSON array only — no explanation, no markdown:\n"
                '[{"index":1,"sentiment":"bullish","confidence":0.8}, ...]'
            )

            client  = _anthropic.AsyncAnthropic(api_key=self.anthropic_key)
            message = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )

            raw = message.content[0].text.strip()
            # Extract JSON array robustly
            m = re.search(r"\[.*\]", raw, re.DOTALL)
            if m:
                parsed = json.loads(m.group())
                return [
                    {
                        "index":      int(item.get("index", 0)),
                        "sentiment":  str(item.get("sentiment", "neutral")).lower(),
                        "confidence": float(item.get("confidence", 0.5)),
                        "classifier": "Claude",
                    }
                    for item in parsed
                ]
        except Exception:
            pass

        return self._classify_headlines_local(headlines)

    def _classify_headlines_local(self, headlines: list) -> list:
        """Keyword-based fallback classifier."""
        result = []
        for i, h in enumerate(headlines):
            title = h.get("title", "").lower()
            bull  = sum(1 for kw in BULLISH_KEYWORDS if kw in title)
            bear  = sum(1 for kw in BEARISH_KEYWORDS if kw in title)
            total = bull + bear
            if total == 0:
                result.append({"index": i+1, "sentiment": "neutral",  "confidence": 0.5, "classifier": "keyword"})
            elif bull > bear:
                result.append({"index": i+1, "sentiment": "bullish",  "confidence": round(bull/total, 2), "classifier": "keyword"})
            else:
                result.append({"index": i+1, "sentiment": "bearish",  "confidence": round(bear/total, 2), "classifier": "keyword"})
        return result

    # ─────────────────────────────────────────────────────────────────────────
    # ECONOMIC CALENDAR  (Forex Factory macro events)
    # ─────────────────────────────────────────────────────────────────────────

    async def _fetch_economic_events(self) -> dict:
        upcoming = []
        now_utc  = datetime.now(timezone.utc)
        try:
            url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    events_raw = await resp.json(content_type=None)
            for ev in events_raw:
                if ev.get("impact", "").lower() != "high":
                    continue
                try:
                    dt_str   = f"{ev.get('date')} {ev.get('time')}"
                    event_dt = datetime.strptime(dt_str, "%Y-%m-%d %I:%M%p").replace(tzinfo=timezone.utc)
                except Exception:
                    continue
                hours_away = (event_dt - now_utc).total_seconds() / 3600
                if 0 <= hours_away <= ECONOMIC_EVENT_WINDOW_HOURS:
                    upcoming.append({
                        "title":      ev.get("title", ""),
                        "time":       ev.get("time", ""),
                        "hours_away": round(hours_away, 1),
                    })
        except Exception:
            pass
        score = 0.45 if upcoming else 0.5   # upcoming high-impact = slight caution
        return {"score": score, "macro_events": upcoming}

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _score_to_signal(self, score: float) -> tuple:
        if   score >= 0.65: return "BUY",  score
        elif score <= 0.35: return "SELL", 1 - score
        else:               return "HOLD", 1 - abs(score - 0.5) * 2

    def _signal_to_score(self, signal: str, confidence: float) -> float:
        if signal == "BUY":  return 0.5 + confidence * 0.5
        if signal == "SELL": return 0.5 - confidence * 0.5
        return 0.5

    def _build_reasoning(self, news: dict, whale: dict, economic: dict,
                         signal: str, confidence: float) -> str:
        """
        Produce a human-readable one-liner, e.g.:
        "2 large BTC withdrawals from exchanges plus 3 bullish CoinDesk headlines — BUY 81% confidence."
        """
        parts = []

        # Whale part
        feed = whale.get("feed", [])
        bull_moves = [t for t in feed if t["direction"] == "bullish"]
        bear_moves = [t for t in feed if t["direction"] == "bearish"]
        if bull_moves:
            parts.append(f"{len(bull_moves)} large BTC withdrawal{'s' if len(bull_moves)>1 else ''} from exchange{'s' if len(bull_moves)>1 else ''}")
        elif bear_moves:
            parts.append(f"{len(bear_moves)} large BTC deposit{'s' if len(bear_moves)>1 else ''} to exchange{'s' if len(bear_moves)>1 else ''}")
        else:
            parts.append("stable whale flows")

        # News part
        news_feed  = news.get("feed", [])
        bull_news  = [n for n in news_feed if n["sentiment"] == "bullish"]
        bear_news  = [n for n in news_feed if n["sentiment"] == "bearish"]
        if bull_news:
            sources = list(dict.fromkeys(n["source"] for n in bull_news))[:2]
            parts.append(f"{len(bull_news)} bullish {'/'.join(sources)} headline{'s' if len(bull_news)>1 else ''}")
        elif bear_news:
            sources = list(dict.fromkeys(n["source"] for n in bear_news))[:2]
            parts.append(f"{len(bear_news)} bearish {'/'.join(sources)} headline{'s' if len(bear_news)>1 else ''}")
        else:
            parts.append("mixed news sentiment")

        # Macro part
        macro = economic.get("macro_events", [])
        if macro:
            parts.append(f"{len(macro)} high-impact macro event{'s' if len(macro)>1 else ''} within 24h")

        connector = " plus " if len(parts) >= 2 else ""
        body      = " plus ".join(parts)
        return f"{body} — {signal} {round(confidence*100):.0f}% confidence."


# ─────────────────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────────────────
async def _test():
    print("=== Alternative Data Signal Engine ===\n")
    agg    = AlternativeDataAggregator()
    result = await agg.get_signal()
    print(f"Alt Signal : {result['alt_signal']} ({result['alt_confidence']*100:.1f}%)")
    print(f"Reasoning  : {result['reasoning']}")
    print(f"\nWhale Feed ({len(result['whale_feed'])} entries):")
    for w in result['whale_feed']:
        arrow = "▲" if w["direction"] == "bullish" else ("▼" if w["direction"] == "bearish" else "→")
        print(f"  {arrow} {w['label']}  |  {w['amount']} BTC  |  ${w['amount_usd']:,.0f}")
    print(f"\nNews Feed ({len(result['news_feed'])} entries):")
    for n in result['news_feed']:
        icon = "🟢" if n["sentiment"] == "bullish" else ("🔴" if n["sentiment"] == "bearish" else "⚪")
        print(f"  {icon} [{n['source']}] {n['title'][:80]}  ({n['confidence']*100:.0f}%)")

if __name__ == "__main__":
    asyncio.run(_test())
