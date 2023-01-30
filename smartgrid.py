# Thomas, Karel, Joris

from __future__ import annotations
import mesa
from typing import Union, Optional
import csv
from operator import attrgetter
from Agents.cable import Cable
from Agents.house import House
from Agents.battery import Battery
import json
        

class SmartGrid(mesa.Model):
    def __init__(self, district: int) -> None:
        # objects
        self.houses: list[House] = self.add_objects(district, 'houses')
        self.batteries: list[House] = self.add_objects(district, 'batteries')
        self.cables: list[Cable] = []
        self.district = district
        self.information = []

        # total numher of cable
        self.num_cables = 0

        width, height = self.bound()
        self.grid: mesa.space = mesa.space.MultiGrid(width + 1,
                                                     height + 1, False)

        # add houses to grid
        for i in self.houses:
            self.grid.place_agent(i, (i.x, i.y))

        # # add batteries to grid
        for i in self.batteries:
            self.grid.place_agent(i, (i.x, i.y))

        # order placement
        self.placement_order()

        # add cables to grid
        self.link_houses()
        self.lay_cable()
        
        # get representation info
        self.get_information()

    def bound(self) -> tuple[int, int]:
        """
        This function generates the boundaries of the grid

        Returns:
            tuple[int, int]: the maximum x and y values for the grid
        """

        # find the maximum x and y values of the houses and battery lists
        max_x = max([max(self.houses, key=attrgetter('x'))] +
                    [max(self.batteries, key=attrgetter('x'))],
                    key=attrgetter('x'))
        max_y = max([max(self.houses, key=attrgetter('y'))] +
                    [max(self.batteries, key=attrgetter('y'))],
                    key=attrgetter('y'))

        return (max_x.x, max_y.y)

    def placement_order(self) -> None:
        """
        This function finds the order in which the houses get
        their battery assigned and sort the house list
        """

        for house in self.houses:
            # list of distances to all the batteries
            dist_batteries = []
            for battery in self.batteries:
                # add distance to list
                dist_batteries.append(house.distance(battery))

            # sort the list in ascending order
            dist_batteries.sort()

            # assign priority value to house
            house.priority = dist_batteries[1] - dist_batteries[0]

        # sort houses based on priority
        self.houses.sort(key=lambda x: x.priority, reverse=True)

    def link_houses(self) -> None:
        """
        This function finds the two closest batteries with enough capacity
        for every house and assigns the house to that battery
        """

        # find closest battery for every house
        for house in self.houses:
            # smallest distance to a battery
            min_dist = -1.0
            
            # index battery
            index = 0
            
            # best battery index for the house
            best_index = 0
            
            for battery in self.batteries:
                # distance to battery
                dist = house.distance(battery)

                # if the first battery, make it the smallest distance and connect
                if min_dist == -1 and house.check_connection(battery):
                    min_dist = dist
                    best_index = index
                # if distance to new battery is smaller than minimum, update
                elif min_dist > dist and house.check_connection(battery):
                    min_dist = dist
                    best_index = index
                    
                index += 1
            house.connect(self.batteries[best_index])
            self.batteries[best_index].houses.append(house)
                    
    def lay_cable(self) -> None:
        """
        This function connects the houses with the batteries by placing cables
        """

        # unique id for cables
        cable_id = 1000

        # create and place the cables for every house
        for house in self.houses:
            # cable list per house
            cable_list = []

            # x and y coordinate of the connected battery
            battery = house.connection

            # order the x and y values s.t. the cables can be laid
            small_x, big_x = min([house.x, battery.x]), max([house.x, battery.x])
            small_y, big_y = min([house.y, battery.y]), max([house.y, battery.y])

            beginHouse = True

            if house.y < battery.y:
                from_y, from_x = house.y, house.x
                to_x, to_y = battery.x, battery.y
            else:
                from_y, from_x = battery.y, battery.x
                to_x, to_y = house.x, house.y
                beginHouse = False

            i = 0

    	    
            battery_block = True
            break_out_flag = False

            while battery_block == True:
                # no battery block found yet
                battery_block = False
                
                # make the path
                y1 = [(from_x, from_y + j) for j in range(i)]
                x1 = [(j, from_y + i) for j in range(small_x, big_x + 1)]
                y2 = [(to_x, j) for j in range(from_y + i, to_y + 1)]
                # remove the house and battery location
                if i > 0:
                    y1.pop(0)
                
                if len(y2) > 0:
                    y2.pop()

                # merge locations in one list
                if beginHouse:
                    cor_arr = list(set((y1 + x1 + y2)))
                else:
                    y2.reverse()
                    cor_arr = list(set((y2 + x1 + y1)))

                # get all contents of the grid of the locations
                content = self.grid.get_cell_list_contents(cor_arr)
                
                # check if not destination battery
                for bat in self.batteries:
                    if bat in content and not (bat.x == battery.x and bat.y == battery.y):
                        battery_block = True
                        i += 1

            cable_id = 0
            for cor in cor_arr:
                self.add_cable(cor[0], cor[1], house, cable_id)
                # update cable id
                cable_id += 1
            
    def add_cable(self, x, y, house, cable_id):
        new_cable = Cable(cable_id, self, x, y, 0)
        house.add_cable(new_cable)

        # update number of cables
        self.num_cables += 1

        # place cable in the grid
        self.grid.place_agent(new_cable, (x, y))

    def costs(self) -> int:
        """
        This function calculates the total costs for the cables and batteries

        Returns:
            int: total costs
        """

        cable_cost = self.num_cables * 9
        battery_cost = 5000 * len(self.batteries)

        return cable_cost + battery_cost
    
    def get_information(self) -> None:
        """
        This function creates the representation of the data
        """
        
        # dictionary for general information
        dct = {}
        dct["district"] = self.district
        dct["costs-shared"] = self.costs()
        
        # add general information to information list
        self.information.append(dct)
        
        # for every battery make a dictionary with its information
        for battery in self.batteries:
            # dictionary of battery
            dct = {}
            dct["location"] = str(battery.x) + "," + str(battery.y)
            dct["capacity"] = battery.capacity
            dct["houses"] = []
            
            # for every house make a dictionary with its information
            for house in battery.houses:
                # dictionary for house
                dct_house = {}
                dct_house["location"] = str(house.x) + "," + str(house.y)
                dct_house["output"] = house.energy
                dct_house["cables"] = []
                
                # add location of all cables connected to houses
                # in the dictionary of information houses
                for cable in house.cables:
                    dct_house["cables"].append(str(cable.x) + "," + str(cable.y))
                dct["houses"].append(dct_house)
            
            # add all information to self.information
            self.information.append(dct)
        
    def add_objects(self, district: int, info: str) ->Union[list[House], list[Battery]]:
        """
        Add houses or battery list of district depending on 'info'

        Args:
            district (int): district number
            info (str): 'houses' or 'batteries'

        Returns:
            Union[list[House], list[Battery]]: a list with all the houses or batteries
        """

        # path to data
        path = 'Huizen&Batterijen/district_' + str(district) + '/district-' + str(district) + '_' +  info + '.csv'

        # list with the information
        lst = []

        # add the information to the list
        with open(path, 'r') as csv_file:
            data = csv.reader(csv_file)

            # index to skip header
            count = 0

            # go through all rows except the first
            for line in data:
                # skip header
                if count == 0:
                    count += 1
                    continue

                # convert the data to a neat list with floats
                if not line[0].isnumeric():
                    neat_data = line[0].split(',')
                    line = neat_data + [line[1]]

                # information
                x = int(line[0])
                y = int(line[1])
                energy = float(line[2])

                # append a house or Battery
                if info == 'houses':
                    lst.append(House(count, self, x, y, energy))
                else:
                    lst.append(Battery(count, self, x, y, energy))

                count += 1

        return lst

if __name__ == "__main__":
    test_wijk_1 = SmartGrid(1)
    print(test_wijk_1.costs())
    with open("district1.json", "w") as outfile:
        json.dump(test_wijk_1.information, outfile)

    test_wijk_2 = SmartGrid(2)
    print(test_wijk_2.costs())
    with open("district2.json", "w") as outfile:
        json.dump(test_wijk_2.information, outfile)

    test_wijk_3 = SmartGrid(3)
    print(test_wijk_3.costs())
    with open("district3.json", "w") as outfile:
        json.dump(test_wijk_3.information, outfile)
    
    
