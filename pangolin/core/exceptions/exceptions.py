#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.



class PangolinError(Exception):
    pass

class PangolinTypeError(PangolinError, TypeError):
    pass

class PangolinImportError(PangolinError, ImportError):
    pass