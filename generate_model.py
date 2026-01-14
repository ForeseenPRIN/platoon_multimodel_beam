#!/usr/bin/env python3
"""
Generate FMU co-simulation JSON configuration files for vehicle platoons.
Supports V2N (Vehicle-to-Network with MEC controller) and V2V (Vehicle-to-Vehicle with CACC controllers).
"""

import json
import argparse
import sys


def generate_v2n_model(num_cars, base_port):
    """Generate V2N model with MEC controller"""
    
    fmus = {
        "{Controller}": "controller.fmu",
        "{Driver}": "driver.fmu",
        "{MEC}": "MEC.fmu"
    }
    
    # Add car FMUs
    for i in range(num_cars):
        fmus[f"{{Car{i}}}"] = "BeamNG-FMI2.fmu"
    
    connections = {}
    parameters = {}
    
    # Generate connections and parameters for each car
    for i in range(num_cars):
        car_name = f"{{Car{i}}}"
        ctrl_name = f"{{Controller}}.ctrl{i}"
        mec_prefix = f"{{MEC}}.MEC0.platoon_0_{i}"
        
        # Car body state to Controller and MEC
        connections[f"{car_name}.C{i}.body_state.posX"] = [f"{ctrl_name}.posX", f"{mec_prefix}_pos_x"]
        connections[f"{car_name}.C{i}.body_state.posY"] = [f"{ctrl_name}.posY"]
        connections[f"{car_name}.C{i}.body_state.posZ"] = [f"{ctrl_name}.posZ"]
        connections[f"{car_name}.C{i}.body_state.velX"] = [f"{ctrl_name}.velX", f"{mec_prefix}_speed"]
        connections[f"{car_name}.C{i}.body_state.velY"] = [f"{ctrl_name}.velY"]
        connections[f"{car_name}.C{i}.body_state.velZ"] = [f"{ctrl_name}.velZ"]
        connections[f"{car_name}.C{i}.body_state.accX"] = [f"{ctrl_name}.accX"]
        connections[f"{car_name}.C{i}.body_state.accY"] = [f"{ctrl_name}.accY"]
        connections[f"{car_name}.C{i}.body_state.accZ"] = [f"{ctrl_name}.accZ"]
        connections[f"{car_name}.C{i}.body_state.roll"] = [f"{ctrl_name}.roll"]
        connections[f"{car_name}.C{i}.body_state.pitch"] = [f"{ctrl_name}.pitch"]
        connections[f"{car_name}.C{i}.body_state.yaw"] = [f"{ctrl_name}.yaw"]
        connections[f"{car_name}.C{i}.body_state.groundspeed"] = [f"{ctrl_name}.groundSpeed"]
        
        # Controller to car inputs
        connections[f"{ctrl_name}.throttle"] = [f"{car_name}.C{i}.input.throttleInput"]
        connections[f"{ctrl_name}.brake"] = [f"{car_name}.C{i}.input.brakeInput"]
        connections[f"{ctrl_name}.steering"] = [f"{car_name}.C{i}.input.steeringInput"]
        
        # Controller acc_filtered to MEC acceleration
        connections[f"{ctrl_name}.acc_filtered"] = [f"{mec_prefix}_acceleration"]
        
        # MEC desired acceleration to Controller (except car 0 which uses Driver)
        if i > 0:
            connections[f"{mec_prefix}_des_acc"] = [f"{ctrl_name}.a_des"]
        
        # Socket parameters
        parameters[f"{car_name}.C{i}.socket.inPort"] = base_port + i * 2
        parameters[f"{car_name}.C{i}.socket.outPort"] = base_port + i * 2 + 1
    
    # Car 0 uses Driver
    connections["{Driver}.D0.u"] = ["{Controller}.ctrl0.a_des"]
    
    model = {
        "fmus": fmus,
        "connections": connections,
        "parameters": parameters
    }
    
    return model


def generate_v2v_model(num_cars, base_port):
    """Generate V2V model with CACC controllers"""
    
    fmus = {
        "{Controller}": "controller.fmu",
        "{Driver}": "driver.fmu"
    }
    
    # Add car FMUs
    for i in range(num_cars):
        fmus[f"{{Car{i}}}"] = "BeamNG-FMI2.fmu"
    
    # Add CACC FMUs (one per follower car)
    for i in range(1, num_cars):
        fmu_file = "caccpp.fmu" if i == 1 else "CACC.fmu"
        fmus[f"{{CACC{i}f}}"] = fmu_file
    
    connections = {}
    parameters = {}
    
    # Generate connections and parameters for each car
    for i in range(num_cars):
        car_name = f"{{Car{i}}}"
        ctrl_name = f"{{Controller}}.ctrl{i}"
        
        # Start with basic car body state to Controller connections
        car_connections = {
            "posX": [f"{ctrl_name}.posX"],
            "posY": [f"{ctrl_name}.posY"],
            "posZ": [f"{ctrl_name}.posZ"],
            "velX": [f"{ctrl_name}.velX"],
            "velY": [f"{ctrl_name}.velY"],
            "velZ": [f"{ctrl_name}.velZ"],
            "accX": [f"{ctrl_name}.accX"],
            "accY": [f"{ctrl_name}.accY"],
            "accZ": [f"{ctrl_name}.accZ"],
            "roll": [f"{ctrl_name}.roll"],
            "pitch": [f"{ctrl_name}.pitch"],
            "yaw": [f"{ctrl_name}.yaw"],
            "groundspeed": [f"{ctrl_name}.groundSpeed"]
        }
        
        # Add CACC connections based on vehicle role
        if i == 0:
            # Car 0 is the leader - feeds to all CACC controllers
            for j in range(1, num_cars):
                cacc_name = f"{{CACC{j}f}}.CACC{j}"
                car_connections["posX"].append(f"{cacc_name}.in_x_leader")
                car_connections["velX"].append(f"{cacc_name}.speed_leader")
            # Car 0 also feeds as preceding vehicle to Car 1's CACC
            if num_cars > 1:
                car_connections["posX"].append(f"{{CACC1f}}.CACC1.in_x_prec")
                car_connections["velX"].append(f"{{CACC1f}}.CACC1.speed_prec")
        elif i < num_cars - 1:
            # Middle cars: controlled by their CACC and preceding vehicle for next CACC
            cacc_name = f"{{CACC{i}f}}.CACC{i}"
            car_connections["posX"].append(f"{cacc_name}.in_x")
            car_connections["velX"].append(f"{cacc_name}.speed_me")
            
            next_cacc_name = f"{{CACC{i+1}f}}.CACC{i+1}"
            car_connections["posX"].append(f"{next_cacc_name}.in_x_prec")
            car_connections["velX"].append(f"{next_cacc_name}.speed_prec")
        else:
            # Last car: only controlled by its CACC
            cacc_name = f"{{CACC{i}f}}.CACC{i}"
            car_connections["posX"].append(f"{cacc_name}.in_x")
            car_connections["velX"].append(f"{cacc_name}.speed_me")
        
        # Add all car connections to main connections dict
        for signal, targets in car_connections.items():
            connections[f"{car_name}.C{i}.body_state.{signal}"] = targets
        
        # Controller to car inputs
        connections[f"{ctrl_name}.throttle"] = [f"{car_name}.C{i}.input.throttleInput"]
        connections[f"{ctrl_name}.brake"] = [f"{car_name}.C{i}.input.brakeInput"]
        connections[f"{ctrl_name}.steering"] = [f"{car_name}.C{i}.input.steeringInput"]
        
        # Controller acc_filtered to CACC controllers
        if i == 0 and num_cars > 1:
            # Car 0 acc_filtered feeds to all CACCs as leader/preceding
            acc_targets = []
            for j in range(1, num_cars):
                cacc_name = f"{{CACC{j}f}}.CACC{j}"
                acc_targets.append(f"{cacc_name}.acc_leader")
            # Car 0 also feeds as preceding to Car 1
            acc_targets.append(f"{{CACC1f}}.CACC1.acc_prec")
            connections[f"{ctrl_name}.acc_filtered"] = acc_targets
        elif i > 0 and i < num_cars - 1:
            # Middle cars feed as preceding to next CACC
            connections[f"{ctrl_name}.acc_filtered"] = [f"{{CACC{i+1}f}}.CACC{i+1}.acc_prec"]
        
        # CACC desired acceleration to Controller (followers only)
        if i > 0:
            connections[f"{{CACC{i}f}}.CACC{i}.accdes"] = [f"{ctrl_name}.a_des"]
            # CACC parameters
            parameters[f"{{CACC{i}f}}.CACC{i}.targetDistance"] = 10
        
        # Socket parameters
        parameters[f"{car_name}.C{i}.socket.inPort"] = base_port + i * 2
        parameters[f"{car_name}.C{i}.socket.outPort"] = base_port + i * 2 + 1
    
    # Car 0 uses Driver
    connections["{Driver}.D0.u"] = ["{Controller}.ctrl0.a_des"]
    
    model = {
        "fmus": fmus,
        "connections": connections,
        "parameters": parameters
    }
    
    return model


def main():
    parser = argparse.ArgumentParser(
        description='Generate FMU co-simulation JSON configuration for vehicle platoons',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('-n', '--num-cars', type=int, default=3,
                        help='Number of cars in the platoon')
    parser.add_argument('-t', '--type', choices=['V2N', 'V2V'], default='V2N',
                        help='Network type: V2N (MEC controller) or V2V (CACC controllers)')
    parser.add_argument('-p', '--base-port', type=int, default=12345,
                        help='Base UDP port number (i-th car use base_port + i*2 and base_port + i*2 + 1)')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='Output file path (default: stdout)')
    
    args = parser.parse_args()
    
    # Validate inputs
    if args.num_cars < 1:
        print("Error: Number of cars must be at least 1", file=sys.stderr)
        sys.exit(1)
    
    if args.type == 'V2N' and args.num_cars > 10:
        print("Error: V2N network type supports a maximum of 10 cars (MEC controller limitation)", file=sys.stderr)
        sys.exit(1)
    
    if args.base_port < 1024 or args.base_port > 65535 - args.num_cars * 2:
        print(f"Error: Base port must be between 1024 and {65535 - args.num_cars * 2}", file=sys.stderr)
        sys.exit(1)
    
    # Generate model
    if args.type == 'V2N':
        model = generate_v2n_model(args.num_cars, args.base_port)
    else:
        model = generate_v2v_model(args.num_cars, args.base_port)
    
    # Output JSON
    json_output = json.dumps(model, indent=4)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(json_output)
        print(f"Model written to {args.output}", file=sys.stderr)
    else:
        print(json_output)


if __name__ == "__main__":
    main()
