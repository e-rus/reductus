# This program is public domain
"""
File extension registry.

This provides routines for opening files based on extension,
and registers the built-in file extensions.
"""

import os.path

class ExtensionRegistry(object):
    """
    Associate a file loader with an extension.

    Note that there may be multiple loaders for the same extension.

    Example:

    registry = ExtensionRegistry()

    # Add an association by setting an element
    registry['.zip'] = unzip

    # Multiple extensions for one loader
    registry['.tgz'] = untar
    registry['.tar.gz'] = untar

    # Multiple loaders for one extension
    registry['.cx'] = cx1
    registry['.cx'] = cx2
    registry['.cx'] = cx3

    # Retrieve loaders for a file name
    registry.lookup('hello.cx') -> [cx3,cx2,cx1]

    # Run loader on a filename
    registry.load('hello.cx') ->
        try:
            return cx3('hello.cx')
        except:
            try:
                return cx2('hello.cx')
            except:
                return cx1('hello.cx')
    """
    def __init__(self):
        self.loaders = {}
    def __setitem__(self, ext, loader):
        if ext not in self.loaders:
            self.loaders[ext] = []
        self.loaders[ext].insert(0,loader)
    def __getitem__(self, ext):
        return self.loaders[ext]
    def __contains__(self, ext):
        return ext in self.loaders
    def lookup(self, path):
        """
        Return the loader associated with the file type of path.
        """
        file = os.path.basename(path)
        idx = file.find('.')
        ext = file[idx:] if idx >= 0 else ''
        try:
            return self.loaders[ext]
        except:
            raise ValueError, "Unknown file type '%s'"%ext
    def load(self, path):
        """
        Call the loader for the file type of path.

        Raises ValueError if no loader is available.
        May raise a loader-defined exception if loader fails.
        """
        loaders = self.lookup(path)
        for fn in loaders:
            try:
                return fn(path)
            except:
                pass # give other loaders a chance to succeed
        # If we get here it is because all loaders failed
        raise # reraises last exception

def test():
    reg = ExtensionRegistry()
    class CxError(Exception): pass
    def cx(file): return 'cx'
    def new_cx(file): return 'new_cx'
    def fail_cx(file): raise CxError
    reg['.cx'] = cx
    reg['.cx1'] = cx
    reg['.cx'] = new_cx
    reg['.cx.gz'] = new_cx
    reg['.cx1'] = fail_cx
    reg['.cx2'] = fail_cx

    # Two loaders associated with .cx
    assert reg.lookup('hello.cx') == [new_cx,cx]
    # Make sure the last loader applies first
    assert reg.load('hello.cx') == 'new_cx'
    # Make sure the next loader applies if the first fails
    assert reg.load('hello.cx1') == 'cx'
    # Make sure the case of all loaders failing is correct
    try:  reg.load('hello.cx2')
    except CxError: pass # correct failure
    else: raise AssertError,"Incorrect error on load failure"
    # Make sure the case of no loaders fails correctly
    try: reg.load('hello.missing')
    except ValueError,msg:
        assert str(msg)=="Unknown file type '.missing'",'Message: <%s>'%(msg)
    else: raise AssertError,"No error raised for missing extension"

if __name__ == "__main__": test()
