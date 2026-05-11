from sea_trend_insight.providers.base import TrendProvider
from sea_trend_insight.providers.sample import SampleProvider
from sea_trend_insight.providers.google_trends import GoogleTrendsProvider
from sea_trend_insight.providers.google_news import GoogleNewsProvider
from sea_trend_insight.providers.gdelt import GdeltProvider
from sea_trend_insight.providers.trends24 import Trends24Provider
from sea_trend_insight.providers.getdaytrends import GetDayTrendsProvider
from sea_trend_insight.providers.kworb_youtube import KworbYouTubeProvider
from sea_trend_insight.providers.appbrain import AppBrainProvider
from sea_trend_insight.providers.appfigures import AppfiguresProvider
from sea_trend_insight.providers.google_play import GooglePlayProvider
from sea_trend_insight.providers.rappler import RapplerProvider
from sea_trend_insight.providers.detik import DetikProvider
from sea_trend_insight.providers.line_today import LineTodayProvider

__all__ = [
    "TrendProvider",
    "SampleProvider",
    "GoogleTrendsProvider",
    "GoogleNewsProvider",
    "GdeltProvider",
    "Trends24Provider",
    "GetDayTrendsProvider",
    "KworbYouTubeProvider",
    "AppBrainProvider",
    "AppfiguresProvider",
    "GooglePlayProvider",
    "RapplerProvider",
    "DetikProvider",
    "LineTodayProvider",
]

LIVE_PROVIDERS = {
    "google_trends": GoogleTrendsProvider,
    "google_news": GoogleNewsProvider,
    "gdelt": GdeltProvider,
    "trends24": Trends24Provider,
    "getdaytrends": GetDayTrendsProvider,
    "kworb_youtube": KworbYouTubeProvider,
    "appbrain": AppBrainProvider,
    "appfigures": AppfiguresProvider,
    "google_play": GooglePlayProvider,
    "rappler": RapplerProvider,
    "detik": DetikProvider,
    "line_today": LineTodayProvider,
}

