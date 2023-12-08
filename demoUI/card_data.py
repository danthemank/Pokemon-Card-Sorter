import requests
from pprint import pprint
import sqlite3
import json
import datetime
import os
from demoUI.settings import settings 
import asyncio
import aiohttp
import aiofiles
import csv
import shutil

#Pokémon TCG API Developer Portal
#pokemontcg.io
#Manage Your Account
#API Key
api_endpoint = "https://api.pokemontcg.io/v2"
api_key = "12dc0a63-8b44-4836-87c6-59e592827a50"

database_file=settings['database_file']
image_base_folder=settings['reference_image_path']
 
class card_data:
   
    ############################################################test methods
    @classmethod
    def get_card_test(cls):
        print(datetime.datetime.now())
        card_code = "swsh4-22"
        print(f'get_card: {card_code}')
        data= cls.get_card(card_code)
        #pprint(data)
        print(data['name'])
        print(data['images']['large'])
        print()
    
    @classmethod
    def get_all_card_sets2(cls):
        try:
            url = f"{api_endpoint}/sets"
            response = requests.get(url)
            cls.save_api_call(url, response)
            if response.status_code == 200:
                data = response.json()
                pprint(data)
                #return data['data']
            else:
                print("Request failed with status code:", response.status_code)
        except Exception as error:
            print("Request failed with error:", error)
        return None
   
    @classmethod
    def get_card_from_database(cls):
        try:
            sqlite_connection = sqlite3.connect(database_file)
            sqlite_connection.row_factory = sqlite3.Row
            sql_cursor = sqlite_connection.cursor()
    
            sql = "SELECT * FROM api_calls"
            sql_cursor.execute(sql)
            records = sql_cursor.fetchall()
            for row in records:
                card =json.loads(row['response'])
                print(card['data']['name']);
                #pprint(json.loads(row[4]))
                print()
        except Exception as error:
            print("Failed to retrieve data", error)
    
    def get_all_sets_from_database():
        try:
            sqlite_connection = sqlite3.connect(database_file)
            sqlite_connection.row_factory = sqlite3.Row
    
            sql_cursor = sqlite_connection.cursor()
            sql = "delete from sets;"
            sql_cursor.execute(sql)
            sqlite_connection.commit()
    
            sql = "SELECT * FROM api_calls where request like '%/sets'"
            sql_cursor.execute(sql)
            row = sql_cursor.fetchone()
            sets =json.loads(row['response'])
            #pprint(sets['data'][0:5]);
    
            for cset in sets['data']:
                sql_cursor = sqlite_connection.cursor()
                sql = "INSERT INTO sets (code, name, printedTotal, total, updatedAt, json) VALUES (?, ?, ?, ?, ?, ?)"
                sql_values = (
                        cset['id'],
                        cset['name'],
                        cset['printedTotal'],
                        cset['total'],
                        cset['updatedAt'],
                        json.dumps(cset)
                        )
                sql_cursor.execute(sql, sql_values)
                sqlite_connection.commit()
        except Exception as error:
            print(error)
            print("Failed to retrieve data", error)
    #################end test methods
    
    @classmethod
    def save_api_call(cls, request, response):
        try:
            sqlite_connection = sqlite3.connect(database_file)
            sql_cursor = sqlite_connection.cursor()
    
            sql = "INSERT INTO api_calls (request, status, response) VALUES (?, ?, ?)"
            sql_values = (request, response.status_code, response.content)
    
            sql_cursor.execute(sql, sql_values)
            sqlite_connection.commit()
        except Exception as error:
            print("Failed to insert data into sqlite table", error)
            print(request)
            print(response)
    
    @classmethod
    def insert_missing_cards(cls, debug=False):
        try:
            sqlite_connection = sqlite3.connect(database_file)
            sql_cursor = sqlite_connection.cursor()

            sql = "delete from cards where card_number = '-1'"
            sql_cursor.execute(sql)
            sqlite_connection.commit()
 
            #read cards for a csv file
            cards = []
            missing_cards_file = settings['missing_cards_file']
            with open(missing_cards_file, newline='') as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';', quotechar='"')
                for row in reader:
                    #print(row)
                    json_row = {
                        'set': {
                            'id': row['set_code'],
                            },
                        'id': row['code'],
                        'name': row['name'],
                        'number': row['number'],
                        'cardmarket': {
                            'prices':{
                                'averageSellPrice': row['averageSellPrice'],
                                'trendPrice': row['trendPrice'],
                                },
                            'updatedAt': row['updatedAt'],
                            },
                        'images': {
                            'small': row['image_url'],
                            'large': row['image_url'],
                            },
                        }
                    cards.append(json_row)
            #print(cards)

            for card in cards:
                #sql = """INSERT INTO cards (json, set_code, code, name, card_number, artist, flavorText, supertype, rarity, averageSellPrice, trendPrice, updatedAt) 
                sql = """INSERT INTO cards (json, set_code, code, name, card_number, averageSellPrice, trendPrice, updatedAt) 
                VALUES (?,?,?,?,?,?,?,?)"""
                sql_values = (
                        json.dumps(card)
                        ,card['set']['id']
                        ,card['id']
                        ,card['name']
                        ,card['number']
                        #,card['artist'] if 'artist' in card else ''
                        #,card['flavorText'] if 'flavorText' in card else ''
                        #,card['supertype'] if 'supertype' in card else ''
                        #,card['rarity'] if 'rarity' in card else '
                        ,card['cardmarket']['prices']['averageSellPrice'] 
                        ,card['cardmarket']['prices']['trendPrice'] 
                        ,card['cardmarket']['updatedAt']
                        #,card['cardmarket']['prices']['averageSellPrice'] if 'cardmarket' in card and 'prices' in card['cardmarket'] and 'averageSellPrice' in card['cardmarket']['prices'] else ''
                        #,card['cardmarket']['prices']['trendPrice'] if 'cardmarket' in card and 'prices' in card['cardmarket'] and 'trendPrice' in card['cardmarket']['prices'] else ''
                        #,card['cardmarket']['updatedAt'] if 'cardmarket' in card and 'updatedAt' in card['cardmarket'] else ''
                        )

                sql_cursor.execute(sql, sql_values)
                sqlite_connection.commit()

        except Exception as error:
            print("Failed to insert missing cards", error)


    @classmethod
    def get_all_cards_for_each_set(cls, debug=False, sets=None):
        try:
            sqlite_connection = sqlite3.connect(database_file)
            sqlite_connection.row_factory = sqlite3.Row
            sql_cursor = sqlite_connection.cursor()
    
            if sets:
                sql = "select * from sets where code in ({})".format(','.join('?' for _ in sets))
                sql_values = sets
                sql_cursor.execute(sql, sql_values)
            else:
                sql = "select * from sets;"
                sql_cursor.execute(sql)
            records = sql_cursor.fetchall()
            i=0
            number_of_sets = len(records)
            print()
            for row in records:
                i+=1
                if debug and i > 4:
                    print("debug mode, only retrieving 4 sets")
                    break
                print(f"\rretrieving cards for set: {row['code']}  {i} of {number_of_sets}               ", end="");
                cls.get_cards_from_set(row['code'])
            print()
        except Exception as error:
            print("Failed to retrieve data", error)
    
    @classmethod
    def get_all_card_sets(cls, debug=False):
        try:
            print("retrieving all card sets");
            url = f"{api_endpoint}/sets"
            response = requests.get(url)
            cls.save_api_call(url, response)
            if response.status_code == 200:
                sets = response.json()
                #pprint(sets['data'][0:5]);
    
                sqlite_connection = sqlite3.connect(database_file)
                sqlite_connection.row_factory = sqlite3.Row
                sql_cursor = sqlite_connection.cursor()
    
                sql = "INSERT INTO sets (code, name, printedTotal, total, updatedAt, json) VALUES (?, ?, ?, ?, ?, ?)"
                i = 0
                for cset in sets['data']:
                    i += 1
                    if debug and i>4:
                        print("debug mode, only processing 4 sets")
                        break
                    sql_values = (
                            cset['id'],
                            cset['name'],
                            cset['printedTotal'],
                            cset['total'],
                            cset['updatedAt'],
                            json.dumps(cset)
                            )
                    sql_cursor.execute(sql, sql_values)
                    sqlite_connection.commit()
            else:
                print("Request failed with status code:", response.status_code)
        except Exception as error:
            print("Failed to retrieve data", error)
    
    @classmethod
    def get_cards_from_set(cls, set_code):
        try:
            current_count=0
            total_count=100
            current_page=0
            while current_count < total_count:
                current_page += 1
                #url = f"{api_endpoint}/cards?q=set.name:generations subtypes:mega
                #url = f"{api_endpoint}/cards?q=set.id:{set_code}"
                url = f"{api_endpoint}/cards?q=set.id:{set_code}&page={current_page}"
                response = requests.get(url)
                cls.save_api_call(url, response)
                if response.status_code == 200:
                    data = response.json()
                    #pprint(data)
        
                    cards = data
                    current_count = current_count + cards['count']
                    print(f"Page {current_page}: {current_count} of {cards['totalCount']}           ",end="")
                    total_count = cards['totalCount']
                    sqlite_connection = sqlite3.connect(database_file)
                    for card in cards['data']:
                        sql_cursor = sqlite_connection.cursor()
                        sql = """INSERT INTO cards (json, set_code, code, name, card_number, artist, flavorText, supertype, rarity, averageSellPrice, trendPrice, updatedAt) 
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"""
                        sql_values = (
                                json.dumps(card)
                                ,card['set']['id']
                                ,card['id']
                                ,card['name']
                                ,card['number']
                                ,card['artist'] if 'artist' in card else ''
                                ,card['flavorText'] if 'flavorText' in card else ''
                                ,card['supertype'] if 'supertype' in card else ''
                                ,card['rarity'] if 'rarity' in card else ''
                                ,card['cardmarket']['prices']['averageSellPrice'] if 'cardmarket' in card and 'prices' in card['cardmarket'] and 'averageSellPrice' in card['cardmarket']['prices'] else ''
                                ,card['cardmarket']['prices']['trendPrice'] if 'cardmarket' in card and 'prices' in card['cardmarket'] and 'trendPrice' in card['cardmarket']['prices'] else ''
                                ,card['cardmarket']['updatedAt'] if 'cardmarket' in card and 'updatedAt' in card['cardmarket'] else ''
                                )
        
                        sql_cursor.execute(sql, sql_values)
                        sqlite_connection.commit()
                else:
                    print("Request failed with status code:", response.status_code)
            #end while
        except Exception as error:
            print("Request failed with error:", error)
        return None
    
    @classmethod
    def get_all_cards_images(cls, debug=False, full_size_images=False, condition=None):
        try:
            sqlite_connection = sqlite3.connect(database_file)
            sqlite_connection.row_factory = sqlite3.Row
            sql_cursor = sqlite_connection.cursor()
            sql = """select 
                    code,
                    set_code,
                    json_extract(cards.json, '$.images.small') as small,
                    json_extract(cards.json, '$.images.large') as large
                    from cards
                    """
            if condition:
                sql += "where " + condition

            sql_cursor.execute(sql)
            cards = sql_cursor.fetchall()
            i=0
            number_of_cards = len(cards)
            loop = asyncio.get_event_loop()
            tasks = []
            session = aiohttp.ClientSession()
            print()
            for card in cards:
                i+=1
                if debug and i>4:
                    print("Debug mode, only getting images for 4 cards")
                    break
                print(f"\rCard: {i} of {number_of_cards}               ",end="")
                message = f"Card: {i} of {number_of_cards}"
                task = asyncio.ensure_future(cls.get_card_image(card['code'], full_size_images, card, message, session))
                tasks.append(task)
            results = loop.run_until_complete(asyncio.gather(*tasks))
        except Exception as error:
            print("\nRequest failed with error:", error)
            raise error
    
    @classmethod
    async def get_card_image(cls, card_code, full_size_images=False, card=None, message=None, session=None):
        try:
            print("\rGetting image for card:", message, card_code, datetime.datetime.now(),end="")
            if card is None:
                sqlite_connection = sqlite3.connect(database_file)
                sqlite_connection.row_factory = sqlite3.Row
                sql_cursor = sqlite_connection.cursor()
                sql = """select 
                        code,
                        set_code,
                        json_extract(cards.json, '$.images.small') as small,
                        json_extract(cards.json, '$.images.large') as large
                        from cards
                        where code=?
                        limit 1"""
                sql_values = (card_code,)
                sql_cursor.execute(sql, sql_values)
                card = sql_cursor.fetchone()
            #print(dict(card))
            #create a folder for the set
            set_folder = os.path.join(image_base_folder, card['set_code'])
            if not os.path.exists(set_folder):
                os.makedirs(set_folder)
            #download the image
            if full_size_images:
                image_url = card['large']
            else:
                image_url = card['small']
            image_file = os.path.join(set_folder, card_code + '.png')
            if os.path.exists(image_file):
                print("\rImage already exists:", image_file, end="")
            elif image_url.startswith("missing/"):
                # Handle local file paths in URL format
                #local_path = image_url[len("file:///"):]
                missing_cards_file = settings["missing_cards_file"]
                local_path = os.path.join(os.path.dirname(missing_cards_file), image_url)
                shutil.copy(local_path, image_file)
            else:
                print(f"\rDownload: {image_url}",end="")
                async with session.get(image_url) as async_response:
                    #response = requests.get(image_url)
                    if async_response.status == 200:
                        f = await aiofiles.open(image_file, mode='wb')
                        await f.write(await async_response.read())
                        await f.close()
                        print("\rImage downloaded:", image_file, end="")
                    else:
                        print("\nRequest failed with status code:", async_response.status, image_url)
        except Exception as error:
            print("Request failed with error:", error)
        finally:
            #print("\rGetting image for card (completed):",message, card_code, datetime.datetime.now(),end="")
            pass
    
    @classmethod
    def clean_database(cls):
        try:
            print("Cleaning database...")
            sqlite_connection = sqlite3.connect(database_file)
            sql_cursor = sqlite_connection.cursor()
    
            sql = "delete from api_calls"
            sql_cursor.execute(sql)
            sqlite_connection.commit()
    
            sql = "delete from cards"
            sql_cursor.execute(sql)
            sqlite_connection.commit()
    
            sql = "delete from sets"
            sql_cursor.execute(sql)
            sqlite_connection.commit()

            sql = "vacuum"
            sql_cursor.execute(sql)
            sqlite_connection.commit()
        except Exception as error:
            print("Error cleaning database:", error)
    
    @classmethod
    def build_database(cls, debug=False, full_size_images=False, retrieve_images=False, update_database=True, add_missing_cards=False):
        if update_database:
            cls.clean_database()
            cls.get_all_card_sets(debug=False)
            cls.get_all_cards_for_each_set(debug=debug)
            cls.insert_missing_cards(debug=debug)
        if add_missing_cards:
            cls.insert_missing_cards(debug=debug)
            cls.get_all_cards_images(debug=debug, full_size_images=full_size_images, condition="card_number = '-1'")
        if retrieve_images:
            cls.insert_missing_cards(debug=debug)
            cls.get_all_cards_images(debug=debug, full_size_images=full_size_images)
    
    @classmethod
    def get_card(cls, card_code, is_online=False):
        try:
            print (f"Getting card {card_code}...")
            if is_online:
                url = f"{api_endpoint}/cards/{card_code}"
                response = requests.get(url)
                cls.save_api_call(url, response)
                if response.status_code == 200:
                    data = response.json()
                    #convert json data varable to dict
                    card_values = dict(data)
                    return card_values
                else:
                    print("Request failed with status code:", response.status_code)
            else:
                sqlite_connection = sqlite3.connect(database_file)
                sqlite_connection.row_factory = sqlite3.Row
                sql_cursor = sqlite_connection.cursor()
                sql = "select * from cards where code = ?"
                sql_cursor.execute(sql, (card_code,))
                card_values = sql_cursor.fetchone()
                if card_values is not None:
                    card_values = dict(card_values)
                    new_card_values = {
                             "code" : card_values["code"]
                            ,"set_code" : card_values["set_code"]

                            ,"id" : card_values["code"]
                            ,"name" : card_values["name"]
                            ,"rarity" : card_values["rarity"]#uncommon#rare#common
                            ,"cardmarket.prices.averageSellPrice" : card_values["averageSellPrice"]
                            ,"recent.sale.price" : card_values["trendPrice"]

                            ,"art.style" : "no"#reverse.holo#full.art.holo#no
                            ,"edges" : "8.5"
                            ,"corners" : "9"
                            ,"surface" : "9"
                            ,"centering" : "8.5"
                            ,"sold.at" : "Ebay"

                            ,"imgname" : ""
                            ,"database" : ""
                            }
                    return new_card_values
        except Exception as error:
            print("Request failed with error:", error)
        return None
 
    @classmethod
    def print_database_brief(cls):
        try:
            print("Printing database brief")
            sqlite_connection = sqlite3.connect(database_file)
            sqlite_connection.row_factory = sqlite3.Row
            sql_cursor = sqlite_connection.cursor()

            sql="select count(1) as number_of_sets from sets;"
            sql_cursor.execute(sql)
            rows = sql_cursor.fetchall()
            for row in rows:
                print(dict(row))

            sql="select count(1) as number_of_cards from cards;"
            sql_cursor.execute(sql)
            rows = sql_cursor.fetchall()
            for row in rows:
                print(dict(row))

            sql="select set_code, count(1) as number_of_cards from cards group by set_code;"
            sql_cursor.execute(sql)
            rows = sql_cursor.fetchall()
            for row in rows:
                print(dict(row))
        except Exception as error:
            print("Request failed with error:", error)

    @classmethod
    def get_cards_sorted_by_price(cls, price):
        try:
            print("Printing cards sorted by price")
            sqlite_connection = sqlite3.connect(database_file)
            sqlite_connection.row_factory = sqlite3.Row
            sql_cursor = sqlite_connection.cursor()

            sql=""" select set_code, code, averageSellPrice
                    from cards 
                    where cast(averageSellPrice as decimal) > ?
                    order by cast(averageSellPrice as decimal) desc
                    -- limit 10;"""
            sql_values = (price,)
            sql_cursor.execute(sql, sql_values)
            rows = sql_cursor.fetchall()
            cards = []
            for row in rows:
                cards.append(dict(row))
            return cards
        except Exception as error:
            print("Request failed with error:", error)
            
    

