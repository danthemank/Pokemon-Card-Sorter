import asyncio
import websockets
#import chatGPT as ChatGPT
import logging
import json
import uuid
import jwt
import time

class websocket_server:
    
    async def websocket_handler(self, websocket, path):
        # Called when a new WebSocket connection is established
        print("New connection established")
        random_uuid = uuid.uuid4()
        random_uuid_str = str(random_uuid)
        print("Random UUID:", random_uuid_str)
        current_connection = {}
        current_connection["websocket"] = websocket
        current_connection["messages"] = []
        current_connection["token"] = "TODO"
        self.connections[random_uuid_str] = current_connection

        try:
            while True:
                # Wait for incoming messages
                message = await websocket.recv()
                message_short = message[0:100]
                logging.debug(f"Received message: {message_short}")
    
                # Process the received message
                # ...
    
                # Send a response back to the client
                #response = "Response from server"
                response = await self.process_message(message, current_connection)
                if response != "":
                    await websocket.send(response)
        except websockets.ConnectionClosed:
            # Connection closed by the client
            print("Connection closed")
    
    async def process_message(self, message, current_connection):
        try:
            self.config_logging()
            logging.info("\n\n\n---------------------------------------------------------------------------------------------------------")
            logging.info("Welcome to the OpenAI Chatbot!")
    
            logging.info("Prompt: "+ message[0:100])
            messages=json.loads(message)

            if 'token' in messages:
                try:
                    decoded_token = jwt.decode(messages['token'], 'jwtcardsortertoken', algorithms=['HS256'])
                    current_connection["token"] = messages["token"]
                    print("Token received")
                    print(decoded_token)
                    return ""
                except jwt.ExpiredSignatureError:
                    print("Token expired")
                    return ""
                except jwt.InvalidTokenError:
                    print("Invalid token")
                    return ""
            elif "token" not in current_connection:
                return "Token required"

            #current_connection["messages"].extend(messages)

            if "frame" in messages:
                for connection in self.connections.values():
                    other_client = connection["websocket"]
                    if other_client.closed:
                        continue
                    try:
                        await other_client.send(json.dumps(messages))
                    except Exception as ex:
                        print('error forwarding status')
                        print(ex)
                        await other_client.close()
    
            #chat = ChatGPT.ChatGPT()
            #chat.set_model(ChatGPT.ChatGPT_Model.GPT_3_5_TURBO)
            #response =logging.info(str(current_connection["messages"]))
            #response =str(current_connection["messages"])
            ##response = chat.make_question(prompt, is_base64=True)
            #response = await chat.make_question_async(messages=current_connection["messages"], is_base64=False)
            #response = chat.make_question(prompt, is_base64=False)
            #logging.info(u[0:100])
            #ChatGPT.loop(ChatGPT_Model.GPT_3_5_TURBO)
            response = ''
            return response
        except Exception as e:
            logging.exception(e)
            return "Error: " + str(e)
        finally:
            pass
            #logging.info("---------------------------------------------------------------------------------------------------------")

    def start_server(self):
        self.connections = {}
        self.server = websockets.serve(self.websocket_handler, '0.0.0.0', 8080)
        
        # Run the WebSocket server indefinitely
        asyncio.get_event_loop().run_until_complete(self.server)
        asyncio.get_event_loop().run_forever()

    def config_logging(self):
        #logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        #logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

        #file_handler = logging.FileHandler('chatGPT.log')
        #file_handler.setLevel(logging.ERROR)

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        #file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)

        logger = logging.getLogger('')
        #logger.addHandler(file_handler)
        logger.addHandler(stream_handler)


class websocket_client:
    def __init__(self, server_uri):
        self.server_uri = server_uri
        self.websocket = None

    async def connect(self):
        try:
            self.websocket = await websockets.connect(self.server_uri)
            #await self.websocket.send(json.dumps({ 'token': "jwtcardsortertoken" }));
            print("Connected to WebSocket server");
        except Exception as e:
            #print("Error connecting to WebSocket server: ")
            #print(e)
            await self.disconnect()
            time.sleep(1)
            self.websocket = None
            #await self.connect()

    async def send_message(self, message):
        try:
            #print('Sending message: ')
            if not self.websocket:
                print ("WebSocket is not connected")
                await self.connect()
                #raise Exception("WebSocket is not connected")
    
            await self.websocket.send(message)
        except Exception as e:
            time.sleep(1)
            print("Error sending message: ")
            await self.disconnect()
            time.sleep(1)
            await self.connect()

    async def receive_message(self):
        if not self.websocket:
            raise Exception("WebSocket is not connected")

        return await self.websocket.recv()

    async def disconnect(self):
        if self.websocket:
            print('closing connection')
            await self.websocket.close()
            self.websocket = None



if __name__ == "__main__":
    websocket_server().start_server()
