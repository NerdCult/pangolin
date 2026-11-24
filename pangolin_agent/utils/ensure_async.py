#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import asyncio
from inspect import iscoroutinefunction, isasyncgenfunction

async def ensure_async(func, *args):
    if iscoroutinefunction(func):
        return await func(*args)
    else:
        return await asyncio.to_thread(func,*args)

def ensure_async_gen(func, *args):
    if isasyncgenfunction(func):
        return func(*args)
    else:
        async def async_gen_wrapper(gen):
            for item in gen:
                yield item
        return async_gen_wrapper(func(*args))