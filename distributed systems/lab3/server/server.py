# coding=utf-8
# ------------------------------------------------------------------------------------------------------
# TDA596 - Lab 3 - Implementing Eventuall Consistency across several servers which has total ordering in their blackboards
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
from random import randint

from bottle import Bottle, run, request, template, HTTPResponse
import requests
# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()

    board = {} 

    modification_history = {} # history of actions

    # ------------------------------------------------------------------------------------------------------
    # BOARD FUNCTIONS
    # ------------------------------------------------------------------------------------------------------
    # Method for adding element to the board
    def add_new_element_to_store(node_id, random_id, entry_sequence, element):
        global board
        success = False
        try:
            board[(entry_sequence, random_id, node_id)] = element
            success = True
        except Exception as e:
            print e
        return success

    # Method for modifying an element from the board
    def modify_element_in_store(node_id, entry_sequence, random_id, modified_element):
        global board
        success = False
        try:
            print 'modifying in store. entry_sequence = {}, random_id = {}, node_id = {}'.format(entry_sequence, random_id, node_id)
            if (entry_sequence, random_id, node_id) in board:
                board[(entry_sequence, random_id, node_id)] = modified_element
            success = True
        except Exception as e:
            print e
        return success

    # Method for deleting element from board
    def delete_element_from_store(node_id, entry_sequence, random_id):
        global board
        success = False
        try:
            print 'deleting from store. entry_sequence = {}, random_id = {}, node_id = {}'.format(entry_sequence, random_id, node_id)
            if (entry_sequence, random_id, node_id) in board:
                del board[(entry_sequence, random_id, node_id)]
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

    # ---------------------------------------------------------------------------------------
    # A vessel upon adding something to it's own board will propagate the following:
    # entry = input text in the message
    # clock = it's logical clock
    # tiebreaker = the random id of the vessel that posted a message (or that is currently posting)
    # node_id = Vessel number, or rather IP
    # sender_id = Vessel number, for propagation of modify/delete-actions
    # sender_random_id = it's random id, for propagation of modify/delete-actions
    # ---------------------------------------------------------------------------------------

    def propagate_to_vessels_on_thread(action, element_id = None, second_id=None, third_id=None, entry = None):
        global random_id, node_id
        path = '/propagate/{}/{}'.format(action, element_id)
        payload = {
            'entry':entry,
            'clock':logical_clock,
            'tiebreaker':second_id,
            'node_id':third_id,
            'sender_id':node_id,
            'sender_random_id':random_id
        }
        th = Thread(target=propagate_to_vessels, args=[path, payload]) # propagates entry, logical clock and a random id to solve tiebreakers
        th.daemon = True
        th.start()


    # ------------------------------------------------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------------------------------------------------
    @app.route('/')
    def index():
        global board, node_id, logical_clock
        return template(
            'server/index.tpl',
            board_title='Vessel {}'.format(node_id),
            board_dict=sorted(board.iteritems(), key=lambda (k,v): k),
            members_name_string='Group 88',
            logical_clock=logical_clock
        )

    @app.get('/board')
    def get_board():
        global board, node_id, logical_clock
        return template(
            'server/boardcontents_template.tpl',
            board_title='Vessel {}'.format(node_id),
            board_dict=sorted(board.iteritems(), key= lambda (k,v): k),
            logical_clock=logical_clock
        )

    @app.post('/board')
    def client_add_received():
        global board, node_id, logical_clock, random_id
        try:
            new_entry = request.forms.get('entry') # a new entry
            add_new_element_to_store(node_id, random_id,logical_clock, new_entry) # adds the new entry at the highest id
            propagate_to_vessels_on_thread('add', entry = new_entry, second_id=random_id, third_id=node_id)
            logical_clock = logical_clock +1 # increment its logical clock upon event
            return HTTPResponse(status=200)
        except Exception as e:
            print e
        return HTTPResponse(status=500)

    #-------------------------------------------------------------------------------------------------------------------------
    # Method for handling acitons performed on a vessels board
    # 
    # new_modification : contains information about the sender of an action, such as clock of the sender, senders random id, sender id and action
    # board_key : contains information about the owner of the entry, such as Vessel ID, sequence number of entry and random_id
    # 
    # MODIFY
    # If there occurs a modify action on your own board, you will first check if it should be done, by comparing the latest
    # update vs the one that is recieved.
    # See should_modify() for conditions
    # If the modify you are about to perform is "newer"/"fresher", it will be done, and then propagated to all other vessels
    #
    # DELETE
    # If there occurs a delete of an entry, you will set it as the latest modification done, and it will "beat" incoming
    # actions, since you can't modify something that has been deleted. Which means that the delete action beats all actions
    # So if you have many modify-request on a certain element with a "low" logical clock, and then a delete request with a higher clock
    # It implies that the deletion will take place nevertheless, so it will be prioritized.
    # Propagates to all other vessels when done.
    #-------------------------------------------------------------------------------------------------------------------------
    
    @app.post('/board/<element_id:int>/<element_random_id:int>/<element_node_id:int>')
    def client_action_received(element_id, element_random_id, element_node_id):
        global logical_clock, node_id, random_id
        print 'client_action_received. element_id = {},  element_random_id = {}, element_node_id = {}'.format(element_id, element_random_id, element_node_id)
        action = int(request.forms.get('delete')) #value depending on action
        entry = request.forms.get('entry') # the entry in question
        int_id = int(element_id) # sequence number
        int_random_id = int(element_random_id) # random_id
        logical_clock = logical_clock +1 # logical clock
        new_modification = (logical_clock, random_id, node_id, action, entry) 
        board_key = (element_node_id, int_id, int_random_id)
        if action == 0: # modify action is recieved
            modify = False
            if should_modify(new_modification, board_key): # checks if the modification is old or a future modification
                modification_history[board_key] = new_modification # sets the latest modification to the newest
                modify_element_in_store(element_node_id, int_id, int_random_id, entry) # modify the entry at a given index
                propagate_to_vessels_on_thread('modify', element_id=int_id, second_id=int_random_id, third_id=element_node_id, entry=entry) # propagate it to all other vessels
        elif action == 1: # delete action is recieved
            modification_history[board_key] = new_modification # sets the latest action as a delete
            delete_element_from_store(element_node_id, int_id, int_random_id) # delete the entry at the given index
            propagate_to_vessels_on_thread('delete', element_id=int_id, second_id=int_random_id, third_id=element_node_id) # propagate it to all other vessels
        else:
            return HTTPResponse(status=400)
        return HTTPResponse(status=200)

    #-------------------------------------------------------------------------------------------------------------------------
    # Method for recieving a propagation, which can either be 'add', 'delete' or 'modify'
    # If an add is propagated to you, you will check several things.
    #
    # 1) Is there an history? If not, the entry is added
    # 2) If there is an 'delete', do a bunch of things before doing the deletion depending on the history of the entry, written below
    # 3) If there is an 'modify', do a bunch of things before doing the modification depending on the history of the entry, written below
    #
    # HANDLING CONCURRENT MODIFICATIONS AND DELETIONS
    #
    # When an modify or delete request is recieved, it will collect some information before choosing wheater it should modify or delete.
    #
    # board_key : contains information about the owner of the entry, such as Vessel ID, sequence number of entry and random_id
    # new_modification : contains information about the sender, such as clock, senders random id, sender id and action
    # last_update : will contain the latest action on an entry.
    #
    # In the if-statement it will use this information to determine wheater it should update the entry with the incoming
    # action or not by checking the history of the entry and comparing to the latest action made, see should_modify()
    #--------------------------------------------------------------------------------------------------------------------------

    @app.post('/propagate/<action>/<element_id>')
    def propagation_received(action, element_id):
        global board, node_id, logical_clock
        entry = request.forms.get('entry')
        incoming_clock = int(request.forms.get('clock')) 
        incoming_random_id = int(request.forms.get('tiebreaker'))
        incoming_node_id = int(request.forms.get('node_id'))
        logical_clock = max(logical_clock, incoming_clock + 1)
        if action == 'add':
            try:
                board_key = (incoming_node_id, incoming_clock, incoming_random_id)
                add = False
                if board_key in modification_history:
                    last_update = modification_history[board_key]
                    if last_update[3] == 0: # if there is a modification before the add has occured
                        new_entry = last_update[4] # the entry becomes what the latest modify should be
                        add = True # add succesful
                else:
                    add = True # add succesful
                if add:
                    add_new_element_to_store(incoming_node_id, incoming_random_id, incoming_clock, entry) # add the entry
            except Exception as e:
                print e
        elif action == 'delete':
            try:
                sender_id = int(request.forms.get('sender_id'))
                sender_random_id = int(request.forms.get('sender_random_id'))
                int_id = int(element_id) # element id is string but board keys are integers.
                board_key = (incoming_node_id, int_id, incoming_random_id)
                new_modification = (incoming_clock, sender_random_id, sender_id, 1) # delete action properties
                modification_history[board_key] = new_modification # sets delete as the newest action performed
                delete_element_from_store(incoming_node_id, int_id, incoming_random_id)
            except Exception as e:
                print e
        elif action == 'modify':
            try:
                sender_id = int(request.forms.get('sender_id'))
                sender_random_id = int(request.forms.get('sender_random_id'))
                int_id = int(element_id) # element id is string but board keys are integers.
                board_key = (incoming_node_id, int_id, incoming_random_id)
                new_modification = (incoming_clock, sender_random_id, sender_id, 0, entry) # modify action properties
                if should_modify(new_modification, board_key): # checks the latest modification action vs the one the one just recieved
                    modification_history[board_key] = new_modification # if it should update, set the latest modification action to the one just performed
                    modify_element_in_store(incoming_node_id, int_id, incoming_random_id, entry)
            except Exception as e:
                print e
        else:
            return HTTPResponse(status=500)
        return HTTPResponse(status=200)

    #-----------------------------------------------------------------------------------------------------------------------
    # Method for checking previous history at an entry
    #
    # If there are no modifications before, simply add the modification to the history
    # if there is an action (previously) made on the entry, compare their clock, random_id and node_id (tiebreaker), check newer_modification()
    # This is to handle concurrent modifications of an entry, let's say if someone recieves two modify requests with
    # LC = 2 and LC = 9, this will mean that 9 will eventually happen in the future, so its unessecary to do 2..8 and then 9
    # and directly save you the trouble by choosing LC = 9 
    #-----------------------------------------------------------------------------------------------------------------------

    def should_modify(new_modification, board_key):
        global modification_history
        modify = False
        if board_key in modification_history: # There are previous modifications on this element
            last_modification = modification_history[board_key]
            if newer_modification(new_modification, last_modification):
                modify = True
        else:
            modify = True
        return modify

    #-----------------------------------------------------------------------------------------------------------------------
    # Condition method regarding modifications
    # Method takes two arugments, a new modification and the latest modification made on an entry
    # It first compares Logical Clocks, if they both are the same
    # It will continue by also compare their senders random id
    # If those two conditions are the same, it will finish with the last tiebreaker, the node_id (IP)
    # to determine in which one is to be made
    #-----------------------------------------------------------------------------------------------------------------------

    def newer_modification(new_modification, last_modification):
        if last_modification[3] == 1:
            return False
        if new_modification[0] > last_modification[0]:
            return True
        elif new_modification[0] == last_modification[0]:
            if new_modification[1] > last_modification[1]:
                return True
            elif new_modification[1] == last_modification[1]:
                if new_modification[2] > new_modification[2]:
                    return True
        return False



    # Used for testing to compare the entries at specific ID between vessels.
    @app.get('/entry/get/<element_id:int>')
    def get_entry(element_id):
        if element_id < len(board):
            sorted_items = sorted(board.items(), key=lambda (k,v):(k[1],k[0]) )
            print 'returning entry {}'.format(sorted_items[element_id][1])
            return HTTPResponse(status=200, body=json.dumps({"entry": sorted_items[element_id][1]}))
        else:
            print 'returning entry {}'.format(None)
            return HTTPResponse(status=200, body=json.dumps({"entry": None}))
        return HTTPResponse(status=200)

    @app.get('/random_id/get')
    def get_random_id():
        global random_id
        return HTTPResponse(status=200, body=json.dumps({"random_id": random_id}))
        
    # ------------------------------------------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------------------------------------------
    def main():
        global vessel_list, node_id, app, logical_clock, random_id

        port = 80
        parser = argparse.ArgumentParser(description='Your own implementation of the distributed blackboard')
        parser.add_argument('--id', nargs='?', dest='nid', default=1, type=int, help='This server ID')
        parser.add_argument('--vessels', nargs='?', dest='nbv', default=1, type=int, help='The total number of vessels present in the system')
        args = parser.parse_args()
        node_id = args.nid

        logical_clock = 0
        print "Logical clock is {}".format(logical_clock)

        vessel_list = dict()


        # We need to write the other vessels IP, based on the knowledge of their number
        for i in range(1, (args.nbv + 1)): # Make sure vessel number is included in list of vessels.
            vessel_list[str(i)] = '10.1.0.{}'.format(str(i))
        
        max_random_id = (len(vessel_list) * 20) + 1 # Make sure we have enough random IDs to choose from.
        random_id = randint(1, max_random_id)
        print 'random id = {}'.format(random_id)

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
