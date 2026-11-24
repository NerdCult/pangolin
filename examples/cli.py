#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from colorama import Fore, init
from pynput import keyboard
import asyncio, threading
from pangolin_agent.core.interfaces import AgentRuntime, AgentRuntimeToQueue, AgentRuntimeAsync
from pangolin_agent.messages.chat_record import user_record

init(autoreset=True)

def printout(a, behaviors):
    if a.behavior == 'message':
        return
    behavior = a.behavior
    content = a.content
    
    if behavior == 'thinking':
        if not behaviors['thinking']:
            behaviors['thinking'] = True
            behaviors['replying'] = False
            behaviors['using_tool'] = False
            print (Fore.LIGHTRED_EX + '\nthinking> ', end="")
        print (Fore.LIGHTRED_EX + content, end="")

    if behavior == 'replying':
        if not behaviors['replying']:
            behaviors['thinking'] = False
            behaviors['replying'] = True
            behaviors['using_tool'] = False
            print (Fore.CYAN + '\nagent> ', end="")
        print (Fore.CYAN + content, end="")

    if behavior == 'tool_calls':
        if not behaviors['using_tool']:
            behaviors['thinking'] = False
            behaviors['replying'] = False
            behaviors['using_tool'] = True
            print (Fore.LIGHTYELLOW_EX + "\ntool> ", end="")
        print (Fore.LIGHTYELLOW_EX + str(a.content))

    # if behavior == 'done':
    #     print (Fore.CYAN + f'\nagent round ended: {content}')
    
    if behavior == 'error':
        print (Fore.MAGENTA + f'\nERROR: {content}')


def cli(session: AgentRuntime):
    '''simple command line interface to use an AgentRuntime. Press any key cancel the agent's turn'''
    asyncio.run(cli_async(session))

async def cli_async(session: AgentRuntime):
    '''same as cli() but implements the async work flow '''
    if not isinstance(session, AgentRuntimeAsync):
        raise TypeError('Agent Runtime does not implement AgentRuntimeAsync')


    stop = threading.Event()

    def on_key(key):
        stop.set()

    listener = keyboard.Listener(on_press=on_key)
    listener.start()

    print ("press any key to interrupt the agent's turn")

    while True:
        behaviors = {'thinking': False,
        'replying': False,
        'using_tool': False}                                                
        user_input = input(Fore.GREEN + '\n>>> ')

        stop.clear()

        async for a in session.handle_user_message(user_record(text=user_input), stop):
            printout(a, behaviors)

            if stop.is_set(): break

async def cli_queue(session: AgentRuntime):
    '''works the same as cli() but implements an async to queue work flow'''

    if not isinstance(session, AgentRuntimeToQueue):
        raise TypeError('Agent Runtime does not implement AgentRuntimeToQueue')

    async def output(queue: asyncio.Queue):
        behaviors = {'thinking': False,
        'replying': False,
        'using_tool': False} 
        while True:
            a = await queue.get()
            if not a: break
            printout(a, behaviors)

    stop = threading.Event()
    done = threading.Event()

    def on_key(key):
        stop.set()

    listener = keyboard.Listener(on_press=on_key)
    listener.start()

    print ("press any key to interrupt the agent's turn")
    
    while True:                                               
        user_input = input(Fore.GREEN + '\n>>> ') 

        queue = asyncio.Queue()
        stop.clear()
        done.clear()

        await asyncio.gather(
            output(queue),                            
            session.handle_user_message_to_queue(user_record(text=user_input), queue, stop, done)
        )