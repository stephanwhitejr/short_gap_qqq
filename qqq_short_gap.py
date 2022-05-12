import datetime, config, pandas, sys, talib
from alpaca_trade_api.stream import Stream
from alpaca_trade_api.rest import REST, TimeFrame, TimeFrameUnit

pandas.set_option('display.max_rows', None)

api = REST(key_id=config.API_KEY, secret_key=config.SECRET_KEY, base_url=config.BASE_URL)
account = api.get_account()

# if market is closed, exit
if not api.get_clock().is_open:
    sys.exit("market is not open")

universe = api.get_bars(QQQ_SYMBOLS, TimeFrame.Day, initial_start_date.isoformat(), end_date.isoformat()).df # get market data
# clean up df
universe = universe.drop(columns=['high','low','volume','trade_count','vwap']) # drop unneeded columns
universe = universe[['symbol', 'open', 'close']] # rearrange columns
universe['prev_close'] = universe['close'].shift(1) # shift close price of previous day to current day
universe = universe[universe.index.strftime('%Y-%m-%d') == end_date.isoformat()].copy() # drop all rows not from today
universe['perc_change'] = universe['open'] / universe['prev_close'] # create column with percentage change from open to previous close
universe = universe[universe['perc_change'] < 0.98] # filter only stocks that have dipped by 2% or more

universe_symbols = universe['symbol'].tolist() # create first filtered list

# get more data and redifine our universe
universe = api.get_bars(universe_symbols, TimeFrame.Day, start_date.isoformat(), end_date.isoformat()).df # grab only the stocks that have gapped down by 5% or more
universe['sma_20'] = talib.SMA(universe['close'], timeperiod = 20)
universe = universe[['symbol', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'trade_count','sma_20']] # rearrange columns
universe = universe[universe.index.strftime('%Y-%m-%d') == end_date.isoformat()].copy() # remove all rows besides current day
universe = universe[universe['open'] < universe['sma_20']] # filter to only stocks below the sma20

universe_symbols = universe['symbol'].tolist() # create final filtered list

capital_per_symbol = int(account.cash) // len(universe_symbols) # grab account cash balance

for symbol in universe_symbols:
    open_price = universe[universe.symbol == symbol]['open'].iloc[-1]
    quantity = capital_per_symbol // open_price

    print("{} shorting {} {} at {} - {}".format(datetime.datetime.now().isoformat(), quantity, symbol, open_price, quantity * open_price))

    try:
        order = api.submit_order(symbol, quantity, 'sell', 'market')
        print("successfully submitted market order with order_id {}".format(order.id))
    except Exception as e:
        print("error executing the above order {}".format(e))