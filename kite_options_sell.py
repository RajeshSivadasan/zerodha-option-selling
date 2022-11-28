# Code to delete log files older than 30 days
# To get a list of latest instruments as csv dump, type in browser the below url:
# https://api.kite.trade/instruments


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

# Long or Short Bias decision:
# Long Bias  : When Nifty/Call opens above r1
# Short Bias : When Nifty/Call opens below  Pivot. 


# Strategy 0:
# Instead of Pivot point levels, use (open -  close) to see the % rise or fall and decide bias and 20/30/40/50 pts entry targets
# So no need for getting historic data and all. 

# Strategy 1 (Neutral Bias/Small Short Bias): Sell Both Call and Put at 10:08 AM of strike around 150  
# Entry Criteria    : Entry post 10:30 AM to 12;
# If crossed R3 sell next strike
# Exit Criteria     : 1% of Margin used (1100 per lot) or 75% at first support   

# Strategy 2 (Long Biased): 
# Entry (Option 1) :Sell at R2(Base Lot), at R3(Base Lot*1.5) , at R4(Base Lot*2)  
# Entry (Option 2-Wed,Thu) :Sell at R2(Base Lot), at R2+30(Base Lot) , Sell next Strike at NextStrikPrice=Martek+5 (Base Lot) 
# , at NextStrikPrice+30(Base Lot), at NextToNextStrikPrice(Market)+5(Base Lot),at NextToNextStrikPrice30(Base Lot)
# Entry (Option 2-Fri,Mon,Tue) :Sell at R2(Base Lot), at R2+30(Base Lot) , Sell next Strike at NextStrikPrice=Martek+5 (Base Lot) 
# , at NextStrikPrice+30(Base Lot), at NextToNextStrikPrice(Market)+5(Base Lot),at NextToNextStrikPrice30(Base Lot)
# or Use Golden Ratio (Fibonacci series) for entry prices

# Exit Criteria    : Book 75% of Qty at 1% of Margin used (Rs 1200 per lot) or 75% at first support if profit is above

# TO DO
# net_margin_utilised =  (abs(pos)/50) * 100000   # lot size to be parameterised for nifty/bank


import pyotp
from kiteext import KiteExt
import time
import datetime
import os
import sys
import configparser
import pandas as pd
import requests
# from kiteconnect import KiteTicker    # Used for websocket only

# For Logging and send messages to Telegram
def iLog(strMsg,sendTeleMsg=False):
    print(f"{datetime.datetime.now()}|{strMsg}",flush=True)
    if sendTeleMsg :
        try:
            requests.get("https://api.telegram.org/"+strBotToken+"/sendMessage?chat_id="+strChatID+"&text="+strMsg)
        except:
            iLog("Telegram message failed."+strMsg)



# If log folder is not present create it
if not os.path.exists("./log"):
    os.makedirs("./log")


# Initialise logging and set console and error target as log file
LOG_FILE = r"./log/kite_options_sell_" + datetime.datetime.now().strftime("%Y%m%d") +".log"
# Uncomment below code to get the logs into the logfile 
# sys.stdout = sys.stderr = open(LOG_FILE, "a") # use flush=True parameter in print statement if values are not seen in log file



########################################################
#        Initialise Variables/parameters
########################################################
# Read parameters and settings from the .ini file
INI_FILE = "kite_options_sell.ini"
cfg = configparser.ConfigParser()
cfg.read(INI_FILE)


strChatID = cfg.get("tokens", "chat_id")
strBotToken = cfg.get("tokens", "options_bot_token")    #Bot include "bot" prefix in the token

# Kept the below line here as telegram bot token is read from the .ini file in the above line 
iLog(f"====== Starting Algo ====== @ {datetime.datetime.now()}",True)
iLog(f"Logging to file :{LOG_FILE}",True)

nifty_ce_max_price_limit = int(cfg.get("info", "nifty_ce_max_price_limit")) # 51
nifty_pe_max_price_limit = int(cfg.get("info", "nifty_pe_max_price_limit")) # 51

short_strangle_time = int(cfg.get("info", "short_strangle_time"))   # 925
short_strangle_flag = False

# Time interval in seconds. Order processing happens after every interval seconds
interval_seconds = int(cfg.get("info", "interval_seconds"))   # 30

# profit target percentage of the utilised margin
profit_target_perc = float(cfg.get("info", "profit_target_perc"))  # 0.1 
loss_limit_perc = float(cfg.get("info", "loss_limit_perc")) # 40
stratgy1_entry_time = int(cfg.get("info", "stratgy1_entry_time"))


#List of thursdays when its NSE holiday
weekly_expiry_holiday_dates = cfg.get("info", "weekly_expiry_holiday_dates").split(",") # 2023-01-26,2023-03-30,2024-08-15

# List of days in number for which next week expiry needs to be selected, else use current week expiry
next_week_expiry_days = list(map(int,cfg.get("info", "next_week_expiry_days").split(",")))

# Get base lot and qty 
nifty_opt_base_lot = int(cfg.get("info", "nifty_opt_base_lot"))         # 1
nifty_opt_per_lot_qty = int(cfg.get("info", "nifty_opt_per_lot_qty"))   # 50

nifty_avg_margin_req_per_lot = int(cfg.get("info", "nifty_avg_margin_req_per_lot"))

virtual_trade = int(cfg.get("info", "virtual_trade"))   # 0 = Disabled - Trades will be executed in real; 1 = Enabled - No trades will be executed on exchange


multi_user_list = list(eval(cfg.get("info", "multi_user_list")))


all_variables = f"INI_FILE={INI_FILE} interval_seconds={interval_seconds} profit_target_perc={profit_target_perc} loss_limit_perc={loss_limit_perc}"\
    f" stratgy1_entry_time={stratgy1_entry_time} nifty_opt_base_lot={nifty_opt_base_lot}"\
    f" nifty_ce_max_price_limit={nifty_ce_max_price_limit} nifty_pe_max_price_limit={nifty_pe_max_price_limit} \n***virtual_trade={virtual_trade}"

iLog("Settings used : " + all_variables,True)

# Get NIfty and BankNifty instrument data
instruments = ["NSE:NIFTY 50","NSE:NIFTY BANK"] 



# Login and get kite objects for multiple users 
# ---------------------------------------------
kite_users = []
for user in multi_user_list:
    # print(user.items())
    # 'userid 'password''totpkey'
    totp = pyotp.TOTP(user["totpkey"]).now()
    twoFA = f"{int(totp):06d}" if len(totp) <=5 else totp
    user_id = user["userid"]
    if user["active"]=="Y":     # Only consider users where active flag is Y
        try:
            kite_users.append (KiteExt(user_id=user_id, password=user["password"], twofa=twoFA))
            iLog(f"[{user_id}] User Logged in successfuly.",True)
        except Exception as e:
            iLog(f"[{user_id}] Unable to login user. Pls check credentials. {e}",True)

if len(kite_users)<1:
    iLog(f"No users found in the multi_user_list {multi_user_list}",True)
    sys.exit(0)


# for kiteuser in kite_users:
#     print(kiteuser.profile())

# Set kite object to the first user
kite = kite_users[0]



# # Get the latest TOTP
# totp = pyotp.TOTP(totp_key).now()
# twoFA = f"{int(totp):06d}" if len(totp) <=5 else totp   # Suffix zeros if length of the totp is less than 5 digits

# # Authenticate using kite bypass and get Kite object
# kite = KiteExt(user_id=user_id, password=password, twofa=twoFA)
# # iLog(f"totp={twoFA}")




# Get current/next week expiry 
# ----------------------------
# if today is tue or wed then use next expiry else use current expiry. .isoweekday() 1 = Monday, 2 = Tuesday
if datetime.date.today().isoweekday()  in (next_week_expiry_days):  # next_week_expiry_days = 2,3,4 
    expiry_date = datetime.date.today() + datetime.timedelta( ((3-datetime.date.today().weekday()) % 7)+7 )
else:
    expiry_date = datetime.date.today() + datetime.timedelta( ((3-datetime.date.today().weekday()) % 7))

if str(expiry_date) in weekly_expiry_holiday_dates :
    expiry_date = expiry_date - datetime.timedelta(days=1)

iLog(f"expiry_date = {expiry_date}")


# Will need to add banknifty here later if required
# Get option instruments for the current and next expiry
df = pd.DataFrame(kite.instruments("NFO"))
df = df[ (df.segment=='NFO-OPT')  & (df.name=='NIFTY') & (df.expiry<datetime.date.today()+datetime.timedelta(16)) ]  


# To find nifty open range to decide market bias (Long,Short,Neutral)
nifty_olhc = kite.ohlc(instruments[0])
# WIP - Need to work on this

# iLog(f"opt_instrument={opt_instrument}")
# iLog(f"nifty_opt_ltp={nifty_opt_ltp}")
# iLog(f"nifty_opt_ohlc={nifty_opt_ohlc}")
# iLog(f"nifty_olhc={nifty_olhc}")


# Get Nifty ATM
inst_ltp = kite.ltp(instruments)
nifty_ltp = inst_ltp['NSE:NIFTY 50']['last_price']
nifty_atm = round(int(nifty_ltp),-2)

# Prepare the list of option stikes for entry 
#--------------------------------------------
# Get list of CE/PE strikes 600 pts on either side of the ATM from option chain # & (df.strike%100==0)
lst_nifty_opt = df[(df.name=='NIFTY') & (df.expiry==expiry_date) & ((df.strike>=nifty_atm-600) & (df.strike<=nifty_atm+600)) ].tradingsymbol.apply(lambda x:'NFO:'+x).tolist()
# df = []
# print(df.shape)


# Dictionary to store single row of call /  put option details
dict_nifty_ce = {}
dict_nifty_pe = {}
dict_nifty_opt_selected = {} # for storing the details of existing option position which needs reversion

# # Declare Class for users
# class MyUsers:
#   def __init__(self, userid, password,totpkey):
#     self.userid = userid
#     self.password = password
#     self.totpkey = totpkey


########################################################
#        Declare Functions
########################################################

def get_pivot_points(instrument_token):
    ''' Returns Pivot points dictionary for a given instrument token using previous day vaues
    '''
    from_date = datetime.date.today()-datetime.timedelta(days=5)
    to_date = datetime.date.today()-datetime.timedelta(days=1)
    try:
        # Return last row of the dataframe as dictionary
        dict_ohlc =  pd.DataFrame(kite.historical_data(instrument_token,from_date,to_date,'day')).iloc[-1].to_dict()

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
        iLog(f"Unable to fetch pivor points for token {instrument_token}. Error : {ex}")
        return {}


def get_options(instrument_token=None):
    '''
    Gets the call and put option in the global df objects (dict_nifty_ce, df_instrument_nifty_opt_pe) 
    for the required strike as per the parameters and and calculates pivot points for entry and exit
    '''
    global dict_nifty_ce, dict_nifty_pe, dict_nifty_opt_selected

    iLog(f"In get_options(): instrument_token={instrument_token}")
  
    # Get ltp for the list of filtered CE/PE strikes 
    dict_nifty_opt_ltp = kite.ltp(lst_nifty_opt)

    # Convert the option ltp dict to dataframe for filtering option
    df_nifty_opt = pd.DataFrame.from_dict(dict_nifty_opt_ltp,orient='index')

    df_nifty_opt['type']= df_nifty_opt.index.str[-2:]               # Create type column
    df_nifty_opt['tradingsymbol'] = df_nifty_opt.index.str[4:]      # Create tradingsymbol column


    if instrument_token is None:
        # Check if we can use Dask to parallelise the operations
        # If no istrument token passed then get default options for both CE and PE
        # Get the CE/PE instrument data(instrument_token,last_price,type,symbol) where last_price is maximum but less than equal to option max price limit (e.g <=200)
        df_nifty_opt_ce = df_nifty_opt[(df_nifty_opt.type=='CE') & (df_nifty_opt.last_price==df_nifty_opt[(df_nifty_opt.type=='CE') & (df_nifty_opt.last_price<=nifty_ce_max_price_limit)].last_price.max())]
        df_nifty_opt_pe = df_nifty_opt[(df_nifty_opt.type=='PE') & (df_nifty_opt.last_price==df_nifty_opt[(df_nifty_opt.type=='PE') & (df_nifty_opt.last_price<=nifty_pe_max_price_limit)].last_price.max())]
    
        iLog(f"Call selected is : {df_nifty_opt_ce.tradingsymbol[-1]}({df_nifty_opt_ce.instrument_token[-1]}) last_price = {df_nifty_opt_ce.last_price[-1]}")
        iLog(f"Put  selected is : {df_nifty_opt_pe.tradingsymbol[-1]}({df_nifty_opt_pe.instrument_token[-1]}) last_price = {df_nifty_opt_pe.last_price[-1]}")

        # Get CE Pivot Points
        instrument_token = str(df_nifty_opt_ce.instrument_token[-1])
        dict_pivot = get_pivot_points(instrument_token)
        if dict_pivot:
            dict_nifty_ce = dict_pivot
            # update the ltp and tradingsymbol
            dict_nifty_ce["last_price"] = kite.ltp(instrument_token)[instrument_token]['last_price']
            dict_nifty_ce["tradingsymbol"] = df_nifty_opt_ce.tradingsymbol[-1]
            # iLog("dict_nifty_ce:=",dict_nifty_ce)

        else:
            iLog(f"Unable to get Pivot points for CE {instrument_token}")

        
        
        # Get PE Pivot Points
        instrument_token = str(df_nifty_opt_pe.instrument_token[-1])
        dict_pivot = get_pivot_points(instrument_token)
        if dict_pivot:
            dict_nifty_pe = dict_pivot
            # update the ltp and tradingsymbol
            dict_nifty_pe["last_price"] = kite.ltp(instrument_token)[instrument_token]['last_price']
            dict_nifty_pe["tradingsymbol"] = df_nifty_opt_pe.tradingsymbol[-1]
            # iLog("dict_nifty_ce:=",dict_nifty_ce)

        else:
            iLog(f"Unable to get Pivot points for PE {instrument_token}")


    
    else:
        # # instrument can be of previous expiry
        # Check instrument in the current expiry, if not found create dict 
        df_nifty_opt_selected = df_nifty_opt[df_nifty_opt.instrument_token==instrument_token]
        if df_nifty_opt_selected.empty:
            iLog(f"instrument_token {instrument_token} not found. Getting it from the main dataframe.")
            df_nifty_opt_selected = df[df.instrument_token==instrument_token]
        
        
        # iLog(f"Call/Put selected is : {df_nifty_opt_selected.tradingsymbol[-1]}({df_nifty_opt_selected.instrument_token[-1]}) last_price = {df_nifty_opt_selected.last_price[-1]}")
        # instrument_token = str(df_nifty_opt_selected.instrument_token[-1])

        dict_pivot = get_pivot_points(instrument_token)
        if dict_pivot:
            dict_nifty_opt_selected = dict_pivot
            # update the ltp and tradingsymbol
            dict_nifty_opt_selected["last_price"] = kite.ltp(instrument_token)[str(instrument_token)]['last_price']
            # dict_nifty_opt_selected["tradingsymbol"] = df_nifty_opt_selected.tradingsymbol[-1]
            # iLog("dict_nifty_ce:=",dict_nifty_ce)
        
        else:
            iLog(f"Unable to get Pivot points for selected CE/PE  {instrument_token}")


def place_option_orders(kiteuser,flgMeanReversion=False,flgPlaceSelectedOptionOrder=False):
    ''' Place call orders and targets based on pivots/levels if no order exists'''

    iLog(f"[{kiteuser.user_id}] In place_call_orders():")

    
    # Get open orders
    df_orders = pd.DataFrame(kiteuser.orders())
    
    
    if df_orders.empty:
        # Place both CE and PE orders if order is empty 
        # Place Call orders
        place_option_orders_CEPE(kiteuser,flgMeanReversion,dict_nifty_ce)
        # Place Put orders
        place_option_orders_CEPE(kiteuser,flgMeanReversion,dict_nifty_pe)
    
    else:
        if flgPlaceSelectedOptionOrder:
            tradingsymbol = dict_nifty_opt_selected["tradingsymbol"]
            if sum((df_orders.status=='OPEN') & (df_orders.transaction_type=='SELL') & (df_orders.tradingsymbol==tradingsymbol)) > 0:
                
                iLog(f"[{kiteuser.user_id}] In place_call_orders(): Existing order found for {tradingsymbol}, NO order will be placed.")
                return
            else:
                # Place orders for selected option
                place_option_orders_CEPE(kiteuser,flgMeanReversion,dict_nifty_opt_selected) 
        else:
            # Check existing orders for CE as well as PE and place orders accordingly
            # There can be BUY orders as well
            # Place CE orders if no existing orders are there
            tradingsymbol = dict_nifty_ce["tradingsymbol"]
            if sum((df_orders.status=='OPEN') & (df_orders.transaction_type=='SELL') & (df_orders.tradingsymbol==tradingsymbol)) > 0:
                iLog(f"[{kiteuser.user_id}] Open Orders found for {tradingsymbol}. No orders will be placed.")
                # iLog(df_orders)
            else:
                # Place Call orders
                place_option_orders_CEPE(kiteuser,flgMeanReversion,dict_nifty_ce)

            # Place PE orders if no existing orders are there
            tradingsymbol = dict_nifty_pe["tradingsymbol"]
            if sum((df_orders.status=='OPEN') & (df_orders.transaction_type=='SELL') & (df_orders.tradingsymbol==tradingsymbol)) > 0:
                iLog(f"[{kiteuser.user_id}] Open Orders found for {tradingsymbol}. No orders will be placed.")
            else:
                # Place Put orders
                place_option_orders_CEPE(kiteuser,flgMeanReversion,dict_nifty_pe)


def place_option_orders_CEPE(kiteuser,flgMeanReversion,dict_opt):
    '''
    Called from place_option_orders(). All arguments are mandatory.
    '''
    iLog(f"[{kiteuser.user_id}] In place_option_orders_CEPE():")
    
    last_price = dict_opt["last_price"]
    tradingsymbol = dict_opt["tradingsymbol"]
    qty = nifty_opt_base_lot * nifty_opt_per_lot_qty


    if flgMeanReversion :
        #Put orders for mean reversion for existing positions while addding new positions 
        # rng = (dict_nifty_ce["r2"] - dict_nifty_ce["r1"])/2
        if dict_opt["s2"] <= last_price < dict_opt["s1"] :
            # place_order(kiteuser,tradingsymbol,qty,float(dict_opt["s1"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["pp"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r1"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r2"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r3"]))
            # place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r4"]))

        elif dict_opt["s1"] <= last_price < dict_opt["pp"] :
            # place_order(kiteuser,tradingsymbol,qty,float(dict_opt["pp"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r1"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r2"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r3"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r4"]))

        elif dict_opt["pp"] <= last_price < dict_opt["r1"] :
            # place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r1"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r2"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r3"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r4"]))

        elif dict_opt["r1"] <= last_price < dict_opt["r2"] :
            # place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r2"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r3"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r4"]))

        elif dict_opt["r2"] <= last_price < dict_opt["r3"] :
            # place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r3"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r4"]))

        else:
            iLog(f"[{kiteuser.user_id}] Unable to find pivots and place order for {tradingsymbol}")

    else:
        # Regular orders for fresh positions or new position for next strike for mean reversion 
        if dict_opt["s2"] <= last_price < dict_opt["s1"] :
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["s1"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["pp"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r1"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r2"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r3"]))
            # place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r4"]))

        elif dict_opt["s1"] <= last_price < dict_opt["pp"] :
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["pp"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r1"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r2"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r3"]))
            # place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r4"]))

        elif dict_opt["pp"] <= last_price < dict_opt["r1"] :
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r1"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r2"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r3"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r4"]))

        elif dict_opt["r1"] <= last_price < dict_opt["r2"] :
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r2"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r3"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r4"]))

        elif dict_opt["r2"] <= last_price < dict_opt["r3"] :
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r3"]))
            place_order(kiteuser,tradingsymbol,qty,float(dict_opt["r4"]))

        else:
            iLog(f"[{kiteuser.user_id}] Unable to find pivots and place order for {tradingsymbol}")


def place_order(kiteuser,tradingsymbol,qty,limit_price=None,transaction_type=kite.TRANSACTION_TYPE_SELL,order_type=kite.ORDER_TYPE_LIMIT,tag="Algo"):
    
    # Place orders for all users
    if virtual_trade:
        iLog(f"[{kiteuser.user_id}] Placing virtual order : tradingsymbol={tradingsymbol}, qty={qty}, limit_price={limit_price}, transaction_type={transaction_type}",True )
        return 
    else:
        iLog(f"[{kiteuser.user_id}] Placing order : tradingsymbol={tradingsymbol}, qty={qty}, limit_price={limit_price}, transaction_type={transaction_type}",True)
    
    # If not virtual trade, execute order on exchange
    try:
        order_id = kiteuser.place_order(variety=kite.VARIETY_REGULAR,
                            exchange=kite.EXCHANGE_NFO,
                            tradingsymbol=tradingsymbol,
                            transaction_type=transaction_type,
                            quantity=qty,
                            product=kite.PRODUCT_NRML,
                            order_type=order_type,
                            price=limit_price,
                            validity=kite.VALIDITY_DAY,
                            tag=tag
                            )

        iLog(f"[{kiteuser.user_id}] Order Placed. order_id={order_id}",True)
        return order_id
    
    except Exception as e:
        iLog(f"[{kiteuser.user_id}] place_order(): Error placing order. {e}",True)
        return False


def process_orders(kiteuser=kite,flg_place_orders=False):
    '''Check the status of orders/squareoff/add positions'''
    # FOr each users do the following:
    # 1. Check existing positions if any
    # 2. If no positions get options and place orders (check if orders already exists) based on pivot points
    # 3. If existing position, place orders for existing position if not already present
    #       

    iLog(f"[{kiteuser.user_id}] In process_orders():")

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
        if flg_place_orders:
            iLog(f"[{kiteuser.user_id}] No Positions found. New orders will be placed")
            get_options()                   # Refresh call and put to be traded into the global variables
            place_option_orders(kiteuser)   # Place orders as per the stratefy designated time in the parameter 
        else:
            iLog(f"[{kiteuser.user_id}] No Positions found. New orders will NOT be placed as strategy1 time {stratgy1_entry_time} not met.")
    else:
        # Check if orders are there
        # if mtm is positive check if leave_till_expiry is true and 
        # Check if profit/loss target achieved
        net_margin_utilised = sum(abs(df_pos.quantity/50)*nifty_avg_margin_req_per_lot)
        profit_target = round(net_margin_utilised * (profit_target_perc/100))
        mtm = round(sum(df_pos.mtm),2)

        # position/quantity will be applicable for each symbol
        iLog(f"[{kiteuser.user_id}] Existing position available. mtm={mtm}, approx. net_margin_utilised={net_margin_utilised}, profit_target={profit_target}",True)

        if mtm > profit_target:
            # Squareoff 80% (In Case of Large Qtys) of the positions 
            iLog("mtm > profit_target; Squareoff")
            # df_SqOff = pd.DataFrame(kite.positions().get('net'))[['tradingsymbol','m2m','quantity']]
            for indx in df_pos.index:
                tradingsymbol = df_pos['tradingsymbol'][indx]
                qty = df_pos['quantity'][indx] * -1
                iLog(f"tradingsymbol={tradingsymbol}, qty={qty}")
                
                # Square off only options
                if tradingsymbol[-2:] in ('CE','PE') and (abs(qty)>0):
                    iLog(f"[{kiteuser.user_id}] Placing Squareoff order for tradingsymbol={tradingsymbol}, qty={qty}",True)
                    
                    # Cancel any buy order already placed
                    
                    place_order(kiteuser,tradingsymbol=tradingsymbol,qty=qty, transaction_type=kite.TRANSACTION_TYPE_BUY, order_type=kite.ORDER_TYPE_MARKET)


            iLog(f"[{kiteuser.user_id}] All Positions Squared Off")
            # exit_algo()
        else:
                # Check if loss needs to be booked
                current_mtm_perc = round((mtm / net_margin_utilised)*100,1)
                iLog(f"[{kiteuser.user_id}] MTM less than target profit. current_mtm_perc={current_mtm_perc}, loss_limit_perc={loss_limit_perc}",True)
                
                if current_mtm_perc < 0:
                    if abs(current_mtm_perc) > loss_limit_perc:
                        iLog(f"[{kiteuser.user_id}] Book Loss.(Placeholder Only)")
                    else:
                        # Apply Mean Reversion
                        # Check if order is alredy there and pending
                        iLog(f"[{kiteuser.user_id}] Apply Mean Reversion orders if not already present")
                
                iLog(f"[{kiteuser.user_id}] Checking existing positions and applying Mean Reversion orders if not already present")
                
                # Place mean reversion orders for the current positions irrespective of profit target achieved
                for opt in df_pos.itertuples():
                    iLog(f"[{kiteuser.user_id}] opt.tradingsymbol={opt.tradingsymbol} opt.mtm={opt.mtm}")
                    if opt.mtm<100:
                        get_options(opt.instrument_token)
                        if flg_place_orders:
                            place_option_orders(kiteuser,True)
                        else:
                            iLog(f"[{kiteuser.user_id}] Mean reversion orders will NOT be placed as flg_place_orders is false")


def get_positions(kiteuser):
    '''Returns dataframe columns (m2m,quantity) with net values for Options only'''
    iLog(f"[{kiteuser.user_id}] In get_positions():")

    # Calculae mtm manually as the m2m is 2-3 mins delayed in kite as per public
    try:
        # return pd.DataFrame(kite.positions().get('net'))[['m2m','quantity']].sum()
        dict_positions = kiteuser.positions()["net"]
        # print("dict_positions:")
        # print(dict_positions)
        if len(dict_positions)>0:

            # iLog(f"dict_positions=\n{dict_positions}")
            df_pos = pd.DataFrame(dict_positions)[['tradingsymbol', 'exchange', 'instrument_token','quantity','sell_value','buy_value','last_price','multiplier','average_price']]

            df_pos = df_pos[df_pos.exchange=='NFO']
            # Get only the options and not equity or other instruments
            if df_pos.empty:
                return pd.DataFrame([[0]],columns=['quantity'])
            else:
                df_pos["mtm"] = ( df_pos.sell_value - df_pos.buy_value ) + (df_pos.quantity * df_pos.last_price * df_pos.multiplier)
                return df_pos[['tradingsymbol','instrument_token','quantity','mtm']]


            # for pos in dict_positions:
            #     mtm = mtm + ( float(pos["sell_value"]) - float(pos["buy_value"]) ) + ( float(pos["quantity"]) * float(pos["last_price"]) * float(pos["multiplier"]))
            #     qty = qty + int(pos["quantity"])
            #     iLog(f"Kite m2m={pos['m2m']}")
            #     iLog(f"Calculated(ts,mtm,qty) = {pos['tradingsymbol']}, {mtm}, {qty}")

            # return pd.DataFrame([[mtm,qty]],columns = ['m2m', 'quantity'])
        else:
            # Return zero as quantity if there are no position
            return pd.DataFrame([[0]],columns=['quantity']) 

    except Exception as ex:
        iLog(f"[{kiteuser.user_id}] Unable to fetch positions dataframe. Error : {ex}")
        return pd.DataFrame([[-1]],columns=['quantity'])   # Return empty dataframe


# Check if the stdout resetting works or not else remove this funciton
def exit_algo(): 
    iLog("In exit_algo(): Resetting stdout and stderr before exit")

    # Reset stdout and std error
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    sys.exit(0)


######## Strategy 1: Sell both CE and PE @<=51
# No SL, only Mean reversion(averaging) to be appied for leg with -ve MTM

# Mean reversion for leg with -ve MTM
# -----------------------------------
# Get the Average price of the option
# place 2 orders 150% and 200% each. e.g of avg price is 100, place orders 150 and 200
# keep qty 2 times and 3times respectively 


######## Strategy 2: Sell CE at pivot resistance points , R2(qty=baselot) , R3(qty=baselot*2), R3(qty=baselot*3)

get_options()

cur_HHMM = int(datetime.datetime.now().strftime("%H%M"))
previous_min = 0
iLog(f"Processing in {interval_seconds} seconds interval loop... {cur_HHMM}",True)

stratgy1_flg = False

# Process as per start and end of market timing
while cur_HHMM > 914 and cur_HHMM < 1531:
# while True:
    
    
    cur_min = datetime.datetime.now().minute 
    
    t1 = time.time()

    if stratgy1_entry_time == cur_HHMM and stratgy1_flg == False:
        stratgy1_flg = True
        for kiteuser in kite_users:
            process_orders(kiteuser,True)    # Place CE orders if required which should be done at 10.30 AM (strategy1 time) or so
    else:
        for kiteuser in kite_users:
            process_orders(kiteuser)

    # Find processing time and Log only if processing takes more than 2 seconds
    t2 = time.time() - t1
    # iLog(f"Processing Time(secs) = {t2:.2f}",True)
    # iLog(f"previous_min={previous_min} cur_min={cur_min} cur_HHMM={cur_HHMM} : Processing Time={t2:.2f}")
    if t2 > 2.0: 
        iLog(f"Alert! Increased Processing time(secs) = {t2:.2f}",True)


    cur_HHMM = int(datetime.datetime.now().strftime("%H%M"))

    time.sleep(interval_seconds)   # Process the loop after every n seconds

    # print(".",end="",flush=True)    


iLog(f"====== End of Algo ====== @ {datetime.datetime.now()}",True)

#4