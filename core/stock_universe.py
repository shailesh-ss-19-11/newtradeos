"""
NSE stock universe definitions for Nifty indices.
Symbols are in Fyers API format: NSE:SYMBOL-EQ
"""

# ─── Nifty 50 ──────────────────────────────────────────────────────────────
NIFTY_50 = [
    'NSE:ADANIENT-EQ', 'NSE:ADANIPORTS-EQ', 'NSE:APOLLOHOSP-EQ', 'NSE:ASIANPAINT-EQ',
    'NSE:AXISBANK-EQ', 'NSE:BAJAJ-AUTO-EQ', 'NSE:BAJFINANCE-EQ', 'NSE:BAJAJFINSV-EQ',
    'NSE:BEL-EQ', 'NSE:BHARTIARTL-EQ', 'NSE:BPCL-EQ', 'NSE:BRITANNIA-EQ',
    'NSE:CIPLA-EQ', 'NSE:COALINDIA-EQ', 'NSE:DIVISLAB-EQ', 'NSE:DRREDDY-EQ',
    'NSE:EICHERMOT-EQ', 'NSE:GRASIM-EQ', 'NSE:HCLTECH-EQ', 'NSE:HDFCBANK-EQ',
    'NSE:HDFCLIFE-EQ', 'NSE:HEROMOTOCO-EQ', 'NSE:HINDALCO-EQ', 'NSE:HINDUNILVR-EQ',
    'NSE:ICICIBANK-EQ', 'NSE:INDUSINDBK-EQ', 'NSE:INFY-EQ', 'NSE:ITC-EQ',
    'NSE:JIOFIN-EQ', 'NSE:JSWSTEEL-EQ', 'NSE:KOTAKBANK-EQ', 'NSE:LT-EQ',
    'NSE:M&M-EQ', 'NSE:MARUTI-EQ', 'NSE:NESTLEIND-EQ', 'NSE:NTPC-EQ',
    'NSE:ONGC-EQ', 'NSE:POWERGRID-EQ', 'NSE:RELIANCE-EQ', 'NSE:SBILIFE-EQ',
    'NSE:SBIN-EQ', 'NSE:SHRIRAMFIN-EQ', 'NSE:SUNPHARMA-EQ', 'NSE:TATACONSUM-EQ',
    'NSE:TATAMOTORS-EQ', 'NSE:TATASTEEL-EQ', 'NSE:TCS-EQ', 'NSE:TECHM-EQ',
    'NSE:TITAN-EQ', 'NSE:WIPRO-EQ',
]

# ─── Nifty Next 50 (101–150 not counted separately here, these complete 100) ─
NIFTY_NEXT_50 = [
    'NSE:ABB-EQ', 'NSE:AMBUJACEM-EQ', 'NSE:ATGL-EQ', 'NSE:BANKBARODA-EQ',
    'NSE:CANBK-EQ', 'NSE:CHOLAFIN-EQ', 'NSE:DMART-EQ', 'NSE:GAIL-EQ',
    'NSE:GODREJCP-EQ', 'NSE:HAVELLS-EQ', 'NSE:INDUSTOWER-EQ', 'NSE:IOC-EQ',
    'NSE:IRCTC-EQ', 'NSE:IRFC-EQ', 'NSE:LODHA-EQ', 'NSE:LTIM-EQ',
    'NSE:LTTS-EQ', 'NSE:LUPIN-EQ', 'NSE:MCDOWELL-N-EQ', 'NSE:MOTHERSON-EQ',
    'NSE:MPHASIS-EQ', 'NSE:MRF-EQ', 'NSE:NAUKRI-EQ', 'NSE:NMDC-EQ',
    'NSE:NHPC-EQ', 'NSE:PIDILITIND-EQ', 'NSE:PIIND-EQ', 'NSE:POLYCAB-EQ',
    'NSE:PGHH-EQ', 'NSE:RECLTD-EQ', 'NSE:SIEMENS-EQ', 'NSE:TATAPOWER-EQ',
    'NSE:TIINDIA-EQ', 'NSE:TORNTPHARM-EQ', 'NSE:TRENT-EQ', 'NSE:TVSMOTOR-EQ',
    'NSE:ULTRACEMCO-EQ', 'NSE:UNIONBANK-EQ', 'NSE:VBL-EQ', 'NSE:VEDL-EQ',
    'NSE:ZOMATO-EQ', 'NSE:PAYTM-EQ', 'NSE:NYKAA-EQ', 'NSE:DELHIVERY-EQ',
    'NSE:ADANIGREEN-EQ', 'NSE:ADANITRANS-EQ', 'NSE:ZYDUSLIFE-EQ', 'NSE:MANKIND-EQ',
    'NSE:JSWENERGY-EQ', 'NSE:CUMMINSIND-EQ',
]

# ─── Nifty 150 additional stocks ────────────────────────────────────────────
NIFTY_150_EXTRA = [
    'NSE:ALKEM-EQ', 'NSE:ASTRAL-EQ', 'NSE:BALKRISIND-EQ', 'NSE:BANDHANBNK-EQ',
    'NSE:BERGEPAINT-EQ', 'NSE:BIOCON-EQ', 'NSE:BOSCHLTD-EQ', 'NSE:COFORGE-EQ',
    'NSE:COLPAL-EQ', 'NSE:CONCOR-EQ', 'NSE:CROMPTON-EQ', 'NSE:CRISIL-EQ',
    'NSE:DABUR-EQ', 'NSE:DEEPAKNTR-EQ', 'NSE:ESCORTS-EQ', 'NSE:EXIDEIND-EQ',
    'NSE:FEDERALBNK-EQ', 'NSE:FORTIS-EQ', 'NSE:GMRINFRA-EQ', 'NSE:GODREJPROP-EQ',
    'NSE:GRANULES-EQ', 'NSE:GUJGASLTD-EQ', 'NSE:HFCL-EQ', 'NSE:HONAUT-EQ',
    'NSE:IDFCFIRSTB-EQ', 'NSE:INDIAMART-EQ', 'NSE:ICICIGI-EQ', 'NSE:ICICIPRULI-EQ',
    'NSE:INDIANB-EQ', 'NSE:INDHOTEL-EQ', 'NSE:JSL-EQ', 'NSE:JUBLFOOD-EQ',
    'NSE:KPITTECH-EQ', 'NSE:L&TFH-EQ', 'NSE:LICI-EQ', 'NSE:LAURUSLABS-EQ',
    'NSE:LINDEINDIA-EQ', 'NSE:MARICO-EQ', 'NSE:MAXHEALTH-EQ', 'NSE:MCX-EQ',
    'NSE:MFSL-EQ', 'NSE:MUTHOOTFIN-EQ', 'NSE:NATCOPHARM-EQ', 'NSE:NIACL-EQ',
    'NSE:OBEROIRLTY-EQ', 'NSE:OFSS-EQ', 'NSE:OIL-EQ', 'NSE:PAGEIND-EQ',
    'NSE:PEL-EQ', 'NSE:PERSISTENT-EQ',
]

# ─── Nifty 200 additional stocks ────────────────────────────────────────────
NIFTY_200_EXTRA = [
    'NSE:AIAENG-EQ', 'NSE:AJANTPHARM-EQ', 'NSE:AKZOINDIA-EQ', 'NSE:AMARAJABAT-EQ',
    'NSE:AAVAS-EQ', 'NSE:ABCAPITAL-EQ', 'NSE:ACC-EQ', 'NSE:AEGISCHEM-EQ',
    'NSE:AETHER-EQ', 'NSE:AFFLE-EQ', 'NSE:APLAPOLLO-EQ', 'NSE:APTUS-EQ',
    'NSE:BAJAJHLDNG-EQ', 'NSE:BATAINDIA-EQ', 'NSE:BBTC-EQ', 'NSE:BLUESTARCO-EQ',
    'NSE:BRIGADE-EQ', 'NSE:BSE-EQ', 'NSE:CANFINHOME-EQ', 'NSE:CAPLIPOINT-EQ',
    'NSE:CARBORUNIV-EQ', 'NSE:CASTROLIND-EQ', 'NSE:CDSL-EQ', 'NSE:CEATLTD-EQ',
    'NSE:CENTURYPLY-EQ', 'NSE:CENTURYTEX-EQ', 'NSE:CHAMBLFERT-EQ', 'NSE:CLEAN-EQ',
    'NSE:CMSINFO-EQ', 'NSE:COROMANDEL-EQ', 'NSE:CREDITACC-EQ', 'NSE:CYIENT-EQ',
    'NSE:DATAPATTNS-EQ', 'NSE:DOMS-EQ', 'NSE:ECLERX-EQ', 'NSE:EDELWEISS-EQ',
    'NSE:EMAMILTD-EQ', 'NSE:EPL-EQ', 'NSE:EQUITASBNK-EQ', 'NSE:ETHOSLTD-EQ',
    'NSE:EVONIK-EQ', 'NSE:FINCABLES-EQ', 'NSE:FIVESTAR-EQ', 'NSE:GLAND-EQ',
    'NSE:GLAXO-EQ', 'NSE:GNFC-EQ', 'NSE:GPPL-EQ', 'NSE:GRINDWELL-EQ',
    'NSE:GSFC-EQ', 'NSE:HAPPSTMNDS-EQ',
]

# ─── Nifty 500 additional stocks ────────────────────────────────────────────
NIFTY_500_EXTRA = [
    'NSE:3MINDIA-EQ', 'NSE:AARTIIND-EQ', 'NSE:AARTI-EQ', 'NSE:ABFRL-EQ',
    'NSE:ABSLAMC-EQ', 'NSE:ACCELYA-EQ', 'NSE:ACE-EQ', 'NSE:ACRYSIL-EQ',
    'NSE:ADORWELD-EQ', 'NSE:ADROITINFO-EQ', 'NSE:AGROPHOS-EQ', 'NSE:AHLUCONT-EQ',
    'NSE:AIANANO-EQ', 'NSE:AIIL-EQ', 'NSE:AINDUSGP-EQ', 'NSE:AISECTLTD-EQ',
    'NSE:AJMERA-EQ', 'NSE:AKARTOOLS-EQ', 'NSE:AKSHATFOOD-EQ', 'NSE:AKURATEX-EQ',
    'NSE:ALEMBICLTD-EQ', 'NSE:ALKYLAMINE-EQ', 'NSE:ALLCARGO-EQ', 'NSE:ALLSEC-EQ',
    'NSE:ALMONDZ-EQ', 'NSE:ALOKINDS-EQ', 'NSE:ALPHAGEO-EQ', 'NSE:AMBER-EQ',
    'NSE:AMJLAND-EQ', 'NSE:AMRUTANJAN-EQ', 'NSE:ANANTRAJ-EQ', 'NSE:ANDHRAPER-EQ',
    'NSE:ANDHSUGAR-EQ', 'NSE:ANDHRCEMENT-EQ', 'NSE:ANGELONE-EQ', 'NSE:ANURAS-EQ',
    'NSE:APCL-EQ', 'NSE:APCOTEXIND-EQ', 'NSE:APIINDUSTRIE-EQ', 'NSE:APLLTD-EQ',
    'NSE:APOLLO-EQ', 'NSE:APOLLOPIPE-EQ', 'NSE:APOLLOTYRE-EQ', 'NSE:APTECHT-EQ',
    'NSE:ARCELORMIT-EQ', 'NSE:ARCHIDPLY-EQ', 'NSE:ARDEN-EQ', 'NSE:ARFIN-EQ',
    'NSE:ARIHANTCAP-EQ', 'NSE:ARMANFIN-EQ', 'NSE:ARNAV-EQ', 'NSE:ARROWTEX-EQ',
    'NSE:ARSHIYALTD-EQ', 'NSE:ARTEDZ-EQ', 'NSE:ARVEE-EQ', 'NSE:ARVINDLTD-EQ',
    'NSE:ARVSMART-EQ', 'NSE:ARYAMAN-EQ', 'NSE:ARYASTEELS-EQ', 'NSE:ASAL-EQ',
    'NSE:ASALCBR-EQ', 'NSE:ASGL-EQ', 'NSE:ASHIANA-EQ', 'NSE:ASHIMASYN-EQ',
    'NSE:ASHOKA-EQ', 'NSE:ASHOKLEY-EQ', 'NSE:ASIANENE-EQ', 'NSE:ASIANPAINT-EQ',
    'NSE:ASIANTILES-EQ', 'NSE:ASIAVISION-EQ', 'NSE:ASMTEC-EQ', 'NSE:ATAM-EQ',
    'NSE:ATFL-EQ', 'NSE:ATLANTAA-EQ', 'NSE:AUCO-EQ', 'NSE:AURIONPRO-EQ',
    'NSE:AUROPHARMA-EQ', 'NSE:AURUM-EQ', 'NSE:AVADHSUGAR-EQ', 'NSE:AVANTI-EQ',
    'NSE:AVANTIFEED-EQ', 'NSE:AVATARFIN-EQ', 'NSE:AVONMORE-EQ', 'NSE:AXISCADES-EQ',
    'NSE:AYMSYNTEX-EQ', 'NSE:AZEAGAIA-EQ', 'NSE:AZHAR-EQ', 'NSE:AZIMUTH-EQ',
    'NSE:BAJAJCON-EQ', 'NSE:BAJAJHIND-EQ', 'NSE:BAJLOAN-EQ', 'NSE:BALAMINES-EQ',
    'NSE:BALKRISIND-EQ', 'NSE:BALMLAWRIE-EQ', 'NSE:BALPHARMA-EQ', 'NSE:BALRAMCHIN-EQ',
    'NSE:BANARBEADS-EQ', 'NSE:BANAS-EQ', 'NSE:BANCOINDIA-EQ', 'NSE:BANESWAR-EQ',
]

# ─── Universe lookup ────────────────────────────────────────────────────────

UNIVERSES = {
    'NIFTY50':  NIFTY_50,
    'NIFTY100': NIFTY_50 + NIFTY_NEXT_50,
    'NIFTY150': NIFTY_50 + NIFTY_NEXT_50 + NIFTY_150_EXTRA,
    'NIFTY200': NIFTY_50 + NIFTY_NEXT_50 + NIFTY_150_EXTRA + NIFTY_200_EXTRA,
    'NIFTY500': NIFTY_50 + NIFTY_NEXT_50 + NIFTY_150_EXTRA + NIFTY_200_EXTRA + NIFTY_500_EXTRA,
}


# ─── Searchable stock catalog ────────────────────────────────────────────────
# Format: {'symbol': 'NSE:SYMBOL-EQ', 'name': 'Company Name', 'display': 'SYMBOL'}
STOCK_CATALOG = [
    {'symbol': 'NSE:RELIANCE-EQ',     'name': 'Reliance Industries Ltd',       'display': 'RELIANCE'},
    {'symbol': 'NSE:TCS-EQ',          'name': 'Tata Consultancy Services',      'display': 'TCS'},
    {'symbol': 'NSE:HDFCBANK-EQ',     'name': 'HDFC Bank Ltd',                  'display': 'HDFCBANK'},
    {'symbol': 'NSE:INFY-EQ',         'name': 'Infosys Ltd',                    'display': 'INFY'},
    {'symbol': 'NSE:ICICIBANK-EQ',    'name': 'ICICI Bank Ltd',                 'display': 'ICICIBANK'},
    {'symbol': 'NSE:HINDUNILVR-EQ',   'name': 'Hindustan Unilever Ltd',         'display': 'HINDUNILVR'},
    {'symbol': 'NSE:SBIN-EQ',         'name': 'State Bank of India',            'display': 'SBIN'},
    {'symbol': 'NSE:BHARTIARTL-EQ',   'name': 'Bharti Airtel Ltd',              'display': 'BHARTIARTL'},
    {'symbol': 'NSE:ITC-EQ',          'name': 'ITC Ltd',                        'display': 'ITC'},
    {'symbol': 'NSE:KOTAKBANK-EQ',    'name': 'Kotak Mahindra Bank',            'display': 'KOTAKBANK'},
    {'symbol': 'NSE:LT-EQ',           'name': 'Larsen & Toubro Ltd',            'display': 'LT'},
    {'symbol': 'NSE:AXISBANK-EQ',     'name': 'Axis Bank Ltd',                  'display': 'AXISBANK'},
    {'symbol': 'NSE:ASIANPAINT-EQ',   'name': 'Asian Paints Ltd',               'display': 'ASIANPAINT'},
    {'symbol': 'NSE:MARUTI-EQ',       'name': 'Maruti Suzuki India Ltd',        'display': 'MARUTI'},
    {'symbol': 'NSE:SUNPHARMA-EQ',    'name': 'Sun Pharmaceutical Industries', 'display': 'SUNPHARMA'},
    {'symbol': 'NSE:TITAN-EQ',        'name': 'Titan Company Ltd',              'display': 'TITAN'},
    {'symbol': 'NSE:BAJFINANCE-EQ',   'name': 'Bajaj Finance Ltd',              'display': 'BAJFINANCE'},
    {'symbol': 'NSE:NESTLEIND-EQ',    'name': 'Nestle India Ltd',               'display': 'NESTLEIND'},
    {'symbol': 'NSE:WIPRO-EQ',        'name': 'Wipro Ltd',                      'display': 'WIPRO'},
    {'symbol': 'NSE:ULTRACEMCO-EQ',   'name': 'UltraTech Cement Ltd',          'display': 'ULTRACEMCO'},
    {'symbol': 'NSE:HCLTECH-EQ',      'name': 'HCL Technologies Ltd',          'display': 'HCLTECH'},
    {'symbol': 'NSE:ADANIENT-EQ',     'name': 'Adani Enterprises Ltd',         'display': 'ADANIENT'},
    {'symbol': 'NSE:POWERGRID-EQ',    'name': 'Power Grid Corporation',        'display': 'POWERGRID'},
    {'symbol': 'NSE:NTPC-EQ',         'name': 'NTPC Ltd',                      'display': 'NTPC'},
    {'symbol': 'NSE:BAJAJFINSV-EQ',   'name': 'Bajaj Finserv Ltd',             'display': 'BAJAJFINSV'},
    {'symbol': 'NSE:JSWSTEEL-EQ',     'name': 'JSW Steel Ltd',                 'display': 'JSWSTEEL'},
    {'symbol': 'NSE:TATASTEEL-EQ',    'name': 'Tata Steel Ltd',                'display': 'TATASTEEL'},
    {'symbol': 'NSE:ONGC-EQ',         'name': 'Oil & Natural Gas Corporation', 'display': 'ONGC'},
    {'symbol': 'NSE:COALINDIA-EQ',    'name': 'Coal India Ltd',                'display': 'COALINDIA'},
    {'symbol': 'NSE:INDUSINDBK-EQ',   'name': 'IndusInd Bank Ltd',             'display': 'INDUSINDBK'},
    {'symbol': 'NSE:TATAMOTORS-EQ',   'name': 'Tata Motors Ltd',               'display': 'TATAMOTORS'},
    {'symbol': 'NSE:GRASIM-EQ',       'name': 'Grasim Industries Ltd',         'display': 'GRASIM'},
    {'symbol': 'NSE:CIPLA-EQ',        'name': 'Cipla Ltd',                     'display': 'CIPLA'},
    {'symbol': 'NSE:DIVISLAB-EQ',     'name': "Divi's Laboratories Ltd",       'display': 'DIVISLAB'},
    {'symbol': 'NSE:DRREDDY-EQ',      'name': "Dr. Reddy's Laboratories",      'display': 'DRREDDY'},
    {'symbol': 'NSE:EICHERMOT-EQ',    'name': 'Eicher Motors Ltd',             'display': 'EICHERMOT'},
    {'symbol': 'NSE:HINDALCO-EQ',     'name': 'Hindalco Industries Ltd',       'display': 'HINDALCO'},
    {'symbol': 'NSE:M&M-EQ',          'name': 'Mahindra & Mahindra Ltd',       'display': 'M&M'},
    {'symbol': 'NSE:TECHM-EQ',        'name': 'Tech Mahindra Ltd',             'display': 'TECHM'},
    {'symbol': 'NSE:HEROMOTOCO-EQ',   'name': 'Hero MotoCorp Ltd',             'display': 'HEROMOTOCO'},
    {'symbol': 'NSE:APOLLOHOSP-EQ',   'name': 'Apollo Hospitals Enterprise',   'display': 'APOLLOHOSP'},
    {'symbol': 'NSE:BPCL-EQ',         'name': 'Bharat Petroleum Corporation', 'display': 'BPCL'},
    {'symbol': 'NSE:BRITANNIA-EQ',    'name': 'Britannia Industries Ltd',      'display': 'BRITANNIA'},
    {'symbol': 'NSE:TATACONSUM-EQ',   'name': 'Tata Consumer Products Ltd',   'display': 'TATACONSUM'},
    {'symbol': 'NSE:ADANIPORTS-EQ',   'name': 'Adani Ports & SEZ Ltd',        'display': 'ADANIPORTS'},
    {'symbol': 'NSE:VEDL-EQ',         'name': 'Vedanta Ltd',                   'display': 'VEDL'},
    {'symbol': 'NSE:SBILIFE-EQ',      'name': 'SBI Life Insurance',           'display': 'SBILIFE'},
    {'symbol': 'NSE:HDFCLIFE-EQ',     'name': 'HDFC Life Insurance',          'display': 'HDFCLIFE'},
    {'symbol': 'NSE:BEL-EQ',          'name': 'Bharat Electronics Ltd',       'display': 'BEL'},
    {'symbol': 'NSE:JIOFIN-EQ',       'name': 'Jio Financial Services',       'display': 'JIOFIN'},
    {'symbol': 'NSE:SHRIRAMFIN-EQ',   'name': 'Shriram Finance Ltd',          'display': 'SHRIRAMFIN'},
    {'symbol': 'NSE:BAJAJ-AUTO-EQ',   'name': 'Bajaj Auto Ltd',               'display': 'BAJAJ-AUTO'},
    {'symbol': 'NSE:ZOMATO-EQ',       'name': 'Zomato Ltd',                   'display': 'ZOMATO'},
    {'symbol': 'NSE:TRENT-EQ',        'name': 'Trent Ltd',                    'display': 'TRENT'},
    {'symbol': 'NSE:LTIM-EQ',         'name': 'LTIMindtree Ltd',              'display': 'LTIM'},
    {'symbol': 'NSE:IRFC-EQ',         'name': 'Indian Railway Finance Corp',  'display': 'IRFC'},
    {'symbol': 'NSE:IRCTC-EQ',        'name': 'Indian Railway Catering & Tourism', 'display': 'IRCTC'},
    {'symbol': 'NSE:AMBUJACEM-EQ',    'name': 'Ambuja Cements Ltd',           'display': 'AMBUJACEM'},
    {'symbol': 'NSE:BANKBARODA-EQ',   'name': 'Bank of Baroda',               'display': 'BANKBARODA'},
    {'symbol': 'NSE:GAIL-EQ',         'name': 'GAIL (India) Ltd',             'display': 'GAIL'},
    {'symbol': 'NSE:HAVELLS-EQ',      'name': 'Havells India Ltd',            'display': 'HAVELLS'},
    {'symbol': 'NSE:IOC-EQ',          'name': 'Indian Oil Corporation',       'display': 'IOC'},
    {'symbol': 'NSE:LUPIN-EQ',        'name': 'Lupin Ltd',                    'display': 'LUPIN'},
    {'symbol': 'NSE:MPHASIS-EQ',      'name': 'MphasiS Ltd',                 'display': 'MPHASIS'},
    {'symbol': 'NSE:MRF-EQ',          'name': 'MRF Ltd',                      'display': 'MRF'},
    {'symbol': 'NSE:NAUKRI-EQ',       'name': 'Info Edge (India) Ltd',        'display': 'NAUKRI'},
    {'symbol': 'NSE:PIDILITIND-EQ',   'name': 'Pidilite Industries Ltd',      'display': 'PIDILITIND'},
    {'symbol': 'NSE:POLYCAB-EQ',      'name': 'Polycab India Ltd',            'display': 'POLYCAB'},
    {'symbol': 'NSE:RECLTD-EQ',       'name': 'REC Ltd',                      'display': 'RECLTD'},
    {'symbol': 'NSE:TATAPOWER-EQ',    'name': 'Tata Power Company Ltd',      'display': 'TATAPOWER'},
    {'symbol': 'NSE:TORNTPHARM-EQ',   'name': 'Torrent Pharmaceuticals Ltd', 'display': 'TORNTPHARM'},
    {'symbol': 'NSE:TVSMOTOR-EQ',     'name': 'TVS Motor Company Ltd',       'display': 'TVSMOTOR'},
    {'symbol': 'NSE:GODREJCP-EQ',     'name': 'Godrej Consumer Products Ltd','display': 'GODREJCP'},
    {'symbol': 'NSE:DABUR-EQ',        'name': 'Dabur India Ltd',              'display': 'DABUR'},
    {'symbol': 'NSE:MARICO-EQ',       'name': 'Marico Ltd',                   'display': 'MARICO'},
    {'symbol': 'NSE:COLPAL-EQ',       'name': 'Colgate-Palmolive (India) Ltd','display': 'COLPAL'},
    {'symbol': 'NSE:PAGEIND-EQ',      'name': 'Page Industries Ltd',          'display': 'PAGEIND'},
    {'symbol': 'NSE:BOSCHLTD-EQ',     'name': 'Bosch Ltd',                    'display': 'BOSCHLTD'},
    {'symbol': 'NSE:SIEMENS-EQ',      'name': 'Siemens Ltd',                  'display': 'SIEMENS'},
    {'symbol': 'NSE:OFSS-EQ',         'name': 'Oracle Financial Services',    'display': 'OFSS'},
    {'symbol': 'NSE:MUTHOOTFIN-EQ',   'name': 'Muthoot Finance Ltd',         'display': 'MUTHOOTFIN'},
    {'symbol': 'NSE:PERSISTENT-EQ',   'name': 'Persistent Systems Ltd',      'display': 'PERSISTENT'},
    {'symbol': 'NSE:COFORGE-EQ',      'name': 'Coforge Ltd',                 'display': 'COFORGE'},
    {'symbol': 'NSE:ASTRAL-EQ',       'name': 'Astral Ltd',                  'display': 'ASTRAL'},
    {'symbol': 'NSE:KPITTECH-EQ',     'name': 'KPIT Technologies Ltd',       'display': 'KPITTECH'},
    {'symbol': 'NSE:CHOLAFIN-EQ',     'name': 'Cholamandalam Investment',    'display': 'CHOLAFIN'},
    {'symbol': 'NSE:IDFCFIRSTB-EQ',  'name': 'IDFC First Bank Ltd',         'display': 'IDFCFIRSTB'},
    {'symbol': 'NSE:FEDERALBNK-EQ',   'name': 'The Federal Bank Ltd',        'display': 'FEDERALBNK'},
    {'symbol': 'NSE:CANBK-EQ',        'name': 'Canara Bank',                 'display': 'CANBK'},
    {'symbol': 'NSE:INDHOTEL-EQ',     'name': 'Indian Hotels Company',       'display': 'INDHOTEL'},
    {'symbol': 'NSE:JUBLFOOD-EQ',     'name': "Jubilant FoodWorks Ltd",      'display': 'JUBLFOOD'},
    {'symbol': 'NSE:ADANIGREEN-EQ',   'name': 'Adani Green Energy Ltd',      'display': 'ADANIGREEN'},
    {'symbol': 'NSE:ATGL-EQ',         'name': 'Adani Total Gas Ltd',         'display': 'ATGL'},
    {'symbol': 'NSE:NMDC-EQ',         'name': 'NMDC Ltd',                    'display': 'NMDC'},
    {'symbol': 'NSE:NHPC-EQ',         'name': 'NHPC Ltd',                    'display': 'NHPC'},
    {'symbol': 'NSE:VBL-EQ',          'name': 'Varun Beverages Ltd',         'display': 'VBL'},
    {'symbol': 'NSE:ANGELONE-EQ',     'name': 'Angel One Ltd',               'display': 'ANGELONE'},
    {'symbol': 'NSE:CDSL-EQ',         'name': 'Central Depository Services', 'display': 'CDSL'},
    {'symbol': 'NSE:MCX-EQ',          'name': 'Multi Commodity Exchange',    'display': 'MCX'},
    {'symbol': 'NSE:BSE-EQ',          'name': 'BSE Ltd',                     'display': 'BSE'},
    {'symbol': 'NSE:DEEPAKNTR-EQ',    'name': 'Deepak Nitrite Ltd',          'display': 'DEEPAKNTR'},
    {'symbol': 'NSE:PIIND-EQ',        'name': 'PI Industries Ltd',           'display': 'PIIND'},
    {'symbol': 'NSE:LTTS-EQ',         'name': 'L&T Technology Services',    'display': 'LTTS'},
    {'symbol': 'NSE:DIXON-EQ',        'name': 'Dixon Technologies Ltd',      'display': 'DIXON'},
    {'symbol': 'NSE:CROMPTON-EQ',     'name': 'Crompton Greaves Consumer',  'display': 'CROMPTON'},
    {'symbol': 'NSE:BANDHANBNK-EQ',   'name': 'Bandhan Bank Ltd',            'display': 'BANDHANBNK'},
    {'symbol': 'NSE:MOTHERSON-EQ',    'name': 'Samvardhana Motherson',       'display': 'MOTHERSON'},
    {'symbol': 'NSE:AUROPHARMA-EQ',   'name': 'Aurobindo Pharma Ltd',        'display': 'AUROPHARMA'},
    {'symbol': 'NSE:ALKEM-EQ',        'name': 'Alkem Laboratories Ltd',      'display': 'ALKEM'},
    {'symbol': 'NSE:LAURUSLABS-EQ',   'name': 'Laurus Labs Ltd',             'display': 'LAURUSLABS'},
    {'symbol': 'NSE:GRANULES-EQ',     'name': 'Granules India Ltd',          'display': 'GRANULES'},
    {'symbol': 'NSE:BIOCON-EQ',       'name': 'Biocon Ltd',                  'display': 'BIOCON'},
    {'symbol': 'NSE:ZYDUSLIFE-EQ',    'name': 'Zydus Lifesciences Ltd',      'display': 'ZYDUSLIFE'},
    {'symbol': 'NSE:MANKIND-EQ',      'name': 'Mankind Pharma Ltd',          'display': 'MANKIND'},
    {'symbol': 'NSE:BERGEPAINT-EQ',   'name': 'Berger Paints India Ltd',     'display': 'BERGEPAINT'},
    {'symbol': 'NSE:GODREJPROP-EQ',   'name': 'Godrej Properties Ltd',       'display': 'GODREJPROP'},
    {'symbol': 'NSE:OBEROIRLTY-EQ',   'name': 'Oberoi Realty Ltd',           'display': 'OBEROIRLTY'},
    {'symbol': 'NSE:BRIGADE-EQ',      'name': 'Brigade Enterprises Ltd',     'display': 'BRIGADE'},
    {'symbol': 'NSE:PHOENIXLTD-EQ',   'name': 'Phoenix Mills Ltd',           'display': 'PHOENIXLTD'},
    {'symbol': 'NSE:LODHA-EQ',        'name': 'Macrotech Developers Ltd',    'display': 'LODHA'},
    {'symbol': 'NSE:DMART-EQ',        'name': 'Avenue Supermarts Ltd',       'display': 'DMART'},
    {'symbol': 'NSE:NYKAA-EQ',        'name': 'FSN E-Commerce Ventures',     'display': 'NYKAA'},
    {'symbol': 'NSE:PAYTM-EQ',        'name': 'One 97 Communications',       'display': 'PAYTM'},
    {'symbol': 'NSE:DELHIVERY-EQ',    'name': 'Delhivery Ltd',               'display': 'DELHIVERY'},
    {'symbol': 'NSE:JSWENERGY-EQ',    'name': 'JSW Energy Ltd',              'display': 'JSWENERGY'},
    {'symbol': 'NSE:CUMMINSIND-EQ',   'name': 'Cummins India Ltd',           'display': 'CUMMINSIND'},
    {'symbol': 'NSE:ABB-EQ',          'name': 'ABB India Ltd',               'display': 'ABB'},
    {'symbol': 'NSE:ESCORTS-EQ',      'name': 'Escorts Kubota Ltd',          'display': 'ESCORTS'},
    {'symbol': 'NSE:CONCOR-EQ',       'name': 'Container Corporation of India', 'display': 'CONCOR'},
    {'symbol': 'NSE:ACC-EQ',          'name': 'ACC Ltd',                     'display': 'ACC'},
    {'symbol': 'NSE:ASHOKLEY-EQ',     'name': 'Ashok Leyland Ltd',           'display': 'ASHOKLEY'},
    {'symbol': 'NSE:APOLLOTYRE-EQ',   'name': 'Apollo Tyres Ltd',            'display': 'APOLLOTYRE'},
    {'symbol': 'NSE:BALKRISIND-EQ',   'name': 'Balkrishna Industries Ltd',   'display': 'BALKRISIND'},
    {'symbol': 'NSE:MAXHEALTH-EQ',    'name': 'Max Healthcare Institute',    'display': 'MAXHEALTH'},
    {'symbol': 'NSE:FORTIS-EQ',       'name': 'Fortis Healthcare Ltd',       'display': 'FORTIS'},
    {'symbol': 'NSE:UNIONBANK-EQ',    'name': 'Union Bank of India',         'display': 'UNIONBANK'},
    {'symbol': 'NSE:INDIANB-EQ',      'name': 'Indian Bank',                 'display': 'INDIANB'},
]

# Build index for fast lookup
_CATALOG_INDEX = {item['display'].upper(): item for item in STOCK_CATALOG}
_CATALOG_INDEX.update({item['symbol']: item for item in STOCK_CATALOG})


def get_universe(universe_key: str) -> list[str]:
    return UNIVERSES.get(universe_key.upper(), NIFTY_50)


def search_stocks(query: str, limit: int = 10) -> list[dict]:
    q = query.upper().strip()
    if not q:
        return []
    results = [
        s for s in STOCK_CATALOG
        if q in s['display'].upper() or q in s['name'].upper()
    ]
    return results[:limit]


def get_display_name(fyers_symbol: str) -> str:
    entry = _CATALOG_INDEX.get(fyers_symbol)
    if entry:
        return entry['display']
    return fyers_symbol.replace('NSE:', '').replace('-EQ', '')
