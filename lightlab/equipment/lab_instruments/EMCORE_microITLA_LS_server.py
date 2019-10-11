#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 10 11:08:50 2019

@author: pi


Runs continuously on host machine
Make sure PYTHONPATH points to folder containing itla_msa_modules
"""

# zmq
import time
import zmq

# NEC
try:
    from serial.tools.list_ports import comports
    from itla_msa_modules.emcore_app_pyserial import emcore_app as app
    import serial
except:
   raise


def command_from_name(command_name, laser, *argv):
    ''' Dictionary of commands from command name strings
    
        Returns:
            (str): command output 
    '''
        
    if command_name == "itla_on":
        return laser.itla_on()
    elif command_name == "itla_off":
        return laser.itla_off()
    
    # UNTESTED
    #elif command_name == "set_channel":
    #    return laser.set_channel(int(argv[0]), int(argv[1]))
    elif command_name == "get_channel_frequency":
        return laser.get_channel_frequency()
    
    elif command_name == "ask_device_ready":
        return laser.ask_device_ready()
    
    elif command_name == "set_output_power":
        return laser.set_output_power(float(argv[0][0]))
    elif command_name == "get_output_power":
        return laser.get_output_power()
    
    elif command_name == "set_first_channel_frequency":
        return laser.set_first_channel_frequency(float(argv[0][0]))
    elif command_name == "get_first_channel_frequency":
        return laser.get_first_channel_frequency()
    
    elif command_name == "set_ftf_frequency":
        return laser.set_ftf_frequency(float(argv[0][0]))
    elif command_name == "get_ftf_frequency":
        return laser.get_ftf_frequency()
    
    elif command_name == "get_device_type":
        return laser.get_device_type()
    elif command_name == "get_manufacturer":
        return laser.get_manufacturer()
    elif command_name == "get_manufactured_date":
        return laser.get_manufactured_date()
    elif command_name == "get_serial_number":
        return laser.get_serial_number()
    elif command_name == "get_io_capabilities":
        return laser.get_io_capabilities()
    elif command_name == "get_device_errors":
        return laser.get_device_errors()
    elif command_name == "get_module_monitors":
        return laser.get_module_monitors()
    elif command_name == "get_power_capabilities":
        return laser.get_power_capabilities()
    elif command_name == "get_grid_capabilities":
        return laser.get_grid_capabilities()
    elif command_name == "get_ftf_capabilities":
        return laser.get_ftf_capabilities()
    elif command_name == "get_frequency_capabilities":
        return laser.get_frequency_capabilities()
    
    elif command_name == "port_close":
        return laser.port_close()
    


class COM_manager():
    ''' Keeps track of USB ports
        Attr
            [str] portlist: e.g. ['/dev/ttyUSB0', '/dev/ttyUSB7', ..., '/dev/ttyUSB2']
    '''
    
    def __init__(self):
        self.portlist = self.scan_ports()
        self.unassigned_portlist = []
    
    def scan_ports(self):
        ''' Obtain a list of utilized USB ports
    
            Returns:
               [str] e.g. ['/dev/ttyUSB0', '/dev/ttyUSB7', ..., '/dev/ttyUSB2']
        '''  
        def Filter(string, substr):
            return [str for str in string if any(sub in str for sub in substr)] 
        return Filter([x[0] for x in comports()],["USB"])
    
    def remove_port(self, port):
        self.portlist.remove(port)
        
    def add_port(self, port):
        self.portlist.append(port)
        
    def add_unassigned_port(self, port):
        # Used during initilization
        self.unassigned_portlist.append(port)
        
    def remove_unassigned_port(self, port):
        # Used during initialization
        self.unassigned_portlist.remove(port)
    

class laser_id:
    ''' Holds information about a given laser. Used to manage connections.
    Attr
        (str) port: COM port e.g. /dev/ttyUSB0
        (str) serial_number: ITLA serial number e.g. CRTME2F008
        (emcore) handle: object on which commands are issued, defined by the port
    
    '''
    def __init__(self, serial_number=None, port=None):
        self.port = port
        self.serial_number = serial_number
        
    def set_handle(self, baud=9600, timeout=3, bytesize=8):
        self.handle = app(self.port, baud, timeout, bytesize)
        
    def reconnect(self, COMS, attempts=5, wait_time=2):
        ''' Attempt to reconnect this laser
            Args:
                (COM_manager) old_COMS : COM_manager w/ faulty port removed
        
            Returns:
                (COM_manager) new_COMS : succesful reconnection; here's the new port manager
                0 : unsuccesful reconnection
        '''      
        for n in range(attempts):
            print("Reconnection attempt " + str(n))
            try:
                # wait for reconnection
                time.sleep(wait_time)
                # Get the new COM port
                new_portlist = COM_manager().portlist
                changed = list(set(new_portlist).difference(COMS.portlist))
                print(changed)
                if len(changed) == 1:
                    print("Reseting")
                    print(COMS.portlist)
                    self.port = changed[0]
                    self.set_handle()
                    COMS.add_port(changed[0])
                    print(COMS.portlist)
                    print("Successful reset")
                    return 1
                else:
                    print("More than one port failed at the same time. Need full reset.")
                    return 0
                    #Some other error
            except:
                # Communication error -- try again
                continue
        # If it get here, irrepairable communication error
        return 0


def identify_all(COMS):
    ''' Obtain the serial number of all COM ports, allowing the lasers to be
    addressed by serial number
    Args:
        (COM_manager) COMS : current COM_manager
    
        Returns:
            {serial_number: laser_id} iddict: dictionary of laser_ID objects
    '''    
    iddict = {}
    for port in COMS.portlist:
        try:
            # Create new object
            laser_id_obj = laser_id('empty', port)
            laser_id_obj.set_handle()
            # Get its serial_number
            laser_id_obj.serial_number = laser_id_obj.handle.get_serial_number()
            iddict[laser_id_obj.serial_number] = laser_id_obj
        except:
            print('COM Port ' + port + ' failed, moving on')
            COMS.remove_port(port)
            COMS.add_unassigned_port(port)
            continue
    return iddict

def identify_single(port, COMS, attempts=1):
    ''' After initial pass, try to identify an unassigned ports 'attempts' timese 
    Args:
        (COM_manager) COMS : current COM_manager
    
        Returns:
            {serial_number: laser_id} iddict: dictionary of laser_ID objects
    '''    
    for n in range(attempts):
        print('Port ' + port + ' attempt ' + str(n))
        time.sleep(1)
        # Create new object
        laser_id_obj = laser_id('empty', port)
        try:
            laser_id_obj.set_handle()
            laser_id_obj.serial_number = laser_id_obj.handle.get_serial_number()
            # Clear this port
            COMS.remove_unassigned_port(port)
            COMS.add_port(port)
            # Move on
            print("Fixed")
            return laser_id_obj
        except:
            continue
    return 0



def run(socket, attempts=5):
    ''' Start running the zeromq server on the host machine
        For now, single port hardcoded --run all connections through here
        DOES NOT CURRENTLY TRACK MULTIPLE USERS
    '''  
    
    print("Starting server")
    # Populate laser dictionary
    initialized = 0
    while initialized == 0:
        try:
            COMS = COM_manager()
            iddict = identify_all(COMS)
            initialized = 1
        except KeyboardInterrupt:
            return 0
        except:
            print("Failed to initialize; trying again (ctrl-c to cancel)")
            continue
            
    print("Successfully interfaced :")
    for key in iddict.keys():
        print(key + ' | ' + str(iddict[key].port))
        
    # Run server
    try:    
        while True:
        
            message = socket.recv()
            print("Received request: %s" % message)
            
            # Parse request
            message_parsed = message.decode().split("___")
            serial_number = message_parsed[0]            
            command_name = message_parsed[1]
            if len(message_parsed) > 2:
                command_args = message_parsed[2:]
            else:
                command_args = None
            
            # Attempt to execute
            #for n in range(attempts):
            try:
                # Execute command
                command_output = command_from_name(command_name, iddict[serial_number].handle, command_args)
                #  Send reply back to client
                socket.send(str.encode(str(command_output)))
            # If manuel interruption, clean exit
            except KeyboardInterrupt:
                return
            # If communication error
            except Exception as e:
                print("Entering exception w/ error : ")
                print(e)
                print("This occured on serial " + serial_number + ", port " + iddict[serial_number].port)
                #
                print("Current ports : "+ str(COMS.portlist))

                # Attempt reconnection
                print("Removing faulty port from manager :")
                if iddict[serial_number].port in COMS.portlist:
                    COMS.remove_port(iddict[serial_number].port)
                print("Current ports : "+ str(COMS.portlist))
                print("Attempting reconnection : ")
                reconnected = iddict[serial_number].reconnect(COMS)
                if reconnected:
                    socket.send(str.encode("SERVER : Command failed to complete, but reconnection was successful. Please try again"))
                    #continue
                else:
                    socket.send(str.encode("SERVER : CRITICAL : Could not reconnect."))
                    #break

                
           
    # If server fails for any other reason (including KeyboardInterrupt)
    except:
        # Exit to clean exit command
        return
    
if __name__ == '__main__':
    # Setup server
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5555")
    # Run server
    run(socket)
    # Clean exit
    socket.close()
    context.destroy()

