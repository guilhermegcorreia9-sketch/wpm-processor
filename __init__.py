# -*- coding: utf-8 -*-
def classFactory(iface):
    from .cbers_wpm_plugin import CbersWpmPlugin
    return CbersWpmPlugin(iface)
