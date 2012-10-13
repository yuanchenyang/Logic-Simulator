import copy
import argparse
import os
import sys
import pickle
import graphics

parser = argparse.ArgumentParser(description='Toggle verbose mode')

parser.add_argument('--verbose', '-v', action='store_true')
arguments = parser.parse_args()

class Connector(object):
    def __init__(self, name = None, independent = False):
        self.name = name
        self.value = None
        self.informant = None
        self.constraints = []
        self.independent = independent

    def set_value(self, source, value):
        # if self.informant is independent, its values are independent of other 
        # connectors and can only be changed by the user.

        # Value can only be changed by user if its independent
        if (source != 'user' and not self.independent) or (source == 'user'
                                                           and self.independent):
            pass
        if True:
            global args
            self.informant, self.value = source, value
            if self.name is not None and arguments.verbose: 
                print(self.name, '=', value)
            self.inform_all_except(source, 'new_val')
        else:
            print('Cannot change:', self.value , 'vs', value)

    def forget(self, source):
        if self.informant is source:
            self.informant, self.value = None, None
            if self.name is not None:
                print(self.name, 'is forgetten')
            self.inform_all_except(source, 'forget')

    def inform_all_except(self, source, message):
        for c in self.constraints:
            if c != source:
                getattr(c, message)()
                
    def has_value(self):
        return self.value is not None

    def connect(self, source):
        self.constraints.append(source)

class Constraint(object):
    def __init__(self, values, operation):
        self.connectors = values
        self.operation = operation
        for c in self.connectors:
            c.connect(self)

    def new_val(self):
        pass

    def forget(self):
        for c in self.connectors:
            c.forget(self)

class Gate(Constraint):
    # A gate has a list of inputs and outputs and an operation
    
    def __init__(self, inputs, outputs, operation):    
        self.inputs = inputs
        self.outputs = outputs
        Constraint.__init__(self, inputs + outputs, operation)
        
    def new_val(self):
        #Last entry of self.connectors is the output
        assert len(self.inputs) > 0, \
            'Gate must have at least one input!'
        for c in self.inputs:
            if not c.has_value(): return
        values = [i.value for i in self.inputs]
        result = self.operation(*values)
        for i in range(len(result)):
            self.outputs[i].set_value(self, result[i])

class Chip(object):
    def __init__(self):
        self.chips = {}
        self.gates = []
        self.connected_pins = []
        self.in_name_counter = 0
        self.out_name_counter = 0
        self.make_starting_chips()
        self.click_positions = {}
    
    class MakeChip(object):
        def __init__(self, operation, len_inputs, len_outputs, name):
            self.name = name
            self.x = None
            self.y = None 
            self.len_inputs = len_inputs
            self.len_outputs = len_outputs
            self.inputs = [None for _ in range(len_inputs)]
            self.outputs = [None for _ in range(len_outputs)]
            self.operation = operation # for testing
            self.make_gate_function = lambda inputs, outputs: Gate(inputs,
                                                           outputs, operation)
        def draw(self, canvas):
            # x, y are the top left coordinates
            self.height = max(len(self.inputs), len(self.outputs)) * 15 
            self.width = 100
            canvas.draw_polygon(graphics.rectangle_points((self.x, self.y),
                        self.width, self.height), fill_color = None, filled = 0)
            canvas.draw_text(self.name, (self.x + 20, self.y))
            for i in range(len(self.inputs)):
                canvas.draw_text('i'+str(i), (self.x + 5, self.y + 15*i))

            for j in range(len(self.outputs)):
                canvas.draw_text('o' + str(j), (self.x + self.width - 20 ,
                                         self.y + 15*j))
        def click_position(self, position):
            # checks to see if the click lands on the object
            # returns: index, type
            x, y = position
            if x in range(self.x, self.x + self.width) \
                    and y in range(self.y, self.y + self.width):
                if x in range(self.x, self.x + 20):
                    # Clicks input
                    pos = int((y-self.y)/15)
                    if pos in range(self.len_inputs):
                        return pos, 0
                elif x in range(self.x + self.width - 20, self.x + self.width):
                    # Clicks output
                    pos = int((y-self.y)/15)
                    if pos in range(self.len_outputs):
                        return pos, 1
            return None, None
            

    def make_starting_chips(self):
        and_chip = lambda: self.MakeChip(lambda a, b: [a and b], 2, 1,
                                         'and_chip')
        or_chip = lambda: self.MakeChip(lambda a, b: [a or b], 2, 1, 'or_chip')
        not_chip = lambda: self.MakeChip(lambda a: [[1, 0][a]], 1, 1, 'not_chip')
        self.chips = locals()

    def simulate_chip(self, chip, inputs):
        # chip is an item in the chips dictionary
        return inputs, chip().operation(*inputs)
    
    def add_gate(self, gate, pos = None):
        if pos is not None:
            gate.x, gate.y = pos
        for i in range(gate.len_inputs):
            self.in_name_counter += 1
            c = Connector('in'+str(self.in_name_counter), True)
            gate.inputs[i] = c

        for i in range(gate.len_outputs):
            self.out_name_counter += 1
            c = Connector('out'+str(self.out_name_counter), True)
            gate.outputs[i] = c    
        self.gates.append(gate)
    
    def connect_gates(self, gate1, gate2):
        # format: gate1 = [gate, pin_no., pin_type]
        # pin_type: 0 is input, 1 is output
       
        if gate2[2] == 0:
            pin = gate2[0].inputs[gate2[1]]
        else:
            pin = gate2[0].outputs[gate2[1]]
            
        if gate1[2] == 0:
            gate1[0].inputs[gate1[1]] = pin
        else:
            gate1[0].outputs[gate1[1]] = pin

        if pin not in self.connected_pins:
            self.connected_pins.append(pin)

    def connect_out_in(self, output_gate, output_pin, input_gate, input_pin):
        pin = output_gate.outputs[output_pin]
        input_gate.inputs[input_pin] = pin
        
        if pin not in self.connected_pins:
            self.connected_pins.append(pin)

    def connect_in_in(self, in_gate1, in_pin1, in_gate2, in_pin2):
        pin = in_gate2.inputs[in_pin2]
        in_gate1.inputs[in_pin1] = pin

    def make_chip_from_gates(self, chip_name):
        if chip_name in self.chips:
            print('Name already used!!')
            return  
        f_gates = self.gates
        f_connected_pins = self.connected_pins
        inputs = []
        outputs = []
        for gate in f_gates:
            for i in gate.inputs:
                if i not in f_connected_pins:
                    if i not in inputs:
                        inputs.append(i)
            for i in gate.outputs:
                if i not in f_connected_pins:
                    if i not in outputs:
                        outputs.append(i)
            gate.make_gate_function(gate.inputs, gate.outputs)
        """
        print(inputs)
        print(outputs)
        print(f_connected_pins)
        print(len(outputs), len(inputs))
        """
        def func():        
            def operation(*input_list):
                for i in range(len(input_list)): 
                    inputs[i].set_value('chip', input_list[i])
                output_list = [output.value for output in outputs]
                return output_list
            return self.MakeChip(operation, len(inputs), len(outputs), chip_name)
        self.gates = []
        self.connected_pins = []
        self.in_name_counter = 0
        self.out_name_counter = 0
        self.chips[chip_name] = func
        
    def draw(self, canvas):
        counter = 0
        for chip_name, chip_object in self.chips.items():
            if chip_object is not self:
                canvas.draw_text(chip_name, (20, 20 + counter * 15))
                self.click_positions[chip_name] = (20, 15 + counter * 15)
                counter += 1
        
    def click_on_chip(self, pos):
        # returns the chip that is clicked, returns None if no chip is clicked
        x, y = pos
        for name, position in self.click_positions.items():
            xp, yp = position
            if x in range(xp, xp + 50) and y in range(yp + 5, yp + 20):
                return name
        return None
    
canvas = graphics.Canvas()
c = Chip()
selected_chip = None
add_chip = False

# [Position, [chip_name, index], type]
start_connect = []

lines = []

def draw_interface(canvas):
    global selected_chip, add_chip, start_connect
    canvas.draw_text('Selected Chip:', (150, 20))
    canvas.draw_text(selected_chip, (230, 20))
    canvas.draw_text('Deselect Chip', (150, 35))
    canvas.draw_text('Simulate Chip', (150, 50))
    canvas.draw_text('Remove Chip', (150, 65))
    canvas.draw_text('Add Gate', (300, 20))
    canvas.draw_text('Clear Selected Gate', (400, 20))
    canvas.draw_text('Create Chip', (520, 20))
    canvas.draw_text('Clear', (520, 40))
    canvas.draw_text('Save', (520, 60))
    canvas.draw_text('Load', (520, 80))
    if add_chip:
       canvas.draw_polygon(graphics.rectangle_points((300-3, 20-3), 56 , 21), filled = 0)
    elif start_connect != []:
        x , y = start_connect[0]
        canvas.draw_polygon(graphics.rectangle_points((x-7, y-7), 14, 14)
                            , filled = 0)
        
def check_buttons(pos):
    x, y = pos
    if x in range(150, 220) and y in range(30, 45):
        return 'deselect'
    elif x in range(150, 220) and y in range(45, 60):
        return 'simulate'
    elif x in range(150, 220) and y in range(60, 75):
        return 'remove'
    elif x in range(300, 400) and y in range(15, 30):
        return 'add'
    elif x in range(400, 500) and y in range(15, 30):
        return 'clear_select'
    elif x in range(520, 570) and y in range(15, 30):
        return 'chip'
    elif x in range(520, 570) and y in range(35, 50):
        return 'clear'
    elif x in range(520, 570) and y in range(55, 70):
        return 'save'
    elif x in range(520, 570) and y in range(75, 90):
        return 'load'
    
    return None
    
while True:
    canvas.clear()
    draw_interface(canvas)
    for gate in c.gates:
        gate.draw(canvas)
    c.draw(canvas)
    for line in lines:
        canvas.draw_polygon(line)
    pos, _ = canvas.wait_for_click()
    pressed_chip = c.click_on_chip(pos)
    pressed_button = check_buttons(pos)
    #print(pos)

    for gate in c.gates:
        index, t = gate.click_position(pos)
        if index is not None:
            if start_connect != []:
                pos1 = start_connect[0]
                args1 = start_connect[1]
                type1 = start_connect[2]
                pos2 = pos
                args2 = [gate, index]
                type2 = t
                args = args1 + args2
                if type1 == 0 and type2 == 0:
                    c.connect_in_in(*args)
                else:
                    c.connect_out_in(*args)
                lines.append([pos1, pos2])
                start_connect = []
            else:
                start_connect = [pos, [gate, index], t]
            
    
    if pressed_chip is not None:
        selected_chip = pressed_chip
    elif pressed_button is not None:
        if pressed_button == 'deselect':
            selected_chip = None
        elif pressed_button == 'add':
            add_chip = not add_chip
            continue
        elif pressed_button == 'clear_select':
            start_connect = []
        elif pressed_button == 'chip':
            name = input('Please enter a name for your chip: ')
            c.make_chip_from_gates(name)
            selected_chip = None
            add_chip = False
            start_connect = []
            lines = []
        elif pressed_button == 'remove' and selected_chip is not None:
            _ = c.chips.pop(selected_chip)
            selected_chip = None
            add_chip = False
        elif pressed_button == 'clear':
            c.gates = []
            c.connected_pins = []
            c.in_name_counter = 0
            c.out_name_counter = 0
            selected_chip = None
            add_chip = False
            start_connect = []
            lines = []
        elif pressed_button == 'simulate' and selected_chip is not None:
            inputs = list(eval(input("Please specify the input pins: ")))
            print(inputs, selected_chip)
            print(c.simulate_chip(c.chips[selected_chip], inputs))


    if selected_chip is not None and add_chip:
        c.add_gate(c.chips[selected_chip](), pos)
        add_chip = False
            




"""
c = Chip()

#########
#  XOR  #
#########

c.add_gate(c.chips['and_chip']())
c.add_gate(c.chips['and_chip']())
c.add_gate(c.chips['not_chip']())
c.add_gate(c.chips['not_chip']())
c.add_gate(c.chips['or_chip']())

ag1 = c.gates[0]
ag2 = c.gates[1]
ng1 = c.gates[2]
ng2 = c.gates[3]
og1 = c.gates[4]

c.connect_out_in(ng1, 0, ag1, 0)
c.connect_out_in(ng2, 0, ag2, 1)
c.connect_out_in(ag1, 0, og1, 0)
c.connect_out_in(ag2, 0, og1, 1)

c.connect_in_in(ag1, 1, ng2, 0)
c.connect_in_in(ag2, 0, ng1, 0)

c.make_chip_from_gates('xor')

c.simulate_chip(c.chips['xor'], [0,0])
c.simulate_chip(c.chips['xor'], [1,0])
c.simulate_chip(c.chips['xor'], [0,1])
c.simulate_chip(c.chips['xor'], [1,1])
"""

"""
#########
#HALFADD#
#########

c.add_gate(c.chips['xor']())
c.add_gate(c.chips['and_chip']())

ag = c.gates[1]
xg = c.gates[0]

c.connect_in_in(ag, 0, xg, 0)
c.connect_in_in(ag, 1, xg, 1)

c.make_chip_from_gates('half_adder')
# returns [sum, carry]

#c.simulate_chip(c.chips['half_adder'], [0,0])
#c.simulate_chip(c.chips['half_adder'], [0,1])
#c.simulate_chip(c.chips['half_adder'], [1,0])
#c.simulate_chip(c.chips['half_adder'], [1,1])

#########
#FULLADD#
#########

c.add_gate(c.chips['and_chip']())
c.add_gate(c.chips['and_chip']())
c.add_gate(c.chips['xor']())
c.add_gate(c.chips['xor']())
c.add_gate(c.chips['or_chip']())

ag1 = c.gates[0]
ag2 = c.gates[1]
xg1 = c.gates[2]
xg2 = c.gates[3]
og1 = c.gates[4]

c.connect_out_in(xg1, 0, xg2, 0)
c.connect_out_in(xg1, 0, ag1, 0)
c.connect_out_in(ag1, 0, og1, 0)
c.connect_out_in(ag2, 0, og1, 1)

c.connect_in_in(ag2, 1, xg1, 1)
c.connect_in_in(ag2, 0, xg1, 0)
c.connect_in_in(ag1, 1, xg2, 1)

c.make_chip_from_gates('full_adder')
# returns [sum, carry]

#c.simulate_chip(c.chips['full_adder'], [0,0,0])
#c.simulate_chip(c.chips['full_adder'], [0,0,1])
#c.simulate_chip(c.chips['full_adder'], [0,1,0])
#c.simulate_chip(c.chips['full_adder'], [0,1,1])
#c.simulate_chip(c.chips['full_adder'], [1,0,0])
#c.simulate_chip(c.chips['full_adder'], [1,0,1])
#c.simulate_chip(c.chips['full_adder'], [1,1,0])
#c.simulate_chip(c.chips['full_adder'], [1,1,1])

#########
#8BITADD#
#########

c.add_gate(c.chips['half_adder']())
for _ in range(7):
    c.add_gate(c.chips['full_adder']())

a = [c.gates[i] for i in range(8)]

for n in range(7):
    c.connect_out_in(a[n], 1, a[n+1], 0)

c.make_chip_from_gates('8-bit_adder')

combine_2_lists = lambda a, b: [(a, b)[i][j] for j in range(len(a))
                                             for i in (0, 1) ]

def list_to_bin(l):
    s = 0
    for i in range(len(l)):
        s += l[i] * pow(2, i)
    return s
l1 = [1,1,0,1,1,1,0,1]
l2 = [1,0,1,1,0,1,1,1]

_, answer = c.simulate_chip(c.chips['8-bit_adder'], combine_2_lists(l1, l2))
                            
print(list_to_bin(l1), '+', list_to_bin(l2), '=', list_to_bin(answer))
"""


"""
c.add_gate(c.chips['and_chip']())
c.add_gate(c.chips['and_chip']())
c.add_gate(c.chips['not_chip']())
ag1 = c.gates[0]
ag2 = c.gates[1]
ng = c.gates[2]
c.connect_gates([ag1, 0, 1], [ag2, 0, 0])
c.connect_gates([ag2, 0, 1], [ng, 0, 0])
c.make_chip_from_gates('triple_nand')


c.add_gate(c.chips['triple_nand']())
c.add_gate(c.chips['triple_nand']())

ta1 = c.gates[0]
ta2 = c.gates[1]

c.connect_gates([ta1, 0, 1], [ta2, 0, 0])
c.make_chip_from_gates('double_triple_nand')
c.simulate_chip(c.chips['double_triple_nand'], [1, 1, 0, 1, 1])
"""

"""

    a = Connector('A', True)
    b = Connector('B', True)
    c = Connector('C', True)
    
    i = Connector('i')
    o = Connector('O')
    out = Connector('out')

    f = Connector('f')
    
    and_gate([a, b], [i])
    and_gate([i, c], [o])
    not_gate([o], [out])
    
    a.set_value('user', False)
    b.set_value('user', True)
    a.set_value('user', True)
    c.set_value('user', True)

class UnaryGate(Constraint):
    def new_val(self):
        try:
            a, b = self.connectors
            ab = self.operation
        except:
            print('Incorrect usage: UnaryGate([a, b], ab)')

        if a.has_value():
            b.set_value(self, ab(a.value))


class BinaryGate(Constraint):
    def new_val(self):
        try:
            a, b, c = self.connectors
            abc = self.operation
        except:
            print('Incorrect usage: BinaryGate([a, b, c], abc)')
        
        if a.has_value() and b.has_value():
            c.set_value(self, abc(a.value, b.value))

def and_gate(a, b, c):
    return BinaryGate([a, b, c], lambda a, b: a and b)

def not_gate(a, b):
    return UnaryGate([a, b], lambda a: not a)
"""

"""
class TernaryConstraint(Constraint):
    def new_val(self):
        try:
            a, b, c = self.connectors
            ab, ca, cb = self.operations
        except:
            print('Incorrect usage: TernaryConstraint([a, b, c], [ab, ca, cb])')
        av, bv, cv = [connector.has_value() for connector in self.connectors]
        if av and bv:
            c.set_value(self, ab(a.value, b.value))
        elif av and cv:
            b.set_value(self, ca(c.value, a.value))
        elif bv and cv:
            a.set_value(self, cb(c.value, b.value))
            
def addern(a, b, c):
    from operator import add, sub
    return TernaryConstraint([a, b, c], [add, sub, sub])

def multipliern(a, b, c):
    from operator import mul, truediv
    return TernaryConstraint([a, b, c], [mul, truediv, truediv])

def constantn(connector, value):
    connector.set_value(Constraint([], []), value)

def converter_new(c, f):
    #Connect c to f to convert from Celsius to Fahrenheit.
    u, v, w, x, y = [Connector() for _ in range(5)]
    multipliern(c, w, u)
    multipliern(v, x, u)
    addern(v, y, f)
    constantn(w, 9)
    constantn(x, 5)
    constantn(y, 32)

"""
"""
                new_gate = copy.deepcopy(gate)
                for i in range(len(gate.inputs)):
                    if gate.inputs[i] not in f_connected_pins:
                        new_gate.inputs[i] = copy.deepcopy(gate.inputs[i])
                        inputs.append(new_gate.inputs[i])
                    else:
                        new_gate.inputs[i] = copy.deepcopy(gate.inputs[i])
                        
                for o in range(len(gate.outputs)):
                    if gate.outputs[o] not in f_connected_pins:
                        new_gate.outputs[o] = copy.deepcopy(gate.outputs[o])
                        outputs.append(new_gate.outputs[o])
                    else:
                        new_gate.outputs[o] = copy.deepcopy(gate.outputs[o])

                new_gate.make_gate_function(new_gate.inputs, new_gate.outputs)
"""
