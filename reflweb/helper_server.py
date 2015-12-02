import sys
import BaseHTTPServer, SocketServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer, SimpleJSONRPCRequestHandler
import jsonrpclib.config

import multiprocessing
import webbrowser
import time

jsonrpclib.config.use_jsonclass = False
HandlerClass = SimpleHTTPRequestHandler
ServerClass  = BaseHTTPServer.HTTPServer
Protocol     = "HTTP/1.0"

if sys.argv[1:]:
    port = int(sys.argv[1])
else:
    port = 8000
#server_address = ('localhost', 0 ) # get next open socket

#HandlerClass.protocol_version = Protocol
#httpd = ServerClass(server_address, HandlerClass)
#http_port = httpd.socket.getsockname()[1]
#print "http port: ", http_port

#sa = httpd.socket.getsockname()
#print "Serving HTTP on", sa[0], "port", sa[1], "..."
## httpd.serve_forever()
#http_process = multiprocessing.Process(target=httpd.serve_forever)
#http_process.start()

class JSONRPCRequestHandler(SimpleJSONRPCRequestHandler):
    """JSON-RPC and documentation request handler class.

    Handles all HTTP POST requests and attempts to decode them as
    XML-RPC requests.

    Handles all HTTP GET requests and interprets them as requests
    for web pages, js, json or css.
    
    Put all static files to be served in 'static' subdirectory.
    """
    disable_nagle_algorithm = False
    rbufsize=-1
    wbufsize=-1
    
    #rpc_paths = ('/', '/RPC2')
    rpc_paths = () # accept all
    def __init__(self, request, client_address, server):
        print "init of request handler", request, time.ctime(), self.timeout
        SimpleJSONRPCRequestHandler.__init__(self, request, client_address, server)
        
    def setup(self):
        print "setting up", time.ctime()
        SimpleJSONRPCRequestHandler.setup(self)
        
    def handle(self):
        print "handling", time.ctime(), self.rbufsize, self.request._sock.gettimeout()
        SimpleJSONRPCRequestHandler.handle(self)
    
    def finish(self):
        print "finishing", time.ctime()
        SimpleJSONRPCRequestHandler.setup(self)
        
    def parse_request(self):
        print "parse_requesting", time.ctime()
        return SimpleJSONRPCRequestHandler.parse_request(self)
    
    def handle_one_request(self):
        """Handle a single HTTP request.

        You normally don't need to override this method; see the class
        __doc__ string for information on how to handle specific HTTP
        commands such as GET and POST.

        """
        import socket
        try:
            print "handle one start:", time.ctime()
            #print self.rfile.read(10)
            #print "read"
            self.raw_requestline = self.rfile.readline(65537)
            print "handle one raw request:", self.raw_requestline, time.ctime()
            if len(self.raw_requestline) > 65536:
                self.requestline = ''
                self.request_version = ''
                self.command = ''
                self.send_error(414)
                return
            if not self.raw_requestline:
                print "not!"
                self.close_connection = 1
                return
            if not self.parse_request():
                # An error code has been sent, just exit
                return
            mname = 'do_' + self.command
            if not hasattr(self, mname):
                self.send_error(501, "Unsupported method (%r)" % self.command)
                return
            method = getattr(self, mname)
            method()
            self.wfile.flush() #actually send the response if not already done.
        except socket.timeout, e:
            #a read or a write timed out.  Discard this connection
            self.log_error("Request timed out: %r", e)
            self.close_connection = 1
            return

    
    def do_OPTIONSOLD(self):
        print 'sending response', time.ctime()
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        #self.send_header('Access-Control-Allow-Origin', 'http://localhost:8000')
        #self.send_header('Access-Control-Allow-Origin', "http://localhost:%d" % (http_port,))           
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept")
        print 'response sent', time.ctime()
        #self.end_headers()
        #self.connection.shutdown(0)

    def do_OPTIONS(self):
        print 'sending response', time.ctime()
        self.send_response(200)
        #self.send_header('Access-Control-Allow-Origin', '*')
        #self.send_header('Access-Control-Allow-Origin', 'http://localhost:8000')
        #self.send_header('Access-Control-Allow-Origin', "http://localhost:%d" % (http_port,))           
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        #self.send_header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept")
        print 'response sent', time.ctime()
        self.end_headers()
        self.wfile.write("OK")
        #self.connection.shutdown(1)

      
    # Add these headers to all responses
    def end_headers(self):
        self.send_header("Access-Control-Allow-Headers", 
                          "Origin, X-Requested-With, Content-Type, Accept")
        self.send_header("Access-Control-Allow-Origin", "*")
        SimpleJSONRPCRequestHandler.end_headers(self)
    

class ThreadedJSONRPCServer(SocketServer.ThreadingMixIn, SimpleJSONRPCServer):
    pass
    
#server = SimpleJSONRPCServer(('localhost', 8001), encoding='utf8', requestHandler=JSONRPCRequestHandler)
server = ThreadedJSONRPCServer(('localhost', 8001), encoding='utf8', requestHandler=JSONRPCRequestHandler)
rpc_port = server.socket.getsockname()[1]
#webbrowser.open_new_tab('http://localhost:%d/index.html?rpc_port=%d' % (http_port, rpc_port))
server.register_function(pow)
server.register_function(lambda x,y: x+y, 'add')
server.register_function(lambda x: x, 'ping')

import h5py, os, simplejson

def categorize_files(path='./'):
    fns = os.listdir(path)
    fns.sort()
    categories = {\
        'Specular': 'SPEC',
        'Background': 'BG', 
        'Rocking': 'ROCK',
        'Slit': 'SLIT'}
    output = {}
    for fn in fns:
        try:
            f = h5py.File(os.path.join(path, fn))
            for entry in f.keys():
                _name = f[entry].get('DAS_logs/sample/name').value.flatten()[0]
                output.setdefault(_name, {})
                _num = f[entry].get('DAS_logs/trajectoryData/fileNum').value.flatten()[0]
                _scanType = f[entry].get('DAS_logs/trajectoryData/_scanType')
                if _scanType is not None:
                    _scanType = _scanType.value.flatten()[0]
                else:
                    _scanType = 'uncategorized'
                output[_name].setdefault(_scanType, {})
                output[_name][_scanType]['%d:%s' % (_num, entry)] = {'filename': fn, 'entry': entry}
        except:
            pass
            
    #return simplejson.dumps(output)
    return output

def get_file_metadata(pathlist=None):
    if pathlist is None: pathlist = []
    print pathlist
    import urllib
    import urllib2

    url = 'http://ncnr.nist.gov/ipeek/listftpfiles.php'
    values = {'pathlist[]' : pathlist}
    data = urllib.urlencode(values, True)
    req = urllib2.Request(url, data)
    response = urllib2.urlopen(req)
    fn = response.read()
    return fn
    
#    fns = os.listdir(path)
#    fns.sort()
#    metadata = []
#    for fn in fns:
#        try:
#            f = h5py.File(os.path.join(path, fn))
#            for entry in f.keys():
#                output = {}
#                _name = f[entry].get('DAS_logs/sample/name').value.flatten()[0]
#                output['sample_name'] = str(_name)
#                _num = f[entry].get('DAS_logs/trajectoryData/fileNum').value.flatten()[0]
#                output['fileNum'] = "%d" % (_num,)
#                _scanType = f[entry].get('DAS_logs/trajectoryData/_scanType')
#                if _scanType is not None:
#                    _scanType = _scanType.value.flatten()[0]
#                else:
#                    _scanType = 'uncategorized'
#                output['scanType'] = _scanType
#                output['filename'] = fn
#                output['path'] = path
#                output['entry'] = entry
#                metadata.append(output)
#        except:
#            pass
#    return metadata

def get_jstree(path='./'):
    files = categorize_files(path)
    categories = ['SPEC','BG','ROCK','SLIT','uncategorized']
    output = {'core': {'data': []}}
    sample_names = files.keys()
    for sample in sample_names:
        samp_out = {"text": sample}
        samp_out['children'] = []
        for cat in categories:
            if not cat in files[sample]: break
            cat_out = {"text": cat, "children": []}
            item_keys = files[sample][cat].keys()
            item_keys.sort()
            for child in item_keys:
                cat_out['children'].append({"text": child, "extra_data": {
                    "filename": files[sample][cat][child]['filename'],
                    "entry": files[sample][cat][child]['entry'],
                    "path": path}});
            samp_out['children'].append(cat_out)
        output['core']['data'].append(samp_out)
    return output 
        
def get_plottable(file_and_entry):
    """ file_and_entry should be list of dicts:
    [{ "filename": fn1, "entry": entryname1 }, { "filename": fn2, ...} ...]
    """
    print file_and_entry
    fig = {
        "title": "plot",
        "type": "1d",
        "data": [],
        "options": {
            "axes": {"xaxis": {}, "yaxis": {}},
            "series": [],
            },
        }
    for item in file_and_entry:
        f = h5py.File(item['filename'])
        DAS = f[item['entry']]['DAS_logs']
        print DAS
        xAxis = DAS.get('trajectoryData/xAxis')
        if xAxis is not None:
            xAxis = xAxis.value[0].replace('.', '/')
        if xAxis in DAS.keys() and 'primary' in DAS[xAxis].attrs: 
            # then it's a device name: convert to primary node
            xAxis = xAxis + "/" + DAS[xAxis].attrs['primary']
        if not xAxis in DAS:
            xAxis = DAS.get('trajectory/defaultXAxisPlotNode', "").value[0].replace('.', '/')
        if xAxis == "":
            xAxis = DAS['trajectory/scannedVariables'].value[0].split()[0].replace('.', '/')
        
        yAxis=DAS.get('trajectory/defaultYAxisPlotNode', "").value[0].replace('.', '/')
        if yAxis == "":
            yAxis = "counter/liveROI"
        yAxisChannel = DAS.get('trajectory/defaultYAxisPlotChannel', -1)
        fig_x = fig['options']['axes']['xaxis']
        fig_y = fig['options']['axes']['yaxis']
        if "label" in fig_x:
            if not fig_x['label'] == xAxis:
                raise Exception("axes do not match")
        else:
            fig_x['label'] = xAxis
        if "label" in fig_y:
            if not fig_y['label'] == yAxis:
                raise Exception("axes do not match")
        else: 
            fig_y['label'] = yAxis
        fig['options']['series'].append({"label": item['filename'] + ':' + item['entry']})
        x = DAS[xAxis].value.astype('float')
        y = DAS[yAxis].value.astype('float')
        xy = [[xx,yy] for xx, yy in zip(x,y)]
        fig['data'].append(xy)
        
    fig['options']['axes']['xaxis']['label'] = fig['options']['axes']['xaxis']['label'].replace('/', '.')
    fig['options']['axes']['yaxis']['label'] = fig['options']['axes']['yaxis']['label'].replace('/', '.')
    return fig
    
server.register_function(categorize_files) # deprecated
server.register_function(get_plottable)
server.register_function(get_jstree) # deprecated
server.register_function(get_file_metadata)
server.serve_forever()
print "done serving rpc forever"
#httpd_process.terminate()