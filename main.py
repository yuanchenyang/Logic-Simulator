import graphics
import chip
import os
import sys
import pickle

from itertools import product

class Button(object):
    def __init__(self, name, pos, width, height, action):
        self.name = name
        self.x, self.y, = pos
        self.width = width
        self.height = height
        self.action = action
    def draw(self, canvas):
        canvas.draw_text(self.name, (self.x, self.y))
    def do_action_if_clicked(self, pos, parameters):
        px, py = pos
        if px in range(self.x, self.x + self.width - 5) and \
           py in range(self.y, self.y + self.height):
            self.action(parameters)

class Parameters(object):
    def __init__(self, c):
        self.chip = c
        self.reset()
    def reset(self):
        self.lines = []
        # [Position, [chip_name, index], type]
        self.start_connect = []
        self.add_chip = False
        self.selected_chip = None
        self.selected_remove_gate = False
        
def deselect_chip(parameters):
    parameters.selected_chip = None

def add_gate(parameters):
    parameters.add_chip = not parameters.add_chip

def remove_gate(parameters):
    parameters.selected_remove_gate = not parameters.selected_remove_gate

def clear_select(parameters):
    parameters.start_connect = []

def make_chip(parameters):
    name = input('Please enter a name for your chip: ')
    parameters.chip.make_chip_from_gates(name)
    parameters.reset()

def remove_chip(parameters):
    if parameters.selected_chip:
        _ = parameters.chip.chips.pop(parameters.selected_chip)
        parameters.selected_chip = None
        parameters.add_chip = False

def clear(parameters):
    parameters.reset()
    parameters.chip.reset()

def simulate(parameters):
    if parameters.selected_chip:
        run_chip = lambda inputs: parameters.chip.simulate_chip(
                parameters.chip.chips[parameters.selected_chip], inputs)
        inputs = input("Please specify the input pins: ")
        if inputs != 'all':
            inputs = list(eval(inputs))
            combinations = [inputs]
        else:
            num_inputs = parameters.chip.chips[parameters.selected_chip
                                               ]().len_inputs
            if num_inputs > 5:
                return 'Too many inputs to simulate simultaneously'
            args = [[1, 0] for _ in range(num_inputs)]
            combinations = list(product(*args))
        print(inputs, parameters.selected_chip)
        for comb in combinations:
            run_chip(comb)

def save(parameters):
    save_file_name = input('Please enter a file name to save to:')
    pickle.dump(parameters.chip.chips, open(save_file_name, 'wb'))

def load(parameters):
    load_file_name = input('Please enter a file name to load from:')
    if os.path.isfile(load_file_name):
        parameters.chip.chips = pickle.load(open(load_file_name, 'rb'))

buttons = [Button('Deselect Chip', (150, 35), 70, 15, deselect_chip),
           Button('Simulate Chip', (150, 50), 70, 15, simulate),
           Button('Remove Chip', (150, 65), 70, 15, remove_chip),
           Button('Add Gate', (300, 20), 100, 15, add_gate),
           Button('Clear Selected Gate', (400, 20), 100, 15, clear_select),
           Button('Create Chip', (520, 20), 70, 15, make_chip),
           Button('Clear', (520, 40), 70, 15, clear),
           Button('Remove Gate', (520, 60), 70, 15, remove_gate),
           # Does not work
           # Button('Save', (520, 80), 70, 15, save),
           # Button('Load', (520, 100), 70, 15, load)
           ]
            
def draw_interface(canvas):
    global buttons
    canvas.draw_text('Selected Chip:', (150, 20))
    for b in buttons:
        b.draw(canvas)

def update_interface(canvas, parameters):
    for gate in parameters.chip.gates:
        gate.draw(canvas)
    parameters.chip.draw(canvas)
    canvas.draw_text(parameters.selected_chip, (230, 20))
    for line in parameters.lines:
        canvas.draw_polygon(line)
    if parameters.add_chip:
       canvas.draw_polygon(graphics.rectangle_points((300-3, 20-3), 56 , 21), filled = 0)
    elif parameters.selected_remove_gate:
       canvas.draw_polygon(graphics.rectangle_points((520-3, 60-3), 76 , 21), filled = 0)
    elif parameters.start_connect != []:
        x , y = parameters.start_connect[0]
        canvas.draw_polygon(graphics.rectangle_points((x-7, y-7), 14, 14)
                            , filled = 0)

canvas = graphics.Canvas(width = 600, height = 768)
parameters = Parameters(chip.Chip())

while True:
    canvas.clear()
    draw_interface(canvas)
    update_interface(canvas, parameters)
    pos, _ = canvas.wait_for_click()
    pressed_chip = parameters.chip.click_on_chip(pos)
    #print(pos)
        
    for gate in parameters.chip.gates:
        index, t = gate.click_position(pos)
        if index is not None:
            if parameters.start_connect != []:
                pos1 = parameters.start_connect[0]
                args1 = parameters.start_connect[1]
                pos2 = pos
                args2 = [gate, index, t]
                cant_connect = parameters.chip.connect_gates(args1, args2)
                if cant_connect is None:
                    parameters.lines.append([pos1, pos2])
                    parameters.start_connect = []
            else:
                parameters.start_connect = [pos, [gate, index, t]] 
    
    if pressed_chip is not None:
        parameters.selected_chip = pressed_chip

    if parameters.selected_chip is not None and parameters.add_chip:
        parameters.chip.add_gate(parameters.chip.chips[
                parameters.selected_chip](), pos)
        parameters.add_chip = False

    if parameters.selected_remove_gate:
        for gate in parameters.chip.gates:
            if gate.click_on_gate(pos):
                parameters.chip.gates.remove(gate)
                def remove_pin(pin, chip):
                    if i in chip.connected_pins:
                        chip.connected_pins.remove(i)
                for i in gate.inputs:
                    remove_pin(i, parameters.chip)
                for i in gate.outputs:
                    remove_pin(i, parameters.chip)
                parameters.selected_remove_gate = False

    for b in buttons:
        b.do_action_if_clicked(pos, parameters)
            





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
