import axios from 'axios';

// Load from environment variables
const FINNHUB = process.env.FINNHUB_API_KEY;
const TE_USER = process.env.TE_USERNAME;
const TE_PASS = process.env.TE_API_KEY;

/**
 * Returns a combined sentiment score for a given symbol, based on multiple real-time sources.
 * Score is a float between -1.00 (very bearish) and +1.00 (very bullish).
 */
export async function get_combined_score(symbol: string): Promise<number> {
  let newsSentiment = 0, earningsSentiment = 0, ipoSentiment = 0;
  let macroRiskScore = 0, optionsSentiment = 0, cotSentiment = 0, geoRisk = 0;

  try {
    /** 1. News Sentiment - from Finnhub */
    const news = await axios.get(`https://finnhub.io/api/v1/news-sentiment?symbol=${symbol}&token=${FINNHUB}`);
    newsSentiment = news.data?.sentiment?.score || 0;

    /** 2. Earnings Sentiment - based on earnings surprise */
    const earnings = await axios.get(`https://finnhub.io/api/v1/stock/earnings?symbol=${symbol}&token=${FINNHUB}`);
    if (earnings.data?.length > 0) {
      const last = earnings.data[0];
      const surprise = last.actual - last.estimate;
      earningsSentiment = surprise > 0 ? 0.7 : surprise < 0 ? -0.7 : 0;
    }

    /** 3. IPO Sentiment - bullish if lots of IPOs this month */
    const ipo = await axios.get(`https://finnhub.io/api/v1/calendar/ipo?from=2025-07-01&to=2025-07-31&token=${FINNHUB}`);
    ipoSentiment = ipo.data?.ipoCalendar?.length > 5 ? 0.5 : -0.5;

    /** 4. Macro Risk - based on upcoming high-impact events */
    const macro = await axios.get(`https://api.tradingeconomics.com/calendar/country/all?c=${TE_USER}:${TE_PASS}`);
    const events = macro.data?.filter((e: any) =>
      e.Importance >= 2 &&
      new Date(e.Date) >= new Date()
    );
    macroRiskScore = events.length > 10 ? -1 : 1;

    /** 5. Options Sentiment - call/put skew from Yahoo Finance */
    const opt = await axios.get(`https://query2.finance.yahoo.com/v7/finance/options/${symbol}`);
    const calls = opt.data?.optionChain?.result[0]?.options[0]?.calls?.length || 0;
    const puts = opt.data?.optionChain?.result[0]?.options[0]?.puts?.length || 0;
    optionsSentiment = calls > puts ? 0.6 : calls < puts ? -0.6 : 0;

    /** 6. COT Sentiment - from TradingEconomics (or fallback 0) */
    const cot = await axios.get(`https://api.tradingeconomics.com/cot?symbol=${symbol}&c=${TE_USER}:${TE_PASS}`);
    cotSentiment = cot.data?.netPosition > 0 ? 0.4 : -0.4;

    /** 7. Geopolitical Risk - headline keyword scan */
    const geo = await axios.get(`https://finnhub.io/api/v1/news?category=general&token=${FINNHUB}`);
    const warHeadlines = geo.data?.filter((n: any) =>
      /war|conflict|missile|nuclear|strike|tensions/i.test(n.headline)
    );
    geoRisk = warHeadlines.length > 3 ? -0.5 : 0.2;

  } catch (err: any) {
    console.error(`Sentiment error for ${symbol}:`, err.message);
  }

  /** Combine all factors into weighted score */
  const score =
    0.25 * newsSentiment +
    0.20 * earningsSentiment +
    0.10 * ipoSentiment +
    0.20 * macroRiskScore +
    0.10 * optionsSentiment +
    0.10 * cotSentiment +
    0.05 * geoRisk;

  console.log(`[SCORE] ${symbol}`, {
    newsSentiment,
    earningsSentiment,
    ipoSentiment,
    macroRiskScore,
    optionsSentiment,
    cotSentiment,
    geoRisk,
    score: score.toFixed(2),
  });

  return parseFloat(score.toFixed(2));
}
