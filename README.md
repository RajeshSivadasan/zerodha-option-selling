Zerodha Kite Multi user option selling Algo (Beta):
---------------------------------------------------
1. kite_options_sell.py - Option Selling program based on short strangle (premium<=50, can be configured) and Mean Reversion approach.   
2. kite_options_sell.ini - This .ini file is used by the above kite_options_sell.py for picking up its parameters.

<b><u>Highlights of the algo:</u></b>
1. <b>virtual_trade</b> parameter if set to 1 in the kite_options_sell.ini file will not trigger orders to the exchange. It will just log the generated order details. Set this to 0 for realtime exchange execution of order.
2. The algo uses pivot points to punch Nifty call orders at resistance/support levels. Parameterisation of this feature is in progress.
3. The nifty call is selected based on the following .ini parameters:
  => <b>nifty_ce_max_price_limit</b> is the limit price for the call option
  => <b>next_week_expiry_days</b> is the list of days for which next week expiry needs to be selected insted of current week. E.g if this parameter is set to 3,4 
  it will select next week expiry date on wed and thu and for rest of the days it will use current week expiry. 
4. Parameter <b>profit_target_perc</b> can be specified to book the profit after certain percentage of margin is achieved in the MTM. Margin considered per lot is 1 lakh which can be also specified at the <b>nifty_avg_margin_req_per_lot</b> parameter. Using margin parameter as zerodha margin api doesn't give the correct margin of executed orders, it shows even for the open orders where margins are blocked.
<i>Note:</i> Set <b>profit_target_perc</b> to higher percentage (10) to avoid auto squareoff.
5. The algo runs in a loop and processes the orders/books profits/loss after every x mins as specified in the <b>interval</b> parameter. Default value set to 2 (mins).   
6. For getting the updates in Telegram chat, create a telegram bot using the botfather and ensure to start the bot. Specify the bot token in the .ini file with bot prefix and also specify your telegram chat id.
