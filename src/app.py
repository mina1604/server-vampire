"""The application entry point."""

import sys
if sys.version_info < (3,0,0):
    raise Exception("User error: This application does not support Python 2. You probably need to use python3 instead of python.")
if sys.version_info < (3,6,0):
    raise Exception("User error: This application requires Python 3.6 or higher!")
import json

from model.parsing import parse
from model.vampire import VampireWrapper

import tempfile

import argparse

from bottle import route, post, run, request, response

parser = argparse.ArgumentParser(description='Run Vampire Server')
parser.add_argument("-vampire", "--vampire", required=True, action="store", dest="vampirePath", help="path to vampire-executable")
parser.add_argument("--verbose", action="store_true", help="use verbose logging")
args = parser.parse_args()

vampireWrapper = VampireWrapper(args.vampirePath)


def startVampire(manualCS):
    data = request.json
    fileContent = data['file']
    if fileContent == "":
        message = "User error: Input encoding must not be empty!"
        print(message)
        return json.dumps({
            "status" : "error",
            "message" : message
        })
    vampireUserOptions = data["vampireUserOptions"]
    if args.verbose:
        print("Vampire user options are: " + str(vampireUserOptions))
    temporaryFile = tempfile.NamedTemporaryFile()
    temporaryFile.write(str.encode(fileContent))
    temporaryFile.flush() # commit file buffer to disk so that Vampire can access it

    if manualCS:
        output = vampireWrapper.startManualCS(temporaryFile.name, vampireUserOptions, args.verbose)
    else:
        output = vampireWrapper.start(temporaryFile.name, vampireUserOptions, args.verbose)

    if vampireWrapper.vampireState == "error":
        message = "User error: Wrong options for Vampire or mistake in encoding"
        print(message)
        return json.dumps({
            "status" : "error",
            "message" : message
        })

    if args.verbose:
        print("Now parsing output from Vampire")
    lines = parse(output)
    temporaryFile.close()

    if args.verbose:
        print("Finishing with status success, Vampire is in state " + str(vampireWrapper.vampireState) + ", will return " + str(len(lines)) + " lines." )
    if manualCS:
        return json.dumps({
            'status' : "success",
            'vampireState' : vampireWrapper.vampireState, 
            'lines' : [line.to_json() for line in lines], 
        })
    else:
        return json.dumps({
            'status' : "success",
            'vampireState' : vampireWrapper.vampireState, 
            'lines' : [line.to_json() for line in lines]
        })

def allow_cors(func):
    """ this is a decorator which enable CORS for specified endpoint """
    def wrapper(*args, **kwargs):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, PUT, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'
        return func(*args, **kwargs)

    return wrapper

@route('/vampire/start', method='OPTIONS')
@allow_cors
def handle_cors_start():
    return {}

@route('/vampire/startmanualcs', method='OPTIONS')
@allow_cors
def handle_cors_startmanualcs():
    return {}

@route('/vampire/select', method='OPTIONS')
@allow_cors
def handle_cors_select():
    return {}

@post('/vampire/start')
@allow_cors
def handle_startVampire():
    if args.verbose:
        print("Entering handle_startVampire.")
    return startVampire(False)

@post('/vampire/startmanualcs')
@allow_cors
def handle_startVampireManualCS():
    if args.verbose:
        print("Entering handle_startVampireManualCS.")
    return startVampire(True)

@post('/vampire/select')
@allow_cors
def handle_selection():    
    if args.verbose:
        print("Entering handle_selection.")

    data = request.json
    selectedId = int(data['id'])
    if args.verbose:
        print("Selected id is " + str(selectedId))

    if(vampireWrapper.vampireState != "running"):
        message = "User error: Vampire is not running, so it makes no sense to perform selection!"
        print(message)
        return json.dumps({
            'status' : "error",
            "message" : message,    
            'vampireState' : vampireWrapper.vampireState
        })
    # TODO: check that selectedId was accepted by Vampire
    output = vampireWrapper.select(selectedId, args.verbose)

    if args.verbose:
        print("Now parsing output from Vampire")
    lines = parse(output)

    if args.verbose:
        print("Finishing with status success, Vampire is in state " + str(vampireWrapper.vampireState) + ", will return " + str(len(lines)) + " lines." )
    return json.dumps({
        "status" : "success",
        'vampireState' : vampireWrapper.vampireState, 
        'lines' : [line.to_json() for line in lines], 
    })  

if __name__ == '__main__':
    run(host='localhost', port=5000, debug=True)
