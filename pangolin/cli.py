#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

from .core.interfaces import AgentRuntime
from .messages.chat_record import user_record

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
            print ('\nTHINKING> ', end="")
        print (content, end="")

    if behavior == 'replying':
        if not behaviors['replying']:
            behaviors['thinking'] = False
            behaviors['replying'] = True
            behaviors['using_tool'] = False
            print ('\nAGENT>>> ', end="")
        print (content, end="")

    if behavior == 'tool_calls':
        if not behaviors['using_tool']:
            behaviors['thinking'] = False
            behaviors['replying'] = False
            behaviors['using_tool'] = True
            print ("\nTOOL> ", end="")
        print (str(a.content))

    # if behavior == 'done':
    #     print (Fore.CYAN + f'\nagent round ended: {content}')
    
    if behavior == 'error':
        print (f'\nERROR: {content}')


def cli(session: AgentRuntime, show_welcome: bool = True):
    '''simple command line interface to use an AgentRuntime. Press ctrl+c to cancel the agent's turn'''

    if show_welcome:
        print ("Welcome to the Pangolin cli, a minimal AI Agentic interface!\nPress ctrl+c to interrupt the agent's turn.\nThe Github repo examples provides a cli with color coded text, omitted here to keep dependencies minimal.")

    while True:
        behaviors = {'thinking': False,
        'replying': False,
        'using_tool': False}                                        
        user_input = input('\nUSER>>> ')

        try:
            for a in session.handle_user_message(user_record(text=user_input)):
                printout(a, behaviors)
        except KeyboardInterrupt:
            print ('AGENT TURN CANCELLED')