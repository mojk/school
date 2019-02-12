# coding=utf-8
# ------------------------------------------------------------------------------------------------------
# TDA596 - Lab 1
# server/server.py
# Input: Node_ID total_number_of_ID
# Students: Lage Bergman & Mikael Gordani
# ------------------------------------------------------------------------------------------------------
import traceback
import sys
import time
import json
import argparse
from threading import Thread

from bottle import Bottle, run, request, template, HTTPResponse
import requests
# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()

    board = {} 


    # ------------------------------------------------------------------------------------------------------
    # BOARD FUNCTIONS
    # ------------------------------------------------------------------------------------------------------
    def add_new_element_to_store(entry_sequence, element, is_propagated_call=False):
        global board, node_id
        success = False
        try:
            board[entry_sequence] = element
            success = True
        except Exception as e:
            print e
        return success

    # Method for modifying an element from the board
    def modify_element_in_store(entry_sequence, modified_element, is_propagated_call = False):
        global board, node_id
        success = False
        try:
            board[entry_sequence] = modified_element
            success = True
        except Exception as e:
            print e
        return success
    # Method for deleting element from board
    def delete_element_from_store(entry_sequence, is_propagated_call = False):
        global board, node_id
        success = False
        try:
            del board[entry_sequence]
            success = True
        except Exception as e:
            print e
        return success

    # ------------------------------------------------------------------------------------------------------
    # DISTRIBUTED COMMUNICATIONS FUNCTIONS
    # ------------------------------------------------------------------------------------------------------
    def contact_vessel(vessel_ip, path, payload=None, req='POST'):
        # Try to contact another server (vessel) through a POST or GET, once
        success = False
        try:
            if 'POST' in req:
                res = requests.post('http://{}{}'.format(vessel_ip, path), data=payload)
            elif 'GET' in req:
                res = requests.get('http://{}{}'.format(vessel_ip, path))
            else:
                print 'Non implemented feature!'
            # result is in res.text or res.json()
            print(res.text)
            if res.status_code == 200:
                success = True
        except Exception as e:
            print e
        return success

    def propagate_to_vessels(path, payload = None, req = 'POST'):
        global vessel_list, node_id

        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id: # don't propagate to yourself
                success = contact_vessel(vessel_ip, path, payload, req)
                if not success:
                    print "\n\nCould not contact vessel {}\n\n".format(vessel_id)

    def propagate_to_vessels_on_thread(action, element_id = None, entry = None):
        path = '/propagate/{}/{}'.format(action, element_id)
        th = Thread(target=propagate_to_vessels, args=[path,{'entry':entry}])
        th.daemon = True
        th.start()


    # ------------------------------------------------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) should be done for get, and one for post
    # ------------------------------------------------------------------------------------------------------
    @app.route('/')
    def index():
        global board, node_id
        return template('server/index.tpl', board_title='Vessel {}'.format(node_id), board_dict=sorted(board.iteritems(), key=lambda (k,v):k), members_name_string='YOUR NAME')

    @app.get('/board')
    def get_board():
        global board, node_id
        return template('server/boardcontents_template.tpl',board_title='Vessel {}'.format(node_id), board_dict=sorted(board.iteritems(), key= lambda (k,v):k))

    @app.post('/board')
    def client_add_received():
        global board, node_id
        try:
            new_entry = request.forms.get('entry') # a new entry
            new_id = len(board) # the entry will be last in the "list" that the board is, so it will have the highest id
            add_new_element_to_store(new_id, new_entry) # adds the new entry at the highest id
            propagate_to_vessels_on_thread('add', entry = new_entry)
            return HTTPResponse(status=200)
        except Exception as e:
            print e
        return HTTPResponse(status=500)

    @app.post('/board/<element_id:int>/')
    def client_action_received(element_id):
        action = int(request.forms.get('delete')) #value depending on action
        entry = request.forms.get('entry') # the entry in question
        index = int(element_id) # index of the entry
        if action == 0: # modify
            modify_element_in_store(index, entry) # modify the entry at a given index
            propagate_to_vessels_on_thread('modify', index, entry) # propagate it to all other vessels
        elif action == 1: # delete
            delete_element_from_store(index) # delete the entry at the given index
            propagate_to_vessels_on_thread('delete', index) # propagate it to all other vessels
        else:
            return HTTPResponse(status=400)
        return HTTPResponse(status=200)

    # Action is 'add', 'delete' or  'modify. If not, status code 500 is returned.'
    @app.post('/propagate/<action>/<element_id>')
    def propagation_received(action, element_id):
        global board, node_id
        entry = request.forms.get('entry')
        if action == 'add':
            try:
                # Add entry to end of board. Does not guarantee consistency
                #  but prevents concurrent messages from overwriting each other.
                add_new_element_to_store(len(board), entry)
            except Exception as e:
                print e
        elif action == 'delete':
            try:
                int_id = int(element_id) # element id is string but board keys are integers.
                if not int_id in board:
                    return HTTPResponse(status=200) # Entry already not in board
                delete_element_from_store(int_id)
            except Exception as e:
                print e
        elif action == 'modify':
            try:
                int_id = int(element_id) # element id is string but board keys are integers.
                if (not int_id in board):
                    return HTTPResponse(status=200) # Entry not in board
                modify_element_in_store(int_id, entry)
            except Exception as e:
                print e
        else:
            return HTTPResponse(status=500)
        return HTTPResponse(status=200)
        
    # ------------------------------------------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------------------------------------------
    def main():
        global vessel_list, node_id, app

        port = 80
        parser = argparse.ArgumentParser(description='Your own implementation of the distributed blackboard')
        parser.add_argument('--id', nargs='?', dest='nid', default=1, type=int, help='This server ID')
        parser.add_argument('--vessels', nargs='?', dest='nbv', default=1, type=int, help='The total number of vessels present in the system')
        args = parser.parse_args()
        node_id = args.nid
        vessel_list = dict()
        # We need to write the other vessels IP, based on the knowledge of their number
        for i in range(1, (args.nbv + 1)): # Make sure vessel number is included in list of vessels.
            vessel_list[str(i)] = '10.1.0.{}'.format(str(i))

        try:
            run(app, host=vessel_list[str(node_id)], port=port)
        except Exception as e:
            print e

    if __name__ == '__main__':
        main()
except Exception as e:
        traceback.print_exc()
        while True:
            time.sleep(60.)