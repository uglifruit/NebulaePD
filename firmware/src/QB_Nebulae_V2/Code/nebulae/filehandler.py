import glob
import os

class FileHandler(object):
    def __init__(self, directory, extensions, hide_prefix=None):
        # uf1: hide_prefix (e.g. "_") leaves matching files out of the list (Pd helper abstractions)
        self.dir = directory
        self.maximum_capacity = 75
        self.files = []
        self.filesizes = []
        self.totalsize = 0
        self.loadedsize = 0
        self.files_to_load = []
        for ext in extensions:
            self.files.extend(glob.glob(directory + '*' + ext))
        if hide_prefix:
            self.files = [f for f in self.files if not os.path.basename(f).startswith(hide_prefix)]
        self.files.sort(key=lambda v: (v.upper(), v[0].islower()))
        self.fileCount = len(self.files)
        if "audio" in directory:
            print "Audio Directory Detected - Checking Capacity"
            self.conformToSize() 
            self.files = self.files_to_load
            self.fileCount = len(self.files)
            

    def conformToSize(self):
        for f in self.files:
            b = os.path.getsize(f)
            b /= 1024.0 # conform to KB
            b /= 1024.0 # conform to MB
            print "File: " + str(f) + " is " + str(b) + " MB"
            if self.totalsize + b < self.maximum_capacity:
                self.totalsize += b
                self.files_to_load.append(f)
        print "Total Size: " + str(self.totalsize) + " MB"
        print "Printing List of Loaded Files"
        print "============================="
        for f in self.files_to_load:
            print f
        print "============================="
                
            
            
    def getFileNames(self):
        read_friendly = []
        for f in self.files:
            pathless_name = os.path.basename(f)
            extensionless_name = os.path.splitext(pathless_name)[0]
            read_friendly.append(extensionless_name)
        return read_friendly

    def getFilename(self, idx):
        index = idx
        if index < len(self.files):
            pathless_name = os.path.basename(self.files[index])
            return os.path.splitext(pathless_name)[0]

    def getIndex(self, name):
        # uf1: exact name match (stock matched any substring of the path, so "drone" also hit "01_drone")
        for i, f in enumerate(self.files):
            if os.path.splitext(os.path.basename(f))[0] == name:
                return i
        return None

    def numFiles(self):
        return self.fileCount

