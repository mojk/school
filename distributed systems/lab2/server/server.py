# coding=utf-8
# ------------------------------------------------------------------------------------------------------
# TDA596 - Lab 2
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
from requests import ConnectionError
# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()

    board = {} 

    # ------------------------------------------------------------------------------------------------------
    # BOARD FUNCTIONS
    # ------------------------------------------------------------------------------------------------------

    # Method for adding a new element to the board
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
            if res.status_code == 200: # Only an ok response is considered a successful rest call.
                success = True
        except Exception as e:
            success = False
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
        global board, node_id, leader_id, leader_random_id
        leader = 'Vessel {}'.format(leader_id) if (leader_id != 0) else "No leader elected"
        return template(
            'server/index.tpl',
            board_title='Vessel {}'.format(node_id),
            board_leader='Leader: {}'.format(leader),
            board_leader_randomid='Leader random id: {}'.format(leader_random_id),
            board_dict=sorted(board.iteritems(),
            key=lambda (k,v):k),
            members_name_string='Group 88'
        )

    @app.get('/board')
    def get_board():
        global board, node_id, leader_id, leader_random_id
        leader = 'Vessel {}'.format(leader_id) if (leader_id != 0) else "No leader elected"
        return template(
            'server/boardcontents_template.tpl',
            board_title='Vessel {}'.format(node_id),
            board_leader='Leader: {}'.format(leader),
            board_leader_randomid='Leader random id: {}'.format(leader_random_id),
            board_dict=sorted(board.iteritems(),
            key= lambda (k,v):k)
        )

    @app.post('/board')
    def client_add_received():
        global board, node_id, leader_ip
        contact = False
        try:
            new_entry = request.forms.get('entry') # a new entry
            node_ip = '10.1.0.{}'.format(node_id)
            if(node_ip == leader_ip):
                new_id = len(board) # the entry will be last in the "list" that the board is, so it will have the highest id
                add_new_element_to_store(new_id, new_entry) # adds the new entry at the highest id
                propagate_to_vessels_on_thread('add', element_id=new_id, entry = new_entry)
            else:
                # Before sending to the leader, we check if the leader is still alive
                try:
                    contact = contact_vessel(leader_ip, '/status', req = 'GET') # check ping_vessel() for the path
                    # successfully contacted the leader
                except Exception as e: 
                    print e

                if (contact): # If the leader is alive -> send the new entry to the leader on a new thread
                    start_thread(contact_vessel, leader_ip, '/board', {'entry': new_entry},'POST')
                else: # If the leader is dead, clear everyones current leader and re-initiate LE
                    print "The leader is dead ({}), re-initiating LE".format(leader_ip)
                    clear_leader()
                    propagate_to_vessels('/leader/clear', req='GET')
                    wait_and_start_election()
                return HTTPResponse(status=200)
        except Exception as e:
            print e
        return HTTPResponse(status=500)

    @app.post('/board/<element_id:int>')
    def client_action_received(element_id):
        global board, node_id, leader_ip
        try:
            entry = request.forms.get('entry') # the entry in question
            int_id = int(element_id) # the id
            action = int(request.forms.get('delete')) # value depending on action
            node_ip = '10.1.0.{}'.format(node_id)

            if(node_ip == leader_ip): # If you are the leader, you should propagate to others
                if action == 0: # modify
                    if int_id in board:
                        modify_element_in_store(int_id, entry) # modify the entry at a given int_id
                    propagate_to_vessels_on_thread('modify', int_id, entry) # propagate it to all other vessels
                elif action == 1: # delete
                    if int_id in board:
                        delete_element_from_store(int_id) # delete the entry at the given int_id
                    propagate_to_vessels_on_thread('delete', int_id) # propagate it to all other vessels
                else:
                    return HTTPResponse(status=400)

            else: # If you are not the leader, you should propagate your action to the leader
                start_thread(contact_vessel, leader_ip, '/board/{}'.format(int_id), {'entry': entry, 'delete': action},'POST')

            return HTTPResponse(status=200)
        except Exception as e:
            print e
        return HTTPResponse(status=500)

    # Action is 'add', 'delete' or  'modify. If not, status code 500 is returned.'
    @app.post('/propagate/<action>/<element_id>')
    def propagation_received(action, element_id):
        global board, node_id
        entry = request.forms.get('entry')
        int_id = int(element_id) # element_id is string but board keys are integers.
        try:
            if action == 'add':
                add_new_element_to_store(int_id, entry)
            elif action == 'delete':
                if int_id in board:
                    delete_element_from_store(int_id)
            elif action == 'modify':
                if (int_id in board):
                    modify_element_in_store(int_id, entry)
            else:
                return HTTPResponse(status=500)
        except Exception as e:
            print e
        return HTTPResponse(status=200)

    # This is the initiation method used when starting LE and restarting LE if the current Leader has died.
    # What we do is simply clearing the "nominated" leader
    @app.get('/leader/clear')
    def clear_leader():
        global leader_ip, leader_id, leader_random_id
        leader_ip = None
        leader_id = 0
        leader_random_id = 0
        print 'Resetting leader'
        return HTTPResponse(status=200)

    # This is the method for starting LE, where we begin by clearing all leader values,
    # The vessel which initiated LE finds the next neighbor which is alive, and starts comparing leaders.
    def start_election():
        global leader_id, leader_ip, leader_random_id, node_id
        alive_neighbor = contact_neighbor() # fetching the closest alive neighbor
        vessel_ip = '10.1.0.{}'.format(node_id)
        if alive_neighbor == vessel_ip: # If ring is only one vessel, the next alive neighbour is self.
            leader_id = node_id
            leader_ip = vessel_ip
            leader_random_id = random_id
        else:
            print '{} is alive,'.format(alive_neighbor) + ' sending to {}'.format(alive_neighbor)
            start_thread(contact_vessel, alive_neighbor, '/election/continue',{'leader_id':node_id, 'random_id': random_id},'POST')
        return HTTPResponse(status = 200)

    # This is used for contacting a vessel to see if it's alive or dead
    @app.get('/status')
    def ping_vessel():
        return HTTPResponse(status = 200)

    # This method is used for the second and later steps in the LE-algorithm, where we compare leaders from one vessel to another.
    # When a Vessel receives data from it's predecessor we've implemented two checks:
        # Scenario 1 : Checking if our random id is bigger than the received id
        # Scenario 2 : Checking if we have the same random id and if our node_id is bigger
    # If either of these two is True, we compare our own id instead of the received id
        # Scenario 1 : Check if the new random id is bigger that of our nominated leader
        # Scenario 2 : Check if the new random id is equal to the nominated leader and the new node id is greater
    # If either of these two is True, the new ID is the leader.
    # When the received id is not greater than our nominated leader, that means no vessel in the ring has proposed a new
    # candidate which is larger than the one we have nominated, and so the algorithm terminates.
  
    @app.post('/election/continue')
    def continue_election():
        global leader_id, leader_ip, leader_random_id, node_id
        new_random_id = int(request.forms.get('random_id'))
        new_leader_id = int(request.forms.get('leader_id'))

        if(random_id > new_random_id or (random_id == new_random_id and node_id > new_leader_id)):
            new_random_id = random_id
            new_leader_id = node_id

        if(new_random_id > leader_random_id or (new_random_id == leader_random_id and new_leader_id > leader_id)):
            print 'New leader is vessel{} '.format(leader_id)
            leader_id = new_leader_id
            leader_ip = '10.1.0.{}'.format(leader_id)
            leader_random_id = new_random_id
            print 'Sending new_leader_id={}, new_random_id={} to vessel{}'.format(new_leader_id,new_random_id,leader_id)
        
            # Before propagating the newly decided leader we first try to contact the next vessel 
            # in order to check if it's alive
            alive_neighbor = contact_neighbor()

            # When a vessel was successfully contacted, we continue the leader election      
            print '{} is alive,'.format(alive_neighbor) + ' sending to {}'.format(alive_neighbor)
            # continuing the LE to the next alive vessel in the ring on a new thread
            vessel_ip = '10.1.0.{}'.format(node_id)
            if alive_neighbor != vessel_ip: # If ring is only one vessel, the next alive neighbour is self.
                start_thread(contact_vessel, alive_neighbor, '/election/continue',{'leader_id':leader_id, 'random_id': leader_random_id},'POST')
        else:
            print 'Terminating. Leader is vessel{}'.format(leader_id)
        return HTTPResponse(status=200)
    
    # Method used for LE to contact the next available neighbor
    # using the variable n, we iterate the "next in line" and +1 if it's not available
    # We check if the next vessel is alive by a simple ping, returns the vessel_ip
    def contact_neighbor():
        global node_id
        contact = False
        n = 0 # iterating variable, starting to 1 since we don't want to contact ourselves
        while(not (contact and n <= len(vessel_list))):
            try:
                vessel_ip = '10.1.0.{}'.format((int(node_id)+n)%len(vessel_list) + 1) # IP of the vessel its trying to contact,
                print 'Trying to contact {}'.format(vessel_ip) # trying to contact next vessel
                n = n + 1 # increasing 
                self_ip = '10.1.0.{}'.format(node_id)
                if vessel_ip != self_ip: # If ring is only one vessel, the next alive neighbour is self.
                    contact = contact_vessel(vessel_ip, '/status', req = 'GET') # contact becomes true if this returns status = 200
                else:
                    return self_ip
            except Exception as e: 
                print e
        print "Next alive neighbour is {}".format(vessel_ip) # debug
        return vessel_ip

    # Used for testing to check that all vessels have the same leader.
    @app.get('/leader/get')
    def get_leader():
        global leader_ip
        return HTTPResponse(status=200, body=json.dumps({"leader_ip": leader_ip}))

    # Used for testing to compare the entries at specific ID between vessels.
    @app.get('/entry/get/<element_id:int>')
    def get_entry(element_id):
        global leader_ip
        if element_id in board:
            return HTTPResponse(status=200, body=json.dumps({"entry": board[element_id]}))
        else:
            return HTTPResponse(status=200, body=json.dumps({"entry": None}))

    # Helper method for starting threads in one line.
    def start_thread(target, vessel_ip, path, payload, req = 'POST'):
        th = Thread(target=target, args=[vessel_ip, path,payload,req])
        th.daemon = True
        th.start()

    def wait_and_start_election():
        time.sleep(5)
        start_election()
        
    # ------------------------------------------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------------------------------------------

    def main():
        global vessel_list, node_id, app, leader_ip, leader_id, random_id, leader_random_id

        port = 80
        parser = argparse.ArgumentParser(description='Your own implementation of the distributed blackboard')
        parser.add_argument('--id', nargs='?', dest='nid', default=1, type=int, help='This server ID')
        parser.add_argument('--vessels', nargs='?', dest='nbv', default=1, type=int, help='The total number of vessels present in the system')
        args = parser.parse_args()
        node_id = args.nid
        vessel_list = dict()
        # We need to write the other vessels IP, based on the knowledge of their number
        for i in range(1, (args.nbv + 1)): # Make sure vessel number 8 is included in list of vessels.
            vessel_list[str(i)] = '10.1.0.{}'.format(str(i))

        clear_leader()

        max_random_id = (len(vessel_list) * 2) + 1 # Make sure we have enough random IDs to choose from.
        random_id = randint(1, max_random_id)
        print 'random id = {}'.format(random_id)

        try:
            # Create a thread that sleeps for 5 seconds, then starts an election.
            # We sleep to make sure all servers have started before election starts.
            th = Thread(target=wait_and_start_election)
            th.daemon = True
            th.start()
            run(app, host=vessel_list[str(node_id)], port=port)
        except Exception as e:
            print e

    if __name__ == '__main__':
        main()
except Exception as e:
        traceback.print_exc()
        while True:
            time.sleep(60.)