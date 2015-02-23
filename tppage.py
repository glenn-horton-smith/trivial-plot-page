"""tppage.py -- proof-of-principle of a trivial plots page utility

Requires imagemagick's convert utility for making thumbnails,
otherwise just uses Python's standard modules.

Usage examples:
  Starting in the root directory of the plots pages:

   To put captions and files from doc 9876 in the under_review pages:

    $ python tppage.py under_review 9876

   To do the same thing, but reading from a .zip file instead of Doc-DB:

    $ python tppage.py under_review 9876 example_9876.zip

   To rebuild under_review/index.html without changing any other files:

    $ python tppage.py under_review

The documents must conform to a particular structure in order to be imported.
Captions must be provided in files with the naming convention 
*_caption.txt or *_caption.tex.  Only files whose names who are matched with
captions will be imported.

:author: G. Horton-Smith
"""

import zipfile
import os
import time
import urllib
import re

################################################################
# Some constants
################################################################

# Warning: CAP_END_TXT and CAP_END_TEX have to be the same length
CAP_END_TXT = '_caption.txt'
CAP_END_TEX = '_caption.tex'

THUMB_END = "_thumb.png"

IMAGE_EXT_LIST = ['pdf', 'eps', 'jpeg', 'jpg', 'png', 'gif']

DOCDB_SHOW_DOC_TEMPLATE = 'http://microboone-docdb.fnal.gov:8080/cgi-bin/ShowDocument?docid=%s'

DOCDB_GET_ZIP_TEMPLATE = 'http://microboone-docdb.fnal.gov:8080/cgi-bin/RetrieveArchive?docid=%s&type=zip'

HTML_HEADER = """<html>
<head><title>Index of %(status)s plots and other data representations</title>
<link rel="StyleSheet" href="ubplot.css" type="text/css"  
media="screen, projection"/>
<style>
div.FLOATBOX { border: thin solid #b37013; box-shadow: 2pt 2pt 2pt #f4cd98; 
               margin: 4pt; padding: 2pt; float: left; }
#plotpagefooter { width: 100%%; position:fixed; bottom:0; left:0;
                  background: #fed; padding-top: 2pt; }
</style>
</head>
<body>
<h1>Index of %(status)s plots and other data representations</h1>
"""

HTML_FOOTER = """<br/>
 <div id="plotpagefooter">
 Questions?  Click on the document numbers for notes and authors,
 or <a href="../plot_contacts.html">contact us</a>.
 <span style="float:right">Page last updated: %s </span>
 </div>
</body>
</html>
"""
 
################################################################
# Utility functions
################################################################

def smartExtractFromZip(zipfile, fn, destdir):
    shortfn = fn[fn.rfind('/')+1:]
    data = zipfile.read( fn )
    file(destdir+"/"+shortfn,'w').write(data)



################################################################
# The code that does all the work.
################################################################
    
class TPP:
    """TPP is the main class for the "trivial plots page" utility."""
    def __init__(self):
        pass

    def add_plots( self, status, docno, zf=None ):
        """Add all captioned files from docno to subdirectory named
        status in current directory, and rebuild index pages.
        Clears old files in the destination directory before filling.
        Does not remove old files from other directories.
        If zipfile is provided, use it instead of retrieving zipfile from
        Doc-DB."""

        #-- get zip file from Doc-DB if none supplied
        if zf == None:
            zf = self.getZip(docno)

        #-- clean up "status" and form destination dir
        status = status.strip().strip('/')
        docno = docno.strip()
        destdir = './%s/%s' % ( status, docno )
        self.cleardir( destdir )
        namelist = zf.namelist()
        captions = list(fn for fn in namelist 
                        if fn.endswith(CAP_END_TXT) or fn.endswith(CAP_END_TEX))
        for cap in captions:
            # zf.extract( cap, destdir )
            smartExtractFromZip( zf, cap, destdir )
            # warning: next line assumes CAP_END_TXT and CAP_END_TEX same length
            prefix = cap[:-len(CAP_END_TXT)]
            for fn in namelist:
                if fn.startswith(prefix):
                    #zf.extract( fn, destdir )
                    smartExtractFromZip( zf, fn, destdir )
        self.rebuild_index_page( status )

    def cleardir( self, dname ):
        """Clear files from the given directory, or make directory if needed"""
        # does directory already exist?
        if os.access( dname, os.F_OK ):
            # clear directory
            for fn in os.listdir( dname ):
                os.remove( dname + '/' + fn)
        else:
            os.makedirs( dname )

    def rebuild_index_page( self, status ):
        """Rebuild the html pages from the files found in subdirectories.
        Relies on python's "walk" function -- see help(os.walk).
        """
        status = status.strip().strip('/')
        fout = file("%s/index.html" % status, "w")
        fout.write( HTML_HEADER % { 'status' : status } )
        dirwalk_list = list( os.walk(status) )
        dirwalk_list.sort()
        for dirpath, subdirnames, filenames in dirwalk_list:
            captionfns = list( fn for fn in filenames 
                               if (fn.endswith(CAP_END_TXT) 
                                   or fn.endswith(CAP_END_TEX)) )
            if captionfns == []:
                continue
            # form relative directory name from "dirpath" returned by os.walk()
            reldir = dirpath[len(status)+1:]
            # use first part of reldir (DocDB number) as section title
            if '/' in reldir:
                header2 = reldir[:reldir.find('/')]
            else:
                header2 = reldir
            docinfo = self.getDocInfo(header2)
            fout.write('<hr/><a href="%s"><h2>%s &nbsp; (#%s)</h2></a>\n' % (
                DOCDB_SHOW_DOC_TEMPLATE % header2, docinfo['title'], header2) )
            # uncomment line below to show authors
            # fout.write('<ul>%s</ul>\n' % docinfo['authors'])
            captionfns.sort()
            for cap in captionfns:
                # warning: next line assumes CAP_END_TXT and CAP_END_TEX same length
                prefix = cap[:-len(CAP_END_TXT)]
                fout.write("<div><h3>%s</h3><br/>\n" % prefix)
                fnlist = list( fn for fn in filenames if (
                        fn.startswith(prefix+".") 
                        or fn.startswith(prefix+"_caption.") )
                               and not fn.endswith(THUMB_END) )
                fnlist.sort()
                # find a good image for making a thumbnail image
                thumbfn = None
                for ext in IMAGE_EXT_LIST:
                    thumbfn = prefix + "." + ext
                    if thumbfn in fnlist:
                        break
                    else:
                        thumbfn = None
                # make the thumbnail
                if thumbfn != None:
                    thumb_fn = self.make_thumb( dirpath+"/"+thumbfn )
                    fout.write('<div class="FLOATBOX"><img src="%s"/></div>\n' %
                               thumb_fn[len(status)+1:] )
                for fn in fnlist:
                    if fn.endswith(THUMB_END):
                        continue
                    fout.write('<a href="%s">%s</a><br/>\n' % 
                               (reldir+"/"+fn, fn) )
                # now the caption
                caption = file(dirpath + "/" + cap).read()
                fout.write('<br clear="all"/><p>%s</p>\n' % caption)
                fout.write("</div>\n")
        fout.write("<hr/>\n")
        fout.write( HTML_FOOTER % time.ctime())
        fout.write("</body>\n</html>\n")
        fout.close()
                        
                    
    def make_thumb(self, fn):
        """Make a thumbnail.  Requires imagemagick's convert utiltity."""
        thumbfn = fn + THUMB_END
        os.system("convert -trim +repage -resize 400 %s %s" % (fn, thumbfn))
        return thumbfn


    def getZip(self, docno):
        """Get the zip file from Doc-DB."""
        url = DOCDB_GET_ZIP_TEMPLATE % docno
        (filename, headers) = urllib.urlretrieve(url)
        print "Retrieved document %s to temporary file %s" % (docno, filename)
        return zipfile.ZipFile( filename )

    def getDocInfo(self, docno):
        """Get the document info from Doc-DB."""
        url = DOCDB_SHOW_DOC_TEMPLATE % docno
        info = {}
        data = urllib.urlopen(url).read()
        m = re.search('<div[^>]*id *= *"DocTitle"[^>]*>.*<h1>([^<]*)</h1>',
                      data, re.S)
        if m:
            info['title'] = m.groups()[0]
        else:
            info['title'] = ""
            print "No title found for %s" % docno
        m = re.search('<div[^>]*id *= *"Authors"[^>]*>.*<ul>(.*)</ul>',
                      data, re.S)
        if m:
            info['authors'] = m.groups()[0]
        else:
            info['authors'] = ''
            print "No authors found for %s" % docno
        return info


################################################################
# ye basic "main" entry point
################################################################

if __name__ == "__main__":
    import sys
    tpp = TPP()
    if len(sys.argv) >= 4:
        tpp.add_plots( sys.argv[1], sys.argv[2], zipfile.ZipFile(sys.argv[3]) )
    elif len(sys.argv) == 3:
        tpp.add_plots( sys.argv[1], sys.argv[2] )
    elif len(sys.argv) == 2:
        tpp.rebuild_index_page( sys.argv[1] )
    else:
        print """Usage examples:
  Starting in the root directory of the plots pages:

   To put captions and files from doc 9876 in the under_review pages:

    $ python tppage.py under_review 9876

   To do the same thing, but reading from a .zip file instead of Doc-DB:

    $ python tppage.py under_review 9876 example_9876.zip

   To rebuild under_review/index.html without changing any other files:

    $ python tppage.py under_review
"""
        sys.exit(1)
