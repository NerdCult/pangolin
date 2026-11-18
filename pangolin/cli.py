#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from colorama import Fore, init
from pynput import keyboard
import asyncio, threading, sys
from .core.interfaces import AgentRuntime, AgentRuntimeToQueue
from .messages.ta_record import user_record
init(autoreset=True)

def cli(session: AgentRuntime):
    '''simple command line interface to use an AgentRuntime. ctrl+c will cancel the agent's turn'''
    while True:
        thinking = False
        replying = False
        using_tool = False                                                
        user_input = input(Fore.GREEN + '\n>>> ')   
        try:                                                
            for a in session.handle_user_message(user_record(text=user_input)):
                if a.behavior == 'message':
                    continue
                behavior = a.behavior
                content = a.content
            
                if behavior == 'thinking':
                    if not thinking:
                        thinking = True
                        replying = False
                        using_tool = False
                        print (Fore.LIGHTRED_EX + '\nthinking> ', end="")
                    print (Fore.LIGHTRED_EX + content, end="")

                if behavior == 'replying':
                    if not replying:
                        thinking = False
                        replying = True
                        using_tool = False
                        print (Fore.CYAN + '\nagent> ', end="")
                    print (Fore.CYAN + content, end="")

                if behavior == 'tool_calls':
                    if not using_tool:
                        thinking = False
                        replying = False
                        using_tool = True
                        print (Fore.LIGHTYELLOW_EX + "\ntool> ", end="")
                    print (Fore.LIGHTYELLOW_EX + str(a.content))

                if behavior == 'done':
                    print (Fore.CYAN + f'\nagent turn ended: {content}')

        except KeyboardInterrupt:
            pass

async def cli_queue(session: AgentRuntime):
    '''simple command line interface to use an AgentRuntime. ctrl+c will cancel the agent's turn'''

    if not isinstance(session, AgentRuntimeToQueue):
        raise TypeError('Agent Runtime does not implement AgentRuntimeToQueue')

    async def output(queue: asyncio.Queue):
        thinking = False
        replying = False
        using_tool = False 
        while True:
            a = await queue.get()

            if not a: break

            behavior = a.behavior
            content = a.content
        
            if behavior == 'thinking':
                if not thinking:
                    thinking = True
                    replying = False
                    using_tool = False
                    print (Fore.LIGHTRED_EX + '\nthinking> ', end="")
                print (Fore.LIGHTRED_EX + content, end="")
            if behavior == 'replying':
                if not replying:
                    thinking = False
                    replying = True
                    using_tool = False
                    print (Fore.CYAN + '\nagent> ', end="")
                print (Fore.CYAN + content, end="")

            if behavior == 'tool_calls':
                if not using_tool:
                    thinking = False
                    replying = False
                    using_tool = True
                    print (Fore.LIGHTYELLOW_EX + "\ntool> ", end="")
                print (Fore.LIGHTYELLOW_EX + str(a.content))

            if behavior == 'done':
                print (Fore.CYAN + f'\nagent turn ended: {content}')

            if behavior == 'error':
                print (Fore.MAGENTA + f'\nERROR: {content}')

    stop = threading.Event()
    done = threading.Event()

    def on_key(key):
        stop.set()

    listener = keyboard.Listener(on_press=on_key)
    listener.start()

    while True:                                               
        user_input = input(Fore.GREEN + '\n>>> ') 

        queue = asyncio.Queue()
        stop.clear()
        done.clear()

        await asyncio.gather(
            output(queue),                            
            session.handle_user_message_to_queue(user_record(text=user_input), queue, stop, done)
        )