import sublime
import sublime_plugin
import os
import subprocess
import re
import sys

if sys.platform == "win32":
    if sys.version_info >= (3, 0, 0):
        from winreg import *
    else:
        from _winreg import *


container = {}
last_row = 0
settingsfile = 'Enhanced-R.sublime-settings'
default_pkgs = 'ggplot2,data.table'

# get platform specific key
def get(plat, key, default=None):
    settings = sublime.load_settings(settingsfile)
    plat_settings = settings.get(plat)
    if key in plat_settings:
        return plat_settings[key]
    else:
        return default

def get_Rscript():
    plat = sublime.platform()
    if plat == "windows":
        App = get(plat, "R", "R64")
        arch = "x64" if App == "R64" else "i386"
        Rscript = get(plat, "Rscript")
        if not Rscript:
            akey=OpenKey(HKEY_LOCAL_MACHINE, "SOFTWARE\\R-core\\"+App, 0, KEY_WOW64_64KEY|KEY_READ)
            path=QueryValueEx(akey, "InstallPath")[0]
            Rscript = path + "\\bin\\"  + arch + "\\Rscript.exe"
    else:
        Rscript = get(plat, "Rscript", "Rscript")
    # print(Rscript)
    return Rscript

def mycheck_output(args):
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        output = subprocess.Popen(args, stdout=subprocess.PIPE, startupinfo=startupinfo).communicate()[0]
    else:
        output = subprocess.Popen(args, stdout=subprocess.PIPE).communicate()[0]

    return output.decode('utf-8')


class RStatusListener(sublime_plugin.EventListener):

    def RStatusUpdater(self, view):
        point = view.sel()[0].end() if view.sel() else 0
        if not view.score_selector(point, "source.r"):
            return

        this_row = view.rowcol(point)[0]
        sel = view.sel()
        if len(sel)!=1: return
        if sel[0].begin() != sel[0].end(): return
        contentb = view.substr(sublime.Region(view.line(point).begin(), point))
        m = re.match(r".*?([a-zA-Z0-9.]+)\($", contentb)
        if not m: return
        view.set_status("Enhanced-R", "")
        func = m.group(1)

        global container
        # print(func in container)
        if func in container:
            prototype = container[func]
        else:
            Rscript = get_Rscript()
            plat = sublime.platform()
            output = mycheck_output([Rscript, '-e', 'args(' + func + ')', '--default-packages=' + default_pkgs])
            if not re.match("function ", output): return
            output = re.sub(r"^function ", "", output)
            output = re.sub(r"\)[^)]*$", ")", output)
            output =re.sub(r"\s*\n\s*", " ", output)
            prototype = func + output
            container.update({func: prototype})

        global last_row
        last_row = this_row
        view.set_status("Enhanced-R", prototype)

    def on_modified(self, view):
        if view.is_scratch() or view.settings().get('is_widget'): return
        point = view.sel()[0].end() if view.sel() else 0
        if not view.score_selector(point, "source.r"):
            return
        # run it in another thread
        sublime.set_timeout(lambda : self.RStatusUpdater(view), 100)

    def on_selection_modified(self,view):
        if view.is_scratch() or view.settings().get('is_widget'): return
        point = view.sel()[0].end() if view.sel() else 0
        if not view.score_selector(point, "source.r"):
            return
        this_row = view.rowcol(point)[0]
        global last_row
        if this_row!= last_row: view.set_status("Enhanced-R", "")


    def on_post_save(self, view):
        if view.is_scratch() or view.settings().get('is_widget'): return
        point = view.sel()[0].end() if view.sel() else 0
        if not view.score_selector(point, "source.r"):
            return
        self.obtain_func_prototype(view)

    def on_load(self, view):
        if view.is_scratch() or view.settings().get('is_widget'): return
        point = view.sel()[0].end() if view.sel() else 0
        if not view.score_selector(point, "source.r"):
            return
        self.obtain_func_prototype(view)

    def on_activated(self, view):
        if view.is_scratch() or view.settings().get('is_widget'): return
        point = view.sel()[0].end() if view.sel() else 0
        if not view.score_selector(point, "source.r"):
            return
        self.obtain_func_prototype(view)
        # print(container)

    def obtain_func_prototype(self, view):
        global container
        funcsel = view.find_all(r"\b(?:[a-zA-Z0-9._:]*)\s*(?:<-|=)\s*function\s*(\((?:(?:[^()]*|(?1)))*\))")
        for s in funcsel:
            m = re.match(r"^([^ ]+)\s*(?:<-|=)\s*(?:function)\s*(.+)$", view.substr(s))
            if m:
                container.update({m.group(1): m.group(1)+m.group(2)})