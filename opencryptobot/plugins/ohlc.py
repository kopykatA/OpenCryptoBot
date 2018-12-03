import io
import threading
import pandas as pd
import plotly.io as pio
import plotly.graph_objs as go
import opencryptobot.emoji as emo
import plotly.figure_factory as fif
import opencryptobot.constants as con

from io import BytesIO
from telegram import ParseMode
from coinmarketcap import Market
from telegram.ext import CommandHandler
from opencryptobot.plugin import OpenCryptoPlugin
from opencryptobot.api.cryptocompare import CryptoCompare


# TODO: Default from_cur should be fiat
class Ohlc(OpenCryptoPlugin):

    cmc_coin_id = None

    def get_handler(self):
        return CommandHandler("ohlc", self._ohlc, pass_args=True)

    @OpenCryptoPlugin.add_user
    @OpenCryptoPlugin.send_typing
    def _ohlc(self, bot, update, args):
        time_frame = 120  # Hours
        from_sy = "BTC"

        if not args:
            update.message.reply_text(
                text=f"Usage:\n{self.get_usage()}",
                parse_mode=ParseMode.MARKDOWN)
            return

        # TODO: Doesn't work. Why?
        if "-" in args[0]:
            pair = args[0].split("-", 1)
            from_sy = pair[0].upper()
            to_sy = pair[1].upper()
        else:
            to_sy = args[0].upper()

        if len(args) > 1 and args[1].isnumeric():
            time_frame = int(args[1])

        cmc_thread = threading.Thread(target=self._get_cmc_coin_id, args=[to_sy])
        cmc_thread.start()

        ohlcv = CryptoCompare().historical_ohlcv_hourly(to_sy, from_sy, time_frame)["Data"]

        if not ohlcv:
            update.message.reply_text(
                text=f"No OHLC data available for {to_sy} {emo.OH_NO}",
                parse_mode=ParseMode.MARKDOWN)
            return

        o = [value["open"] for value in ohlcv]
        h = [value["high"] for value in ohlcv]
        l = [value["low"] for value in ohlcv]
        c = [value["close"] for value in ohlcv]
        t = [value["time"] for value in ohlcv]

        fig = fif.create_candlestick(o, h, l, c, pd.to_datetime(t, unit='s'))
        fig['layout']['yaxis'].update(tickformat="0.8f", ticksuffix="  ")
        fig['layout'].update(title=f"{from_sy} - {to_sy}")

        fig['layout'].update(
            shapes=[{
                "type": "line",
                "xref": "paper",
                "yref": "y",
                "x0": 0,
                "x1": 1,
                "y0": c[len(c) - 1],
                "y1": c[len(c) - 1],
                "line": {
                    "color": "rgb(50, 171, 96)",
                    "width": 1,
                    "dash": "dot"
                }
            }])

        fig['layout'].update(
            autosize=False,
            width=800,
            height=600,
            margin=go.layout.Margin(
                l=125,
                r=50,
                b=70,
                t=100,
                pad=4
            ))

        cmc_thread.join()

        fig['layout'].update(
            images=[dict(
                source=f"{con.LOGO_URL_PARTIAL}{self.cmc_coin_id}.png",
                opacity=0.8,
                xref="paper", yref="paper",
                x=1.05, y=1,
                sizex=0.2, sizey=0.2,
                xanchor="right", yanchor="bottom"
            )])

        update.message.reply_photo(
            photo=io.BufferedReader(BytesIO(pio.to_image(fig, format='webp'))),
            parse_mode=ParseMode.MARKDOWN)

    def _get_cmc_coin_id(self, ticker):
        for listing in Market().listings()["data"]:
            if ticker.upper() == listing["symbol"].upper():
                self.cmc_coin_id = listing["id"]
                break