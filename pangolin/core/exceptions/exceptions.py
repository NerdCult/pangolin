#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import traceback

class PangolinError(Exception):
    def __init__(self, message):
        # Capture the current stack trace as a string
        stack = "".join(traceback.format_stack())
        # Bake it into the actual message
        super().__init__(f"{message}\n\nTraceback:\n{stack}")

class PangolinTypeError(PangolinError, TypeError):...

class PangolinImportError(PangolinError, ImportError):...

class PangolinValueError(PangolinError, ValueError):...

class PangolinGuardRailDenial(PangolinError):...