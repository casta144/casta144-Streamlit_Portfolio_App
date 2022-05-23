import pandas as pd
import plotly.graph_objects as go
import psycopg2.extras
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Advance Trading Bot",
    page_icon=":rocket:",
    layout="wide",
    initial_sidebar_state="expanded", )

option = st.sidebar.selectbox('What would you like to do?',
                              ['🏠 Home', '🔎 Search for Stocks', '🚀 Wallstreetbets', '📈 Trending'])

st.sidebar.text_area(label="Notes", placeholder="Please feel free to use the following text area for note taking.")


# Passing secret variables to connect to the Database
def init_connection():
    return psycopg2.connect(**st.secrets["wbets"])


connection = init_connection()
cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)


# Tab 🔎 Search for Stocks
# Function to fetch the historical dataset for selected stock
@st.experimental_memo(ttl=86400, show_spinner=True)
def get_data_search(ticker):
    data_full_set = cursor.execute("""
                select date(date) as date, open, high, low, close
                from data_stocks_daily
                where symbol = %s
                and date(date) > current_date - interval '%s day'
                order by date asc""", (ticker.upper(), 3650,))

    columns = [col[0] for col in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return rows


# Tab 🚀 Wallstreetbets
# Function to fetch a query with the count of mentions for each stock, grouped by stock
@st.experimental_memo(ttl=86400, show_spinner=True)
def get_data_wsbt(num_of_days):
    cursor.execute("""
                    SELECT COUNT(*) AS num_mentions, symbol, name, MAX(dt) AS dt
                    FROM mention JOIN stock ON stock.id = mention.stock_id
                    WHERE date(dt) > (SELECT MAX(date(dt)) FROM mention) - interval '%s day'
                    GROUP BY stock_id, symbol, name         
                    ORDER BY num_mentions DESC
                    """, (num_of_days,))
    columns = [col[0] for col in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return rows


# Tab 🚀 Wallstreetbets
# Function to fetch a query with all the data within the mentions query, sorted by the date field
@st.experimental_memo(ttl=86400, show_spinner=True)
def get_dict_wsb():
    cursor.execute("""
                SELECT symbol, message, url, dt, author
                FROM mention JOIN stock ON stock.id = mention.stock_id
                ORDER BY dt DESC
            """)
    mentions_data_dict = cursor.fetchall()
    return mentions_data_dict


mentions = get_dict_wsb()


# Tab 📈 Trending
# Function that runs through the historical data and selects stocks based on a calculations known as a breakout trend.
@st.experimental_memo(show_spinner=True)
def get_trending_stock(trending_num_days):
    cursor.execute(f""" SELECT * FROM ( SELECT date, open, close, symbol, lAG(close, 1) OVER ( ORDER BY date) 
    previous_close, LAG(open, 1) OVER ( ORDER BY date) previous_open FROM data_stocks_daily ) a 
    WHERE date(date) > (SELECT MAX(date(date)) FROM data_stocks_daily) - interval '%s day' 
    AND previous_close < previous_open AND close > previous_open 
    AND open < previous_close""", (trending_num_days,))
    rows_engulfing = cursor.fetchall()
    return rows_engulfing


# Tab 🔎 Search for Stocks
# Convert Dataframe to csv for users to be able to download
@st.experimental_memo(show_spinner=True)
def convert_df(data_set_for_download):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return data_set_for_download.to_csv().encode('utf-8')


# Tab 🔎 Search for Stocks
# Function to obtain a list of the symbols that have at least 4 years of historical data, for the user to be able to
# filter through in the tab
@st.experimental_memo(show_spinner=True)
def get_symbol_list():
    data_full_set = cursor.execute("""
                select symbol
                FROM data_stocks_daily
                WHERE char_length(data_stocks_daily.symbol) < 5
                GROUP BY data_stocks_daily.symbol
                HAVING COUNT(data_stocks_daily.index) > 1460
                """)

    list_symbols_data = cursor.fetchall()
    return list_symbols_data


symbols_list_comp = []
list_symbols = get_symbol_list()

for row in list_symbols:
    symbols_list_comp.append(row['symbol'])

symbols_list_comp.sort()


# Tab 🔎 Search for Stocks
# Function that runs an API request to obtain the information for a company
# with that it is paired with preselected fields to display, limiting the information for the tab.
# And a iterations to match both the API results with the preselected fields
@st.experimental_memo(show_spinner=True)
def yahoo_company_info(ticker):
    symbol_info_company = yf.Ticker(ticker)
    company_info = symbol_info_company.info
    company_information_layout = ["longName", "symbol", "quoteType", "sector", "market", "exchange",
                                  "exchangeTimezoneName", "exchangeTimezoneShortName", "city", "phone",
                                  "country", 'fullTimeEmployees', "website", "industry",
                                  'longBusinessSummary']
    out = {v: company_info[v] for v in company_information_layout if v in company_info}
    return out


if option == '🏠 Home':
    st.title('🏠 Welcome!')
    st.markdown("## Thank you for taking the time to look through my work. ##")

    home_about_project, home_about_others = st.columns(2)

    with home_about_project.expander("🔖 My Coding Journey"):
        st.markdown("### Hi, my name is Alejandro Castro.")
        st.write("""Over the past couple of years, I started to learn how to code over a personal interest I had in 
        the stock market. My first script was a web scraper that collects the real-time stock price from Yahoo 
        Finance, utilizing BeautifulSoup & Requests as the two libraries. I have also developed multiple projects 
        that allowed me to explore libraries such as; Numpy, Pandas, Talib, Concurrent.futures, Plotly, Matplotlib, 
        Datetime, Time, Logging, and a few APIs. I have developed scripts to request historical data for over ten 
        years of stock price movement from APIs and lowered the total time of execution from a standard for-loop 
        taking 7-8 hours to only taking a maximum of 30-45 minutes using the Concurrent.futures. I would then send 
        the data to a Local Docker Postgres Container that I developed, making the data more accessible for future 
        scripts. With that data, I would execute another script to run a calculation to identify stocks with 
        potential gains using Numpy, Pandas, and Talib. I also developed a trading bot to execute trades within the 
        market's open and close timeframe based on further tracking of the stocks in real-time. I believe, 
        with my experience as an analyst for over five years and these skillsets, I am ready for the next step in my 
        journey.""")

        st.markdown('###### Linkedin: www.linkedin.com/in/alejandro-castro-0938101a9')
        st.markdown('###### Email: Castro.alejandro1808@gmail.com',)
        with open("Alejandro Castro Resume 2022.pdf", "rb") as file:
            btn = st.download_button(
                label="Download my Resume",
                data=file,
                file_name="Alejandro Castro Resume 2022.pdf",
                mime="application/octet-stream"
            )

    with home_about_others.expander("🔖 About My Portfolio"):
        st.markdown("### The Dashboard")
        st.write("""The following project consists of three tabs that enable the user to comprehend a company and its 
        historical performance, learn which companies are frequently mentioned in forums, and identify which stocks 
        fit a specific trend pattern. The main script runs a series of functions that connect to a Postgres Container 
        and run cursor.execute from the psycopg2.extras library to obtain data from multiple SQL queries. These 
        functions use SQL coding to select, filter, and extract the data for each tab to utilize and transform as 
        needed. These queries were developed and fed from other scripts I have. However, if you are interested in 
        this script, you may find it using the link below. Aside from the functions, data transformation, 
        and calculations, I used the library Plotly to display some of the charts you will find along the tabs. 
         """)

    st.markdown("#### Disclaimer: This portfolio is not meant to be used as real financial or investment advice.")

    with st.expander('Raw code'):
        st.code('''
import pandas as pd
import plotly.graph_objects as go
import psycopg2.extras
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Advance Trading Bot",
    page_icon=":rocket:",
    layout="wide",
    initial_sidebar_state="expanded", )

option = st.sidebar.selectbox('What would you like to do?',
                              ['🏠 Home', '🔎 Search for Stocks', '🚀 Wallstreetbets', '📈 Trending'])

st.sidebar.text_area(label="Notes", placeholder="Please feel free to use the following text area for note taking.")


# Passing secret variables to connect to the Database
def init_connection():
    return psycopg2.connect(**st.secrets["wbets"])


connection = init_connection()
cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)


# Tab 🔎 Search for Stocks
# Function to fetch the historical dataset for selected stock
@st.experimental_memo(ttl=86400, show_spinner=True)
def get_data_search(ticker):
    data_full_set = cursor.execute("""
                select date(date) as date, open, high, low, close
                from data_stocks_daily
                where symbol = %s
                and date(date) > current_date - interval '%s day'
                order by date asc""", (ticker.upper(), 3650,))

    columns = [col[0] for col in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return rows


# Tab 🚀 Wallstreetbets
# Function to fetch a query with the count of mentions for each stock, grouped by stock
@st.experimental_memo(ttl=86400, show_spinner=True)
def get_data_wsbt(num_of_days):
    cursor.execute("""
                    SELECT COUNT(*) AS num_mentions, symbol, name, MAX(dt) AS dt
                    FROM mention JOIN stock ON stock.id = mention.stock_id
                    WHERE date(dt) > (SELECT MAX(date(dt)) FROM mention) - interval '%s day'
                    GROUP BY stock_id, symbol, name         
                    ORDER BY num_mentions DESC
                    """, (num_of_days,))
    columns = [col[0] for col in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return rows


# Tab 🚀 Wallstreetbets
# Function to fetch a query with all the data within the mentions query, sorted by the date field
@st.experimental_memo(ttl=86400, show_spinner=True)
def get_dict_wsb():
    cursor.execute("""
                SELECT symbol, message, url, dt, author
                FROM mention JOIN stock ON stock.id = mention.stock_id
                ORDER BY dt DESC
            """)
    mentions_data_dict = cursor.fetchall()
    return mentions_data_dict


mentions = get_dict_wsb()


# Tab 📈 Trending
# Function that runs through the historical data and selects stocks based on a calculations known as a breakout trend.
@st.experimental_memo(ttl=86400, show_spinner=True)
def get_trending_stock(trending_num_days):
    cursor.execute(f""" SELECT * FROM ( SELECT date, open, close, symbol, lAG(close, 1) OVER ( ORDER BY date) 
    previous_close, LAG(open, 1) OVER ( ORDER BY date) previous_open FROM data_stocks_daily ) a 
    WHERE date(date) > (SELECT MAX(date(date)) FROM data_stocks_daily) - interval '%s day' 
    AND previous_close < previous_open AND close > previous_open 
    AND open < previous_close""", (trending_num_days,))
    rows_engulfing = cursor.fetchall()
    return rows_engulfing


# Tab 🔎 Search for Stocks
# Convert Dataframe to csv for users to be able to download
@st.experimental_memo(ttl=86400, show_spinner=True)
def convert_df(data_set_for_download):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return data_set_for_download.to_csv().encode('utf-8')


# Tab 🔎 Search for Stocks
# Function to obtain a list of the symbols that have at least 4 years of historical data, for the user to be able to 
# filter through in the tab 
@st.experimental_memo(ttl=86400, show_spinner=True)
def get_symbol_list():
    data_full_set = cursor.execute("""
                select symbol
                FROM data_stocks_daily
                WHERE char_length(data_stocks_daily.symbol) < 5
                GROUP BY data_stocks_daily.symbol
                HAVING COUNT(data_stocks_daily.index) > 1460
                """)

    list_symbols_data = cursor.fetchall()
    return list_symbols_data


symbols_list_comp = []
list_symbols = get_symbol_list()

for row in list_symbols:
    symbols_list_comp.append(row['symbol'])
    
symbols_list_comp.sort()


# Tab 🔎 Search for Stocks
# Function that runs an API request to obtain the information for a company
# with that it is paired with preselected fields to display, limiting the information for the tab. 
# And a iterations to match both the API results with the preselected fields
@st.experimental_memo(ttl=86400, show_spinner=True)
def yahoo_company_info(ticker):
    symbol_info_company = yf.Ticker(ticker)
    company_info = symbol_info_company.info
    company_information_layout = ["longName", "symbol", "quoteType", "sector", "market", "exchange",
                                  "exchangeTimezoneName", "exchangeTimezoneShortName", "city", "phone",
                                  "country", 'fullTimeEmployees', "website", "industry",
                                  'longBusinessSummary']
    out = {v: company_info[v] for v in company_information_layout if v in company_info}
    return out


if option == '🏠 Home':
    st.title('🏠 Welcome!')
    st.markdown("## Thank you for taking the time to look through my work. ##")

    home_about_project, home_about_others = st.columns(2)

    with home_about_project.expander("🔖 My Coding Journey"):
        st.markdown("### Hi, my name is Alejandro Castro.")
        st.write("""Over the past couple of years, I started to learn how to code over a personal interest I had in 
        the stock market. My first script was a web scraper that collects the real-time stock price from Yahoo 
        Finance, utilizing BeautifulSoup & Requests as the two libraries. I have also developed multiple projects 
        that allowed me to explore libraries such as; Numpy, Pandas, Talib, Concurrent.futures, Plotly, Matplotlib, 
        Datetime, Time, Logging, and a few APIs. I have developed scripts to request historical data for over ten 
        years of stock price movement from APIs and lowered the total time of execution from a standard for-loop 
        taking 7-8 hours to only taking a maximum of 30-45 minutes using the Concurrent.futures. I would then send 
        the data to a Local Docker Postgres Container that I developed, making the data more accessible for future 
        scripts. With that data, I would execute another script to run a calculation to identify stocks with 
        potential gains using Numpy, Pandas, and Talib. I also developed a trading bot to execute trades within the 
        market's open and close timeframe based on further tracking of the stocks in real-time. I believe, 
        with my experience as an analyst for over five years and these skillsets, I am ready for the next step in my 
        journey.""")

    with home_about_others.expander("🔖 About My Portfolio"):
        st.markdown("### The Dashboard")
        st.write("""The following project consists of three tabs that enable the user to comprehend a company and its 
        historical performance, learn which companies are frequently mentioned in forums, and identify which stocks 
        fit a specific trend pattern. The main script runs a series of functions that connect to a Postgres Container 
        and run cursor.execute from the psycopg2.extras library to obtain data from multiple SQL queries. These 
        functions use SQL coding to select, filter, and extract the data for each tab to utilize and transform as 
        needed. These queries were developed and fed from other scripts I have. However, if you are interested in 
        this script, you may find it using the link below. Aside from the functions, data transformation, 
        and calculations, I used the library Plotly to display some of the charts you will find along the tabs. 
         """)

    st.markdown("#### Disclaimer: This portfolio is not meant to be used as real financial or investment advice.")

    with st.expander('Raw code'):
        st.code(language='python')

if option == '🔎 Search for Stocks':
    # Title and container for stock information in the Title
    title_search_stock, company_name_title, stock_search_stock = st.columns([.8, 3, .5])
    title_search_stock.title("🔎 Data for:")

    # Stock's Symbol selection box on side panel
    symbol = st.sidebar.selectbox(label="Symbols", options=symbols_list_comp)

    # Timeframe Option
    timeframe_for_data = st.selectbox('Timescale', ('Year', 'Month', 'Week', 'Day'), )

    # Stock Symbol
    stock_search_stock.title(f"__${symbol.upper()}__")

    # Yahoo Finance API call for company's information to match with preselected values under company_information_layout
    out = yahoo_company_info(symbol)

    company_name_filtered = out['longName']
    company_name_title.title(f"__{company_name_filtered}__")

    # About this tab & Company information expandable blocks
    about_this_tab, about_company_information = st.columns([3, 3])
    a = "🔖 Company Information"
    b = "🔖 About this tab"
    with about_this_tab.expander(b):
        st.write("""The 🔎 Search for Stocks tab fetches two SQL queries using two functions. The first function 
        executes a query to account for all the Stock Symbols available in the data set for the user to filter 
        through in the side panel. The second function uses the Stock Symbol as an argument to fetch the stock's 
        historical data set for over ten years. The dataset is placed into a pandas DataFrame for the graphs below. 
        Another feature for this tab is the Timescale selection box at the top of the page, which allows the user to 
        decide whether to aggregate the data by year, month, week, or daily for the analysis. For this feature, 
        I ran an if statement to change the date format of the DateTime column to the timescale the user selected. On 
        the side panel, you can decide how far back you would like to review the data. Further down, I calculate the 
        percentage of change in the DataFrame for the histogram to understand the distribution of a historical data 
        set and it's percent of change over time. The Company Information section is acquired through an API call 
        using the YFinance Library. The output is placed into a dictionary and then matched with specific labels to 
        only display limited information for the company, effectively choosing what to display instead of displaying 
        all of the output.""")
    with about_company_information.expander(a):
        hello = [st.write(f"**{i}:**", out[i]) for i in out]

    # Yahoo Finance links
    url1, url2 = st.columns([4, 2])
    url1_text = f"https://finance.yahoo.com/chart/{symbol.upper()}"
    url2_text = f"https://finance.yahoo.com/quote/{symbol.upper()}"
    url2.write(f"**Yahoo Stock Info link: {url2_text}**")
    url1.write(f"**Yahoo Stock Chart link: {url1_text}**")

    # Bring in Data from Function into a Dataframe

    df = pd.DataFrame(get_data_search(symbol))
    df['date'] = pd.to_datetime(df['date'].astype(str))
    df['open'] = pd.to_numeric(df['open'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['close'] = pd.to_numeric(df['close'])

    # Depending on the User selection for timeframe, apply the following logic
    if timeframe_for_data == 'Week':
        df = df.groupby(df.date.dt.strftime('%Y-W%U')).agg(
            {'open': 'first', 'close': 'last', 'low': 'min', 'high': 'max'}).reset_index()
        df['percent_change'] = ((df['close'] - df['open']) / df['open'])
    elif timeframe_for_data == 'Month':
        df = df.groupby(df.date.dt.strftime('%Y-%m')).agg(
            {'open': 'first', 'close': 'last', 'low': 'min', 'high': 'max'}).reset_index()
        df['percent_change'] = ((df['close'] - df['open']) / df['open'])
    elif timeframe_for_data == 'Year':
        df = df.groupby(df.date.dt.strftime('%Y')).agg(
            {'open': 'first', 'close': 'last', 'low': 'min', 'high': 'max'}).reset_index()
        df['percent_change'] = ((df['close'] - df['open']) / df['open'])
    elif timeframe_for_data == 'Day':
        df['percent_change'] = ((df['close'] - df['open']) / df['open'])
        date_time = df['date'].dt.strftime('%d/%m/%Y')

    # Slider to control date range for data analysis
    data_days = st.sidebar.slider(f'Number of {timeframe_for_data}s', min_value=1, max_value=len(df.index),
                                  value=len(df.index))
    df = df.tail(data_days)

    # Cleaning up some of the date texts in case it displays time as well
    df['date'] = df['date'].astype(str).str[:10]

    # Candlestick chart
    fig = go.Figure(data=[go.Candlestick(x=df['date'],
                                         open=df['open'],
                                         high=df['high'],
                                         low=df['low'],
                                         close=df['close'],
                                         name=symbol)])
    fig.update_xaxes(type='category')
    fig.update_layout(height=700, title_text=f"Candlestick Chart by {timeframe_for_data} for {symbol.upper()}",
                      xaxis_title_text=f'{timeframe_for_data}s')
    st.plotly_chart(fig, use_container_width=True)

    # Information about the probability chart coming up
    displo_header = st.header("**Histogram for Probability**")
    with st.expander("🔖 Information"):
        displo_subheader1 = st.write('The area of each bar corresponds to the probability that an '
                                     'event will fall with respect to the total number of sample points. '
                                     'the value in this graph is the "percent_change" from the DataFrame '
                                     ', which can be exported into CSV.')
        displo_subheader2 = st.write('**Example on how to read graph:**')
        displo_write1 = st.write(
            '***(-1 - -.03*** **<-** these numbers represent the percentage of change through the giving time, '
            'grouped based on the probability of that event historically. **Multiply the percentage of change by 100 '
            'to get %.**')
        displo_write2 = st.write(
            '***, .03124)*** **<-** this number represent the probability of that event historically. '
            ' **Multiply this number by 100 to get the probability in %.**')

    # Dataset is cleaned up for Probability chart
    df['percent_change'] = pd.to_numeric(df['percent_change'], errors='coerce')
    df['percent_change'] = round(df['percent_change'], 2)
    list1 = [list(df['percent_change'].values)]
    group_labels = ['percent_change']  # name of the dataset
    df = round(df, 3)

    # Color for Probability chart
    color = st.color_picker('Pick A Color')
    colors = '#622E2E'
    colors2 = color

    # Probability chart
    fig1 = go.Figure(
        data=[go.Histogram(x=df['percent_change'], histnorm='probability', marker_color=colors2, autobinx=True)])
    fig1.update_xaxes()
    fig1.update_layout(height=700)
    fig1.update_layout(title_text=f"Probability Graph for {symbol.upper()}", bargap=0.02,
                       bargroupgap=0.02, xaxis_title_text='% Change', yaxis_title_text='% Probability')
    st.plotly_chart(fig1, use_container_width=True)

    # Fillers used to display dataframe and download link in the middle
    filler_5, dataframe_Title, filler_6 = st.columns([2.28, 2, 1])
    filler_3, dataframe_search, filler_4 = st.columns([1.1, 2, 1])
    filler_1, link_dataset_search, filler_2 = st.columns([2.33, 2, 1])

    dataframe_Title.subheader("Historic Dataset")
    dataframe_search.dataframe(df, width=1000)
    csv = convert_df(df)

    link_dataset_search.download_button(
        label="Download data as CSV",
        data=csv,
        file_name=f'Historic Dataset for {symbol.upper()}.csv',
        mime='text/csv',
    )

if option == '🚀 Wallstreetbets':
    # Title
    st.title(option)

    filler_wsbt_1, wsbt_about_tab, filler_wsbt_2 = st.columns([.3, 5.6, .6])
    with wsbt_about_tab.expander("🔖 About this tab"):
        st.write("""The 🚀 Wallstreetbets tab fetches a SQL query using two distinct functions. Similar to the 🔎 
        Search for Stocks, the first function executes a query to account for all the Stock Symbols available in the 
        data set for the user to filter through in the side panel as well as the count of times a particular stock 
        was mentioned in the Reddit forum. The data is then placed into a graph depicting the most mentioned stock 
        out of the all the other stocks. The second function fetches another set of data that contains the reddit 
        post, Stock symbol, author, and the url. This data set is then placed into an iteration that unpacks the 
        posts based on the symbol that was selected. If no symbol was selected the iterations unpacks 100 recent 
        posts.""")

    # Slider input that gets placed into the get_data_wsbt function that does a SQL call/
    # filter how many days to look back to in the dataset for Wallstreetbets Query
    num_days = st.sidebar.slider('Number of days', 1, 30, 15)
    dataframe_wsbt_fullset = pd.DataFrame(get_data_wsbt(num_days))

    # List of all the stock symbols to run a len function to ensure only a certain number of symbols get through
    max_count_symbol_wsbt = dataframe_wsbt_fullset.symbol.unique()

    # Keep only the top 15 stocks mentioned in the reddit post for data analysis and research.
    # By count of mentions
    if len(max_count_symbol_wsbt) > 15:
        dataframe_wsbt_fullset = dataframe_wsbt_fullset[:15]
    else:
        pass

    # List of all the stock symbols found in the filtered query
    list_wsbt_symbols_df = dataframe_wsbt_fullset.symbol.unique()
    list_wsbt_symbols_df.sort()

    # Added this line to ensure user can see full list of stocks in the bar chart
    # Once user selects a symbol the chart and list of mentions gets filtered
    list_wsbt_symbols_df[0] = ""
    symbol_wsbt = st.sidebar.selectbox(label="Symbols",
                                       options=list_wsbt_symbols_df,
                                       key="WSTB_Symbol")

    # When the user selects a particular stock the lambda will call all the mentions of that stock.
    # mentions = get_dict_wsb() is the line we used earlier to call the function.
    if symbol_wsbt != "":
        dataframe_wsbt_fullset = dataframe_wsbt_fullset[dataframe_wsbt_fullset['symbol'] == symbol_wsbt]
        mentioned_t = list(filter(lambda x: x[0] == symbol_wsbt, mentions))
    else:
        mentioned_t = mentions

    # Color for the bar graph
    colors = ['lightslategray', ] * 100

    # Color for the the stock symbol with most counts of mentions
    colors[0] = 'crimson'

    # Plotly bar graph
    # list comprehension to put both the Symbol and Name in the X field in a formatted string
    fig = go.Figure(data=[go.Bar(x=(["%s<br>%s" % (l, w) for l, w in zip(dataframe_wsbt_fullset['symbol'],
                                                                         dataframe_wsbt_fullset['name'])]),
                                 y=dataframe_wsbt_fullset['num_mentions'], marker_color=colors,
                                 text=dataframe_wsbt_fullset['num_mentions'], textposition='auto', hovertext="  ",
                                 textfont=dict(family="sans serif", color="white", size=16))])
    fig.update_layout(
        title_text="Top Stocks Mentioned in WSBT")
    st.plotly_chart(fig, use_container_width=True)

    # for loop to unpack the mentions from reddit post. limit up to 100
    for mention in mentioned_t[:100]:
        st.subheader(mention['symbol'])
        st.text(mention['dt'])
        st.text(mention['author'])
        st.text(mention['message'])
        st.text(mention['url'])

if option == '📈 Trending':
    # Title
    st.title(option)

    wsbt_trend_tab, filler_trend_2 = st.columns([5.6, 3.3])
    with wsbt_trend_tab.expander("🔖 About this tab"):
        st.write("""The 📈 Trending tab fetches a SQL query using a functions. The function runs through the data and 
        calculates the stocks that appear to be trending in a particular timeframe. The selection of the number of 
        days is the input argument for this function. And the calculation don is a standard break out pattern ran 
        through a SQL code within the function.""")

    # Number of days slider to tell the function get_trending_stock() how far back to analyze the data to find matches
    num_days = st.sidebar.slider('Number of days', 1, 7, 2)
    rows = get_trending_stock(num_days)

    # List that will be populated with symbols that return from the function get_trending_stock()
    symbols_filtered = [""]

    # For loop to unpack the symbols from the function and append them to the list above
    for row in rows:
        symbols_filtered.append(row['symbol'])

    # Select box that is populated with the list of symbols that were appended in the for Loop
    symbol_selected = st.sidebar.selectbox(label="Symbols", options=symbols_filtered, )

    # IF statement use to determine
    # IF there is a symbol selected from the Selectbox to only show the graph for that symbol
    # IF not then show all the symbols that matched the SQL results
    if symbol_selected == '':
        for row in rows:
            st.image(f"https://finviz.com/chart.ashx?t={row['symbol']}")
    else:
        st.image(f"https://finviz.com/chart.ashx?t={symbol_selected}")

        ''',
                language='python')

if option == '🔎 Search for Stocks':
    # Title and container for stock information in the Title
    title_search_stock, company_name_title, stock_search_stock = st.columns([.8, 3, .5])
    title_search_stock.title("🔎 Data for:")

    # Stock's Symbol selection box on side panel
    symbol = st.sidebar.selectbox(label="Symbols", options=symbols_list_comp)

    # Timeframe Option
    timeframe_for_data = st.selectbox('Timescale', ('Year', 'Month', 'Week', 'Day'), )

    # Stock Symbol
    stock_search_stock.title(f"__${symbol.upper()}__")

    # Yahoo Finance API call for company's information to match with preselected values under company_information_layout
    out = yahoo_company_info(symbol)

    company_name_filtered = out['longName']
    company_name_title.title(f"__{company_name_filtered}__")

    # About this tab & Company information expandable blocks
    about_this_tab, about_company_information = st.columns([3, 3])
    a = "🔖 Company Information"
    b = "🔖 About this tab"
    with about_this_tab.expander(b):
        st.write("""The 🔎 Search for Stocks tab fetches two SQL queries using two functions. The first function 
        executes a query to account for all the Stock Symbols available in the data set for the user to filter 
        through in the side panel. The second function uses the Stock Symbol as an argument to fetch the stock's 
        historical data set for over ten years. The dataset is placed into a pandas DataFrame for the graphs below. 
        Another feature for this tab is the Timescale selection box at the top of the page, which allows the user to 
        decide whether to aggregate the data by year, month, week, or daily for the analysis. For this feature, 
        I ran an if statement to change the date format of the DateTime column to the timescale the user selected. On 
        the side panel, you can decide how far back you would like to review the data. Further down, I calculate the 
        percentage of change in the DataFrame for the histogram to understand the distribution of a historical data 
        set and its percent of change over time. The Company Information section is acquired through an API call 
        using the YFinance Library. The output is placed into a dictionary and then matched with specific labels to 
        only display limited information for the company, effectively choosing what to show instead of displaying 
        all of the output.""")
    with about_company_information.expander(a):
        hello = [st.write(f"**{i}:**", out[i]) for i in out]

    # Yahoo Finance links
    url1, url2 = st.columns([4, 2])
    url1_text = f"https://finance.yahoo.com/chart/{symbol.upper()}"
    url2_text = f"https://finance.yahoo.com/quote/{symbol.upper()}"
    url2.write(f"**Yahoo Stock Info link: {url2_text}**")
    url1.write(f"**Yahoo Stock Chart link: {url1_text}**")

    # Bring in Data from Function into a Dataframe

    df = pd.DataFrame(get_data_search(symbol))
    df['date'] = pd.to_datetime(df['date'].astype(str))
    df['open'] = pd.to_numeric(df['open'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['close'] = pd.to_numeric(df['close'])

    # Depending on the User selection for timeframe, apply the following logic
    if timeframe_for_data == 'Week':
        df = df.groupby(df.date.dt.strftime('%Y-W%U')).agg(
            {'open': 'first', 'close': 'last', 'low': 'min', 'high': 'max'}).reset_index()
        df['percent_change'] = ((df['close'] - df['open']) / df['open'])
    elif timeframe_for_data == 'Month':
        df = df.groupby(df.date.dt.strftime('%Y-%m')).agg(
            {'open': 'first', 'close': 'last', 'low': 'min', 'high': 'max'}).reset_index()
        df['percent_change'] = ((df['close'] - df['open']) / df['open'])
    elif timeframe_for_data == 'Year':
        df = df.groupby(df.date.dt.strftime('%Y')).agg(
            {'open': 'first', 'close': 'last', 'low': 'min', 'high': 'max'}).reset_index()
        df['percent_change'] = ((df['close'] - df['open']) / df['open'])
    elif timeframe_for_data == 'Day':
        df['percent_change'] = ((df['close'] - df['open']) / df['open'])
        date_time = df['date'].dt.strftime('%d/%m/%Y')

    # Slider to control date range for data analysis
    data_days = st.sidebar.slider(f'Number of {timeframe_for_data}s', min_value=1, max_value=len(df.index),
                                  value=len(df.index))
    df = df.tail(data_days)

    # Cleaning up some of the date texts in case it displays time as well
    df['date'] = df['date'].astype(str).str[:10]

    # Candlestick chart
    fig = go.Figure(data=[go.Candlestick(x=df['date'],
                                         open=df['open'],
                                         high=df['high'],
                                         low=df['low'],
                                         close=df['close'],
                                         name=symbol)])
    fig.update_xaxes(type='category')
    fig.update_layout(height=700, title_text=f"Candlestick Chart by {timeframe_for_data} for {symbol.upper()}",
                      xaxis_title_text=f'{timeframe_for_data}s')
    st.plotly_chart(fig, use_container_width=True)

    # Information about the probability chart coming up
    displo_header = st.header("**Histogram for Probability**")
    with st.expander("🔖 Information"):
        displo_subheader1 = st.write('The area of each bar corresponds to the probability that an '
                                     'event will fall with respect to the total number of sample points. '
                                     'the value in this graph is the "percent_change" from the DataFrame '
                                     ', which can be exported into CSV.')
        displo_subheader2 = st.write('**Example on how to read graph:**')
        displo_write1 = st.write(
            '***(-1 - -.03*** **<-** these numbers represent the percentage of change through the giving time, '
            'grouped based on the probability of that event historically. **Multiply the percentage of change by 100 '
            'to get %.**')
        displo_write2 = st.write(
            '***, .03124)*** **<-** this number represent the probability of that event historically. '
            ' **Multiply this number by 100 to get the probability in %.**')

    # Dataset is cleaned up for Probability chart
    df['percent_change'] = pd.to_numeric(df['percent_change'], errors='coerce')
    df['percent_change'] = round(df['percent_change'], 2)
    list1 = [list(df['percent_change'].values)]
    group_labels = ['percent_change']  # name of the dataset
    df = round(df, 3)

    # Color for Probability chart
    color = st.color_picker('Pick A Color')
    colors = '#622E2E'
    colors2 = color

    # Probability chart
    fig1 = go.Figure(
        data=[go.Histogram(x=df['percent_change'], histnorm='probability', marker_color=colors2, autobinx=True)])
    fig1.update_xaxes()
    fig1.update_layout(height=700)
    fig1.update_layout(title_text=f"Probability Graph for {symbol.upper()}", bargap=0.02,
                       bargroupgap=0.02, xaxis_title_text='% Change', yaxis_title_text='% Probability')
    st.plotly_chart(fig1, use_container_width=True)

    # Fillers used to display dataframe and download link in the middle
    filler_5, dataframe_Title, filler_6 = st.columns([2.28, 2, 1])
    filler_3, dataframe_search, filler_4 = st.columns([1.1, 2, 1])
    filler_1, link_dataset_search, filler_2 = st.columns([2.33, 2, 1])

    dataframe_Title.subheader("Historic Dataset")
    dataframe_search.dataframe(df, width=1000)
    csv = convert_df(df)

    link_dataset_search.download_button(
        label="Download data as CSV",
        data=csv,
        file_name=f'Historic Dataset for {symbol.upper()}.csv',
        mime='text/csv',
    )

if option == '🚀 Wallstreetbets':
    # Title
    st.title(option)

    filler_wsbt_1, wsbt_about_tab, filler_wsbt_2 = st.columns([.3, 5.6, .6])
    with wsbt_about_tab.expander("🔖 About this tab"):
        st.write("""The 🚀 Wallstreetbets tab fetches a SQL query using two distinct functions. Similar to the 🔎 
        Search for Stocks the first function executes a query to account for all the Stock Symbols available in the 
        data set for the user to filter through in the side panel and the count of times a particular stock 
        was mentioned in the Reddit forum. The data is then placed into a graph depicting the most mentioned stock 
        out of all the other stocks. The second function fetches another set of data that contains the Reddit 
        post, Stock symbol, author, and URL. This data set is then placed into an iteration that unpack the 
        posts based on the symbol that was selected. If no symbol was selected the iterations unpacks 100 recent 
        posts.""")

    # Slider input that gets placed into the get_data_wsbt function that does a SQL call/
    # filter how many days to look back to in the dataset for Wallstreetbets Query
    num_days = st.sidebar.slider('Number of days', 1, 30, 15)
    dataframe_wsbt_fullset = pd.DataFrame(get_data_wsbt(num_days))

    # List of all the stock symbols to run a len function to ensure only a certain number of symbols get through
    max_count_symbol_wsbt = dataframe_wsbt_fullset.symbol.unique()

    # Keep only the top 15 stocks mentioned in the reddit post for data analysis and research.
    # By count of mentions
    if len(max_count_symbol_wsbt) > 15:
        dataframe_wsbt_fullset = dataframe_wsbt_fullset[:15]
    else:
        pass

    # List of all the stock symbols found in the filtered query
    list_wsbt_symbols_df = dataframe_wsbt_fullset.symbol.unique()
    list_wsbt_symbols_df.sort()

    # Added this line to ensure user can see full list of stocks in the bar chart
    # Once user selects a symbol the chart and list of mentions gets filtered
    list_wsbt_symbols_df[0] = ""
    symbol_wsbt = st.sidebar.selectbox(label="Symbols",
                                       options=list_wsbt_symbols_df,
                                       key="WSTB_Symbol")

    # When the user selects a particular stock the lambda will call all the mentions of that stock.
    # mentions = get_dict_wsb() is the line we used earlier to call the function.
    if symbol_wsbt != "":
        dataframe_wsbt_fullset = dataframe_wsbt_fullset[dataframe_wsbt_fullset['symbol'] == symbol_wsbt]
        mentioned_t = list(filter(lambda x: x[0] == symbol_wsbt, mentions))
    else:
        mentioned_t = mentions

    # Color for the bar graph
    colors = ['lightslategray', ] * 100

    # Color for the the stock symbol with most counts of mentions
    colors[0] = 'crimson'

    # Plotly bar graph
    # list comprehension to put both the Symbol and Name in the X field in a formatted string
    fig = go.Figure(data=[go.Bar(x=(["%s<br>%s" % (l, w) for l, w in zip(dataframe_wsbt_fullset['symbol'],
                                                                         dataframe_wsbt_fullset['name'])]),
                                 y=dataframe_wsbt_fullset['num_mentions'], marker_color=colors,
                                 text=dataframe_wsbt_fullset['num_mentions'], textposition='auto', hovertext="  ",
                                 textfont=dict(family="sans serif", color="white", size=16))])
    fig.update_layout(
        title_text="Top Stocks Mentioned in WSBT")
    st.plotly_chart(fig, use_container_width=True)

    # for loop to unpack the mentions from reddit post. limit up to 100
    for mention in mentioned_t[:100]:
        st.subheader(mention['symbol'])
        st.text(mention['dt'])
        st.text(mention['author'])
        st.text(mention['message'])
        st.text(mention['url'])

if option == '📈 Trending':
    # Title
    st.title(option)

    wsbt_trend_tab, filler_trend_2 = st.columns([5.6, 3.3])
    with wsbt_trend_tab.expander("🔖 About this tab"):
        st.write("""The 📈 Trending tab fetches a SQL query using a function. The function runs through the data and 
        calculates the stocks that appear to be trending in a particular timeframe. The selection of the number of 
        days is the input argument for this function. The calculation done is a standard break-out pattern executed 
        through a SQL code within the function.""")

    # Number of days slider to tell the function get_trending_stock() how far back to analyze the data to find matches
    num_days = st.sidebar.slider('Number of days', 1, 7, 2)
    rows = get_trending_stock(num_days)

    # List that will be populated with symbols that return from the function get_trending_stock()
    symbols_filtered = [""]

    # For loop to unpack the symbols from the function and append them to the list above
    for row in rows:
        symbols_filtered.append(row['symbol'])

    # Select box that is populated with the list of symbols that were appended in the for Loop
    symbol_selected = st.sidebar.selectbox(label="Symbols", options=symbols_filtered, )

    # IF statement use to determine
    # IF there is a symbol selected from the Selectbox to only show the graph for that symbol
    # IF not then show all the symbols that matched the SQL results
    if symbol_selected == '':
        for row in rows:
            st.image(f"https://finviz.com/chart.ashx?t={row['symbol']}")
    else:
        st.image(f"https://finviz.com/chart.ashx?t={symbol_selected}")
