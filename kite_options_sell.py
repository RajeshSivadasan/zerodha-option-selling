# Todo:
# Below base lots to be enabled as user specific 
# nifty_opt_base_lot = 1
# bank_opt_base_lot = 1
# process_orders() need restructuring
# If dow is 5,1,2 and MTM is below -1% then no order to be placed that day and wait for next day
# carry_till_expiry_price ? Do we really need this setting? What is the tradeoff?
# Code to delete log files older than 30 days
# For calculation of option greeks using Black Scholes - https://www.youtube.com/watch?v=T6tI3hVks5I 
# Autoupdate: https://www.gkbrk.com/wiki/python-self-update/ ; https://gist.github.com/gesquive/8363131 ; 

# 1.0.0 Base Version, Fixed AttributeError: 'dict' object has no attribute 'margins'. Fixed potential plac_order error due to incorrect usage of kite object
# 1.0.1 Fixed KeyError: 'partial_profit_booked_flg' at line 796, Updated process_orders() to telegram mtm for each user. Check if processing is delayed and is needed 
# 1.0.2 Added code to send log. Changed mtm printing frequency
# 1.0.3 Profit booking not happening. Fixed float qty issue in book_profit(); print mtm at the end; changed process_orders();
# 1.0.4 Added profit_booking_type (PERCENT|PIVOT). Update .ini file user sections with profit_booking_type = PERCENT | PIVOT   
# 1.0.5 used sell_quantity instead of quantity in get_positions() to calculate profit_target_amount as new positions were getting squared off due to profit target already being achieved
# 1.0.6 Exception handling for processing as the algo gets aborted totally; print position and MTM each 5mins
# 1.0.7 Added nifty_opt_base_lot and bank_opt_base_lot parameters to the user. Implementation pending
# 1.0.8 Handled Unknown Content-Type issue using retry option
# 1.0.9 Fixed error in exception handling at line 256 
# 1.1.0 Wait for 180 seconds to print into logs
# 1.1.1 Error: Market orders are blocked from trading due to illiquidity. book_profit_PERC() and book_profit_eod() updated with limit orders
# 1.1.2 auto_profit_booking implemented to override automatic profit booking and give more control to manually manage positions
# 1.1.3 book_profit_eod() not working on expiry. Modified the code to fix the issue.
# 1.1.4 book_profit_eod() bug fix in if condition
# 1.1.5 book_profit_eod() bug fix in date condition
# 1.1.6 Changes for debugging blank list of nifty strikes
# 1.1.7 Implemented autosquareoff for loss percentage as well. Learnt very hard way. Option prices moved 11 times against the position
# 1.1.8 Use Kiteuser as the root user which has the API Key and Secret
# 1.1.9 Fix the bug of booking loss for future positions as well. Condition for options only added. 
# 1.2.0 Changed option strike filter to 1500 away from ATM both sides to prevent error during extreme option prices
# 1.2.1 Fixed tradingsymbol access error in profit booking code
# Plan Tag based order management


version = "1.3.0"
# Kite bypass api video (from TradeViaPython)
# https://youtu.be/dLtWgpjsWdk?si=cPsQJpd0f1zkE4-N

# Autoupdate latest version from github
# Script to be scheduled at 9:14 AM IST
# Can run premarket advance and decline check to find the market sentiment
#  
###### STRATEGY / TRADE PLAN #####
# Trading Style     : Intraday Strangle with premium <=50. Positional if MTM is negative(Use Mean reversion)
# Trade Timing      : Entry: Morning 10:30 
# Trading Capital   : Rs 6,60,000 approx to start with
# Script            : Nifty Options
# Trading Qty       : Min upto 6 lots
# Premarket Routine : None
# Trading Goals     : Short max Nifty OTM Call/Put < 100   
# Time Frame        : CHeck position every 30 seconds

# Risk Capacity     : <>
# Order Management  : 

# Check after first 15 mins. If nifty breaks high, positive bias, if breaks low negative bias.


# Strategy 0:
# Instead of Pivot point levels, use (open -  close) to see the % rise or fall and decide bias and 20/30/40/50 pts entry targets
# So no need for getting historic data and all. 

# Strategy 1 (Neutral Bias/Small Short Bias): Sell Both Call and Put at 11:30 AM of strike around 30 (configurable)  
# Entry Criteria    : Entry post 10:30 AM to 12;
# If crossed R3 sell next strike
# Exit Criteria     : 1% of Margin used (1100 per lot) or 75% at first support   

# Strategy 2 (Short Biased): Sell ATM CE
# Entry Criteria    : Entry at 11:30 (when usually market has peaked out);
# If crossed R3 sell next strike
# Exit Criteria     : 1% of Margin used (1100 per lot) or 75% at first support


# Strategy 3 (Long Biased): 
# Entry (Option 1) :Sell at R2(Base Lot), at R3(Base Lot*1.5) , at R4(Base Lot*2)  
# Entry (Option 2-Wed,Thu) :Sell at R2(Base Lot), at R2+30(Base Lot) , Sell next Strike at NextStrikPrice=Martek+5 (Base Lot) 
# , at NextStrikPrice+30(Base Lot), at NextToNextStrikPrice(Market)+5(Base Lot),at NextToNextStrikPrice30(Base Lot)
# Entry (Option 2-Fri,Mon,Tue) :Sell at R2(Base Lot), at R2+30(Base Lot) , Sell next Strike at NextStrikPrice=Martek+5 (Base Lot) 
# , at NextStrikPrice+30(Base Lot), at NextToNextStrikPrice(Market)+5(Base Lot),at NextToNextStrikPrice30(Base Lot)
# or Use Golden Ratio (Fibonacci series) for entry prices

# Exit Criteria    : Book 75% of Qty at 1% of Margin used (Rs 1200 per lot) or 75% at first support if profit is above


# Strategy 4 (Far Shorts):
# Identify far strikes (CE/PE) which expire zero with at least 11+ points 
# Entry : Trigger this strike only if market moves 0.5% either side. For each 0.5% move  the strike selection further.


# pip install kiteconnect pyotp requests pandas



import pyotp
# from kiteext import KiteExt
# from kiteext import *
import time
import datetime
import os
import sys
import configparser
import pandas as pd
import requests
# from kiteconnect import KiteTicker    # Used for websocket only

from kiteconnect import KiteConnect

# ---- For API Based login -----------------
LOGINURL = "https://kite.zerodha.com/api/login"
TWOFAURL = "https://kite.zerodha.com/api/twofa"

def Zerodha(user_id, password, totp, api_key, secret, tokpath):
    try:
        session = requests.Session()
        session_post = session.post(LOGINURL, data={
            "user_id": user_id, "password": password}).json()
        # iLog(f"{session_post=}")
        if (
            session_post and
            isinstance(session_post, dict) and
            session_post['data'].get('request_id', False)
        ):
            request_id = session_post["data"]["request_id"]
            # iLog(f"{request_id=}")
        else:
            raise ValueError("Request id is not found")
    except ValueError as ve:
        iLog(f"ValueError: {ve}")
        sys.exit(1)  # Exit with a non-zero status code to indicate an error
    except requests.RequestException as re:
        iLog(f"RequestException: {re}")
        sys.exit(1)
    except Exception as e:
        # Handle other unexpected exceptions
        iLog(f"An unexpected error occurred: {e}")
        sys.exit(1)

    try:
        # Generate a TOTP token
        totp = pyotp.TOTP(totp)
        twofa = totp.now()

        # Prepare the data for the 2FA request
        data = {
            "user_id": user_id,
            "request_id": request_id,
            "twofa_value": twofa
        }

        # Perform the 2FA request
        response = session.post(TWOFAURL, data=data)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Get the request token from the redirect URL
        session_get = session.get(
            f"https://kite.trade/connect/login?api_key={api_key}")
        session_get.raise_for_status()  # Raise an exception for HTTP errors

        split_url = session_get.url.split("request_token=")
        if len(split_url) >= 2:
            request_token = split_url[1].split("&")[0]
            # iLog(f"{request_token=}")
        else:
            raise ValueError("Request token not found in the URL")

    except requests.RequestException as re:
        # Handle network-related errors, including HTTP errors
        iLog(f"RequestException: {re}")
        sys.exit(1)
    # except pyotp.utils.OtpError as otp_error:
    #     # Handle TOTP generation errors
    #     iLog(f"TOTP Generation Error: {otp_error}")
    #     sys.exit(1)
    except ValueError as value_error:
        # Handle the case where the request token is not found
        iLog(f"ValueError: {value_error}")
        sys.exit(1)
    except Exception as e:
        # Handle other unexpected exceptions
        iLog(f"An unexpected error occurred: {e}")
        sys.exit(1)

    try:
        kite = KiteConnect(api_key=api_key)
        data = kite.generate_session(request_token, api_secret=secret)
        # iLog(f"{data=}")
        if (
            data and
            isinstance(data, dict) and
            data.get('access_token', False)
        ):
            # iLog(f"{data['access_token']}")
            # with open(tokpath, 'w') as tok:
            #     tok.write(data['access_token'])
            return kite
        else:
            raise ValueError(f"Unable to generate session: {str(data)}")
    except Exception as e:
        # Handle any unexpected exceptions
        iLog(f"when generating session: {e}")
        sys.exit(1)
# -- For API Based Login -----------------


# For Logging and send messages to Telegram
def iLog(strMsg,sendTeleMsg=False):
    print(f"{datetime.datetime.now()}|{strMsg}",flush=True)
    if sendTeleMsg :
        try:
            requests.get("https://api.telegram.org/"+strBotToken+"/sendMessage?chat_id="+strChatID+"&text="+strMsg)
        except:
            strMsg = "Telegram message failed."+strMsg
            print(f"{datetime.datetime.now()}|{strMsg}",flush=True)





########################################################
#        Declare Functions
########################################################

def get_pivot_points(instrument_token):
    ''' Returns Pivot points dictionary for a given instrument token using previous day values
    '''
    from_date = datetime.date.today()-datetime.timedelta(days=5)
    to_date = datetime.date.today()-datetime.timedelta(days=1)
    try:
        # Return last row of the dataframe as dictionary
        kite_temp = kite_users[0]["kite_object"]
        # Historical data can be fetched using KiteExt only if needed
        dict_ohlc =  pd.DataFrame(kite_temp.historical_data(instrument_token,from_date,to_date,'day')).iloc[-1].to_dict()
        # dict_ohlc =  pd.DataFrame(kite.historical_data(instrument_token,from_date,to_date,'day')).iloc[-1].to_dict()

        # Calculate Pivot Points and update the dictionary
        last_high = dict_ohlc["high"]
        last_low = dict_ohlc["low"]
        last_close = dict_ohlc["close"]

        range = last_high - last_low
        dict_ohlc["pp"] = pp = round((last_high + last_low + last_close)/3)
        dict_ohlc["r1"] = r1 = round((2 * pp) - last_low)
        dict_ohlc["r2"] = r2 = round(pp + range)
        dict_ohlc["r3"] = r3 = round(pp + 2 * range)
        dict_ohlc["r4"] = r4 = r3 + (r3 - r2)   # ???? For r4 Check if we need to divide / 2 and then round
        dict_ohlc["s1"] = s1 = round((2 * pp) - last_high)
        dict_ohlc["s2"] = s2 = round(pp - (r1 - s1))
        dict_ohlc["s3"] = s3 = round(pp - 2 * (last_high - last_low))

        iLog(f"Pivot Points for {instrument_token} :  {s3}(s3) {s2}(s2) {s1}(s1) {pp}(pp) {r1}(r1) {r2}(r2) {r3}(r3) {r4}(r4)")
        
        dict_ohlc["instrument_token"] = instrument_token

        return dict_ohlc

    except Exception as ex:
        iLog(f"Unable to fetch pivot points for token {instrument_token}. Error : {ex}")
        return {}


def get_options(instrument_token=None):
    '''
    Gets the call and put option in the global df objects (dict_nifty_ce, dict_nifty_pe, dict_nifty_opt_selected) 
    for the required strike as per the parameters and and calculates pivot points for entry and exit
    '''
    global dict_nifty_ce, dict_nifty_pe, dict_nifty_opt_selected

    
    iLog(f"In get_options(): instrument_token={instrument_token}")

    # Get ltp for the list of filtered CE/PE strikes 
    # print("lst_nifty_opt:")
    # print(lst_nifty_opt)
    
    dict_nifty_opt_ltp = kite.ltp(lst_nifty_opt)

    # Convert the option ltp dict to dataframe for filtering option
    df_nifty_opt = pd.DataFrame.from_dict(dict_nifty_opt_ltp,orient='index')

    df_nifty_opt['type']= df_nifty_opt.index.str[-2:]               # Create type column
    df_nifty_opt['tradingsymbol'] = df_nifty_opt.index.str[4:]      # Create tradingsymbol column

    # print("df_nifty_opt:=")
    # print(df_nifty_opt)

    if instrument_token is None:
        # Check if we can use Dask to parallelize the operations
        # If no instrument token passed then get default options for both CE and PE
        # Get the CE/PE instrument data(instrument_token,last_price,type,symbol) where last_price is maximum but less than equal to option max price limit (e.g <=200)
        df_nifty_opt_ce = df_nifty_opt[(df_nifty_opt.type=='CE') & (df_nifty_opt.last_price==df_nifty_opt[(df_nifty_opt.type=='CE') & (df_nifty_opt.last_price<=nifty_ce_max_price_limit)].last_price.max())]
        df_nifty_opt_pe = df_nifty_opt[(df_nifty_opt.type=='PE') & (df_nifty_opt.last_price==df_nifty_opt[(df_nifty_opt.type=='PE') & (df_nifty_opt.last_price<=nifty_pe_max_price_limit)].last_price.max())]
    
        iLog(f"get_options(): Call selected is : {df_nifty_opt_ce.iloc[0,3]}, last_price = {df_nifty_opt_ce.iloc[0,1]}")
        iLog(f"get_options(): Put  selected is : {df_nifty_opt_pe.iloc[0,3]}, last_price = {df_nifty_opt_pe.iloc[0,1]}")

        # commented due to Futurewarning:Series.__getitem__ treating keys as positions is deprecated
        # iLog(f"get_options(): Call selected is : {df_nifty_opt_ce.tradingsymbol[-1]}({df_nifty_opt_ce.instrument_token[-1]}) last_price = {df_nifty_opt_ce.last_price[-1]}")
        # iLog(f"get_options(): Put  selected is : {df_nifty_opt_pe.tradingsymbol[-1]}({df_nifty_opt_pe.instrument_token[-1]}) last_price = {df_nifty_opt_pe.last_price[-1]}")


        # Get CE Pivot Points
        # instrument_token = str(df_nifty_opt_ce.instrument_token[-1])
        instrument_token = str(df_nifty_opt_ce.iloc[0,0])
        dict_pivot = get_pivot_points(instrument_token)
        if dict_pivot:
            dict_nifty_ce = dict_pivot
            # update the ltp and tradingsymbol

            # iLog("dict_nifty_ce:=",dict_nifty_ce)

        else:
            iLog(f"get_options(): Unable to get Pivot points for CE {instrument_token}")

        dict_nifty_ce["last_price"] = kite.ltp(instrument_token)[instrument_token]['last_price']
        dict_nifty_ce["tradingsymbol"] = df_nifty_opt_ce.iloc[0,3]
        
        # Get PE Pivot Points
        instrument_token = str(df_nifty_opt_pe.iloc[0,0])
        dict_pivot = get_pivot_points(instrument_token)
        if dict_pivot:
            dict_nifty_pe = dict_pivot
            # update the ltp and tradingsymbol

            # iLog("dict_nifty_ce:=",dict_nifty_ce)

        else:
            iLog(f"get_options(): Unable to get Pivot points for PE {instrument_token}")

        dict_nifty_pe["last_price"] = kite.ltp(instrument_token)[instrument_token]['last_price']
        dict_nifty_pe["tradingsymbol"] = df_nifty_opt_pe.iloc[0,3]

    
    else:
        # # instrument can be of previous expiry
        # Check instrument in the current expiry, if not found create dict 
        df_nifty_opt_selected = df_nifty_opt[df_nifty_opt.instrument_token==instrument_token]
        if df_nifty_opt_selected.empty:
            iLog(f"instrument_token {instrument_token} not found. Getting it from the main dataframe.")
            df_nifty_opt_selected = df[df.instrument_token==instrument_token]
            print("df_nifty_opt_selected=")
            print(df_nifty_opt_selected)
        
        # iLog(f"Call/Put selected is : {df_nifty_opt_selected.tradingsymbol[-1]}({df_nifty_opt_selected.instrument_token[-1]}) last_price = {df_nifty_opt_selected.last_price[-1]}")
        # instrument_token = str(df_nifty_opt_selected.instrument_token[-1])


        dict_pivot = get_pivot_points(instrument_token)
        if dict_pivot:
            dict_nifty_opt_selected = dict_pivot
            # update the ltp and tradingsymbol
            dict_nifty_opt_selected["last_price"] = kite.ltp(instrument_token)[str(instrument_token)]['last_price']
            dict_nifty_opt_selected["tradingsymbol"] = df_nifty_opt_selected.tradingsymbol.values[0] 
            # iLog("dict_nifty_ce:=",dict_nifty_ce)
        
        else:
            iLog(f"Unable to get Pivot points for selected CE/PE  {instrument_token}")


def get_options_NSE():
    '''
    Gets the call and put option in the global df objects (dict_nifty_ce, dict_nifty_pe) 
    '''
    global dict_nifty_ce, dict_nifty_pe

    
    iLog(f"get_options_NSE():")

    # Get ltp for the list of filtered CE/PE strikes 
    # print("lst_nifty_opt:\n{lst_nifty_opt}")
    
    dict_nifty_opt_ltp = kite.ltp(lst_nifty_opt)

    # Convert the option ltp dict to dataframe for filtering option
    df_nifty_opt = pd.DataFrame.from_dict(dict_nifty_opt_ltp,orient='index')

    df_nifty_opt['type']= df_nifty_opt.index.str[-2:]               # Create type column
    df_nifty_opt['tradingsymbol'] = df_nifty_opt.index.str[4:]      # Create tradingsymbol column

    # print("df_nifty_opt:=\n{df_nifty_opt}")


    # Check if we can use Dask to parallelize the operations
    # If no instrument token passed then get default options for both CE and PE
    # Get the CE/PE instrument data(instrument_token,last_price,type,symbol) where last_price is maximum but less than equal to option max price limit (e.g <=200)
    df_nifty_opt_ce = df_nifty_opt[(df_nifty_opt.type=='CE') & (df_nifty_opt.last_price==df_nifty_opt[(df_nifty_opt.type=='CE') & (df_nifty_opt.last_price<=nifty_ce_max_price_limit)].last_price.max())]
    df_nifty_opt_pe = df_nifty_opt[(df_nifty_opt.type=='PE') & (df_nifty_opt.last_price==df_nifty_opt[(df_nifty_opt.type=='PE') & (df_nifty_opt.last_price<=nifty_pe_max_price_limit)].last_price.max())]

    iLog(f"get_options(): Call selected is : {df_nifty_opt_ce.iloc[0,3]}, last_price = {df_nifty_opt_ce.iloc[0,1]}")
    iLog(f"get_options(): Put  selected is : {df_nifty_opt_pe.iloc[0,3]}, last_price = {df_nifty_opt_pe.iloc[0,1]}")


    # CE
    instrument_token = str(df_nifty_opt_ce.iloc[0,0])
    dict_nifty_ce["last_price"] = kite.ltp(instrument_token)[instrument_token]['last_price']
    dict_nifty_ce["tradingsymbol"] = df_nifty_opt_ce.iloc[0,3]

    # PE
    instrument_token = str(df_nifty_opt_pe.iloc[0,0])
    dict_nifty_pe["last_price"] = kite.ltp(instrument_token)[instrument_token]['last_price']
    dict_nifty_pe["tradingsymbol"] = df_nifty_opt_pe.iloc[0,3]


def get_options_BSE():
    '''
    Gets the call and put option in the global df objects (dict_sensex_ce, dict_sensex_pe) 
    '''
    global dict_sensex_ce, dict_sensex_pe

    
    iLog(f"get_options_BSE():")

  
    dict_sensex_opt_ltp = kite.ltp(lst_sensex_opt)

    # Convert the option ltp dict to dataframe for filtering option
    df_sensex_opt = pd.DataFrame.from_dict(dict_sensex_opt_ltp,orient='index')

    df_sensex_opt['type']= df_sensex_opt.index.str[-2:]               # Create type column
    df_sensex_opt['tradingsymbol'] = df_sensex_opt.index.str[4:]      # Create tradingsymbol column

    # print("df_sensex_opt:=\n{df_sensex_opt}")


    # Check if we can use Dask to parallelize the operations
    # If no instrument token passed then get default options for both CE and PE
    # Get the CE/PE instrument data(instrument_token,last_price,type,symbol) where last_price is maximum but less than equal to option max price limit (e.g <=200)
    df_sensex_opt_ce = df_sensex_opt[(df_sensex_opt.type=='CE') & (df_sensex_opt.last_price==df_sensex_opt[(df_sensex_opt.type=='CE') & (df_sensex_opt.last_price<=sensex_ce_max_price_limit)].last_price.max())]
    df_sensex_opt_pe = df_sensex_opt[(df_sensex_opt.type=='PE') & (df_sensex_opt.last_price==df_sensex_opt[(df_sensex_opt.type=='PE') & (df_sensex_opt.last_price<=sensex_pe_max_price_limit)].last_price.max())]

    iLog(f"get_options(): Call selected is : {df_sensex_opt_ce.iloc[0,3]}, last_price = {df_sensex_opt_ce.iloc[0,1]}")
    iLog(f"get_options(): Put  selected is : {df_sensex_opt_pe.iloc[0,3]}, last_price = {df_sensex_opt_pe.iloc[0,1]}")


    # CE
    instrument_token = str(df_sensex_opt_ce.iloc[0,0])
    dict_nifty_ce["last_price"] = kite.ltp(instrument_token)[instrument_token]['last_price']
    dict_nifty_ce["tradingsymbol"] = df_sensex_opt_ce.iloc[0,3]

    # PE
    instrument_token = str(df_sensex_opt_pe.iloc[0,0])
    dict_nifty_pe["last_price"] = kite.ltp(instrument_token)[instrument_token]['last_price']
    dict_nifty_pe["tradingsymbol"] = df_sensex_opt_pe.iloc[0,3]



def place_option_orders(kiteuser,flgMeanReversion=False,flgPlaceSelectedOptionOrder=False):
    ''' Place call orders and targets based on pivots/levels if no order exists
    flgMeanReversion is set to True in case of loss in existing position and need to average out.
    flgPlaceSelectedOptionOrder is set to True in case of orders for existing instrument needs to be placed and get_Options() is already run for that instrument.
    '''

    iLog(f"[{kiteuser['userid']}] In place_call_orders(): Orders will be placed based on the option_sell_type={option_sell_type}")

    
    
    # Get open orders
    df_orders = pd.DataFrame(kiteuser["kite_object"].orders())
    
    
    if df_orders.empty:
        # This can be BUY orders, so check in the else part if no sell orders place 
        # Place immediate Strangle order, both CE and PE Pivot orders if order is empty 
        # Price is ltp-5 so that its executed as market order
        # ======================
        # Place CE and PEmarket order and also pivot levels orders
        # ======================
        iLog(f"[{kiteuser['userid']}] In place_call_orders(): No existing orders found")
        if option_sell_type=='CE' or option_sell_type=='BOTH': 
            # 1. Place Market order
            # place_order(kiteuser,dict_nifty_ce["tradingsymbol"], nifty_opt_base_lot * nifty_opt_per_lot_qty, float(dict_nifty_ce["last_price"] - 5 ))
            # Market order not required. Start the ord_sizing_lvls_reg from 0 instead

            # 2. Place orders based on pivot levels
            place_option_orders_CEPE(kiteuser,flgMeanReversion,dict_nifty_ce)
        
        if option_sell_type=='PE' or option_sell_type=='BOTH':
            # 1. Place Market order
            # place_order(kiteuser,dict_nifty_pe["tradingsymbol"], nifty_opt_base_lot * nifty_opt_per_lot_qty, float(dict_nifty_pe["last_price"] - 5 ))
            # Market order not required. Start the ord_sizing_lvls_reg from 0 instead

            # 2. Place orders based on pivot levels
            place_option_orders_CEPE(kiteuser,flgMeanReversion,dict_nifty_pe)

    else:
        if flgPlaceSelectedOptionOrder:
            tradingsymbol = dict_nifty_opt_selected["tradingsymbol"]
            if sum((df_orders.status=='OPEN') & (df_orders.transaction_type=='SELL') & (df_orders.tradingsymbol==tradingsymbol)) > 0:
                iLog(f"[{kiteuser['userid']}] In place_call_orders(): Existing order found for the selected option {tradingsymbol}, NO order will be placed.")
                return

            else: 
                # Place orders for selected option
                place_option_orders_CEPE(kiteuser,flgMeanReversion,dict_nifty_opt_selected) 
        else:
            # Check existing orders for CE as well as PE and place orders accordingly
            # There can be BUY orders as well
            # Place CE orders if no existing orders are there
            if option_sell_type=='CE' or option_sell_type=='BOTH': 
                tradingsymbol = dict_nifty_ce["tradingsymbol"]
                if sum((df_orders.status=='OPEN') & (df_orders.transaction_type=='SELL') & (df_orders.tradingsymbol==tradingsymbol)) > 0:
                    iLog(f"[{kiteuser['userid']}] Open CE Orders found for {tradingsymbol}. No CE orders will be placed.")
                    # iLog(df_orders)
                else:
                    # Place Call orders
                    place_option_orders_CEPE(kiteuser,flgMeanReversion,dict_nifty_ce)


            if option_sell_type=='PE' or option_sell_type=='BOTH': 
                # Place PE orders if no existing orders are there
                tradingsymbol = dict_nifty_pe["tradingsymbol"]
                if sum((df_orders.status=='OPEN') & (df_orders.transaction_type=='SELL') & (df_orders.tradingsymbol==tradingsymbol)) > 0:
                    iLog(f"[{kiteuser['userid']}] Open PE Orders found for {tradingsymbol}. No PE orders will be placed.")
                else:
                    # Place Put orders
                    place_option_orders_CEPE(kiteuser,flgMeanReversion,dict_nifty_pe)


def place_option_orders_CEPE(kiteuser,flgMeanReversion,dict_opt):
    '''
    Called from place_option_orders(). All arguments are mandatory.
    This procedure is used for putting regular or mean reversion (position sizing) orders based on pivot levels 
    '''
    # iLog(f"[{kiteuser['userid']}] place_option_orders_CEPE(): flgMeanReversion = {flgMeanReversion} dict_opt = {dict_opt}")
    iLog(f"[{kiteuser['userid']}] place_option_orders_CEPE():")    

    last_price = dict_opt["last_price"]
    tradingsymbol = dict_opt["tradingsymbol"]
    qty = nifty_opt_base_lot * nifty_opt_per_lot_qty


    # level 0 = immediate resistance level, level 1 = Next resistance level and so on  
    if flgMeanReversion :
        #Put orders for mean reversion for existing positions while addding new positions 
        # rng = (dict_nifty_ce["r2"] - dict_nifty_ce["r1"])/2
        if dict_opt["s2"] <= last_price < dict_opt["s1"] :
            # S/R to Level Mapping: s1=0, pp=1, r1=2, r2=3, r3=4, r4=5
            # place_order(kiteuser,tradingsymbol,qty,float(dict_opt["s1"]))
            
            if 1 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[1],float(dict_opt["pp"]))
            if 2 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[2],float(dict_opt["r1"]))
            if 3 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[3],float(dict_opt["r2"]))
            if 4 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[4],float(dict_opt["r3"]))
            if 5 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[5],float(dict_opt["r4"]))

        elif dict_opt["s1"] <= last_price < dict_opt["pp"] :
            # S/R to Level Mapping: pp=0, r1=1, r2=2, r3=3, r4=4
            # place_order(kiteuser,tradingsymbol,qty,float(dict_opt["pp"]))
            if 1 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[1],float(dict_opt["r1"]))
            if 2 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[2],float(dict_opt["r2"]))
            if 3 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[3],float(dict_opt["r3"]))
            if 4 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[4],float(dict_opt["r4"]))
            if 5 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[5],float(dict_opt["r4"]) + ( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )

        elif dict_opt["pp"] <= last_price < dict_opt["r1"] :
            # S/R to Level Mapping: r1=0, r2=1, r3=2, r4=3
            # place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r1"]))
            if 1 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[1],float(dict_opt["r2"]))
            if 2 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[2],float(dict_opt["r3"]))
            if 3 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[3],float(dict_opt["r4"]))
            if 4 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[4],float(dict_opt["r4"]) + ( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )
            if 5 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[5],float(dict_opt["r4"]) + 2*( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )

        elif dict_opt["r1"] <= last_price < dict_opt["r2"] :
            # S/R to Level Mapping: r2=0, r3=1, r4=2
            # place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r2"]))
            if 1 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[1],float(dict_opt["r3"]))
            if 2 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[2],float(dict_opt["r4"]))
            if 3 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[3],float(dict_opt["r4"]) + ( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )
            if 4 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[4],float(dict_opt["r4"]) + 2*( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )
            if 5 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[5],float(dict_opt["r4"]) + 3*( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )

        elif dict_opt["r2"] <= last_price < dict_opt["r3"] :
            # S/R to Level Mapping: r3=0, r4=1
            # place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r3"]))
            if 1 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[1],float(dict_opt["r4"]))
            if 2 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[2],float(dict_opt["r4"]) + ( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )
            if 3 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[3],float(dict_opt["r4"]) + 2*( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )
            if 4 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[4],float(dict_opt["r4"]) + 3*( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )
            if 5 in lst_ord_lvl_mr: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_mr[5],float(dict_opt["r4"]) + 4*( float(dict_opt["r4"]) - float(dict_opt["r3"]) ) )

        else:
            iLog(f"[{kiteuser['userid']}] place_option_orders_CEPE(): flgMeanReversion=True, Unable to find pivots and place order for {tradingsymbol}")

    else:
        # Regular orders for fresh positions or new position for next strike for mean reversion
        if dict_opt["s3"] <= last_price < dict_opt["s2"] : 
            if 0 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[0],float(dict_opt["s2"]))
            if 1 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[1],float(dict_opt["s1"]))
            if 2 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[2],float(dict_opt["pp"]))
            if 3 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[3],float(dict_opt["r1"]))
            if 4 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[4],float(dict_opt["r2"]))
            if 5 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[5],float(dict_opt["r3"]))
        
        if dict_opt["s2"] <= last_price < dict_opt["s1"] :
            if 0 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[0],float(dict_opt["s1"]))
            if 1 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[1],float(dict_opt["pp"]))
            if 2 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[2],float(dict_opt["r1"]))
            if 3 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[3],float(dict_opt["r2"]))
            if 4 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[4],float(dict_opt["r3"]))
            if 5 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[5],float(dict_opt["r4"]))

        elif dict_opt["s1"] <= last_price < dict_opt["pp"] :
            if 0 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[0],float(dict_opt["pp"]))
            if 1 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[1],float(dict_opt["r1"]))
            if 2 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[2],float(dict_opt["r2"]))
            if 3 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[3],float(dict_opt["r3"]))
            if 4 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[4],float(dict_opt["r4"]))

        elif dict_opt["pp"] <= last_price < dict_opt["r1"] :
            if 0 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[0],float(dict_opt["r1"]))
            if 1 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[1],float(dict_opt["r2"]))
            if 2 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[2],float(dict_opt["r3"]))
            if 3 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[3],float(dict_opt["r4"]))

        elif dict_opt["r1"] <= last_price < dict_opt["r2"] :
            if 0 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[0],float(dict_opt["r2"]))
            if 1 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[1],float(dict_opt["r3"]))
            if 2 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[2],float(dict_opt["r4"]))

        elif dict_opt["r2"] <= last_price < dict_opt["r3"] :
            if 0 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[0],float(dict_opt["r3"]))
            if 1 in lst_ord_lvl_reg: place_order(kiteuser,tradingsymbol,qty*lst_qty_multiplier_reg[1],float(dict_opt["r4"]))

        else:
            iLog(f"[{kiteuser['userid']}] place_option_orders_CEPE(): flgMeanReversion=False, Unable to find pivots and place order for {tradingsymbol}")


def place_NSE_option_orders_fixed(kiteuser):
    '''
    Dependency on get_options() to get the dict_nifty_ce and dict_nifty_pe; get_options need optimisations
    Place fixed orders for CE/PE 
    '''

    iLog(f"[{kiteuser['userid']}] place_option_orders_fixed():")    


    # CE Market Order
    place_order(kiteuser, dict_nifty_ce["tradingsymbol"], nifty_opt_base_lot * nifty_opt_per_lot_qty, round(dict_nifty_ce["last_price"] - 5.0,1))

    # PE Market Order
    place_order(kiteuser, dict_nifty_pe["tradingsymbol"], nifty_opt_base_lot * nifty_opt_per_lot_qty, round(dict_nifty_pe["last_price"] - 5.0,1))

    # CE Order 2,3,4
    place_order(kiteuser, dict_nifty_ce["tradingsymbol"], nifty_opt_base_lot * nifty_opt_per_lot_qty, 30.0)
    place_order(kiteuser, dict_nifty_ce["tradingsymbol"], nifty_opt_base_lot * nifty_opt_per_lot_qty, 60.0)
    place_order(kiteuser, dict_nifty_ce["tradingsymbol"], nifty_opt_base_lot * nifty_opt_per_lot_qty, 90.0)

    # PE Order 2,3,4
    place_order(kiteuser, dict_nifty_pe["tradingsymbol"], nifty_opt_base_lot * nifty_opt_per_lot_qty,30.0)
    place_order(kiteuser, dict_nifty_pe["tradingsymbol"], nifty_opt_base_lot * nifty_opt_per_lot_qty,60.0)
    place_order(kiteuser, dict_nifty_pe["tradingsymbol"], nifty_opt_base_lot * nifty_opt_per_lot_qty,90.0)


def place_BSE_option_orders_fixed(kiteuser):
    '''
    Dependency on get_options() to get the dict_nifty_ce and dict_nifty_pe; get_options need optimisations
    Place fixed orders for CE/PE 
    '''

    iLog(f"[{kiteuser['userid']}] place_BSE_option_orders_fixed():")    


    # CE Market Order
    place_order(kiteuser, dict_nifty_ce["tradingsymbol"], nifty_opt_base_lot * nifty_opt_per_lot_qty, dict_nifty_ce["last_price"] - 5.0)

    # PE Market Order
    place_order(kiteuser, dict_nifty_pe["tradingsymbol"], nifty_opt_base_lot * nifty_opt_per_lot_qty, dict_nifty_pe["last_price"] - 5.0)

    # CE Order 2,3,4
    place_order(kiteuser, dict_nifty_ce["tradingsymbol"], nifty_opt_base_lot * nifty_opt_per_lot_qty, 50.0)
    place_order(kiteuser, dict_nifty_ce["tradingsymbol"], nifty_opt_base_lot * nifty_opt_per_lot_qty, 100.0)
    place_order(kiteuser, dict_nifty_ce["tradingsymbol"], nifty_opt_base_lot * nifty_opt_per_lot_qty, 150.0)

    # PE Order 2,3,4
    place_order(kiteuser, dict_nifty_pe["tradingsymbol"], nifty_opt_base_lot * nifty_opt_per_lot_qty,50.0)
    place_order(kiteuser, dict_nifty_pe["tradingsymbol"], nifty_opt_base_lot * nifty_opt_per_lot_qty,100.0)
    place_order(kiteuser, dict_nifty_pe["tradingsymbol"], nifty_opt_base_lot * nifty_opt_per_lot_qty,150.0)


def place_order(kiteuser,tradingsymbol,qty,limit_price=None,transaction_type=None,order_type=None,tag="kite_options_sell"):
    

    kite_obj = kiteuser["kite_object"]

    # 
    if transaction_type is None:
        transaction_type = kite_obj.TRANSACTION_TYPE_SELL

    if order_type is None:
        order_type = kite_obj.ORDER_TYPE_LIMIT


    # Place orders for all users
    if kiteuser['virtual_trade']:
        iLog(f"[{kiteuser['userid']}] place_order(): Placing virtual order : tradingsymbol={tradingsymbol}, qty={qty}, limit_price={limit_price}, transaction_type={transaction_type}",True )
        return 
    else:
        iLog(f"[{kiteuser['userid']}] place_order(): Placing order : tradingsymbol={tradingsymbol}, qty={qty}, limit_price={limit_price}, transaction_type={transaction_type}",True)
    
    # If not virtual trade, execute order on exchange
    try:
        order_id = kiteuser["kite_object"].place_order(variety=kite_obj.VARIETY_REGULAR,
                            exchange=kite_obj.EXCHANGE_NFO,
                            tradingsymbol=tradingsymbol,
                            transaction_type=transaction_type,
                            quantity=qty,
                            product=kite_obj.PRODUCT_NRML,
                            order_type=order_type,
                            price=limit_price,
                            validity=kite_obj.VALIDITY_DAY,
                            tag=tag )

        iLog(f"[{kiteuser['userid']}] place_order(): Order Placed. order_id={order_id}",True)
        return order_id
    
    except Exception as e:
        iLog(f"[{kiteuser['userid']}] place_order(): Error placing order. {e}",True)
        return False


def process_orders(kiteuser,flg_place_orders=False):
    '''
    Check the status of orders/squareoff/add positions
    '''
    # For each users do the following:
    # 1. Check existing positions if any
    # 2. If no positions 
    #       2.1 Get options and place orders (check if orders already exists) based on pivot points regular levels
    # 3. If existing positions:
    #       3.2 place orders for existing position if not already present based on pivot points higher leves (mean reversion)
    #       
    strMsgSuffix = f"[{kiteuser['userid']}] process_orders():" 
    iLog(strMsgSuffix)

    mtm = 0
    pos = 0

    # Check MTM price with the actual on portal
    df_pos = get_positions(kiteuser)
    # iLog(f"df_pos={df_pos}")
    
    
    pos = min(df_pos.quantity)
    # Check if there are no open positions
    if pos == -1:
        # Error already printed in the get_positions() function
        pass

    elif pos == 0:
        mtm = round(sum(df_pos.mtm),2)
        kiteuser["partial_profit_booked_flg"] = 0   # Reset the profit book flag to zero
        if flg_place_orders:
            iLog( strMsgSuffix + f" No Positions found. New orders will be placed mtm={mtm}")
            # Below is called only one time in the strategy1() before calling process_orders() for each user
            # get_options()                 # Refresh call and put to be traded into the global variables
            place_option_orders(kiteuser)   # Place orders as per the strategy designated time in the parameter 
        else:
            iLog(strMsgSuffix + f" No Positions found. New orders will NOT be placed as strategy1 time {stratgy1_entry_time} passed/not met. mtm={mtm}")

    else:
        # Check if orders are there
        # if mtm is positive check if carry_till_expiry is true and 
        # Check if profit/loss target achieved
        kite_margin = kiteuser["kite_object"].margins()["equity"]["utilised"]["debits"]
        net_margin_utilised = sum(abs(df_pos.quantity/nifty_opt_per_lot_qty)*nifty_avg_margin_req_per_lot) 
        profit_target = round(net_margin_utilised * (kiteuser['profit_target_perc']/100))
        mtm = round(sum(df_pos.mtm),2)

        # position/quantity will be applicable for each symbol
        if int(time.time())%180 == 0 :  # Wait for 3 mins to print into log
            strMsg = strMsgSuffix + f" Existing position {pos} available. Overall mtm={mtm} profit_target={profit_target} net_margin_utilised={net_margin_utilised} kite_margin={kite_margin}" 
            iLog(strMsg,True)

        # May be revised based on the overall profit strategy
        # Book profit if any of the position has achieved the profit target
        if kiteuser['profit_booking_type']=="PIVOT":
            pass
        else:
            if kiteuser['auto_profit_booking'] == 1 :
                book_profit_PERC(kiteuser,df_pos)
            else:
                iLog(strMsgSuffix+" Auto Profit booking disabled !")
        
        loss_limit_perc = kiteuser['loss_limit_perc']
        current_mtm_perc = round((mtm / net_margin_utilised)*100,1)
        
        # iLog(strMsgSuffix + f" MTM {mtm} less than target profit {profit_target}. current_mtm_perc={current_mtm_perc}, loss_limit_perc={loss_limit_perc}",True)


        # In case of existing positions Check if loss needs to be booked
        if current_mtm_perc < 0 and kiteuser['auto_profit_booking'] == 1:
            if abs(current_mtm_perc) > loss_limit_perc:
                iLog(strMsgSuffix + f" Booking Loss for option positions. MTM {mtm} current_mtm_perc={current_mtm_perc} loss_limit_perc={loss_limit_perc}")
                for opt in df_pos.itertuples():
                    tradingsymbol = opt.tradingsymbol
                    if (tradingsymbol[-2:] in ('CE','PE')) and abs(opt.quantity)>0:
                        qty = int(opt.quantity)
                        iLog(strMsgSuffix + f" tradingsymbol={tradingsymbol} qty={qty} opt.ltp={opt.ltp} expiry={opt.expiry} carry_till_expiry_price={carry_till_expiry_price} opt.mtm={opt.mtm} opt.profit_target_amt={opt.profit_target_amt}")
                        if qty > 0 :
                            transaction_type = kite.TRANSACTION_TYPE_SELL
                            limit_price = round(opt.ltp - 5)
                        else:
                            transaction_type = kite.TRANSACTION_TYPE_BUY
                            limit_price = round(opt.ltp + 5)

                        qty = abs(qty)
                        
                        place_order(kiteuser, tradingsymbol=tradingsymbol, qty=qty, limit_price=limit_price, transaction_type=transaction_type)

            else:
                # Apply Mean Reversion
                # Check if order is alredy there and pending
                iLog(strMsgSuffix + " Checking existing positions and applying Mean Reversion orders if not already present and mtm<100")
                # Check and Place mean reversion orders for the current positions
                for opt in df_pos.itertuples():
                    iLog(strMsgSuffix + f" opt.tradingsymbol={opt.tradingsymbol} opt.instrument_token={opt.instrument_token} opt.mtm={opt.mtm}")
                    if opt.mtm<100:
                        get_options(opt.instrument_token)
                        if flg_place_orders:
                            place_option_orders(kiteuser,True,True)
                        else:
                            iLog(strMsgSuffix + " Mean reversion orders will NOT be placed as flg_place_orders is false")
    

def get_positions(kiteuser):
    '''Returns dataframe columns (m2m,quantity) with net values for Options only'''
    iLog(f"[{kiteuser['userid']}] get_positions():")

    # Calculae mtm manually as the m2m is 2-3 mins delayed in kite as per public
    try:
        # return pd.DataFrame(kite.positions().get('net'))[['m2m','quantity']].sum()
        dict_positions = kiteuser["kite_object"].positions()["net"]
        # print("dict_positions:")
        # print(dict_positions)
        if len(dict_positions)>0:

            # iLog(f"dict_positions=\n{dict_positions}")
            df_pos = pd.DataFrame(dict_positions)[['tradingsymbol', 'exchange', 'instrument_token','quantity','sell_quantity','sell_value','buy_value','last_price','multiplier','average_price']]

            df_pos = df_pos[df_pos.exchange=='NFO']

            # Get latest ltp
            # df_pos["ltp"]=[val['last_price'] for keys, val in kite.ltp(df_pos.instrument_token).items()]
            # dict_ltp = {value['instrument_token']:value['last_price'] for key, value in kite.ltp(df_pos.instrument_token).items()}
            df_pos["ltp"]=df_pos.instrument_token.map({value['instrument_token']:value['last_price'] for key, value in kite.ltp(df_pos.instrument_token).items()})

            df_pos["expiry"] = df_pos.instrument_token.map(dict_token_expiry)

            # Get only the options and not equity or other instruments
            if df_pos.empty:
                return pd.DataFrame([[0]],columns=['quantity'])
            else:
                # df_pos["mtm"] = ( df_pos.sell_value - df_pos.buy_value ) + (df_pos.quantity * df_pos.last_price * df_pos.multiplier)
                df_pos["mtm"] = ( df_pos.sell_value - df_pos.buy_value ) + (df_pos.quantity * df_pos.ltp * df_pos.multiplier)
                df_pos["profit_target_amt"] = (abs(df_pos.sell_quantity/50)*nifty_avg_margin_req_per_lot) * (kiteuser["profit_target_perc"]/100)    # used sell_quantity insted of quantity to captue net profit target
                return df_pos[['tradingsymbol','instrument_token','quantity','mtm','profit_target_amt','ltp','expiry']]


            # for pos in dict_positions:
            #     mtm = mtm + ( float(pos["sell_value"]) - float(pos["buy_value"]) ) + ( float(pos["quantity"]) * float(pos["last_price"]) * float(pos["multiplier"]))
            #     qty = qty + int(pos["quantity"])
            #     iLog(f"Kite m2m={pos['m2m']}")
            #     iLog(f"Calculated(ts,mtm,qty) = {pos['tradingsymbol']}, {mtm}, {qty}")

            # return pd.DataFrame([[mtm,qty]],columns = ['m2m', 'quantity'])
        else:
            # Return zero as quantity if there are no position
            return pd.DataFrame([[0,0]],columns=['quantity','mtm']) 

    except Exception as ex:
        iLog(f"[{kiteuser['userid']}] Unable to fetch positions dataframe. Error : {ex}")
        return pd.DataFrame([[-1,0]],columns=['quantity','mtm'])   # Return empty dataframe


def strategy1():
    '''
    Place nifty CE and PE fixed orders on wed morning
    '''
    
    iLog(f"strategy1():")
    
    # Check day of week
    if dow == 1:  # Monday
        get_options()   # Get the latest options as per the settings  
        
        for kiteuser in kite_users:
            # Will need to give strike selection method (price based or ATM based)
            # process_orders(kiteuser,True)    
            place_BSE_option_orders_fixed(kiteuser)  # Place fixed orders for CE/PE as per the settings
    
    elif dow == 2:  # Tuesday
        pass
    
    elif dow == 3:  # Wednesday
        get_options_NSE()   # Get the latest options as per the settings  
        
        for kiteuser in kite_users:
            # Will need to give strike selection method (price based or ATM based)
            # process_orders(kiteuser,True)    
            place_NSE_option_orders_fixed(kiteuser)  # Place fixed orders for CE/PE as per the settings

    elif dow == 4:  # Thursday
        pass


# Check if we need to set SL for this strategy
def strategy2(kiteuser):
    pass


def book_profit_PERC(kiteuser,df_pos):
    '''
    Books profit based on the profit booking percentage settings. Takes position dataframe as the mandatory parameter
    '''

    strMsgSuffix = f"[{kiteuser['userid']}] book_profit_PERC(): partial_profit_booked_flg {kiteuser['partial_profit_booked_flg']}"
    iLog(strMsgSuffix) 
    
    # Remove logging in loops
    if kiteuser["partial_profit_booked_flg"] == 0:
        for opt in df_pos.itertuples():
            # Check if instrument options and position is sell and its mtm is greater than profit target amt
            tradingsymbol = opt.tradingsymbol
            # Get the partial profit booking quantity
            
            qty = abs(opt.quantity) * (kiteuser["profit_booking_qty_perc"]/100)
            qty = qty - (qty % -50)
            qty = int(qty * (-1 if opt.quantity>0 else 1))   # Get reverse sign to b
            iLog(strMsgSuffix + f" tradingsymbol={tradingsymbol} opt.quantity={opt.quantity} qty={qty} opt.ltp={opt.ltp} carry_till_expiry_price={carry_till_expiry_price} opt.mtm={opt.mtm} opt.profit_target_amt={opt.profit_target_amt}")
            # Need to provision for partial profit booking
            if (tradingsymbol[-2:] in ('CE','PE')) and (opt.quantity < 0) and (opt.mtm > opt.profit_target_amt)  and (opt.ltp > carry_till_expiry_price) :
                # iLog(strMsgSuffix + f" Placing Squareoff order for tradingsymbol={tradingsymbol}, qty={qty}",True)
                # if place_order(kiteuser,tradingsymbol=tradingsymbol,qty=qty, transaction_type=kite.TRANSACTION_TYPE_BUY, order_type=kite.ORDER_TYPE_MARKET):
                if place_order(kiteuser,tradingsymbol=tradingsymbol,qty=qty,limit_price=round(opt.ltp+5),transaction_type=kite.TRANSACTION_TYPE_BUY,tag="PartialBooking"):
                    kiteuser["partial_profit_booked_flg"] = 1


def book_profit_eod(kiteuser):
    '''
    Books full profit at EOD if the scrip MTM is positive/>100 or expiry
    '''
    strMsgSuffix = f"[{kiteuser['userid']}] book_profit_eod():"
    iLog(strMsgSuffix) 

    df_pos = get_positions(kiteuser)

    for opt in df_pos.itertuples():
        if abs(opt.quantity)>0:
            tradingsymbol = opt.tradingsymbol
            qty = int(opt.quantity)
            iLog(strMsgSuffix + f" tradingsymbol={tradingsymbol} qty={qty} opt.ltp={opt.ltp} expiry={opt.expiry} carry_till_expiry_price={carry_till_expiry_price} opt.mtm={opt.mtm} opt.profit_target_amt={opt.profit_target_amt}")
            # Check if expiry is today then force squareoff
            
            if opt.expiry == datetime.date.today(): # Replaced exipry_date with todays date
                # Force squareoff
                iLog(strMsgSuffix + f" **************** Force Squareoff order for tradingsymbol={tradingsymbol} as expiry today ****************",True)
                limit_price = 0
                if qty > 0 :
                    transaction_type = kite.TRANSACTION_TYPE_SELL
                    limit_price = round(opt.ltp - 5)
                else:
                    transaction_type = kite.TRANSACTION_TYPE_BUY
                    limit_price = round(opt.ltp + 5)

                qty = abs(qty)

                # place_order(kiteuser, tradingsymbol=tradingsymbol, qty=qty, transaction_type=transaction_type, order_type=kite.ORDER_TYPE_MARKET)
                # Changed to limit order
                place_order(kiteuser, tradingsymbol=tradingsymbol, qty=qty, limit_price=limit_price, transaction_type=transaction_type)
            
            else:
                # Squareoff only if MTM > profit target
                if (tradingsymbol[-2:] in ('CE','PE')) and (opt.quantity < 0) and (opt.mtm > opt.profit_target_amt) :
                    iLog(strMsgSuffix + f" Execution Commented: Placing Squareoff order for tradingsymbol={tradingsymbol}",True)
                    # place_order(kiteuser,tradingsymbol=tradingsymbol,qty=qty*-1, transaction_type=kite.TRANSACTION_TYPE_BUY, order_type=kite.ORDER_TYPE_MARKET)
                    # Changed to limit order
                    # place_order(kiteuser,tradingsymbol=tradingsymbol,qty=qty*-1,limit_price=round(opt.ltp + 5), transaction_type=kite.TRANSACTION_TYPE_BUY)


def get_realtime_config():
    ''''
    Set the realtime configuration parmeters after each minute 
    '''
    global option_sell_type, stratgy1_entry_time, stratgy2_entry_time, auto_profit_booking

    iLog("get_realtime_config") 
    cfg.read(INI_FILE)

    option_sell_type = cfg.get("realtime", "option_sell_type")
    stratgy1_entry_time = int(cfg.get("realtime", "stratgy1_entry_time"))
    stratgy2_entry_time = int(cfg.get("realtime", "stratgy2_entry_time"))


def get_pcr():
    ''' Gets the current put call ratio for deciding market direction
    '''
    pass


# Check if the stdout resetting works or not else remove this function
def exit_algo(): 
    iLog("In exit_algo(): Resetting stdout and stderr before exit")

    # Reset stdout and std error
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    sys.exit(0)



######## Strategy 1: Sell both CE and PE @<=15
# No SL, only Mean reversion(averaging) to be applied for leg with -ve MTM

# Mean reversion for leg with -ve MTM
# -----------------------------------
# Get the Average price of the option
# place 2 orders 150% and 200% each. e.g of avg price is 100, place orders 150 and 200
# keep qty 2 times and 3times respectively 


######## Strategy 2: Sell CE at pivot resistance points , R2(qty=baselot) , R3(qty=baselot*2), R3(qty=baselot*3)




# If log folder is not present create it
if not os.path.exists("./log") : os.makedirs("./log")


########################################################
#        Initialise Variables/parameters
########################################################
# Read parameters and settings from the .ini file
INI_FILE = __file__[:-3]+".ini"
cfg = configparser.ConfigParser()
cfg.read(INI_FILE)


log_to_file = int(cfg.get("tokens", "log_to_file"))
# Initialise logging and set console and error target as log file
LOG_FILE = r"./log/tradelog_" + datetime.datetime.now().strftime("%Y%m%d") +".log"
if log_to_file: sys.stdout = sys.stderr = open(LOG_FILE, "a") # use flush=True parameter in print statement if values are not seen in log file


strChatID = cfg.get("tokens", "chat_id")
strBotToken = cfg.get("tokens", "bot_token")    #Bot include "bot" prefix in the token

# Kept the below line here as telegram bot token is read from the .ini file in the above line 
iLog(f"====== Starting Algo ({version}) ====== @ {datetime.datetime.now()}",True)
iLog(f"Logging to file :{LOG_FILE}",True)

nifty_ce_max_price_limit = int(cfg.get("info", "nifty_ce_max_price_limit")) # 15
nifty_pe_max_price_limit = int(cfg.get("info", "nifty_pe_max_price_limit")) # 15

sensex_ce_max_price_limit = int(cfg.get("info", "sensex_ce_max_price_limit")) # 30
sensex_pe_max_price_limit = int(cfg.get("info", "sensex_pe_max_price_limit")) # 30

short_strangle_time = int(cfg.get("info", "short_strangle_time"))   # 925
short_strangle_flag = False

# Time interval in seconds. Order processing happens after every interval seconds
interval_seconds = int(cfg.get("info", "interval_seconds"))   # 30

#List of thursdays when its NSE holiday
weekly_expiry_holiday_dates = cfg.get("info", "weekly_expiry_holiday_dates").split(",") # 2023-01-26,2023-03-30,2024-08-15

# List of days in number for which next week expiry needs to be selected, else use current week expiry
next_week_expiry_days = list(map(int,cfg.get("info", "next_week_expiry_days").split(",")))

# Get base lot and qty 
nifty_opt_base_lot = int(cfg.get("info", "nifty_opt_base_lot"))         # 1
nifty_opt_per_lot_qty = int(cfg.get("info", "nifty_opt_per_lot_qty"))   # 50

nifty_avg_margin_req_per_lot = int(cfg.get("info", "nifty_avg_margin_req_per_lot"))


# carry_till_expiry_price Might need a dict for all days of week settings
carry_till_expiry_price = float(cfg.get("info", "carry_till_expiry_price"))  # 20

# stratgy2_enabled = int(cfg.get("info", "stratgy2_enabled"))

###### Realtime Config Parameters for the first user  #################
# replicate the below in get_realtime_config()
option_sell_type = cfg.get("realtime", "option_sell_type")
stratgy1_entry_time = int(cfg.get("realtime", "stratgy1_entry_time"))
stratgy2_entry_time = int(cfg.get("realtime", "stratgy2_entry_time"))


# profit_booking_qty_perc = int(cfg.get("info", "profit_booking_qty_perc"))  
eod_process_time = int(cfg.get("info", "eod_process_time")) # Time at which the eod process needs to run. Usually final profit/loss booking(in case of expiry)



book_profit_eod_processed = 0


# all_variables = f"INI_FILE={INI_FILE} interval_seconds={interval_seconds}"\
#     f" stratgy1_entry_time={stratgy1_entry_time} nifty_opt_base_lot={nifty_opt_base_lot}"\
#     f" nifty_ce_max_price_limit={nifty_ce_max_price_limit} nifty_pe_max_price_limit={nifty_pe_max_price_limit}"\
#     f" carry_till_expiry_price={carry_till_expiry_price} stratgy2_entry_time={stratgy2_entry_time}"\
#     f" option_sell_type={option_sell_type} auto_profit_booking={auto_profit_booking}"

# iLog("Settings used : " + all_variables,True)



# Ravigupta code
# import requests, json, pyotp
# from kiteconnect import KiteConnect
# from urllib.parse import urlparse
# from urllib.parse import parse_qs
# def login(api_key, api_secret, user_id, user_password, totp_key):
#     http_session = requests.Session()
#     url = http_session.get(url='https://kite.trade/connect/login?v=3&api_key='+api_key).url
#     response = http_session.post(url='https://kite.zerodha.com/api/login', data={'user_id':user_id, 'password':user_password})
#     resp_dict = json.loads(response.content)
#     http_session.post(url='https://kite.zerodha.com/api/twofa', data={'user_id':user_id, 'request_id':resp_dict["data"]["request_id"], 'twofa_value':pyotp.TOTP(totp_key).now()})
#     url = url + "&skip_session=true"
#     response = http_session.get(url=url, allow_redirects=True).url
#     request_token = parse_qs(urlparse(response).query)['request_token'][0]

#     kite = KiteConnect(api_key=api_key)
#     data = kite.generate_session(request_token, api_secret=api_secret)
#     kite.set_access_token(data["access_token"])

#     return kite





# Login and get kite objects for multiple users 
# ---------------------------------------------
# Manually authorise first time this url for each user f"https://kite.trade/connect/login?api_key={api_key}"
kite_users = []
for section in cfg.sections():
    user={}

    if section[0:5]=='user-':

        user['userid'] = cfg.get(section, "userid")
        user['password'] = cfg.get(section, "password")
        user['totp_key'] = cfg.get(section, "totp_key")
        user['api_key'] = cfg.get(section, "api_key")
        user['api_secret']  = cfg.get(section, "api_secret")
        user['profit_booking_type'] = cfg.get(section, "profit_booking_type")   # PERCENT | PIVOT
        user['profit_target_perc'] = float(cfg.get(section, "profit_target_perc"))
        user['loss_limit_perc'] = float(cfg.get(section, "loss_limit_perc"))
        user['profit_booking_qty_perc'] = int(cfg.get(section, "profit_booking_qty_perc"))
        user['virtual_trade'] = int(cfg.get(section, "virtual_trade"))
        user['nifty_opt_base_lot'] = int(cfg.get(section, "nifty_opt_base_lot"))
        user['bank_opt_base_lot'] = int(cfg.get(section, "bank_opt_base_lot"))
        user['auto_profit_booking'] = int(cfg.get(section, "auto_profit_booking"))
        



        if  cfg.get(section, "root") == 'Y':
            # This part takes care of creating the root kite object which has the API access enabled
            
            try:

                kite = Zerodha(user['userid'] , user['password'], user['totp_key'], user['api_key'], user['api_secret'], "tokpath.txt")

                iLog(f"Root User {user['userid']} Logged in successfuly.",True)

                if cfg.get(section, "active")=='Y': #Root user may not be active in trading
                    user["kite_object"] = kite
                    kite_users.append(user)
                    iLog(f"Root User {user['userid']} is Active in Trading.",True)


            except Exception as e:
                iLog(f"Unable to login root user. Pls check credentials. {e}",True)
        
        
        elif  cfg.get(section, "active")=='Y':

            try:
                user["kite_object"] = Zerodha(user['userid'] , user['password'], user['totp_key'], user['api_key'], user['api_secret'], "tokpath.txt")
                user["partial_profit_booked_flg"]=0    # Initialise partial profit booking flag; Set this to 1 if partial profit booking is done.

                kite_users.append(user)

                iLog(f"[{user['userid'] }] User Logged in successfuly.",True)

            except Exception as e:
                iLog(f"[{user['userid'] }] Unable to login user. Pls check credentials. {e}",True)



if len(kite_users)<1:
    iLog(f"Unable to load or No users found in the .ini file",True)
    sys.exit(0)


# sys.exit(0)

# Set kite object to the first user to retrive LTP and other common info; user specific kite info needs to be accessed by kiteuser[n]["kite_object"] 
# kite = kite_users[0]["kite_object"]


# # Get the latest TOTP
# totp = pyotp.TOTP(totp_key).now()
# twoFA = f"{int(totp):06d}" if len(totp) <=5 else totp   # Suffix zeros if length of the totp is less than 5 digits

# # Authenticate using kite bypass and get Kite object
# kite = KiteExt(user_id=user_id, password=password, twofa=twoFA)
# # iLog(f"totp={twoFA}")




# Get current/next week expiry 
# ----------------------------
# if today is tue or wed then use next expiry else use current expiry. .isoweekday() 1 = Monday, 2 = Tuesday
dow = datetime.date.today().isoweekday()    # Also used in placing orders 
next_expiry_date = datetime.date.today() + datetime.timedelta( ((3-datetime.date.today().weekday()) % 7)+7 )
curr_expiry_date = datetime.date.today() + datetime.timedelta( ((3-datetime.date.today().weekday()) % 7))

curr_expiry_date_BFO = datetime.date.today() + datetime.timedelta( ((1-datetime.date.today().weekday()) % 7))

if str(curr_expiry_date) in weekly_expiry_holiday_dates :
    curr_expiry_date = curr_expiry_date - datetime.timedelta(days=1)

if str(next_expiry_date) in weekly_expiry_holiday_dates :
    next_expiry_date = next_expiry_date - datetime.timedelta(days=1)

if str(curr_expiry_date_BFO) in weekly_expiry_holiday_dates :
    curr_expiry_date_BFO = curr_expiry_date_BFO - datetime.timedelta(days=1)



iLog(f"dow = {dow} curr_expiry_date = {curr_expiry_date} curr_expiry_date_BFO = {curr_expiry_date_BFO} next_expiry_date = {next_expiry_date}",True)


# Get the trading levels and quantity multipliers to be followed for the day .e.g on Friday only trade reversion 3rd or 4th levels to be safe
lst_ord_lvl_reg =  eval(cfg.get("info", "ord_sizing_lvls_reg"))[dow]
lst_ord_lvl_mr =  eval(cfg.get("info", "ord_sizing_lvls_mr"))[dow]
lst_qty_multiplier_reg = eval(cfg.get("info", "qty_multiplier_per_lvls_reg"))[dow]
lst_qty_multiplier_mr = eval(cfg.get("info", "qty_multiplier_per_lvls_mr"))[dow]


iLog(f"dow={dow} lst_ord_lvl_reg={lst_ord_lvl_reg} lst_ord_lvl_mr={lst_ord_lvl_mr} lst_qty_multiplier_reg={lst_qty_multiplier_reg} lst_qty_multiplier_mr={lst_qty_multiplier_mr}")

# Will need to add banknifty here later if required
# Get option instruments for the current and next expiry
while True:
    try:
        df = pd.DataFrame(kite.instruments("NFO"))
        df_BFO = pd.DataFrame(kite.instruments("BFO")) 
        # df.to_csv("./log/instruments_nfo.csv",index=False)
        # df_BFO.to_csv("./log/instruments_bfo.csv",index=False)
        break
    except Exception as ex:
        iLog(f"Exception occurred {ex}. Will wait for 10 seconds before retry.",True)
        time.sleep(10)

df = df[ (df.segment=='NFO-OPT')  & (df.name=='NIFTY') & (df.expiry==curr_expiry_date) ]
df_BFO = df_BFO[ (df_BFO.segment=='BFO-OPT')  & (df_BFO.name=='SENSEX') & (df_BFO.expiry==curr_expiry_date_BFO) ]  


# Get a dict of instrument_token and expiry for getting the expiry in the get_positions()
dict_token_expiry = df.set_index('instrument_token').to_dict()['expiry']

# Get NIfty and BankNifty instrument data
instruments = ["NSE:NIFTY 50","NSE:NIFTY BANK","BSE:SENSEX"]  # Add more indices if needed

# To find nifty open range to decide market bias (Long,Short,Neutral)
nifty_olhc = kite.ohlc("NSE:NIFTY 50")

# List of nifty options
lst_nifty_opt = []


# Dictionary to store single row of call /  put option details
dict_nifty_ce = {}
dict_nifty_pe = {}
dict_nifty_opt_selected = {} # for storing the details of existing older option position which needs reversion



# Get ATM
nifty_atm = round(int( kite.ltp(instruments)[instruments[0]]["last_price"] ),-2)
sensex_atm = round(int( kite.ltp(instruments)[instruments[2]]["last_price"] ),-2)


iLog(f"Nifty ATM : {nifty_atm} sensex_atm : {sensex_atm}")



# Prepare the list of option stikes for entry 
#--------------------------------------------
lst_nifty_opt = df[((df.strike>=nifty_atm-1500) & (df.strike<=nifty_atm+1500)) ].tradingsymbol.apply(lambda x:'NFO:'+x).tolist()
lst_sensex_opt = df_BFO[ ((df_BFO.strike>=sensex_atm-3000) & (df_BFO.strike<=sensex_atm+3000)) ].tradingsymbol.apply(lambda x:'BFO:'+x).tolist()



# Test Area
# process_orders(kite)
# get_options()
# for kiteuser in kite_users:
#     place_option_orders_fixed(kiteuser)

# strategy1()

# get_options_BSE()
# get_options_NSE()

# print("Test Complete")
# sys.exit(0)

# Check current time
cur_HHMM = int(datetime.datetime.now().strftime("%H%M"))

nxt_5min = time.time() 
nxt_2min = time.time() 

# Process as per start and end of market timing
while cur_HHMM > 913 and cur_HHMM < 1631:

    t1 = time.time()

    if stratgy1_entry_time==cur_HHMM:
        stratgy1_entry_time = 0
        iLog(f"Triggering Strategy1...")
        strategy1()
    
    # EOD profit booking / Squareoff
    elif eod_process_time==cur_HHMM:
        if book_profit_eod_processed == 0 :
            # Book profit at eod or loss in case expiry
            for kiteuser in kite_users:
                book_profit_eod(kiteuser)

            book_profit_eod_processed = 1
        eod_process_time = 0

    else:
        for kiteuser in kite_users:
            try:
                process_orders(kiteuser)

            except Exception as e:
                iLog(f"[{kiteuser['userid']}] Exception '{e}' occured while processing process_orders(kiteuser) in for loop line 1279.",True)


    # Find processing time and Log only if processing takes more than 2 seconds
    t2 = time.time() - t1
    # iLog(f"Processing Time(secs) = {t2:.2f}",True)
    # iLog(f"cur_min={cur_min} cur_HHMM={cur_HHMM} : Processing Time={t2:.2f}")
    if t2 > 2.0: 
        iLog(f"Alert! Increased Processing time(secs) = {t2:.2f}",True)


    cur_HHMM = int(datetime.datetime.now().strftime("%H%M"))

    time.sleep(interval_seconds)   # Process the loop after every n seconds

    # Get the realtime config information every 2 mins
    if time.time()>nxt_2min: 
        nxt_2min = time.time() + (2 * 60)
        iLog("In 2 mins block")
        get_realtime_config()



    if time.time()>nxt_5min:
        nxt_5min = time.time() + (5 * 60)
        iLog("In 5 mins block")
        # Print MTM for each user every 5 mins
        for kiteuser in kite_users:
            df_pos = get_positions(kiteuser)
            iLog( f"[{kiteuser['userid']}] mtm = {round(sum(df_pos.mtm),2)} net_positon = {sum(df_pos.quantity)}",sendTeleMsg=True) 


    # End of algo activities

iLog(f"====== End of Algo ====== @ {datetime.datetime.now()}",True)
