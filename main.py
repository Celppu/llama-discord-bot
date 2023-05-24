
#Author: Emil Lintunen
#Date: 2023-05-24
import os

# export GGML_CUDA_NO_PINNED=1 to enviromentvariables fix cuda error TODO add this to local env variables using python
os.environ["GGML_CUDA_NO_PINNED"] = "1"


import discord
from dotenv import load_dotenv
from llama_cpp import Llama
import asyncio
from datetime import datetime, timedelta
import pytz

from fuzzywuzzy import fuzz

import re

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

MODEL_PATH = os.getenv('MODEL_PATH')

chathis = "This is a discord chat. Make short helpfull answer, tag users using @username \n"

inUse = False
tokenshist = []

intents = discord.Intents.default()
client = discord.Client(intents=intents)

def initialize_model(model_path):
    try:
        llm = Llama(model_path=model_path, n_ctx = 2048, n_gpu_layers= 40)
        return llm
    except Exception as e:
        print(f"Failed to initialize model due to {e}")
        return None

llm = initialize_model(MODEL_PATH)

@client.event
async def on_ready():
    print(f'{client.user} has connected!')

def remove_words_with_char(s, char):
    words = s.split()
    words = [word for word in words if char not in word]
    return ' '.join(words)

async def replace_mentions_with_names(message):
    content = message.content
    for mention in message.mentions:
        content = content.replace(f'<@{mention.id}>', f'@{mention.name}')
    for mention in message.role_mentions:
        content = content.replace(f'<@&{mention.id}>', f'@{mention.name}')
    return content

def replace_usernames_with_mentions(text):
    usernames = re.findall(r'@(\w+)', text)
    for username in usernames:
        user = discord.utils.get(client.get_all_members(), name=username)
        if user:
            text = text.replace(f'@{username}', f'<@{user.id}>')
    return text

def clean_username(username):
    """Remove non-alphanumeric characters from a username."""
    return re.sub(r'\W+', '', username)

def similar_enough(username1, username2, allowed_ratio=70):
    """Check if two usernames are similar enough, allowing for a certain percentage of typos."""
    username1, username2 = clean_username(username1), clean_username(username2)
    ratio = fuzz.ratio(username1.lower(), username2.lower())
    print(f"debug {username1} {username2} {ratio}")
    return ratio >= allowed_ratio

# replace_usernames_with_mentions but is more forgiving with typos. get the closest match from the list of usernames
def replace_usernames_with_mentions_fuzzy(text):
    usernames = re.findall(r'@(\w+)', text)
    for username in usernames:
        print("debug " + username)
        # do not use discord utils, rather get all members and find the closest match using python
        users = client.get_all_members()
        
        user = None
        for u in users:
            print("debug " + u.name)
            #if username is very similar to the name of the user, then use that user
            # from both only take alphanumeric characters and lowercase them
            if similar_enough(username, u.name):
                user = u
                break

        #user = discord.utils.find(lambda m: username in m.name, client.get_all_members())
        if user:
            text = text.replace(f'@{username}', f'<@{user.id}>')
    return text

def limit_to_last_n_tokens(text, n=1000):
    # Define a regex pattern to match words, punctuation, and newlines
    pattern = r'\b\w+\b|[.,!?;]|\n'
    tokens = re.findall(pattern, text)

    # Find the index to slice the text from
    slice_index = len(text)
    for _ in range(n):
        if tokens:
            token = tokens.pop()
            slice_index = text.rfind(token, 0, slice_index)
        else:
            break

    # Slice the text from the calculated index
    return text[slice_index:]

# from messag text remove mention of bot and replace with nothing. Serach id and bot name
def remove_bot_mention(text):
    text = text.replace(f'<@{client.user.id}>', '')
    text = text.replace(f'<@!{client.user.id}>', '')
    text = text.replace(f'@{client.user.id}', '')
    text = text.replace(f'@{client.user.name}', '')
    return text



#response edit method that checks that the message is not empty and contains at least one character that is not a space
async def edit_response(response, text):
    if len(text) > 1 and not text.isspace():
        await response.edit(content = text)
    
response = None

@client.event
async def on_message(message):
    global inUse, chathis, llm, tokenshist, response

    if message.author == client.user or not message.mentions:
        return

    if client.user in message.mentions:
        try:
            msg = message.content 
            msg = await replace_mentions_with_names(message)

            msg = remove_bot_mention(msg)
            print(f"User: {msg}")

            user = message.author
            bot = client.user

            prompt = f"\nUser  {user} :\n{msg}   \nAssistant {bot} : "
            
            if inUse:
                await message.channel.send("```thinkthönkin already somewhere```")
            else:
                inUse = True
                response = await message.channel.send("```thinking...```")

                # Initialize chat history
                chathis = ""

                # Fetch the history of the channel from the past day or last 10 messages
                time_boundary = datetime.utcnow() - timedelta(days=1)

                # Get the current time
                now = datetime.now(pytz.utc)    
                # Set the boundary for 24 hours ago
                day_ago = now - timedelta(days=1)

                #list of message strings
                messages = []
                async for m in message.channel.history(limit=30):
                    #take only messages less than a day old
                    if m.created_at > day_ago:
                        if m.id == response.id:
                            continue
                        if bot in m.mentions or m.author == bot:
                            # change id to username
                            contents = await replace_mentions_with_names(m)
                            contents = remove_bot_mention(contents)
                            # if message is from user, add user to the start of the message and is from bot, add assistant to the start of the message
                            usertype = "Assistant" if m.author == bot else "User"
                            
                            #add to messages list
                            messages.append(f"{usertype} {m.author} : {contents}\n")
                            #print messages
                            print(f"{usertype} {m.author} : {contents}\n")

                #take last 10 messages
                #messages = messages[-30:]
                #for m in messages:
                #    chathis += m
                
                #reverse order of messages
                messages.reverse()
                for m in messages:
                    chathis += m

                #mentioner 
                #chathis += f"User @{user} : {msg}\n"

                # Append the new message to the chat history
                chathis += f"Assistant {bot} : \n"

                max_chunk_length = 100  # Adjust this value as necessary

                chunks = []
                tokenshist = []
                start = 0

                while start < len(chathis):
                    # Find the last whitespace character in the next chunk
                    end = start + max_chunk_length
                    if end < len(chathis):
                        while end > start and chathis[end] not in (' ', '\n', '\t'):
                            end -= 1
                        if end == start:
                            end = start + max_chunk_length
                    else:
                        end = len(chathis)

                    # Add the chunk to the list of chunks
                    chunks.append(chathis[start:end])

                    # Move on to the next chunk
                    start = end

                for chunk in chunks:
                    tokens = llm.tokenize(chunk.encode())
                    tokenshist += tokens

                if len(tokenshist) > 1500:
                    tokenshist = tokenshist[-1500:]
                    print("token history too long, removing first 1500 tokens")
                
                #add to the start of the token history explanation
                explanation = f"This is a discord chat. Make short helpfull answer, tag users using @ and username. You are assistant amd your name is {bot} or when mentioned @{bot} \n"

                tokenshist = llm.tokenize(explanation.encode()) + tokenshist


                chathis = llm.detokenize(tokenshist).decode()
                
                print(f"history and new prompt: --- \n{chathis} --- ")


                print(f"number of tokens: {len(tokenshist)}")

                stream = llm(chathis, stop=["User  :\n", "###", 'User', '\nuser', 'USER', '\nUSER' ], stream=True, max_tokens = 500 )

                outtext = ""

                #only edit message once a second
                #get start time
                start = asyncio.get_running_loop().time()

                for output in stream:
                    print(output["choices"][0]["text"], end="")


                    outtext += output["choices"][0]["text"]
                    #get current time
                    now = asyncio.get_running_loop().time()
                    #if half second has passed and outtext is not empty, edit message
                    if (now - start > 0.5) and (len(outtext) > 1):
                        await edit_response(response, outtext)
                        start = now


                #check if outtext has unclosed codeblock or ``` or ``` and close it
                if outtext.count("```") % 2 == 1:
                    outtext += "``` (Output ended with unclosed codeblock. ask bot to continue)"
                    print("added closing codeblock")

                
                #edit message with final output if it is not empty
                if len(outtext) > 1:
                    print("final output: " + outtext)
                    await edit_response(response, outtext)

                outtextwithmentions = replace_usernames_with_mentions_fuzzy(outtext)
                #check if outtextwithmentions is different from outtext and edit message if it is
                if outtextwithmentions != outtext and len(outtextwithmentions) > 1:
                    print("mentions replaced")
                    await edit_response(response, outtextwithmentions)


                inUse = False
                print("\ndone")

        except Exception as e:
            inUse = False
            print(f"An error occurred: {e}")
            await response.edit(content = f"SYSTEM - An error occurred: {e} -")

            llm = initialize_model(MODEL_PATH)

client.run(TOKEN)