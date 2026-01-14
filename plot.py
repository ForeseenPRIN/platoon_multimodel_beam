import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import argparse

class AnimatedPlot:
    def __init__(self, csv_file, num_cars, use_mec=False):
        """
        Initialize animated plot for vehicle simulation data.
        
        Args:
            csv_file: Path to CSV file with simulation data
            num_cars: Number of cars in the simulation
            use_mec: If True, use MEC controller column names, otherwise use CACC
        """
        self.csv_file = csv_file
        self.num_cars = num_cars
        self.use_mec = use_mec
        
        # Color scheme for vehicles
        self.colors = [
            'red', 'blue', 'green', 'orange', 'purple', 
            'cyan', 'magenta', 'brown', 'pink', 'gray'
        ]
        self.linestyles = ['-', '--', '-.', ':', '-', '--', '-.', ':', '-', '--']
        
        # Create figure with 6 subplots (3x2 grid)
        self.fig, self.axes = plt.subplots(3, 2, figsize=(14, 10))
        self.axes = self.axes.flatten()
        
        self.subplot_titles = [
            'Throttle', 'Brake', 'Acceleration', 
            'Inter-vehicular Distance', 'Speed', 'Desired Acceleration Input'
        ]
        
        # Initialize line storage: lines[subplot_idx][car_idx]
        self.lines = [[] for _ in range(6)]
        
        self._setup_subplots()
        plt.tight_layout()
        
    def _setup_subplots(self):
        """Setup all subplots with proper labels and legends"""
        for i, title in enumerate(self.subplot_titles):
            self.axes[i].set_xlabel('Time (s)')
            self.axes[i].set_ylabel(title)
            self.axes[i].set_title(title)
            self.axes[i].grid(True)
            
            if i < 3:  # Throttle, Brake, Acceleration
                for car_idx in range(self.num_cars):
                    line, = self.axes[i].plot(
                        [], [], 
                        color=self.colors[car_idx % len(self.colors)],
                        linestyle=self.linestyles[car_idx % len(self.linestyles)],
                        label=f'Car {car_idx}',
                        linewidth=2
                    )
                    self.lines[i].append(line)
            elif i == 3:  # Inter-vehicular distance
                for car_idx in range(self.num_cars - 1):
                    line, = self.axes[i].plot(
                        [], [],
                        color=self.colors[car_idx % len(self.colors)],
                        linestyle=self.linestyles[car_idx % len(self.linestyles)],
                        label=f'Car {car_idx}-{car_idx+1}',
                        linewidth=2
                    )
                    self.lines[i].append(line)
            elif i == 4:  # Speed
                for car_idx in range(self.num_cars):
                    line, = self.axes[i].plot(
                        [], [],
                        color=self.colors[car_idx % len(self.colors)],
                        linestyle=self.linestyles[car_idx % len(self.linestyles)],
                        label=f'Car {car_idx}',
                        linewidth=2
                    )
                    self.lines[i].append(line)
            else:  # Desired Acceleration Input
                for car_idx in range(self.num_cars):
                    line, = self.axes[i].plot(
                        [], [],
                        color=self.colors[car_idx % len(self.colors)],
                        linestyle=self.linestyles[car_idx % len(self.linestyles)],
                        label=f'Car {car_idx}',
                        linewidth=2
                    )
                    self.lines[i].append(line)
            
            self.axes[i].legend()
    
    def _read_data(self):
        """Read CSV file and extract data for all cars"""
        try:
            df = pd.read_csv(self.csv_file)
            time_data = df['time']
            
            # Extract data for each car
            throttle = []
            brake = []
            acceleration = []
            speed = []
            position = []
            desired_acc = []
            
            for i in range(self.num_cars):
                throttle.append(df[f'{{Controller}}.ctrl{i}.throttle'])
                brake.append(df[f'{{Controller}}.ctrl{i}.brake'])
                speed.append(df[f'{{Car{i}}}.C{i}.body_state.groundspeed'])
                position.append(df[f'{{Car{i}}}.C{i}.body_state.posX'])
                
                # Acceleration: use acc_filtered for all cars
                acceleration.append(df[f'{{Controller}}.ctrl{i}.acc_filtered'])
                
                # Desired acceleration input
                if i == 0:
                    desired_acc.append(df['{Driver}.D0.u'])
                else:
                    if self.use_mec:
                        desired_acc.append(df[f'{{MEC}}.MEC0.platoon_0_{i}_des_acc'])
                    else:
                        desired_acc.append(df[f'{{CACC{i}f}}.CACC{i}.accdes'])
            
            # Calculate inter-vehicular distances
            distances = []
            for i in range(self.num_cars - 1):
                distances.append(np.array(position[i]) - np.array(position[i + 1]))
            
            return time_data, throttle, brake, acceleration, distances, speed, desired_acc
            
        except (FileNotFoundError, pd.errors.EmptyDataError, KeyError) as e:
            print(f"Error reading {self.csv_file}: {e}")
            return None, None, None, None, None, None, None
    
    def animate(self, frame):
        """Animation function called periodically to update all plots"""
        result = self._read_data()
        
        if result[0] is None:
            return []
        
        time_data, throttle, brake, acceleration, distances, speed, desired_acc = result
        
        # Update throttle (subplot 0)
        for i, line in enumerate(self.lines[0]):
            line.set_data(time_data, throttle[i])
        
        # Update brake (subplot 1)
        for i, line in enumerate(self.lines[1]):
            line.set_data(time_data, brake[i])
        
        # Update acceleration (subplot 2)
        for i, line in enumerate(self.lines[2]):
            line.set_data(time_data, acceleration[i])
        
        # Update inter-vehicular distance (subplot 3)
        for i, line in enumerate(self.lines[3]):
            line.set_data(time_data, distances[i])
        
        # Update speed (subplot 4)
        for i, line in enumerate(self.lines[4]):
            line.set_data(time_data, speed[i])
        
        # Update desired acceleration input (subplot 5)
        for i, line in enumerate(self.lines[5]):
            line.set_data(time_data, desired_acc[i])
        
        # Adjust plot limits for each subplot
        for ax in self.axes:
            ax.relim()
            ax.autoscale_view()
        
        # Return all lines
        all_lines = []
        for subplot_lines in self.lines:
            all_lines.extend(subplot_lines)
        return all_lines


def main():
    parser = argparse.ArgumentParser(description='Plot vehicle simulation data')
    parser.add_argument('--csv', type=str, default='outputs.csv', 
                        help='Path to the CSV file to read (default: outputs.csv)')
    parser.add_argument('-n', '--num-cars', type=int, default=3,
                        help='Number of cars in the simulation (default: 3)')
    parser.add_argument('--mec', action='store_true', 
                        help='Use MEC FMU column names instead of CACC')
    args = parser.parse_args()
    
    # Validate inputs
    if args.num_cars < 1:
        print("Error: Number of cars must be at least 1")
        return
    
    # Initialize the animated plot
    plotter = AnimatedPlot(args.csv, args.num_cars, args.mec)
    
    # Set up animation
    ani = animation.FuncAnimation(
        plotter.fig,
        plotter.animate,
        interval=250,
        blit=False,
        cache_frame_data=False
    )
    
    plt.suptitle(f'Vehicle Control and State Signals - {args.num_cars} Cars - Real-time Data', 
                 fontsize=16, y=0.995)
    plt.show()


if __name__ == '__main__':
    main()
