from time import sleep
from beamngpy import BeamNGpy, Scenario, Vehicle
from beamngpy.sensors import Lidar, GPS
import math
import argparse

from beam_fix import *

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Start BeamNG simulation with multiple vehicles')
    parser.add_argument('-n', '--num-cars', type=int, default=3,
                        help='Number of cars in the simulation (default: 3)')
    parser.add_argument('-s', '--spacing', type=float, default=5.0,
                        help='Spacing between cars in meters, car\'s length included (default: 5.0)')
    parser.add_argument('-p', '--base-port', type=int, default=12345,
                        help='Base UDP port for vehicle controllers (default: 12345)')
    parser.add_argument('-b', '--beamng-port', type=int, default=64256,
                        help='BeamNG connection port (default: 64256)')
    parser.add_argument('-S', '--time-scale', type=float, default=1,
                        help='Time scale (default: 1)')
    args = parser.parse_args()

    # Initialize BeamNG connection
    bng = BeamNGpy('localhost', args.beamng_port)
    bng.open(launch=True)

    scenario = Scenario('smallgrid', 'Five Cars in Line')

    # Starting position for the first car
    start_x = 0
    start_y = 0
    start_z = 0

    # Spacing between cars (in meters)
    spacing = args.spacing

    # Assign a unique color to each car
    colors = [
        (1, 0, 0, 1),   # Red
        (0, 1, 0, 1),   # Green
        (0, 0, 1, 1),   # Blue
        (1, 1, 0, 1),   # Yellow
        (1, 0, 1, 1),   # Magenta
        (0, 1, 1, 1),   # Cyan
        (1, 0.5, 0, 1), # Orange
        (0.5, 0, 0.5, 1), # Purple
    ]

    # Create cars in a line
    vehicles: list[Vehicle] = []
    for i in range(args.num_cars):
        # Create vehicle with unique name

        vehicle_name = f'car_{i+1}'

        color = colors[i % len(colors)]
        vehicle = Vehicle(vehicle_name, model='midsize', color=color, license=f"CAR-{i}")

        # Calculate position (spacing them along the X axis)
        pos_x = start_x - (i * spacing)
        pos_y = start_y
        pos_z = start_z

        # Add vehicle to scenario at calculated position
        scenario.add_vehicle(vehicle, pos=(pos_x, pos_y, pos_z), rot_quat=(0, 0, math.sin(-math.pi/4), math.cos(-math.pi/4)))
        #scenario.add_vehicle(vehicle, pos=(pos_x, pos_y, pos_z))
        vehicles.append(vehicle)
        

    # Make the scenario
    scenario.make(bng)

    # Load and start the scenario
    bng.scenario.load(scenario)
    bng.scenario.start()

    for v in vehicles:
        # Set gearbox to realistic mode using Lua command
        v.queue_lua_command("electrics.setGearboxMode('realistic')")
        
        # Release parking brake (set to 0)
        v.control(parkingbrake=0)
        
        # Put vehicle in drive (gear = 2 for automatic transmissions)
        v.control(gear=2)

    sleep(0.33)

    BASE_PORT = args.base_port
    port = BASE_PORT
    dummy_con = DummyConnection(BASE_PORT)
    thread = BeamFixThread(dummy_con)
    thread.start()

    for v in vehicles:
        print(f"Starting controller {port}")
        v.queue_lua_command(f"controller.loadControllerExternal('tech/vehicleSystemsCoupling', 'vehicleSystemsCoupling', {{udpSendPort = {port}, udpReceivePort = {port+1}}})", False)
        port += 2

        thread.message_queue.put("ADD")

    print(f"Setting time scale to {args.time_scale}")
    bng.queue_lua_command(f"be:setSimulationTimeScale({args.time_scale})")

    thread.stop() # type: ignore
    thread.join() # type: ignore
